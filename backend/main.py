"""
Nexus Workspace Backend - FastAPI Application.

Main entry point for the lab workspace AI agent system.
Currently implements LiteratureAgent for testing.

Run with:
    uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
"""

from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.literature_agent import LiteratureAgent
from backend.schemas.chat import ChatRequest, ChatResponse


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Nexus Workspace Backend",
    description="Lab workspace AI agent system",
    version="0.1.0"
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

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Nexus Workspace Backend API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint that routes to LiteratureAgent.
    
    For now, only LiteratureAgent is implemented.
    Future: Add orchestrator to route to different agents based on intent.
    
    Args:
        request: ChatRequest with message and page context
        
    Returns:
        ChatResponse with agent's response and metadata
    """
    try:
        # Initialize LiteratureAgent with request context
        agent = LiteratureAgent(
            workspace_id=request.page_context.workspace_id,
            user_id=request.page_context.user_id
        )
        
        # Process message
        response_text = await agent.process(
            request.message,
            request.page_context
        )
        
        # Return structured response
        return ChatResponse(
            response=response_text,
            agent_used="literature_agent",
            intent="literature_search",
            metadata={"route": request.page_context.route},
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )
