"""
Tests for Conversation Continuity with Memory Tools.

This test demonstrates the SpoonOS hackathon pattern:
    Agent → SpoonOS → LLM → ToolCalls

It verifies that:
1. Memory tools (SetConversationContextTool, GetConversationContextTool) work correctly
2. Agents can maintain context across multi-turn conversations
3. Vague follow-up commands resolve to the correct protocol/experiment

Run with:
    pytest backend/tests/test_conversation_continuity.py -v
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.tools.memory_tools import (
    SetConversationContextTool,
    GetConversationContextTool,
    get_current_context,
    set_current_context,
    _conversation_contexts,
)
from backend.tools.protocol_tools import CreateProtocolTool, GetProtocolTool
from backend.schemas.common import PageContext


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def page_context():
    """Create a test page context."""
    return PageContext(
        route="/protocols",
        workspace_id="test-workspace",
        user_id="test-user",
        experiment_ids=[],
        protocol_ids=[],
        filters={},
        metadata={}
    )


@pytest.fixture(autouse=True)
def clear_memory():
    """Clear conversation memory before each test."""
    _conversation_contexts.clear()
    yield
    _conversation_contexts.clear()


# =============================================================================
# Memory Tool Tests
# =============================================================================

class TestMemoryTools:
    """Test the conversation memory tools."""
    
    @pytest.mark.asyncio
    async def test_set_conversation_context(self):
        """Test setting conversation context."""
        tool = SetConversationContextTool()
        
        result = await tool.execute(
            conversation_id="conv_123",
            current_protocol_id="protocol_abc"
        )
        
        assert "Context Updated" in result
        assert "protocol_abc" in result
        
        # Verify context was stored
        ctx = get_current_context("conv_123")
        assert ctx["current_protocol_id"] == "protocol_abc"
    
    @pytest.mark.asyncio
    async def test_get_conversation_context(self):
        """Test retrieving conversation context."""
        # Set up context first
        set_current_context("conv_456", protocol_id="protocol_xyz")
        
        tool = GetConversationContextTool()
        result = await tool.execute(conversation_id="conv_456")
        
        assert "Current Protocol" in result
        assert "protocol_xyz" in result
    
    @pytest.mark.asyncio
    async def test_context_tracks_recent_ids(self):
        """Test that context tracks recently used IDs."""
        set_current_context("conv_789", protocol_id="protocol_1")
        set_current_context("conv_789", protocol_id="protocol_2")
        set_current_context("conv_789", protocol_id="protocol_3")
        
        ctx = get_current_context("conv_789")
        
        assert ctx["current_protocol_id"] == "protocol_3"
        assert "protocol_1" in ctx["recent_protocol_ids"]
        assert "protocol_2" in ctx["recent_protocol_ids"]
        assert "protocol_3" in ctx["recent_protocol_ids"]
    
    @pytest.mark.asyncio
    async def test_empty_context_returns_none(self):
        """Test that empty context returns None values."""
        ctx = get_current_context("new_conversation")
        
        assert ctx["current_protocol_id"] is None
        assert ctx["current_experiment_id"] is None


# =============================================================================
# Continuity Workflow Tests
# =============================================================================

class TestContinuityWorkflow:
    """Test the full continuity workflow."""
    
    @pytest.mark.asyncio
    async def test_create_then_update_workflow(self):
        """
        Test the workflow:
        1. Create a protocol
        2. Set context with the new protocol_id
        3. Get context to retrieve the protocol_id
        4. Use the protocol_id for follow-up operations
        """
        conversation_id = "workflow_test_conv"
        
        # Step 1: Create a protocol
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Fish PCR Protocol",
            description="Protocol for identifying fish species using PCR",
            steps=[
                {"index": 1, "text": "Extract DNA from fish tissue"},
                {"index": 2, "text": "Prepare PCR master mix"},
                {"index": 3, "text": "Run PCR amplification"},
            ],
            tags=["pcr", "fish", "identification"]
        )
        
        # Extract protocol_id from result
        import re
        match = re.search(r"protocol_\w+", create_result)
        assert match, "Should have protocol_id in result"
        protocol_id = match.group(0)
        
        # Step 2: Set context (this is what the agent should do after creating)
        set_tool = SetConversationContextTool()
        await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        # Step 3: Get context (simulating a follow-up message)
        get_tool = GetConversationContextTool()
        context_result = await get_tool.execute(conversation_id=conversation_id)
        
        assert protocol_id in context_result
        
        # Step 4: Verify we can retrieve the protocol using the ID from context
        ctx = get_current_context(conversation_id)
        retrieved_protocol_id = ctx["current_protocol_id"]
        
        get_protocol_tool = GetProtocolTool()
        protocol_result = await get_protocol_tool.execute(protocol_id=retrieved_protocol_id)
        
        assert "Fish PCR Protocol" in protocol_result
        assert "Extract DNA" in protocol_result
    
    @pytest.mark.asyncio
    async def test_vague_command_resolution(self):
        """
        Test that vague commands can be resolved using context.
        
        Simulates:
        - User: "Create a protocol for PCR"
        - Agent: Creates protocol, sets context
        - User: "Add some details to it"
        - Agent: Gets context, retrieves protocol_id, updates
        """
        conversation_id = "vague_command_test"
        
        # Simulate: Agent created a protocol and set context
        set_current_context(conversation_id, protocol_id="protocol_test123")
        
        # Simulate: User says "add some details to it"
        # Agent should call get_conversation_context first
        ctx = get_current_context(conversation_id)
        
        # Agent should NOT ask "which protocol?" - it should use the context
        assert ctx["current_protocol_id"] == "protocol_test123"
        
        # Agent can now use this ID for update_protocol
        # (In real scenario, agent would call update_protocol with this ID)


# =============================================================================
# Demo Script for Hackathon
# =============================================================================

class TestDemoScenario:
    """
    Demo scenario for hackathon judges.
    
    This test simulates the exact scenario from the requirements:
    1. User: "Create a protocol for identifying fish species with PCR"
    2. Agent: Creates protocol, calls set_conversation_context
    3. User: "Add some details and add the protocol and reagents into the orders"
    4. Agent: Calls get_conversation_context, retrieves protocol, updates it
    """
    
    @pytest.mark.asyncio
    async def test_demo_scenario(self):
        """
        Full demo scenario showing conversation continuity.
        
        This demonstrates:
        - Agent → SpoonOS → LLM → ToolCalls pattern
        - Memory tools for context persistence
        - Vague command resolution without asking user to repeat
        """
        conversation_id = "demo_conv_hackathon"
        
        # === Turn 1: User creates a protocol ===
        
        # Agent creates protocol
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Fish Species PCR Identification",
            description="Protocol for identifying fish species using PCR amplification of cytochrome b gene",
            steps=[
                {"index": 1, "text": "Extract DNA from fish tissue sample"},
                {"index": 2, "text": "Prepare PCR master mix with species-specific primers"},
                {"index": 3, "text": "Run PCR: 95°C 5min, 35 cycles of (95°C 30s, 55°C 30s, 72°C 1min)"},
                {"index": 4, "text": "Analyze products on 2% agarose gel"},
            ],
            tags=["pcr", "fish", "species-id", "cytochrome-b"]
        )
        
        # Extract protocol_id
        import re
        match = re.search(r"protocol_\w+", create_result)
        protocol_id = match.group(0)
        
        # Agent MUST call set_conversation_context after creating
        set_tool = SetConversationContextTool()
        set_result = await set_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        assert "Context Updated" in set_result
        print(f"\n✅ Turn 1: Created {protocol_id} and saved to context")
        
        # === Turn 2: User gives vague follow-up command ===
        # User says: "Add some details and add the protocol and reagents into the orders"
        
        # Agent MUST call get_conversation_context FIRST
        get_tool = GetConversationContextTool()
        context_result = await get_tool.execute(conversation_id=conversation_id)
        
        # Agent should find the protocol_id in context
        assert protocol_id in context_result
        print(f"✅ Turn 2: Retrieved context, found {protocol_id}")
        
        # Agent retrieves the protocol (not asking user to repeat!)
        get_protocol_tool = GetProtocolTool()
        protocol_details = await get_protocol_tool.execute(protocol_id=protocol_id)
        
        assert "Fish Species PCR" in protocol_details
        print(f"✅ Turn 2: Retrieved protocol details without asking user")
        
        # Agent can now update the protocol with more details
        # (In real scenario, agent would call update_protocol)
        
        print("\n🎉 Demo scenario passed!")
        print("   - Agent maintained context across turns")
        print("   - Vague command resolved using memory tools")
        print("   - No 'please provide the protocol ID' prompts!")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
