"""
Protocol service for managing lab protocols.

Provides CRUD operations for protocols and search functionality.
Currently uses in-memory storage for development.

TODO: Replace with Supabase/DB-backed service following backend/services pattern.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class ProtocolService:
    """
    In-memory protocol service.
    
    Manages protocol records including creation, updates, and search.
    
    TODO: Replace with Supabase/DB-backed service following backend/services pattern.
    """
    
    _instance: Optional["ProtocolService"] = None
    
    def __new__(cls) -> "ProtocolService":
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the protocol service with in-memory storage."""
        if self._initialized:
            return
        
        # In-memory storage
        # TODO: Replace with Supabase/DB tables
        self._protocols: Dict[str, Dict[str, Any]] = {}
        
        self._initialized = True
    
    def create_protocol(
        self,
        name: str,
        description: str,
        source_type: str = "manual",
        source_reference: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new protocol.
        
        Args:
            name: Protocol name
            description: Brief description
            source_type: Source type ('manual', 'web', 'literature', 'derived')
            source_reference: Optional source URL, DOI, or paper ID
            steps: List of step objects with index and text
            tags: List of tags for categorization
            metadata: Additional metadata
            
        Returns:
            Created protocol record with id
        """
        protocol_id = f"protocol_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        
        # Normalize steps
        normalized_steps = []
        if steps:
            for i, step in enumerate(steps):
                normalized_steps.append({
                    "index": step.get("index", i + 1),
                    "text": step.get("text", ""),
                    "reagents": step.get("reagents", []),
                    "duration_minutes": step.get("duration_minutes"),
                    "notes": step.get("notes")
                })
        
        protocol = {
            "id": protocol_id,
            "name": name,
            "description": description,
            "source_type": source_type,
            "source_reference": source_reference,
            "steps": normalized_steps,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "metadata": metadata or {}
        }
        
        self._protocols[protocol_id] = protocol
        return protocol.copy()
    
    def update_protocol(
        self,
        protocol_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        source_reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing protocol.
        
        Args:
            protocol_id: Protocol ID to update
            name: New name (optional)
            description: New description (optional)
            steps: New steps list (optional, replaces all steps)
            tags: New tags list (optional, replaces all tags)
            source_reference: New source reference (optional)
            metadata: Additional metadata to merge (optional)
            
        Returns:
            Updated protocol record
            
        Raises:
            ValueError: If protocol not found
        """
        if protocol_id not in self._protocols:
            raise ValueError(f"Protocol not found: {protocol_id}")
        
        protocol = self._protocols[protocol_id]
        changes = []
        
        if name is not None:
            protocol["name"] = name
            changes.append("name")
        
        if description is not None:
            protocol["description"] = description
            changes.append("description")
        
        if steps is not None:
            # Normalize steps
            normalized_steps = []
            for i, step in enumerate(steps):
                normalized_steps.append({
                    "index": step.get("index", i + 1),
                    "text": step.get("text", ""),
                    "reagents": step.get("reagents", []),
                    "duration_minutes": step.get("duration_minutes"),
                    "notes": step.get("notes")
                })
            protocol["steps"] = normalized_steps
            changes.append(f"steps ({len(normalized_steps)} steps)")
        
        if tags is not None:
            protocol["tags"] = tags
            changes.append("tags")
        
        if source_reference is not None:
            protocol["source_reference"] = source_reference
            changes.append("source_reference")
        
        if metadata is not None:
            protocol["metadata"].update(metadata)
            changes.append("metadata")
        
        # Update timestamp and version
        protocol["updated_at"] = datetime.utcnow().isoformat()
        protocol["version"] += 1
        
        return {
            "protocol": protocol.copy(),
            "changes": changes
        }
    
    def get_protocol(self, protocol_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a protocol by ID.
        
        Args:
            protocol_id: Protocol ID
            
        Returns:
            Protocol record or None if not found
        """
        protocol = self._protocols.get(protocol_id)
        return protocol.copy() if protocol else None
    
    def list_protocols(
        self,
        tag_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all protocols, optionally filtered by tag.
        
        Args:
            tag_filter: Optional tag to filter by
            
        Returns:
            List of protocol records
        """
        protocols = list(self._protocols.values())
        
        if tag_filter:
            tag_lower = tag_filter.lower()
            protocols = [
                p for p in protocols
                if any(tag_lower in t.lower() for t in p.get("tags", []))
            ]
        
        # Sort by updated_at descending
        protocols.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        
        return [p.copy() for p in protocols]
    
    def search_protocols_by_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Search protocols by query string.
        
        Searches over name, description, and tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching protocols with relevance scores
        """
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        
        for protocol in self._protocols.values():
            # Build searchable text
            searchable = " ".join([
                protocol.get("name", "").lower(),
                protocol.get("description", "").lower(),
                " ".join(protocol.get("tags", [])).lower()
            ])
            
            # Calculate simple relevance score
            score = 0
            for term in query_terms:
                if term in searchable:
                    score += 1
                    # Bonus for exact match in name
                    if term in protocol.get("name", "").lower():
                        score += 0.5
                    # Bonus for tag match
                    if any(term in t.lower() for t in protocol.get("tags", [])):
                        score += 0.3
            
            if score > 0:
                results.append({
                    "protocol": protocol.copy(),
                    "relevance_score": score / len(query_terms) if query_terms else 0
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return results
    
    def delete_protocol(self, protocol_id: str) -> bool:
        """
        Delete a protocol.
        
        Args:
            protocol_id: Protocol ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if protocol_id in self._protocols:
            del self._protocols[protocol_id]
            return True
        return False


# Singleton instance getter
_protocol_service: Optional[ProtocolService] = None


def get_protocol_service() -> ProtocolService:
    """
    Get the protocol service instance (singleton).
    
    Returns:
        ProtocolService instance
    """
    global _protocol_service
    if _protocol_service is None:
        _protocol_service = ProtocolService()
    return _protocol_service
