"""
Conversation Context Memory Tools for SpoonOS.

This module provides lightweight memory tools that store conversation context
(current protocol_id, experiment_id) to enable continuity across multi-turn
conversations.

Demonstrates: Agent → SpoonOS → LLM → ToolCalls pattern for hackathon.

These tools use a simple in-memory store wrapped as SpoonOS BaseTool instances,
satisfying the requirement to use spoon_ai.tools for context management.
"""

from typing import Any, Dict, Optional
from spoon_ai.tools import BaseTool

# =============================================================================
# In-Memory Conversation Context Store
# =============================================================================

# Simple key-value store: conversation_id -> context dict
# In production, this would use spoon_ai.tools.storage or a database
_conversation_contexts: Dict[str, Dict[str, Any]] = {}


def _get_context(conversation_id: str) -> Dict[str, Any]:
    """Get context for a conversation, creating empty if not exists."""
    if conversation_id not in _conversation_contexts:
        _conversation_contexts[conversation_id] = {
            "current_protocol_id": None,
            "current_experiment_id": None,
            "last_created_protocol_id": None,
            "last_created_experiment_id": None,
            "recent_protocol_ids": [],
            "recent_experiment_ids": [],
        }
    return _conversation_contexts[conversation_id]


def _set_context(conversation_id: str, **kwargs) -> Dict[str, Any]:
    """Update context for a conversation."""
    ctx = _get_context(conversation_id)
    for key, value in kwargs.items():
        if value is not None:
            ctx[key] = value
            # Track recent IDs
            if key == "current_protocol_id" and value:
                if value not in ctx.get("recent_protocol_ids", []):
                    ctx.setdefault("recent_protocol_ids", []).insert(0, value)
                    ctx["recent_protocol_ids"] = ctx["recent_protocol_ids"][:5]
                ctx["last_created_protocol_id"] = value
            elif key == "current_experiment_id" and value:
                if value not in ctx.get("recent_experiment_ids", []):
                    ctx.setdefault("recent_experiment_ids", []).insert(0, value)
                    ctx["recent_experiment_ids"] = ctx["recent_experiment_ids"][:5]
                ctx["last_created_experiment_id"] = value
    return ctx


# =============================================================================
# SpoonOS Tool: Set Conversation Context
# =============================================================================

class SetConversationContextTool(BaseTool):
    """
    Store current working context for a conversation.
    
    This tool saves the current protocol_id and/or experiment_id so that
    follow-up messages can reference them without the user restating.
    
    **IMPORTANT:** Call this tool immediately after creating a new protocol
    or experiment to enable continuity in the conversation.
    
    Demonstrates SpoonOS Tool pattern for hackathon requirements.
    """
    
    name: str = "set_conversation_context"
    description: str = """Store the current working protocol_id and/or experiment_id for this conversation.
    
WHEN TO USE:
- Immediately after creating a new protocol (pass current_protocol_id)
- Immediately after creating a new experiment (pass current_experiment_id)
- When user explicitly switches to working on a different protocol/experiment

This enables follow-up commands like "add details to it" or "modify the protocol" 
to work without asking the user to repeat the ID.

Parameters:
- conversation_id (required): The conversation/session identifier
- current_protocol_id (optional): Protocol ID to set as current working protocol
- current_experiment_id (optional): Experiment ID to set as current working experiment
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Conversation or session identifier"
            },
            "current_protocol_id": {
                "type": "string",
                "description": "Protocol ID to set as current (e.g., protocol_abc123)"
            },
            "current_experiment_id": {
                "type": "string",
                "description": "Experiment ID to set as current (e.g., exp_xyz789)"
            }
        },
        "required": ["conversation_id"]
    }
    
    async def execute(
        self,
        conversation_id: str,
        current_protocol_id: Optional[str] = None,
        current_experiment_id: Optional[str] = None
    ) -> str:
        """
        Store context for the conversation.
        
        Args:
            conversation_id: Session/conversation identifier
            current_protocol_id: Protocol ID to remember
            current_experiment_id: Experiment ID to remember
            
        Returns:
            Confirmation message with stored context
        """
        ctx = _set_context(
            conversation_id,
            current_protocol_id=current_protocol_id,
            current_experiment_id=current_experiment_id
        )
        
        parts = ["✅ **Context Updated**"]
        if current_protocol_id:
            parts.append(f"- Current protocol: `{current_protocol_id}`")
        if current_experiment_id:
            parts.append(f"- Current experiment: `{current_experiment_id}`")
        
        parts.append("\n_Follow-up commands will automatically use these IDs._")
        
        return "\n".join(parts)


# =============================================================================
# SpoonOS Tool: Get Conversation Context
# =============================================================================

class GetConversationContextTool(BaseTool):
    """
    Retrieve current working context for a conversation.
    
    This tool returns the current protocol_id and experiment_id that were
    previously set, enabling the agent to resolve vague references like
    "the protocol" or "add details to it".
    
    **IMPORTANT:** Call this tool FIRST when user gives a vague command
    that refers to a protocol or experiment without specifying the ID.
    
    Demonstrates SpoonOS Tool pattern for hackathon requirements.
    """
    
    name: str = "get_conversation_context"
    description: str = """Retrieve the current working protocol_id and experiment_id for this conversation.

