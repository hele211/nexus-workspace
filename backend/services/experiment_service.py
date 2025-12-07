"""
Experiment service for managing experiments.

Provides in-memory storage and CRUD operations for experiments.
TODO: Integrate with Supabase/database for persistence.

Usage:
    service = get_experiment_service()
    experiment = service.create_experiment(
        title="CRISPR knockout",
        scientific_question="Does Gene X regulate Y?",
        description="...",
        tags=["CRISPR"]
    )
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from backend.schemas.experiment import ReagentUsage


# =============================================================================
# Experiment Service
# =============================================================================

class ExperimentService:
    """
    In-memory experiment management service.
    
    Provides CRUD operations for experiments with support for:
    - Protocol linking
    - Reagent usage tracking
    - Status management
    - Blockchain provenance
    - Results storage
    
    TODO: Replace in-memory storage with Supabase/database.
    """
    
    def __init__(self):
        """Initialize with empty experiment store."""
        self._experiments: Dict[str, Dict[str, Any]] = {}
    
    def create_experiment(
        self,
        title: str,
        scientific_question: str,
        description: str,
        protocol_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new experiment.
        
        Args:
            title: Experiment title
            scientific_question: The question being investigated
            description: Detailed description
            protocol_id: Optional linked protocol ID
            tags: Optional list of tags
            
        Returns:
            Created experiment dict
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        experiment = {
            "id": experiment_id,
            "title": title,
            "scientific_question": scientific_question,
            "description": description,
            "status": "planned",
            "protocol_id": protocol_id,
            "reagent_usages": [],
            "tags": tags or [],
            "notes": None,
            "results_summary": None,
            "blockchain_tx_hash": None,
            "created_at": now,
            "updated_at": now,
        }
        
        self._experiments[experiment_id] = experiment
        return experiment
    
    def update_experiment(
        self,
        experiment_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an experiment with provided fields.
        
        Args:
            experiment_id: ID of experiment to update
            updates: Dict of fields to update
            
        Returns:
            Updated experiment or None if not found
        """
        if experiment_id not in self._experiments:
            return None
        
        experiment = self._experiments[experiment_id]
        
        # Apply updates (only allowed fields)
        allowed_fields = {
            "title", "scientific_question", "description", 
            "status", "protocol_id", "tags", "notes", 
            "results_summary", "blockchain_tx_hash"
        }
        
        for key, value in updates.items():
            if key in allowed_fields:
                experiment[key] = value
        
        experiment["updated_at"] = datetime.now(timezone.utc).isoformat()
        return experiment
    
    def set_status(
        self,
        experiment_id: str,
        status: Literal["planned", "in_progress", "completed"]
    ) -> Optional[Dict[str, Any]]:
        """
        Set experiment status.
        
        Args:
            experiment_id: ID of experiment
            status: New status
            
        Returns:
            Updated experiment or None if not found
        """
        return self.update_experiment(experiment_id, {"status": status})
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an experiment by ID.
        
        Args:
            experiment_id: ID to look up
            
        Returns:
            Experiment dict or None if not found
        """
        return self._experiments.get(experiment_id)
    
    def list_experiments(
        self,
        status_filter: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all experiments with optional filters.
        
        Args:
            status_filter: Filter by status
            tag_filter: Filter by tag
            
        Returns:
            List of experiments
        """
        experiments = list(self._experiments.values())
        
        if status_filter:
            experiments = [e for e in experiments if e["status"] == status_filter]
        
        if tag_filter:
            tag_lower = tag_filter.lower()
            experiments = [
                e for e in experiments 
                if any(tag_lower in t.lower() for t in e.get("tags", []))
            ]
        
        # Sort by created_at descending
        experiments.sort(key=lambda x: x["created_at"], reverse=True)
        return experiments
    
    def attach_protocol(
        self,
        experiment_id: str,
        protocol_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Attach a protocol to an experiment.
        
        Args:
            experiment_id: ID of experiment
            protocol_id: ID of protocol to attach
            
        Returns:
            Updated experiment or None if not found
        """
        return self.update_experiment(experiment_id, {"protocol_id": protocol_id})
    
    def add_reagent_usage(
        self,
        experiment_id: str,
        reagent_id: str,
        amount: float,
        unit: str,
        source: Literal["manual", "auto_from_protocol"] = "manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Add a reagent usage record to an experiment.
        
        Args:
            experiment_id: ID of experiment
            reagent_id: ID of reagent used
            amount: Amount used
            unit: Unit of measurement
            source: How this usage was recorded
            
        Returns:
            Updated experiment or None if not found
        """
        if experiment_id not in self._experiments:
            return None
        
        experiment = self._experiments[experiment_id]
        
        usage = {
            "reagent_id": reagent_id,
            "amount": amount,
            "unit": unit,
            "source": source
        }
        
        experiment["reagent_usages"].append(usage)
        experiment["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        return experiment
    
    def set_blockchain_tx_hash(
        self,
        experiment_id: str,
        tx_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Set the blockchain transaction hash for an experiment.
        
        Args:
            experiment_id: ID of experiment
            tx_hash: Transaction hash from blockchain
            
        Returns:
            Updated experiment or None if not found
        """
        return self.update_experiment(experiment_id, {"blockchain_tx_hash": tx_hash})
    
    def set_results_summary(
        self,
        experiment_id: str,
        summary: str
    ) -> Optional[Dict[str, Any]]:
        """
        Set the results summary for an experiment.
        
        Args:
            experiment_id: ID of experiment
            summary: Results summary text
            
        Returns:
            Updated experiment or None if not found
        """
        return self.update_experiment(experiment_id, {"results_summary": summary})
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete an experiment.
        
        Args:
            experiment_id: ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            return True
        return False


# =============================================================================
# Singleton Instance
# =============================================================================

_experiment_service: Optional[ExperimentService] = None


def get_experiment_service() -> ExperimentService:
    """
    Get the singleton ExperimentService instance.
    
    Returns:
        ExperimentService instance
    """
    global _experiment_service
    if _experiment_service is None:
        _experiment_service = ExperimentService()
    return _experiment_service


# Export
__all__ = [
    "ExperimentService",
    "get_experiment_service",
]
