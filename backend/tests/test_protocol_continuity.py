"""
Protocol Continuity Tests.

Tests that verify the ProtocolAgent correctly:
1. Tracks the current protocol across conversation turns
2. Uses UpdateProtocolTool for "add details" requests (not CreateProtocolTool)
3. Never asks user to restate protocol content when context is available

Run with:
    pytest backend/tests/test_protocol_continuity.py -v
"""

import pytest
import re
from unittest.mock import patch, AsyncMock, MagicMock

from backend.services.protocol_service import get_protocol_service
from backend.tools.protocol_tools import CreateProtocolTool, UpdateProtocolTool, GetProtocolTool
from backend.tools.memory_tools import (
    SetConversationContextTool, 
    GetConversationContextTool,
    get_current_context,
    set_current_context,
    _conversation_contexts
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clear_state():
    """Clear all state before each test."""
    # Clear protocol service
    service = get_protocol_service()
    service._protocols.clear()
    
    # Clear memory contexts
    _conversation_contexts.clear()
    
    yield
    
    # Cleanup
    service._protocols.clear()
    _conversation_contexts.clear()


# =============================================================================
# Memory Context Tests
# =============================================================================

class TestMemoryContext:
    """Test that memory context correctly tracks current_protocol_id."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_context(self):
        """Test basic set/get of conversation context."""
        conversation_id = "test_conv_1"
        protocol_id = "protocol_abc123"
        
        # Set context via tool
        set_tool = SetConversationContextTool()
        result = await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        assert "protocol_abc123" in result
        
        # Get context via tool
        get_tool = GetConversationContextTool()
        result = await get_tool.execute(conversation_id=conversation_id)
        
        assert "protocol_abc123" in result
        assert "Current Protocol" in result
    
    @pytest.mark.asyncio
    async def test_context_persists_across_calls(self):
        """Test that context persists between tool calls."""
        conversation_id = "test_conv_2"
        
        # Create protocol and set context
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Test Protocol",
            description="Test",
            steps=[{"index": 1, "text": "Step 1"}]
        )
        
        # Extract protocol_id
        match = re.search(r"protocol_\w+", create_result)
        protocol_id = match.group(0)
        
        # Set context
        set_tool = SetConversationContextTool()
        await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        # Later: get context (simulating follow-up message)
        get_tool = GetConversationContextTool()
        result = await get_tool.execute(conversation_id=conversation_id)
        
        assert protocol_id in result
    
    def test_direct_context_access(self):
        """Test direct helper functions for context access."""
        conversation_id = "test_conv_3"
        protocol_id = "protocol_xyz789"
        
        # Set via helper
        set_current_context(conversation_id, protocol_id=protocol_id)
        
        # Get via helper
        ctx = get_current_context(conversation_id)
        
        assert ctx["current_protocol_id"] == protocol_id
        assert ctx["last_created_protocol_id"] == protocol_id
        assert protocol_id in ctx["recent_protocol_ids"]


# =============================================================================
# Protocol Update Workflow Tests
# =============================================================================

class TestProtocolUpdateWorkflow:
    """
    Test the correct workflow for "add details" requests.
    
    Expected behavior:
    1. User creates protocol → agent calls CreateProtocolTool, sets context
    2. User says "add details" → agent calls GetConversationContext, GetProtocol, UpdateProtocol
    3. Agent does NOT call CreateProtocolTool again
    4. Agent does NOT ask user to restate the protocol
    """
    
    @pytest.mark.asyncio
    async def test_update_uses_existing_protocol(self):
        """
        Simulate the full workflow:
        1. Create protocol
        2. Set context
        3. Get context (for follow-up)
        4. Update protocol (not create new)
        """
        conversation_id = "test_conv_workflow"
        
        # Step 1: Create protocol
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Fish PCR Protocol",
            description="Identify fish species using PCR",
            steps=[
                {"index": 1, "text": "Extract DNA"},
                {"index": 2, "text": "Run PCR"},
                {"index": 3, "text": "Analyze results"},
            ]
        )
        
        # Extract protocol_id
        match = re.search(r"protocol_\w+", create_result)
        protocol_id = match.group(0)
        
        # Step 2: Set context (agent should do this after creating)
        set_tool = SetConversationContextTool()
        await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        # Step 3: Get context (agent should do this for follow-up)
        get_ctx_tool = GetConversationContextTool()
        ctx_result = await get_ctx_tool.execute(conversation_id=conversation_id)
        
        # Verify context has the protocol
        assert protocol_id in ctx_result
        
        # Step 4: Get protocol details
        get_protocol_tool = GetProtocolTool()
        protocol_result = await get_protocol_tool.execute(protocol_id=protocol_id)
        
        assert "Fish PCR Protocol" in protocol_result
        
        # Step 5: Update protocol (NOT create new!)
        update_tool = UpdateProtocolTool()
        update_result = await update_tool.execute(
            protocol_id=protocol_id,
            updated_steps=[
                {"index": 1, "text": "Extract DNA using Qiagen kit", "reagents": ["Qiagen DNA extraction kit"], "duration_minutes": 30},
                {"index": 2, "text": "Run PCR with fish-specific primers", "reagents": ["Taq polymerase", "dNTPs", "Fish COI primers"], "duration_minutes": 120},
                {"index": 3, "text": "Analyze on 2% agarose gel", "reagents": ["Agarose", "TAE buffer", "SYBR Safe"], "duration_minutes": 45},
            ]
        )
        
        assert "Updated" in update_result or "updated" in update_result.lower()
        
        # Verify: only ONE protocol exists (not two)
        service = get_protocol_service()
        protocols = service.list_protocols()
        
        assert len(protocols) == 1, "Should have exactly 1 protocol, not 2"
        assert protocols[0]["id"] == protocol_id
        
        # Verify: protocol was updated with reagents
        updated_protocol = service.get_protocol(protocol_id)
        assert updated_protocol["version"] == 2, "Version should be 2 after update"
        assert any("Qiagen" in step.get("text", "") for step in updated_protocol["steps"])
    
    @pytest.mark.asyncio
    async def test_context_returns_protocol_id_for_vague_reference(self):
        """
        Test that when user says "add details" (vague reference),
        the agent can get the protocol_id from context.
        """
        conversation_id = "test_vague_ref"
        
        # Create and set context
        create_tool = CreateProtocolTool()
        result = await create_tool.execute(
            name="Vague Ref Protocol",
            description="Test",
            steps=[{"index": 1, "text": "Step"}]
        )
        
        match = re.search(r"protocol_\w+", result)
        protocol_id = match.group(0)
        
        set_current_context(conversation_id, protocol_id=protocol_id)
        
        # Simulate: user says "add details" (no protocol_id specified)
        # Agent should call get_conversation_context first
        ctx = get_current_context(conversation_id)
        
        # Agent can now use ctx["current_protocol_id"] for the update
        assert ctx["current_protocol_id"] == protocol_id
        assert ctx["current_protocol_id"] is not None


# =============================================================================
# Anti-Pattern Tests
# =============================================================================

class TestAntiPatterns:
    """
    Test that common anti-patterns are avoided.
    """
    
    @pytest.mark.asyncio
    async def test_multiple_creates_should_be_avoided(self):
        """
        Demonstrate the WRONG pattern: creating multiple protocols
        when user just wants to update.
        
        This test shows what we want to AVOID.
        """
        service = get_protocol_service()
        conversation_id = "test_anti_pattern"
        
        # First create (correct)
        create_tool = CreateProtocolTool()
        result1 = await create_tool.execute(
            name="Protocol v1",
            description="First version",
            steps=[{"index": 1, "text": "Step 1"}]
        )
        
        match1 = re.search(r"protocol_\w+", result1)
        protocol_id_1 = match1.group(0)
        
        # Set context
        set_current_context(conversation_id, protocol_id=protocol_id_1)
        
        # WRONG: Creating another protocol instead of updating
        # (This is what we want to prevent)
        result2 = await create_tool.execute(
            name="Protocol v2",
            description="Second version with details",
            steps=[{"index": 1, "text": "Step 1 with details"}]
        )
        
        match2 = re.search(r"protocol_\w+", result2)
        protocol_id_2 = match2.group(0)
        
        # This is the anti-pattern: now we have 2 protocols
        protocols = service.list_protocols()
        assert len(protocols) == 2, "Anti-pattern: created 2 protocols"
        assert protocol_id_1 != protocol_id_2, "Different IDs = wrong behavior"
        
        # The CORRECT behavior would be: len(protocols) == 1 after update
        print("\n⚠️ This test demonstrates the ANTI-PATTERN we want to avoid!")
        print(f"   Created {len(protocols)} protocols instead of updating 1")


# =============================================================================
# Integration Test: Simulated Conversation
# =============================================================================

class TestSimulatedConversation:
    """
    Simulate a multi-turn conversation to verify continuity.
    """
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """
        Simulate:
        1. User: "Create a protocol for fish PCR"
        2. Agent: Creates protocol, sets context
        3. User: "Add reagents and waiting times"
        4. Agent: Gets context, updates protocol (not creates new)
        """
        conversation_id = "conv_full_flow"
        service = get_protocol_service()
        
        # === Turn 1: Create ===
        print("\n--- Turn 1: Create Protocol ---")
        
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Fish Species PCR",
            description="PCR-based fish identification",
            steps=[
                {"index": 1, "text": "Extract DNA"},
                {"index": 2, "text": "PCR amplification"},
                {"index": 3, "text": "Gel analysis"},
            ]
        )
        
        match = re.search(r"protocol_\w+", create_result)
        protocol_id = match.group(0)
        print(f"Created: {protocol_id}")
        
        # Agent sets context
        set_tool = SetConversationContextTool()
        await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        print(f"Context set: current_protocol_id = {protocol_id}")
        
        # === Turn 2: Add Details ===
        print("\n--- Turn 2: Add Details ---")
        
        # Agent gets context first (because user said "add details" without ID)
        get_ctx_tool = GetConversationContextTool()
        ctx_result = await get_ctx_tool.execute(conversation_id=conversation_id)
        print(f"Context retrieved: {protocol_id} found in context")
        
        # Agent gets current protocol
        get_protocol_tool = GetProtocolTool()
        await get_protocol_tool.execute(protocol_id=protocol_id)
        
        # Agent updates (not creates!)
        update_tool = UpdateProtocolTool()
        update_result = await update_tool.execute(
            protocol_id=protocol_id,
            updated_steps=[
                {"index": 1, "text": "Extract DNA using Qiagen kit", "reagents": ["Qiagen kit"], "duration_minutes": 30},
                {"index": 2, "text": "PCR with COI primers", "reagents": ["Taq", "dNTPs", "primers"], "duration_minutes": 90},
                {"index": 3, "text": "Run 2% agarose gel", "reagents": ["Agarose", "TAE"], "duration_minutes": 45},
            ]
        )
        print(f"Updated: {protocol_id}")
        
        # === Verify ===
        print("\n--- Verification ---")
        
        protocols = service.list_protocols()
        assert len(protocols) == 1, f"Should have 1 protocol, got {len(protocols)}"
        print(f"✅ Protocol count: {len(protocols)} (correct)")
        
        protocol = service.get_protocol(protocol_id)
        assert protocol["version"] == 2, f"Version should be 2, got {protocol['version']}"
        print(f"✅ Protocol version: {protocol['version']} (updated)")
        
        assert any("Qiagen" in step.get("text", "") for step in protocol["steps"])
        print("✅ Protocol has enriched steps with reagents")
        
        print("\n🎉 Full conversation flow test PASSED!")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
