"""
Protocol schemas for lab protocol management.

Defines data models for protocols including steps, reagent references,
and metadata for tracking sources and versions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReagentReference(BaseModel):
    """Reference to a reagent used in a protocol step."""
    
    reagent_id: str = Field(..., description="ID of the reagent in inventory")
    amount: float = Field(..., description="Amount of reagent needed")
    unit: str = Field(..., description="Unit of measurement (e.g., 'µL', 'mg')")


class ProtocolStep(BaseModel):
    """A single step in a protocol."""
    
    index: int = Field(..., description="Step number (1-indexed)")
    text: str = Field(..., description="Step instructions")
    reagents: List[ReagentReference] = Field(
        default_factory=list,
        description="Reagents used in this step"
    )
    duration_minutes: Optional[int] = Field(
        None,
        description="Estimated duration in minutes"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes or tips for this step"
    )


class Protocol(BaseModel):
    """
    A lab protocol with steps and metadata.
    
    Protocols can be sourced from the web, literature, or created manually.
    They are versionable and can reference reagents from inventory.
    """
    
    id: str = Field(..., description="Unique protocol identifier")
    name: str = Field(..., description="Protocol name")
    description: str = Field(..., description="Brief description of the protocol")
    source_type: str = Field(
        ...,
        description="Source type: 'manual', 'web', 'literature', 'derived'"
    )
    source_reference: Optional[str] = Field(
        None,
        description="Source reference (URL, DOI, paper ID)"
    )
    steps: List[ProtocolStep] = Field(
        default_factory=list,
        description="Ordered list of protocol steps"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., 'immunostaining', 'mouse brain')"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    version: int = Field(
        default=1,
        description="Protocol version number"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "protocol_abc123",
                    "name": "Mouse Brain Immunostaining",
                    "description": "Standard immunostaining protocol for mouse brain sections",
                    "source_type": "literature",
                    "source_reference": "10.1038/s41596-019-0206-y",
                    "steps": [
                        {"index": 1, "text": "Fix tissue in 4% PFA for 24 hours", "reagents": []},
                        {"index": 2, "text": "Wash 3x with PBS", "reagents": []}
                    ],
                    "tags": ["immunostaining", "mouse brain", "histology"],
                    "version": 1
                }
            ]
        }
    }


class ProtocolCandidate(BaseModel):
    """
    A protocol candidate from search results.
    
    Used when presenting options from web or literature searches.
    """
    
    title: str = Field(..., description="Protocol title")
    description: str = Field(..., description="Brief description")
    source_type: str = Field(..., description="Source type: 'web' or 'literature'")
    source_reference: str = Field(..., description="URL or DOI")
    relevance_score: Optional[float] = Field(
        None,
        description="Relevance score from search (0-1)"
    )


class ProtocolSearchResult(BaseModel):
    """Result from protocol search operations."""
    
    query: str = Field(..., description="Original search query")
    candidates: List[ProtocolCandidate] = Field(
        default_factory=list,
        description="List of protocol candidates"
    )
    source: str = Field(..., description="Search source: 'local', 'web', 'literature'")
