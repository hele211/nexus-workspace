"""
Nexus Workspace Backend - FastAPI Application.

Main entry point for the lab workspace AI agent system.
Implements LiteratureAgent and BlockchainAgent with intent routing.

Run with:
    uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx

from backend import config
from backend.agents.literature_agent import LiteratureAgent
from backend.agents.blockchain_agent import BlockchainAgent
from backend.agents.reagent_agent import ReagentAgent
from backend.agents.protocol_agent import ProtocolAgent
from backend.agents.experiment_agent import ExperimentAgent
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services import get_blockchain_service, USE_MOCK_BLOCKCHAIN


# =============================================================================
# Logging Configuration
# =============================================================================

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if config.BLOCKCHAIN_AGENT_DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("nexus.api")
blockchain_logger = logging.getLogger("nexus.blockchain")

# Set blockchain logger level based on debug flag
if config.BLOCKCHAIN_AGENT_DEBUG:
    blockchain_logger.setLevel(logging.DEBUG)
else:
    blockchain_logger.setLevel(logging.INFO)


def log_blockchain_action(
    action: str,
    tool_name: str,
    success: bool,
    experiment_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Log blockchain-related actions with structured data.
    
    Args:
        action: Description of the action (e.g., "store_experiment", "verify_integrity")
        tool_name: Name of the tool used
        success: Whether the action succeeded
        experiment_id: Experiment ID if applicable
        tx_hash: Transaction hash if applicable
        error: Error message if failed
        extra: Additional context data
    """
    service = get_blockchain_service()
    info = service.get_network_info()
    
    log_data = {
        "action": action,
        "agent": "blockchain_agent",
        "tool": tool_name,
        "success": success,
        "network": info.get("network", "unknown"),
        "chain_id": info.get("chain_id", "unknown"),
        "mock_mode": USE_MOCK_BLOCKCHAIN,
    }
    
    if experiment_id:
        log_data["experiment_id"] = experiment_id
    if tx_hash:
        log_data["tx_hash"] = tx_hash
    if error:
        log_data["error"] = error
    if extra:
        log_data.update(extra)
    
    # Format as structured log message
    log_msg = " | ".join(f"{k}={v}" for k, v in log_data.items())
    
    if success:
        blockchain_logger.info(log_msg)
    else:
        blockchain_logger.error(log_msg)
    
    # Debug mode: log full details
    if config.BLOCKCHAIN_AGENT_DEBUG:
        blockchain_logger.debug(f"Full log data: {log_data}")


# =============================================================================
# Intent Router
# =============================================================================

# Keywords for blockchain-related queries
BLOCKCHAIN_KEYWORDS = [
    r"\bblockchain\b",
    r"\bneo\s*x\b",
    r"\bon[- ]?chain\b",
    r"\btransaction\s*hash\b",
    r"\btx\s*hash\b",
    r"\bexperiment\s*integrity\b",
    r"\bprovenance\b",
    r"\bverify\s*(data|experiment|integrity)\b",
    r"\bstore\s*(on|to)\s*(blockchain|chain)\b",
    r"\bnotarize\b",
    r"\btamper(ing|ed)?\b",
    r"\bimmutable\b",
    r"\bgas\s*balance\b",
    r"\bwallet\s*(address|balance)\b",
]

# Keywords for literature-related queries
LITERATURE_KEYWORDS = [
    r"\bpaper(s)?\b",
    r"\bresearch\b",
    r"\bpubmed\b",
    r"\bsemantic\s*scholar\b",
    r"\bliterature\b",
    r"\bpublication(s)?\b",
    r"\bstudy\b",
    r"\bstudies\b",
    r"\bjournal\b",
    r"\barticle(s)?\b",
    r"\bfind\s*(papers?|research|articles?)\b",
    r"\bsearch\s*(for\s*)?(papers?|research|articles?)\b",
]

# Keywords for reagent-related queries
REAGENT_KEYWORDS = [
    r"\breagent(s)?\b",
    r"\bantibod(y|ies)\b",
    r"\bchemical(s)?\b",
    r"\binventory\b",
    r"\bstock\b",
    r"\breorder\b",
    r"\blow\s*(inventory|stock)\b",
    r"\bcd\d+\b",  # CD markers like CD64, CD45
    r"\bcatalog\s*(number|#)?\b",
    r"\bvendor\b",
    r"\babcam\b",
    r"\bthermo\s*fisher\b",
    r"\bbiolegend\b",
    r"\bsigma\s*aldrich\b",
    r"\badd\s*(to\s*)?(my\s*)?reagent(s)?\b",
    r"\bused\s*\d+\s*(µ[lL]|m[lLgG]|[gG])\b",  # "used 5 µL"
    r"\blog\s*(usage|that\s*i\s*used)\b",
    r"\bwhat('s|\s+is)\s+(running\s+)?low\b",
]

