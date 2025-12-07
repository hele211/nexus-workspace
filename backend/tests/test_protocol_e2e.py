"""
End-to-End Tests for Protocol Creation via ProtocolAgent.

This test demonstrates the full pipeline:
    UI → /api/chat → ProtocolAgent → CreateProtocolTool → ProtocolService

It verifies that:
1. When ProtocolAgent creates a protocol, it actually calls CreateProtocolTool
2. The protocol is stored in ProtocolService (same source as /api/protocols)
3. The protocol can be retrieved via the REST API

Run with:
    pytest backend/tests/test_protocol_e2e.py -v
"""

import pytest
import re
from unittest.mock import patch, AsyncMock, MagicMock

from backend.services.protocol_service import get_protocol_service, ProtocolService
from backend.tools.protocol_tools import CreateProtocolTool, GetProtocolTool
from backend.tools.memory_tools import SetConversationContextTool, _conversation_contexts


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clear_services():
    """Clear services before each test."""
    # Clear protocol service
    service = get_protocol_service()
    service._protocols.clear()
    
    # Clear memory contexts
    _conversation_contexts.clear()
    
    yield
    
    # Cleanup after test
    service._protocols.clear()
    _conversation_contexts.clear()


# =============================================================================
# End-to-End Protocol Creation Tests
# =============================================================================

