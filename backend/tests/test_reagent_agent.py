"""
Tests for ReagentAgent and reagent tools.

Tests the reagent agent's ability to:
1. Search for reagents online (with mocked Tavily)
2. Add reagents to inventory
3. Record usage and trigger low-inventory warnings
4. List low-inventory reagents

Run with:
    pytest backend/tests/test_reagent_agent.py -v
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.agents.reagent_agent import ReagentAgent
from backend.schemas.common import PageContext
from backend.main import classify_intent
from backend.services.reagent_service import ReagentService, get_reagent_service


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def page_context():
    """Create a test page context."""
    return PageContext(
        route="/reagents",
        workspace_id="test-workspace",
        user_id="test-user",
        experiment_ids=[],
        protocol_ids=[],
        filters={},
        metadata={}
    )


@pytest.fixture
def reagent_agent():
    """Create a ReagentAgent instance."""
    return ReagentAgent(
        workspace_id="test-workspace",
        user_id="test-user"
    )


@pytest.fixture
def fresh_reagent_service():
    """Create a fresh reagent service for testing."""
    # Reset singleton for clean test state
    service = get_reagent_service()
    service._reagents = {}
    service._usage_events = []
    return service


# =============================================================================
# Intent Router Tests
# =============================================================================

class TestIntentRouter:
    """Test intent classification for reagent queries."""
    
    def test_reagent_keywords(self):
        """Test that reagent keywords route to reagent_agent."""
        reagent_queries = [
            "find mouse CD64 antibody",
            "search for anti-human CD45 antibody",
            "add this antibody to my reagents",
            "I used 5 µL of reagent_abc123",
            "what reagents are low",
            "check my inventory",
            "log that I used some reagent",  # Changed from "log usage for experiment" which now routes to experiment_agent
            "find Abcam products",
            "search Thermo Fisher catalog",
            "what's running low",
        ]
        
        for query in reagent_queries:
            agent_name, intent = classify_intent(query)
            assert agent_name == "reagent_agent", f"Failed for: {query}"
            assert intent == "reagent_operation", f"Failed for: {query}"
    
    def test_literature_keywords_not_reagent(self):
        """Test that literature keywords don't route to reagent_agent."""
        literature_queries = [
            "find papers on CRISPR",
            "search PubMed for gene editing",
        ]
        
        for query in literature_queries:
            agent_name, _ = classify_intent(query)
            assert agent_name == "literature_agent", f"Failed for: {query}"


# =============================================================================
# ReagentAgent Tests
# =============================================================================

class TestReagentAgent:
    """Test ReagentAgent functionality."""
    
    def test_agent_initialization(self, reagent_agent):
        """Test agent initializes correctly."""
        assert reagent_agent.name == "reagent_agent"
        assert reagent_agent.workspace_id == "test-workspace"
        assert reagent_agent.user_id == "test-user"
        assert reagent_agent.available_tools is not None
    
    def test_agent_has_tools(self, reagent_agent):
        """Test agent has all required tools."""
        tool_names = [tool.name for tool in reagent_agent.available_tools.tools]
        assert "search_reagent_online" in tool_names
        assert "get_reagent_details_from_web" in tool_names
        assert "add_reagent_to_inventory" in tool_names
        assert "record_reagent_usage" in tool_names
        assert "list_low_inventory_reagents" in tool_names


# =============================================================================
# Tool Tests
# =============================================================================

class TestSearchReagentOnlineTool:
    """Test SearchReagentOnlineTool with mocked Tavily."""
    
    @pytest.mark.asyncio
    async def test_search_returns_ranked_list(self):
        """Test that search returns a ranked list with top recommendation."""
        from backend.tools.reagent_tools import SearchReagentOnlineTool
        
        # Mock Tavily response
        mock_results = {
            "results": [
                {
                    "title": "Mouse Anti-CD64 Antibody - Abcam",
                    "url": "https://www.abcam.com/products/ab12345",
                    "content": "High quality mouse anti-CD64 antibody, catalog AB-12345"
                },
                {
                    "title": "CD64 Antibody - BioLegend",
                    "url": "https://www.biolegend.com/products/cd64",
                    "content": "Flow cytometry validated CD64 antibody"
                }
            ]
        }
        
        with patch("backend.tools.reagent_tools.config") as mock_config:
            mock_config.TAVILY_API_KEY = "test_key"
            
            # Mock the tavily import inside the execute method
            with patch.dict("sys.modules", {"tavily": MagicMock()}):
                import sys
                mock_tavily_module = sys.modules["tavily"]
                mock_client = MagicMock()
                mock_client.search.return_value = mock_results
                mock_tavily_module.TavilyClient.return_value = mock_client
                
                tool = SearchReagentOnlineTool()
                result = await tool.execute(query="mouse CD64 antibody")
                
                # Should have top recommendation
                assert "Top Recommendation" in result
                assert "Abcam" in result or "BioLegend" in result
                assert "mouse" in result.lower() or "cd64" in result.lower()
    
    @pytest.mark.asyncio
    async def test_search_no_api_key(self):
        """Test search handles missing API key gracefully."""
        from backend.tools.reagent_tools import SearchReagentOnlineTool
        
        with patch("backend.tools.reagent_tools.config") as mock_config:
            mock_config.TAVILY_API_KEY = ""
            
            tool = SearchReagentOnlineTool()
            result = await tool.execute(query="test")
            
            assert "Tavily API not configured" in result