WHEN TO USE:
- When user says "the protocol", "it", "this experiment" without specifying ID
- When user says "add details", "modify", "update" without specifying what
- Before any operation that needs a protocol/experiment ID but user didn't provide one

This tool returns:
- current_protocol_id: The protocol user is currently working on
- current_experiment_id: The experiment user is currently working on
- last_created_protocol_id: Most recently created protocol
- last_created_experiment_id: Most recently created experiment
- recent_protocol_ids: List of recently used protocol IDs
- recent_experiment_ids: List of recently used experiment IDs

Parameters:
- conversation_id (required): The conversation/session identifier
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Conversation or session identifier"
            }
        },
        "required": ["conversation_id"]
    }
    
    async def execute(self, conversation_id: str) -> str:
        """
        Retrieve context for the conversation.
        
        Args:
            conversation_id: Session/conversation identifier
            
        Returns:
            Current context with protocol and experiment IDs
        """
        ctx = _get_context(conversation_id)
        
        parts = ["📋 **Current Conversation Context**"]
        
        if ctx.get("current_protocol_id"):
            parts.append(f"- **Current Protocol:** `{ctx['current_protocol_id']}`")
        else:
            parts.append("- **Current Protocol:** _None set_")
            
        if ctx.get("current_experiment_id"):
            parts.append(f"- **Current Experiment:** `{ctx['current_experiment_id']}`")
        else:
            parts.append("- **Current Experiment:** _None set_")
        
        if ctx.get("last_created_protocol_id"):
            parts.append(f"- **Last Created Protocol:** `{ctx['last_created_protocol_id']}`")
        
        if ctx.get("last_created_experiment_id"):
            parts.append(f"- **Last Created Experiment:** `{ctx['last_created_experiment_id']}`")
        
        if ctx.get("recent_protocol_ids"):
            parts.append(f"- **Recent Protocols:** {', '.join(f'`{p}`' for p in ctx['recent_protocol_ids'][:3])}")
        
        if ctx.get("recent_experiment_ids"):
            recent_exps = [f"`{e}`" for e in ctx["recent_experiment_ids"][:3]]
            parts.append(f"- **Recent Experiments:** {', '.join(recent_exps)}")
        
        # Add guidance for the agent
        if not ctx.get("current_protocol_id") and not ctx.get("current_experiment_id"):
            parts.append("\n⚠️ _No current context set. Ask user to specify which protocol/experiment they mean._")
        
        return "\n".join(parts)


# =============================================================================
# Utility function for direct access (used by agents)
# =============================================================================

def get_current_context(conversation_id: str) -> Dict[str, Any]:
    """
    Direct access to conversation context (for agent internal use).
    
    Args:
        conversation_id: Session/conversation identifier
        
    Returns:
        Dict with current_protocol_id, current_experiment_id, etc.
    """
    return _get_context(conversation_id)


def set_current_context(
    conversation_id: str,
    protocol_id: Optional[str] = None,
    experiment_id: Optional[str] = None
) -> None:
    """
    Direct setter for conversation context (for agent internal use).
    
    Args:
        conversation_id: Session/conversation identifier
        protocol_id: Protocol ID to set as current
        experiment_id: Experiment ID to set as current
    """
    _set_context(
        conversation_id,
        current_protocol_id=protocol_id,
        current_experiment_id=experiment_id
    )


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "SetConversationContextTool",
    "GetConversationContextTool",
    "get_current_context",
    "set_current_context",
]
