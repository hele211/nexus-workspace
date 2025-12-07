"""
Chat API request and response schemas.

These models define the contract between the frontend and backend
for the /api/chat endpoint.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import PageContext


class ChatMessage(BaseModel):
    """A single message in conversation history."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """
    Request payload from frontend to /api/chat endpoint.
    
    Contains the user's message, page context, conversation ID for memory,
    and optional history for multi-turn continuity.
    """
    
    message: str = Field(
        ...,
        min_length=1,
        description="User's query or command"
    )
    page_context: PageContext = Field(
        ...,
        description="Current page state from the frontend"
    )
    conversation_id: str = Field(
        default="default",
        description="Unique conversation/session ID for memory continuity"
    )
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in this conversation (last N for context)"
    )
    stream: bool = Field(
        default=False,
        description="Enable streaming response (Phase 3 feature)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Add some details to the protocol",
                    "page_context": {
                        "route": "/protocols",
                        "workspace_id": "ws_abc123",
                        "user_id": "user_xyz789",
                        "experiment_ids": [],
                        "protocol_ids": ["protocol_abc123"],
                        "filters": {},
                        "metadata": {}
                    },
                    "conversation_id": "conv_12345",
                    "history": [
                        {"role": "user", "content": "Create a protocol for PCR"},
                        {"role": "assistant", "content": "I've created protocol_abc123..."}
                    ],
                    "stream": False
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """
    Response payload from backend to frontend.
    
    Contains the agent's response along with metadata
    about which agent handled the request and how.
    """
    
    response: str = Field(
        ...,
        description="Agent's response message"
    )
    agent_used: str = Field(
        ...,
        description="Name of the agent that handled the request"
    )
    intent: Optional[str] = Field(
        default=None,
        description="Classified intent of the user's query"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata (sources, timing, debug info)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the response"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "I found 5 recent papers on CRISPR-Cas9 gene editing. The most cited is 'Precision genome editing using CRISPR-Cas9' (2024) with 342 citations.",
                    "agent_used": "LiteratureAgent",
                    "intent": "literature_search",
                    "metadata": {
                        "sources": ["PubMed", "Semantic Scholar"],
                        "papers_found": 5,
                        "query_time_ms": 1250
                    },
                    "timestamp": "2025-12-06T14:30:00Z"
                }
            ]
        }
    }