# Keywords for protocol-related queries
PROTOCOL_KEYWORDS = [
    r"\bprotocol(s)?\b",
    r"\bstain(ing)?\s+\w+\s+(brain|tissue|slide|cell)",  # "stain mouse brain slides"
    r"\bpcr\s+protocol\b",
    r"\bwestern\s+blot\b",
    r"\bimmuno(staining|fluorescence|histochemistry)\b",
    r"\bprocedure\s+for\b",
    r"\bmethod(s)?\s+for\b",
    r"\bstep(s)?\s+(for|to)\b",
    r"\bhow\s+to\s+(do|perform|run)\b",
    r"\bdesign\s+a\s+protocol\b",
    r"\bcreate\s+(a\s+)?protocol\b",
    r"\bmodify\s+(my\s+)?protocol\b",
    r"\bupdate\s+(my\s+)?protocol\b",
    r"\blist\s+(my\s+)?protocols?\b",
    r"\bshow\s+(my\s+)?protocols?\b",
    r"\bsaved\s+protocols?\b",
]

# Keywords for experiment-related queries
EXPERIMENT_KEYWORDS = [
    r"\bexperiment(s)?\b",
    r"\bplan\s+(an?\s+)?experiment\b",
    r"\bdesign\s+(an?\s+)?experiment\b",
    r"\bcreate\s+(an?\s+)?experiment\b",
    r"\bstart\s+(an?\s+)?experiment\b",
    r"\bmark\s+exp(eriment)?_?\w+\s+(as\s+)?(completed|done|in.?progress)\b",
    r"\bexp_\w+\b",  # experiment IDs like exp_abc123
    r"\blog\s+(that\s+)?exp(eriment)?\b",
    r"\bused\s+\d+\s*(µ[lL]|m[lLgG]|[gG])\s+(of|for)\s+exp\b",
    r"\banalyze\s+(the\s+)?results?\b",
    r"\bresults?\s+(of|for)\s+exp\b",
    r"\bscientific\s+question\b",
    r"\bhow\s+can\s+i\s+test\b",
    r"\btest\s+(whether|if|that)\b",
    r"\blist\s+(my\s+)?experiments?\b",
    r"\bshow\s+(my\s+)?experiments?\b",
]


def classify_intent(message: str) -> Tuple[str, str]:
    """
    Classify user message intent to route to appropriate agent.
    
    Args:
        message: User's query
        
    Returns:
        Tuple of (agent_name, intent)
    """
    message_lower = message.lower()
    
    # Check for blockchain keywords (highest priority for explicit blockchain requests)
    for pattern in BLOCKCHAIN_KEYWORDS:
        if re.search(pattern, message_lower):
            return ("blockchain_agent", "blockchain_operation")
    
    # Check for experiment keywords (before protocol to catch "plan experiment")
    for pattern in EXPERIMENT_KEYWORDS:
        if re.search(pattern, message_lower):
            return ("experiment_agent", "experiment_operation")
    
    # Check for protocol keywords
    for pattern in PROTOCOL_KEYWORDS:
        if re.search(pattern, message_lower):
            return ("protocol_agent", "protocol_operation")
    
    # Check for reagent keywords
    for pattern in REAGENT_KEYWORDS:
        if re.search(pattern, message_lower):
            return ("reagent_agent", "reagent_operation")
    
    # Check for literature keywords
    for pattern in LITERATURE_KEYWORDS:
        if re.search(pattern, message_lower):
            return ("literature_agent", "literature_search")
    
    # Default to literature agent for general queries
    return ("literature_agent", "general_query")


# =============================================================================
# Response Models for Blockchain Endpoints
# =============================================================================

class BlockchainStatusResponse(BaseModel):
    """Response model for blockchain status endpoint."""
    
    network: str = Field(..., description="Neo X network name (testnet/mainnet)")
    chain_id: int = Field(..., description="Chain ID for the network")
    connected: bool = Field(..., description="Whether RPC connection is healthy")
    latest_block: Optional[int] = Field(None, description="Latest block number")
    account_address: Optional[str] = Field(None, description="Configured wallet address")
    gas_balance: Optional[float] = Field(None, description="GAS balance in native units")
    mock_mode: bool = Field(..., description="Whether using mock blockchain for development")
    timestamp: datetime = Field(..., description="Timestamp of status check")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "network": "testnet",
                "chain_id": 12227332,
                "connected": True,
                "latest_block": 6130000,
                "account_address": "0x96d04FC0261b23e808B19A1F4580EB727B2C151D",
                "gas_balance": 2.5,
                "mock_mode": False,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }


