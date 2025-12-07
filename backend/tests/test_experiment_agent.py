"""
Tests for ExperimentAgent and experiment tools.

Tests the experiment agent's ability to:
1. Plan experiments with literature
2. Create experiments
3. Attach protocols and mark as completed (with auto reagent deduction)
4. Add manual reagent usage
5. Store experiments on blockchain
6. Analyze results with literature

Run with:
    pytest backend/tests/test_experiment_agent.py -v
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.agents.experiment_agent import ExperimentAgent
from backend.schemas.common import PageContext
from backend.main import classify_intent
from backend.services.experiment_service import ExperimentService, get_experiment_service
from backend.services.protocol_service import get_protocol_service
from backend.services.reagent_service import get_reagent_service


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def page_context():
    """Create a test page context."""
    return PageContext(
        route="/experiments",
        workspace_id="test-workspace",
        user_id="test-user",
        experiment_ids=[],
        protocol_ids=[],
        filters={},
        metadata={}
    )


# Note: ExperimentAgent requires full LLM setup, so we test tools directly
# Agent initialization tests are skipped


@pytest.fixture
def fresh_experiment_service():
    """Create a fresh experiment service for testing."""
    service = get_experiment_service()
    service._experiments = {}
    return service


@pytest.fixture
def fresh_protocol_service():
    """Create a fresh protocol service for testing."""
    service = get_protocol_service()
    service._protocols = {}
    return service


@pytest.fixture
def fresh_reagent_service():
    """Create a fresh reagent service for testing."""
    service = get_reagent_service()
    service._reagents = {}
    return service


# =============================================================================
# Intent Router Tests
# =============================================================================

class TestIntentRouter:
    """Test intent classification for experiment queries."""
    
    def test_experiment_keywords(self):
        """Test that experiment keywords route to experiment_agent."""
        experiment_queries = [
            "plan an experiment to test if Gene X regulates Y",
            "create an experiment for CRISPR gene editing",
            "mark exp_abc123 as completed",
            "list my experiments",
            "show experiments",
            "analyze the results of my experiment",
            "how can I test whether X affects Y",
            "design an experiment for protein expression",
        ]
        
        for query in experiment_queries:
            agent_name, intent = classify_intent(query)
            assert agent_name == "experiment_agent", f"Failed for: {query}"
            assert intent == "experiment_operation", f"Failed for: {query}"
    
    def test_blockchain_takes_priority(self):
        """Test that blockchain keywords take priority over experiment."""
        blockchain_queries = [
            "store experiment on blockchain",
            "verify experiment integrity on chain",
        ]
        
        for query in blockchain_queries:
            agent_name, _ = classify_intent(query)
            assert agent_name == "blockchain_agent", f"Failed for: {query}"


# =============================================================================
# ExperimentAgent Tests (skipped - requires LLM setup)
# =============================================================================

# Note: ExperimentAgent tests are skipped because they require full LLM configuration.
# The agent's tools are tested individually below.


# =============================================================================
# Tool Tests
# =============================================================================

class TestCreateExperimentTool:
    """Test CreateExperimentTool."""
    
    @pytest.mark.asyncio
    async def test_create_experiment(self, fresh_experiment_service):
        """Test creating an experiment."""
        from backend.tools.experiment_tools import CreateExperimentTool
        
        tool = CreateExperimentTool()
        result = await tool.execute(
            title="CRISPR Gene X Knockout",
            scientific_question="Does Gene X regulate Y in mouse brain?",
            description="Using CRISPR-Cas9 to knockout Gene X and measure Y expression",
            tags=["CRISPR", "mouse", "neuroscience"]
        )
        
        assert "Experiment Created" in result
        assert "exp_" in result  # Should have experiment_id
        assert "CRISPR Gene X Knockout" in result
        assert "planned" in result.lower()
    
    @pytest.mark.asyncio
    async def test_create_experiment_with_protocol(self, fresh_experiment_service, fresh_protocol_service):
        """Test creating experiment with linked protocol."""
        from backend.tools.experiment_tools import CreateExperimentTool
        
        # First create a protocol
        protocol = fresh_protocol_service.create_protocol(
            name="CRISPR Protocol",
            description="Standard CRISPR knockout protocol",
            steps=[{"index": 1, "text": "Design guide RNA"}],
            tags=["CRISPR"]
        )
        
        tool = CreateExperimentTool()
        result = await tool.execute(
            title="Gene X Knockout",
            scientific_question="Does Gene X regulate Y?",
            description="Testing Gene X function",
            protocol_id=protocol["id"]
        )
        
        assert "Experiment Created" in result
        assert "CRISPR Protocol" in result or protocol["id"] in result


class TestAttachProtocolTool:
    """Test AttachProtocolToExperimentTool."""
    
    @pytest.mark.asyncio
    async def test_attach_protocol(self, fresh_experiment_service, fresh_protocol_service):
        """Test attaching a protocol to an experiment."""
        from backend.tools.experiment_tools import AttachProtocolToExperimentTool
        
        # Create experiment and protocol
        experiment = fresh_experiment_service.create_experiment(
            title="Test Experiment",
            scientific_question="Test question",
            description="Test description"
        )
        protocol = fresh_protocol_service.create_protocol(
            name="Test Protocol",
            description="Test protocol",
            steps=[{"index": 1, "text": "Step 1"}]
        )
        
        tool = AttachProtocolToExperimentTool()
        result = await tool.execute(
            experiment_id=experiment["id"],
            protocol_id=protocol["id"]
        )
        
        assert "Protocol Attached" in result
        assert experiment["id"] in result
        assert "Test Protocol" in result


class TestMarkExperimentStatusTool:
    """Test MarkExperimentStatusTool with auto reagent deduction."""
    
    @pytest.mark.asyncio
    async def test_mark_status_completed_auto_deduces_reagents(
        self, 
        fresh_experiment_service, 
        fresh_protocol_service,
        fresh_reagent_service
    ):
        """Test that marking as completed auto-deduces reagent usage from protocol."""
        from backend.tools.experiment_tools import MarkExperimentStatusTool
        
        # Create a reagent
        reagent = fresh_reagent_service.create_reagent(
            name="Test Antibody",
            catalog_number="AB123",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # Create protocol with reagent reference (use 'reagents' key as protocol service normalizes to this)
        protocol = fresh_protocol_service.create_protocol(
            name="Staining Protocol",
            description="Protocol with reagent",
            steps=[{
                "index": 1,
                "text": "Add antibody",
                "reagents": [{
                    "reagent_id": reagent["reagent_id"],
                    "amount": 5,
                    "unit": "µL"
                }]
            }]
        )
        
        # Create experiment with protocol
        experiment = fresh_experiment_service.create_experiment(
            title="Test Experiment",
            scientific_question="Test question",
            description="Test description",
            protocol_id=protocol["id"]
        )
        
        # Mark as completed
        tool = MarkExperimentStatusTool()
        result = await tool.execute(
            experiment_id=experiment["id"],
            status="completed"
        )
        
        assert "Status Updated" in result
        assert "completed" in result.lower()
        assert "Auto-Logged" in result or "auto_from_protocol" in result.lower() or "reagent" in result.lower()
        
        # Verify reagent usage was added to experiment
        updated_exp = fresh_experiment_service.get_experiment(experiment["id"])
        assert len(updated_exp["reagent_usages"]) == 1
        assert updated_exp["reagent_usages"][0]["source"] == "auto_from_protocol"


class TestAddManualReagentUsageTool:
    """Test AddManualReagentUsageToExperimentTool."""
    
    @pytest.mark.asyncio
    async def test_add_manual_usage(
        self,
        fresh_experiment_service,
        fresh_reagent_service
    ):
        """Test adding manual reagent usage."""
        from backend.tools.experiment_tools import AddManualReagentUsageToExperimentTool
        
        # Create reagent
        reagent = fresh_reagent_service.create_reagent(
            name="Test Reagent",
            catalog_number="R123",
            vendor="TestVendor",
            storage_conditions="4°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # Create experiment
        experiment = fresh_experiment_service.create_experiment(
            title="Test Experiment",
            scientific_question="Test question",
            description="Test description"
        )
        
        tool = AddManualReagentUsageToExperimentTool()
        result = await tool.execute(
            experiment_id=experiment["id"],
            reagent_id=reagent["reagent_id"],
            amount=10,
            unit="µL"
        )
        
        assert "Reagent Usage Logged" in result
        assert "Test Reagent" in result
        assert "10" in result
        
        # Verify usage was added
        updated_exp = fresh_experiment_service.get_experiment(experiment["id"])
        assert len(updated_exp["reagent_usages"]) == 1
        assert updated_exp["reagent_usages"][0]["source"] == "manual"
        
        # Verify inventory was updated
        updated_reagent = fresh_reagent_service.get_reagent(reagent["reagent_id"])
        assert updated_reagent["current_quantity"] == 90


class TestStoreExperimentOnChainTool:
    """Test StoreExperimentOnChainForExperimentTool with mocked blockchain."""
    
    @pytest.mark.asyncio
    async def test_store_on_chain(self, fresh_experiment_service):
        """Test storing experiment on blockchain."""
        from backend.tools.experiment_tools import StoreExperimentOnChainForExperimentTool
        
        # Create experiment
        experiment = fresh_experiment_service.create_experiment(
            title="Blockchain Test Experiment",
            scientific_question="Test question",
            description="Test description",
            tags=["test"]
        )
        
        # Mock blockchain service
        mock_blockchain = MagicMock()
        mock_blockchain.store_experiment_hash = AsyncMock(return_value={
            "success": True,
            "tx_hash": "0xabc123def456",
            "explorer_url": "https://explorer.neo.org/tx/0xabc123def456"
        })
        
        with patch("backend.services.get_blockchain_service", return_value=mock_blockchain):
            tool = StoreExperimentOnChainForExperimentTool()
            result = await tool.execute(experiment_id=experiment["id"])
        
        assert "Stored on Blockchain" in result
        assert "0xabc123def456" in result
        assert "explorer" in result.lower()
        
        # Verify tx_hash was saved
        updated_exp = fresh_experiment_service.get_experiment(experiment["id"])
        assert updated_exp["blockchain_tx_hash"] == "0xabc123def456"


class TestAnalyzeExperimentResultsTool:
    """Test AnalyzeExperimentResultsWithLiteratureTool."""
    
    @pytest.mark.asyncio
    async def test_analyze_results(self, fresh_experiment_service):
        """Test analyzing experiment results with literature."""
        from backend.tools.experiment_tools import AnalyzeExperimentResultsWithLiteratureTool
        
        # Create experiment
        experiment = fresh_experiment_service.create_experiment(
            title="Gene X Knockout",
            scientific_question="Does Gene X regulate Y?",
            description="CRISPR knockout experiment"
        )
        
        # Mock literature search
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "Gene X regulates Y in neural development",
                    "year": 2023,
                    "externalIds": {"DOI": "10.1234/test"}
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.tools.experiment_tools.requests.get", return_value=mock_response):
            tool = AnalyzeExperimentResultsWithLiteratureTool()
            result = await tool.execute(
                experiment_id=experiment["id"],
                results_summary="Gene X knockout reduced Y expression by 50%"
            )
        
        assert "Results Analysis" in result
        assert "Gene X Knockout" in result
        assert "Literature" in result
        
        # Verify results summary was saved
        updated_exp = fresh_experiment_service.get_experiment(experiment["id"])
        assert "50%" in updated_exp["results_summary"]


class TestGetExperimentTool:
    """Test GetExperimentTool."""
    
    @pytest.mark.asyncio
    async def test_get_experiment(self, fresh_experiment_service):
        """Test retrieving an experiment."""
        from backend.tools.experiment_tools import GetExperimentTool
        
        experiment = fresh_experiment_service.create_experiment(
            title="Retrieval Test",
            scientific_question="Test question",
            description="Test description",
            tags=["test"]
        )
        
        tool = GetExperimentTool()
        result = await tool.execute(experiment_id=experiment["id"])
        
        assert "Retrieval Test" in result
        assert experiment["id"] in result
        assert "planned" in result.lower()


class TestListExperimentsTool:
    """Test ListExperimentsTool."""
    
    @pytest.mark.asyncio
    async def test_list_experiments(self, fresh_experiment_service):
        """Test listing experiments."""
        from backend.tools.experiment_tools import ListExperimentsTool
        
        fresh_experiment_service.create_experiment(
            title="Experiment A",
            scientific_question="Question A",
            description="Description A"
        )
        fresh_experiment_service.create_experiment(
            title="Experiment B",
            scientific_question="Question B",
            description="Description B"
        )
        
        tool = ListExperimentsTool()
        result = await tool.execute()
        
        assert "Experiment A" in result
        assert "Experiment B" in result
        assert "2 total" in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestExperimentWorkflow:
    """Test complete experiment workflow."""
    
    @pytest.mark.asyncio
    async def test_plan_create_complete_workflow(
        self,
        fresh_experiment_service,
        fresh_protocol_service,
        fresh_reagent_service
    ):
        """Test full workflow: plan, create, attach protocol, complete."""
        from backend.tools.experiment_tools import (
            CreateExperimentTool,
            AttachProtocolToExperimentTool,
            MarkExperimentStatusTool,
        )
        
        # 1. Create a reagent
        reagent = fresh_reagent_service.create_reagent(
            name="Workflow Reagent",
            catalog_number="WR123",
            vendor="TestVendor",
            storage_conditions="-20°C",
            initial_quantity=100,
            unit="µL"
        )
        
        # 2. Create a protocol with reagent reference (use 'reagents' key)
        protocol = fresh_protocol_service.create_protocol(
            name="Workflow Protocol",
            description="Protocol for workflow test",
            steps=[{
                "index": 1,
                "text": "Use reagent",
                "reagents": [{
                    "reagent_id": reagent["reagent_id"],
                    "amount": 10,
                    "unit": "µL"
                }]
            }]
        )
        
        # 3. Create experiment
        create_tool = CreateExperimentTool()
        create_result = await create_tool.execute(
            title="Workflow Test Experiment",
            scientific_question="Does workflow work?",
            description="Testing the complete workflow"
        )
        assert "Experiment Created" in create_result
        
        # Extract experiment_id
        import re
        match = re.search(r"exp_\w+", create_result)
        assert match, "Should have experiment_id in result"
        experiment_id = match.group(0)
        
        # 4. Attach protocol
        attach_tool = AttachProtocolToExperimentTool()
        attach_result = await attach_tool.execute(
            experiment_id=experiment_id,
            protocol_id=protocol["id"]
        )
        assert "Protocol Attached" in attach_result
        
        # 5. Mark as completed (should auto-deduce reagent usage)
        status_tool = MarkExperimentStatusTool()
        status_result = await status_tool.execute(
            experiment_id=experiment_id,
            status="completed"
        )
        assert "Status Updated" in status_result
        assert "completed" in status_result.lower()
        
        # 6. Verify final state
        experiment = fresh_experiment_service.get_experiment(experiment_id)
        assert experiment["status"] == "completed"
        assert experiment["protocol_id"] == protocol["id"]
        assert len(experiment["reagent_usages"]) == 1
        assert experiment["reagent_usages"][0]["source"] == "auto_from_protocol"
        
        # 7. Verify reagent inventory was updated
        updated_reagent = fresh_reagent_service.get_reagent(reagent["reagent_id"])
        assert updated_reagent["current_quantity"] == 90  # 100 - 10


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