class TestAddReagentToInventoryTool:
    """Test AddReagentToInventoryTool."""
    
    @pytest.mark.asyncio
    async def test_add_reagent_creates_record(self, fresh_reagent_service):
        """Test that adding a reagent creates a record with reagent_id."""
        from backend.tools.reagent_tools import AddReagentToInventoryTool
        
        tool = AddReagentToInventoryTool()
        result = await tool.execute(
            name="Mouse Anti-CD64 Antibody",
            catalog_number="AB-12345",
            vendor="Abcam",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # Should confirm addition
        assert "Reagent Added" in result
        assert "reagent_" in result  # Should have reagent_id
        assert "AB-12345" in result
        assert "Abcam" in result
        assert "100" in result
        assert "µL" in result
    
    @pytest.mark.asyncio
    async def test_add_reagent_stored_in_service(self, fresh_reagent_service):
        """Test that reagent is actually stored in service."""
        from backend.tools.reagent_tools import AddReagentToInventoryTool
        
        tool = AddReagentToInventoryTool()
        await tool.execute(
            name="Test Reagent",
            catalog_number="TEST-001",
            vendor="TestVendor",
            storage_conditions="4°C",
            initial_quantity=50,
            unit="mL"
        )
        
        # Check service has the reagent
        reagent = fresh_reagent_service.get_reagent_by_catalog("TEST-001")
        assert reagent is not None
        assert reagent["name"] == "Test Reagent"
        assert reagent["current_quantity"] == 50


class TestRecordReagentUsageTool:
    """Test RecordReagentUsageTool."""
    
    @pytest.mark.asyncio
    async def test_record_usage_decreases_quantity(self, fresh_reagent_service):
        """Test that recording usage decreases quantity."""
        from backend.tools.reagent_tools import RecordReagentUsageTool
        
        # First add a reagent
        reagent = fresh_reagent_service.create_reagent(
            name="Test Antibody",
            catalog_number="TEST-002",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        reagent_id = reagent["reagent_id"]
        
        # Record usage
        tool = RecordReagentUsageTool()
        result = await tool.execute(
            reagent_id=reagent_id,
            amount_used=20,
            unit="µL"
        )
        
        # Should show before/after
        assert "Before" in result
        assert "After" in result
        assert "100" in result  # Before
        assert "80" in result   # After
    
    @pytest.mark.asyncio
    async def test_record_usage_triggers_low_inventory_warning(self, fresh_reagent_service):
        """Test that low inventory warning triggers when <10% remaining."""
        from backend.tools.reagent_tools import RecordReagentUsageTool
        
        # Add a reagent
        reagent = fresh_reagent_service.create_reagent(
            name="Low Stock Antibody",
            catalog_number="LOW-001",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        reagent_id = reagent["reagent_id"]
        
        # Use 95% of it
        tool = RecordReagentUsageTool()
        result = await tool.execute(
            reagent_id=reagent_id,
            amount_used=95,
            unit="µL"
        )
        
        # Should have low inventory warning
        assert "LOW INVENTORY" in result
        assert "10%" in result or "5%" in result or "less than" in result.lower()


class TestListLowInventoryReagentsTool:
    """Test ListLowInventoryReagentsTool."""
    
    @pytest.mark.asyncio
    async def test_list_low_inventory_shows_low_reagents(self, fresh_reagent_service):
        """Test that low inventory reagents are listed."""
        from backend.tools.reagent_tools import ListLowInventoryReagentsTool
        
        # Add a reagent and deplete it
        reagent = fresh_reagent_service.create_reagent(
            name="Nearly Empty Antibody",
            catalog_number="EMPTY-001",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # Use 95% of it
        fresh_reagent_service.record_usage(
            reagent_id=reagent["reagent_id"],
            amount_used=95,
            unit="µL"
        )
        
        # List low inventory
        tool = ListLowInventoryReagentsTool()
        result = await tool.execute()
        
        # Should show the low reagent
        assert "Nearly Empty Antibody" in result
        assert "EMPTY-001" in result
        assert "5" in result  # 5 µL remaining
    
    @pytest.mark.asyncio
    async def test_list_low_inventory_empty_when_all_good(self, fresh_reagent_service):
        """Test that no low inventory message when all is well."""
        from backend.tools.reagent_tools import ListLowInventoryReagentsTool
        
        # Add a well-stocked reagent
        fresh_reagent_service.create_reagent(
            name="Full Stock Antibody",
            catalog_number="FULL-001",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # List low inventory
        tool = ListLowInventoryReagentsTool()
        result = await tool.execute()
        
        # Should say no low inventory
        assert "No Low-Inventory" in result or "looks good" in result.lower()


# =============================================================================
# Integration Tests
# =============================================================================

class TestReagentWorkflow:
    """Test complete reagent workflow."""
    
    @pytest.mark.asyncio
    async def test_add_use_and_check_low_inventory(self, fresh_reagent_service):
        """Test full workflow: add reagent, use it, check low inventory."""
        from backend.tools.reagent_tools import (
            AddReagentToInventoryTool,
            RecordReagentUsageTool,
            ListLowInventoryReagentsTool,
        )
        
        # 1. Add reagent
        add_tool = AddReagentToInventoryTool()
        add_result = await add_tool.execute(
            name="Workflow Test Antibody",
            catalog_number="WORKFLOW-001",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        assert "Reagent Added" in add_result
        
        # Extract reagent_id from result
        import re
        match = re.search(r"reagent_\w+", add_result)
        assert match, "Should have reagent_id in result"
        reagent_id = match.group(0)
        
        # 2. Use most of it
        usage_tool = RecordReagentUsageTool()
        usage_result = await usage_tool.execute(
            reagent_id=reagent_id,
            amount_used=92,
            unit="µL"
        )
        assert "LOW INVENTORY" in usage_result
        
        # 3. Check low inventory list
        list_tool = ListLowInventoryReagentsTool()
        list_result = await list_tool.execute()
        assert "Workflow Test Antibody" in list_result
        assert "8" in list_result  # 8 µL remaining


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