# =============================================================================
# FastAPI Application
# =============================================================================

# OpenAPI tags for documentation
tags_metadata = [
    {
        "name": "health",
        "description": "Health check and status endpoints",
    },
    {
        "name": "chat",
        "description": "AI chat endpoints with intent-based routing to domain agents",
    },
    {
        "name": "blockchain",
        "description": """**Experiment Provenance on Neo X Blockchain**
        
Endpoints for verifiable scientific data storage:
- Store experiment hashes on Neo X blockchain for immutable records
- Verify experiment data integrity against on-chain records
- Check blockchain connection status and wallet balance

The blockchain integration uses Neo X testnet (EVM-compatible).
Explorer: https://xt4scan.ngd.network/
""",
    },
]

app = FastAPI(
    title="Nexus Workspace Backend",
    description="""
## Lab Workspace AI Agent System

This API provides AI-powered assistance for lab research workflows.

### Available Agents

| Agent | Purpose | Trigger Keywords |
|-------|---------|------------------|
| **LiteratureAgent** | Search PubMed & Semantic Scholar | papers, research, publications |
| **BlockchainAgent** | Experiment provenance on Neo X | blockchain, verify, on-chain, provenance |

### Blockchain Integration

The BlockchainAgent enables **verifiable scientific data storage** on Neo X blockchain:
- **Store**: Create immutable records of experiment data hashes
- **Verify**: Check data integrity against blockchain records
- **Status**: Monitor blockchain connection and wallet balance

All blockchain operations use Neo X testnet. View transactions at: https://xt4scan.ngd.network/
""",
    version="0.1.0",
    openapi_tags=tags_metadata
)

# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Nexus Workspace Backend API",
        "docs": "/docs",
        "health": "/health",
        "blockchain_status": "/api/blockchain/status"
    }


