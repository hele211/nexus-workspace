"""
Common Pydantic schemas shared across the backend.

These models provide standardized structures for page context
and agent responses used throughout the application.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PageContext(BaseModel):
    """
    Represents the current page state from the frontend.
    
    This context is passed with each chat request to give agents
    awareness of what the user is currently viewing/working on.
    """
    
    route: str = Field(
        ...,
        description="Current frontend route (e.g., '/experiments', '/protocols')"
    )
    workspace_id: str = Field(
        ...,
        description="ID of the current workspace"
    )
    user_id: str = Field(
        ...,
        description="ID of the authenticated user"
    )
    experiment_ids: List[str] = Field(
        default_factory=list,
        description="IDs of experiments currently in view or selected"
    )
    protocol_ids: List[str] = Field(
        default_factory=list,
        description="IDs of protocols currently in view or selected"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Active filters applied to the current view"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context-specific metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "route": "/experiments",
                    "workspace_id": "ws_abc123",
                    "user_id": "user_xyz789",
                    "experiment_ids": ["exp_001", "exp_002"],
                    "protocol_ids": [],
                    "filters": {"status": "active"},
                    "metadata": {"view_mode": "grid"}
                }
            ]
        }
    }


class AgentResponse(BaseModel):
    """
    Standardized response structure from domain agents.
    
    All agents return this format to ensure consistent
    handling by the API layer and frontend.
    """
    
    agent_name: str = Field(
        ...,
        description="Name of the agent that generated this response"
    )
    message: str = Field(
        ...,
        description="Human-readable response message"
    )
    actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of actions for the frontend to execute (e.g., navigate, refresh)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata (e.g., sources, confidence)"
    )
    success: bool = Field(
        default=True,
        description="Whether the agent successfully handled the request"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_name": "LiteratureAgent",
                    "message": "Found 5 relevant papers on CRISPR gene editing.",
                    "actions": [
                        {"type": "show_results", "data": {"count": 5}}
                    ],
                    "metadata": {
                        "sources": ["PubMed", "Semantic Scholar"],
                        "query_time_ms": 1250
                    },
                    "success": True
                }
            ]
        }
    }