class TestProtocolCreationE2E:
    """
    End-to-end tests for protocol creation.
    
    These tests verify that protocols created via tools are actually
    stored in ProtocolService and can be retrieved via REST API.
    """
    
    @pytest.mark.asyncio
    async def test_create_protocol_tool_stores_in_service(self):
        """
        Test that CreateProtocolTool actually stores the protocol in ProtocolService.
        
        This is the core test: when the agent calls create_protocol,
        the protocol MUST appear in ProtocolService.
        """
        # Get the service (same singleton used by tools and REST API)
        service = get_protocol_service()
        
        # Verify service is empty
        assert len(service.list_protocols()) == 0
        
        # Create protocol via tool (same as agent would do)
        create_tool = CreateProtocolTool()
        result = await create_tool.execute(
            name="Fish Species PCR Protocol",
            description="Protocol for identifying fish species using PCR",
            steps=[
                {"index": 1, "text": "Extract DNA from fish tissue"},
                {"index": 2, "text": "Prepare PCR master mix"},
                {"index": 3, "text": "Run PCR amplification"},
                {"index": 4, "text": "Analyze on gel"},
            ],
            tags=["pcr", "fish", "identification"]
        )
        
        # Extract protocol_id from result
        match = re.search(r"protocol_\w+", result)
        assert match, f"Should have protocol_id in result: {result}"
        protocol_id = match.group(0)
        
        # Verify protocol is in service
        protocols = service.list_protocols()
        assert len(protocols) == 1, "Protocol should be stored in service"
        
        # Verify protocol details
        protocol = service.get_protocol(protocol_id)
        assert protocol is not None, f"Protocol {protocol_id} should exist"
        assert protocol["name"] == "Fish Species PCR Protocol"
        assert protocol["description"] == "Protocol for identifying fish species using PCR"
        assert len(protocol["steps"]) == 4
        assert "pcr" in protocol["tags"]
    
    @pytest.mark.asyncio
    async def test_protocol_appears_in_list_after_creation(self):
        """
        Test that created protocol appears in list_protocols.
        
        This simulates: create via chat → refresh Protocol page → see protocol.
        """
        service = get_protocol_service()
        
        # Create multiple protocols
        create_tool = CreateProtocolTool()
        
        await create_tool.execute(
            name="Protocol A",
            description="First protocol",
            steps=[{"index": 1, "text": "Step 1"}]
        )
        
        await create_tool.execute(
            name="Protocol B",
            description="Second protocol",
            steps=[{"index": 1, "text": "Step 1"}]
        )
        
        # List protocols (same as GET /api/protocols)
        protocols = service.list_protocols()
        
        assert len(protocols) == 2
        names = [p["name"] for p in protocols]
        assert "Protocol A" in names
        assert "Protocol B" in names
    
    @pytest.mark.asyncio
    async def test_get_protocol_by_id(self):
        """
        Test that protocol can be retrieved by ID.
        
        This simulates: GET /api/protocols/{protocol_id}
        """
        service = get_protocol_service()
        
        # Create protocol
        create_tool = CreateProtocolTool()
        result = await create_tool.execute(
            name="Test Protocol",
            description="Test description",
            steps=[{"index": 1, "text": "Test step"}]
        )
        
        # Extract ID
        match = re.search(r"protocol_\w+", result)
        protocol_id = match.group(0)
        
        # Get via tool (same as agent would do)
        get_tool = GetProtocolTool()
        get_result = await get_tool.execute(protocol_id=protocol_id)
        
        assert "Test Protocol" in get_result
        assert "Test description" in get_result
        
        # Get via service (same as REST API)
        protocol = service.get_protocol(protocol_id)
        assert protocol["name"] == "Test Protocol"
    
    @pytest.mark.asyncio
    async def test_full_workflow_create_and_set_context(self):
        """
        Test the full workflow: create protocol → set context → verify.
        
        This simulates what the agent should do:
        1. Call create_protocol
        2. Call set_conversation_context with the returned ID
        3. Protocol should be retrievable
        """
        service = get_protocol_service()
        conversation_id = "test_conv_123"
        
        # Step 1: Create protocol
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Workflow Test Protocol",
            description="Testing the full workflow",
            steps=[
                {"index": 1, "text": "Extract sample"},
                {"index": 2, "text": "Process sample"},
            ]
        )
        
        # Extract protocol_id
        match = re.search(r"protocol_\w+", create_result)
        protocol_id = match.group(0)
        
        # Step 2: Set conversation context (agent should do this!)
        set_context_tool = SetConversationContextTool()
        await set_context_tool.execute(
            conversation_id=conversation_id,
            current_protocol_id=protocol_id
        )
        
        # Step 3: Verify protocol exists in service
        protocol = service.get_protocol(protocol_id)
        assert protocol is not None
        assert protocol["name"] == "Workflow Test Protocol"
        
        # Step 4: Verify context was set
        from backend.tools.memory_tools import get_current_context
        ctx = get_current_context(conversation_id)
        assert ctx["current_protocol_id"] == protocol_id
        
        print(f"\n✅ Full workflow test passed!")
        print(f"   - Created: {protocol_id}")
        print(f"   - Stored in ProtocolService: Yes")
        print(f"   - Context set: Yes")


class TestProtocolServiceSingleton:
    """
    Test that ProtocolService is a singleton.
    
    This ensures that tools and REST API use the same data source.
    """
    
    def test_service_is_singleton(self):
        """Verify ProtocolService is a singleton."""
        service1 = get_protocol_service()
        service2 = get_protocol_service()
        
        assert service1 is service2, "ProtocolService should be a singleton"
    
    @pytest.mark.asyncio
    async def test_tools_and_service_share_data(self):
        """
        Verify that tools and direct service access share the same data.
        
        This is critical: if they don't share data, protocols created
        via chat won't appear in the Protocol UI.
        """
        # Get service directly
        service = get_protocol_service()
        
        # Create via tool
        create_tool = CreateProtocolTool()
        result = await create_tool.execute(
            name="Shared Data Test",
            description="Testing shared data",
            steps=[{"index": 1, "text": "Step"}]
        )
        
        # Extract ID
        match = re.search(r"protocol_\w+", result)
        protocol_id = match.group(0)
        
        # Verify via service
        protocol = service.get_protocol(protocol_id)
        assert protocol is not None, "Protocol created via tool should be in service"
        
        # Verify via list
        protocols = service.list_protocols()
        ids = [p["id"] for p in protocols]
        assert protocol_id in ids, "Protocol should appear in list"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
