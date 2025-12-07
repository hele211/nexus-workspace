"""
Reagent inventory service for managing lab reagents.

Provides CRUD operations for reagents and usage tracking.
Currently uses in-memory storage for development.

TODO: Replace with Supabase/DB-backed service following backend/services pattern.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class ReagentService:
    """
    In-memory reagent inventory service.
    
    Manages reagent records and usage tracking for lab experiments.
    
    TODO: Replace with Supabase/DB-backed service following backend/services pattern.
    """
    
    _instance: Optional["ReagentService"] = None
    
    def __new__(cls) -> "ReagentService":
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the reagent service with in-memory storage."""
        if self._initialized:
            return
        
        # In-memory storage
        # TODO: Replace with Supabase/DB tables
        self._reagents: Dict[str, Dict[str, Any]] = {}
        self._usage_events: List[Dict[str, Any]] = []
        
        self._initialized = True
    
    def create_reagent(
        self,
        name: str,
        catalog_number: str,
        vendor: str,
        storage_conditions: str,
        initial_quantity: float,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a reagent in the inventory.
        
        Args:
            name: Reagent name
            catalog_number: Vendor catalog number
            vendor: Vendor/supplier name
            storage_conditions: Storage requirements (e.g., "-20°C")
            initial_quantity: Initial quantity
            unit: Unit of measurement (e.g., "µL", "mg")
            metadata: Optional additional metadata
            
        Returns:
            Created/updated reagent record with reagent_id
        """
        # Check if reagent with same catalog_number and vendor exists
        existing_id = None
        for rid, reagent in self._reagents.items():
            if (reagent["catalog_number"] == catalog_number and 
                reagent["vendor"] == vendor):
                existing_id = rid
                break
        
        if existing_id:
            # Update existing reagent
            reagent_id = existing_id
            self._reagents[reagent_id].update({
                "name": name,
                "storage_conditions": storage_conditions,
                "initial_quantity": initial_quantity,
                "current_quantity": initial_quantity,
                "unit": unit,
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            })
        else:
            # Create new reagent
            reagent_id = f"reagent_{uuid.uuid4().hex[:8]}"
            self._reagents[reagent_id] = {
                "reagent_id": reagent_id,
                "name": name,
                "catalog_number": catalog_number,
                "vendor": vendor,
                "storage_conditions": storage_conditions,
                "initial_quantity": initial_quantity,
                "current_quantity": initial_quantity,
                "unit": unit,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
        
        return self._reagents[reagent_id].copy()
    
    def get_reagent(self, reagent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a reagent by ID.
        
        Args:
            reagent_id: Reagent ID
            
        Returns:
            Reagent record or None if not found
        """
        reagent = self._reagents.get(reagent_id)
        return reagent.copy() if reagent else None
    
    def get_reagent_by_catalog(
        self, 
        catalog_number: str, 
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a reagent by catalog number and optionally vendor.
        
        Args:
            catalog_number: Vendor catalog number
            vendor: Optional vendor name to narrow search
            
        Returns:
            Reagent record or None if not found
        """
        for reagent in self._reagents.values():
            if reagent["catalog_number"] == catalog_number:
                if vendor is None or reagent["vendor"] == vendor:
                    return reagent.copy()
        return None
    
    def record_usage(
        self,
        reagent_id: str,
        amount_used: float,
        unit: str,
        experiment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record reagent usage and update inventory.
        
        Args:
            reagent_id: Reagent ID
            amount_used: Amount used
            unit: Unit of measurement
            experiment_id: Optional experiment ID
            
        Returns:
            Dict with before/after quantities and low_inventory flag
            
        Raises:
            ValueError: If reagent not found or unit mismatch
        """
        reagent = self._reagents.get(reagent_id)
        if not reagent:
            raise ValueError(f"Reagent not found: {reagent_id}")
        
        # Validate unit matches
        if reagent["unit"] != unit:
            raise ValueError(
                f"Unit mismatch: reagent uses '{reagent['unit']}', "
                f"but usage recorded in '{unit}'"
            )
        
        # Record the usage event
        usage_event = {
            "event_id": f"usage_{uuid.uuid4().hex[:8]}",
            "reagent_id": reagent_id,
            "amount_used": amount_used,
            "unit": unit,
            "experiment_id": experiment_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._usage_events.append(usage_event)
        
        # Update quantity
        before_quantity = reagent["current_quantity"]
        new_quantity = max(0, before_quantity - amount_used)
        reagent["current_quantity"] = new_quantity
        reagent["updated_at"] = datetime.utcnow().isoformat()
        
        # Calculate remaining percentage
        initial = reagent["initial_quantity"]
        remaining_pct = (new_quantity / initial * 100) if initial > 0 else 0
        low_inventory = remaining_pct < 10
        
        return {
            "reagent_id": reagent_id,
            "reagent_name": reagent["name"],
            "before_quantity": before_quantity,
            "after_quantity": new_quantity,
            "amount_used": amount_used,
            "unit": unit,
            "remaining_percentage": round(remaining_pct, 1),
            "low_inventory": low_inventory,
            "experiment_id": experiment_id
        }
    
    def get_low_inventory_reagents(self, threshold_pct: float = 10.0) -> List[Dict[str, Any]]:
        """
        Get reagents with inventory below threshold percentage.
        
        Args:
            threshold_pct: Threshold percentage (default 10%)
            
        Returns:
            List of low inventory reagents
        """
        low_inventory = []
        
        for reagent in self._reagents.values():
            initial = reagent["initial_quantity"]
            current = reagent["current_quantity"]
            
            if initial > 0:
                remaining_pct = (current / initial) * 100
                if remaining_pct < threshold_pct:
                    low_inventory.append({
                        "reagent_id": reagent["reagent_id"],
                        "name": reagent["name"],
                        "vendor": reagent["vendor"],
                        "catalog_number": reagent["catalog_number"],
                        "current_quantity": current,
                        "initial_quantity": initial,
                        "unit": reagent["unit"],
                        "remaining_percentage": round(remaining_pct, 1)
                    })
        
        # Sort by remaining percentage (lowest first)
        low_inventory.sort(key=lambda x: x["remaining_percentage"])
        
        return low_inventory
    
    def list_all_reagents(self) -> List[Dict[str, Any]]:
        """
        List all reagents in inventory.
        
        Returns:
            List of all reagent records
        """
        return [r.copy() for r in self._reagents.values()]
    
    def get_usage_history(
        self, 
        reagent_id: Optional[str] = None,
        experiment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get usage history, optionally filtered.
        
        Args:
            reagent_id: Optional filter by reagent
            experiment_id: Optional filter by experiment
            
        Returns:
            List of usage events
        """
        events = self._usage_events
        
        if reagent_id:
            events = [e for e in events if e["reagent_id"] == reagent_id]
        if experiment_id:
            events = [e for e in events if e["experiment_id"] == experiment_id]
        
        return [e.copy() for e in events]


# Singleton instance getter
_reagent_service: Optional[ReagentService] = None


def get_reagent_service() -> ReagentService:
    """
    Get the reagent service instance (singleton).
    
    Returns:
        ReagentService instance
    """
    global _reagent_service
    if _reagent_service is None:
        _reagent_service = ReagentService()
    return _reagent_service