@app.get("/health", tags=["health"])
async def health():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(
    "/api/blockchain/status",
    response_model=BlockchainStatusResponse,
    tags=["blockchain"],
    summary="Get Neo X blockchain connection status",
    description="""
Check the status of the Neo X blockchain connection for experiment provenance.

Returns:
- **network**: Current network (testnet/mainnet)
- **connected**: Whether the RPC endpoint is reachable
- **gas_balance**: Available GAS for transactions
- **mock_mode**: Whether using mock blockchain for development

Use this endpoint to verify blockchain connectivity before storing experiment data.
"""
)
async def blockchain_status():
    """
    Get Neo X blockchain connection status and account information.
    
    This endpoint provides a quick health check for the blockchain integration
    used for experiment provenance. It returns network connectivity status,
    wallet balance, and configuration details.
    """
    try:
        service = get_blockchain_service()
        info = service.get_network_info()
        
        # Log the status check
        log_blockchain_action(
            action="status_check",
            tool_name="get_blockchain_status",
            success=info.get("connected", False),
            extra={"endpoint": "/api/blockchain/status"}
        )
        
        return BlockchainStatusResponse(
            network=info.get("network", "unknown"),
            chain_id=info.get("chain_id", 0),
            connected=info.get("connected", False),
            latest_block=info.get("latest_block"),
            account_address=info.get("account_address"),
            gas_balance=float(info.get("gas_balance_ether", 0)) if info.get("gas_balance_ether") else None,
            mock_mode=info.get("mock_mode", USE_MOCK_BLOCKCHAIN),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Blockchain status check failed: {e}")
        log_blockchain_action(
            action="status_check",
            tool_name="get_blockchain_status",
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=503,
            detail=f"Blockchain service unavailable: {str(e)}"
        )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Chat with AI agents",
    description="""
Send a message to the AI assistant. The message is automatically routed to the appropriate agent:

**LiteratureAgent** - Triggered by keywords: papers, research, publications, PubMed, articles
- Searches academic databases (PubMed, Semantic Scholar)
- Returns relevant research papers and summaries

**BlockchainAgent** - Triggered by keywords: blockchain, Neo X, on-chain, verify, provenance, transaction hash
- Stores experiment hashes on Neo X blockchain
- Verifies data integrity against on-chain records
- Checks blockchain connection status

The `page_context` provides awareness of the user's current view for context-relevant responses.
"""
)
async def chat(request: ChatRequest):
    """
    Chat endpoint that routes to appropriate agent based on intent.
    
    Currently supports:
    - LiteratureAgent: Research papers, publications, academic search
    - BlockchainAgent: Experiment provenance, data integrity, Neo X operations
    
    Args:
        request: ChatRequest with message and page context
        
    Returns:
        ChatResponse with agent's response and metadata
    """
    try:
        # Classify intent to determine which agent to use
        agent_name, intent = classify_intent(request.message)
        
        # Log the request
        logger.info(f"Chat request | agent={agent_name} | intent={intent} | route={request.page_context.route}")
        
        # Initialize appropriate agent
        if agent_name == "blockchain_agent":
            agent = BlockchainAgent(
                workspace_id=request.page_context.workspace_id,
                user_id=request.page_context.user_id
            )
            # Log blockchain agent activation
            log_blockchain_action(
                action="agent_activated",
                tool_name="chat_routing",
                success=True,
                extra={
                    "user_id": request.page_context.user_id,
                    "workspace_id": request.page_context.workspace_id,
                    "message_preview": request.message[:50] + "..." if len(request.message) > 50 else request.message
                }
            )
        elif agent_name == "reagent_agent":
            agent = ReagentAgent(
                workspace_id=request.page_context.workspace_id,
                user_id=request.page_context.user_id
            )
        elif agent_name == "protocol_agent":
            agent = ProtocolAgent(
                workspace_id=request.page_context.workspace_id,
                user_id=request.page_context.user_id
            )
        elif agent_name == "experiment_agent":
            agent = ExperimentAgent(
                workspace_id=request.page_context.workspace_id,
                user_id=request.page_context.user_id
            )
        else:
            # Default to LiteratureAgent
            agent = LiteratureAgent(
                workspace_id=request.page_context.workspace_id,
                user_id=request.page_context.user_id
            )
        
        # Process message
        response_text = await agent.process(
            request.message,
            request.page_context
        )
        
        # Log successful response
        logger.info(f"Chat response | agent={agent_name} | success=True | response_length={len(response_text)}")
        
        # Return structured response
        return ChatResponse(
            response=response_text,
            agent_used=agent_name,
            intent=intent,
            metadata={"route": request.page_context.route},
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Chat error | agent={agent_name} | error={str(e)}")
        if agent_name == "blockchain_agent":
            log_blockchain_action(
                action="chat_error",
                tool_name="agent_process",
                success=False,
                error=str(e)
            )
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


# =============================================================================
# Voice TTS Proxy Endpoint
# =============================================================================

# Agent voice ID mapping (ElevenLabs voice IDs)
# TODO: Replace with actual voice IDs from your ElevenLabs account
AGENT_VOICE_MAP = {
    "experiment_agent": "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "protocol_agent": "EXAVITQu4vr4xnSDxMaL",    # Bella
    "literature_agent": "TxGEqnHWrfWFTfGW9XjX",  # Josh
    "reagent_agent": "ErXwobaYiN019PkySvjV",     # Antoni
    "blockchain_agent": "pNInz6obpgDQGcFmaJgB",  # Adam
    "default": "21m00Tcm4TlvDq8ikWAM",           # Rachel
}


class TTSRequest(BaseModel):
    """Request body for TTS endpoint."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    agent_name: Optional[str] = Field(None, description="Agent name for voice selection")
    voice_id: Optional[str] = Field(None, description="Override voice ID")


@app.post("/api/voice/tts")
async def text_to_speech(request: TTSRequest):
    """
    Proxy endpoint for ElevenLabs TTS.
    
    Streams audio from ElevenLabs without exposing the API key to the frontend.
    
    Args:
        request: TTSRequest with text and optional agent_name/voice_id
        
    Returns:
        StreamingResponse with audio/mpeg content
    """
    # Check if ElevenLabs API key is configured
    if not config.ELEVENLABS_API_KEY:
        logger.warning("TTS request failed: ELEVENLABS_API_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="Voice service not configured. Set ELEVENLABS_API_KEY in backend .env"
        )
    
    # Select voice ID
    voice_id = request.voice_id
    if not voice_id:
        voice_id = AGENT_VOICE_MAP.get(request.agent_name or "", AGENT_VOICE_MAP["default"])
    
    # ElevenLabs streaming TTS endpoint
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": config.ELEVENLABS_API_KEY,
    }
    
    payload = {
        "text": request.text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    
    logger.debug(f"TTS request | voice_id={voice_id} | text_length={len(request.text)}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            
            if response.status_code != 200:
                error_text = response.text[:200]  # Truncate for logging
                logger.error(f"ElevenLabs API error: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"TTS service error: {response.status_code}"
                )
            
            # Stream the audio response
            logger.debug(f"TTS success | voice_id={voice_id} | content_length={len(response.content)}")
            
            return StreamingResponse(
                iter([response.content]),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache",
                }
            )
            
    except httpx.TimeoutException:
        logger.error("TTS request timed out")
        raise HTTPException(status_code=504, detail="TTS service timeout")
    except httpx.RequestError as e:
        logger.error(f"TTS request error: {str(e)}")
        raise HTTPException(status_code=502, detail="TTS service unavailable")
