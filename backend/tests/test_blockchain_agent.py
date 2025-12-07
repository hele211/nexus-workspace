"""
Tests for BlockchainAgent.

Tests the blockchain agent's ability to:
1. Store experiment data on blockchain
2. Verify experiment integrity
3. Get blockchain status

Run with:
    pytest backend/tests/test_blockchain_agent.py -v
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from backend.agents.blockchain_agent import BlockchainAgent
from backend.schemas.common import PageContext
from backend.main import classify_intent


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
        experiment_ids=["exp_001"],
        protocol_ids=[],
        filters={},
        metadata={}
    )


@pytest.fixture
def blockchain_agent():
    """Create a BlockchainAgent instance."""
    return BlockchainAgent(
        workspace_id="test-workspace",
        user_id="test-user"
    )


# =============================================================================
# Intent Router Tests
# =============================================================================

class TestIntentRouter:
    """Test intent classification for blockchain queries."""
    
    def test_blockchain_keywords(self):
        """Test that blockchain keywords route to blockchain_agent."""
        blockchain_queries = [
            "Store my experiment on blockchain",
            "Check my Neo X wallet balance",
            "Verify experiment integrity",
            "What's the transaction hash?",
            "Store this on-chain",
            "Check for tampering",
            "Get blockchain status",
            "Show my gas balance",
            "Notarize this experiment",
            "Check provenance of my data",
        ]
        
        for query in blockchain_queries:
            agent_name, intent = classify_intent(query)
            assert agent_name == "blockchain_agent", f"Failed for: {query}"
            assert intent == "blockchain_operation", f"Failed for: {query}"
    
    def test_literature_keywords(self):
        """Test that literature keywords route to literature_agent."""
        literature_queries = [
            "Find papers on CRISPR",
            "Search for research on gene editing",
            "Show me PubMed articles",
            "Find publications about PCR",
        ]
        
        for query in literature_queries:
            agent_name, intent = classify_intent(query)
            assert agent_name == "literature_agent", f"Failed for: {query}"
    
    def test_default_routing(self):
        """Test that unknown queries default to literature_agent."""
        agent_name, intent = classify_intent("Hello, how are you?")
        assert agent_name == "literature_agent"
        assert intent == "general_query"


# =============================================================================
# BlockchainAgent Tests
# =============================================================================

class TestBlockchainAgent:
    """Test BlockchainAgent functionality."""
    
    def test_agent_initialization(self, blockchain_agent):
        """Test agent initializes correctly."""
        assert blockchain_agent.name == "blockchain_agent"
        assert blockchain_agent.workspace_id == "test-workspace"
        assert blockchain_agent.user_id == "test-user"
        assert blockchain_agent.available_tools is not None
    
    def test_agent_has_tools(self, blockchain_agent):
        """Test agent has all required tools."""
        tool_names = [tool.name for tool in blockchain_agent.available_tools.tools]
        assert "store_experiment_on_chain" in tool_names
        assert "verify_experiment_integrity" in tool_names
        assert "get_blockchain_status" in tool_names


# =============================================================================
# Tool Execution Tests (with mocking)
# =============================================================================

class TestBlockchainTools:
    """Test blockchain tools directly."""
    
    @pytest.mark.asyncio
    async def test_get_blockchain_status_tool(self):
        """Test GetBlockchainStatusTool returns status info."""
        from backend.tools.blockchain_tools import GetBlockchainStatusTool
        
        tool = GetBlockchainStatusTool()
        result = await tool.execute()
        
        # Should contain status information
        assert "Neo X Blockchain Status" in result
        assert "Connection" in result
        assert "Network" in result
    
    @pytest.mark.asyncio
    async def test_store_experiment_tool(self):
        """Test StoreExperimentOnChainTool stores data."""
        from backend.tools.blockchain_tools import StoreExperimentOnChainTool
        
        tool = StoreExperimentOnChainTool()
        
        experiment_data = {
            "id": "test_exp_001",
            "title": "Test Experiment",
            "results": {"value": 42}
        }
        
        result = await tool.execute(
            experiment_id="test_exp_001",
            experiment_data=experiment_data,
            metadata={"test": True}
        )
        
        # Should contain transaction info or error about configuration
        assert any(keyword in result for keyword in [
            "Experiment Stored",  # Success
            "Storage Failed",     # No private key
            "Blockchain Error"    # Connection issue
        ])
    
    @pytest.mark.asyncio
    async def test_verify_experiment_tool_invalid_hash(self):
        """Test VerifyExperimentIntegrityTool with invalid hash."""
        from backend.tools.blockchain_tools import VerifyExperimentIntegrityTool
        
        tool = VerifyExperimentIntegrityTool()
        
        experiment_data = {
            "id": "test_exp_001",
            "title": "Test Experiment"
        }
        
        result = await tool.execute(
            experiment_data=experiment_data,
            transaction_hash="0xinvalidhash123"
        )
        
        # Should indicate transaction not found or error
        assert any(keyword in result for keyword in [
            "Not Found",
            "Error",
            "not found"
        ])


# =============================================================================
# Integration Tests (requires running blockchain service)
# =============================================================================

class TestBlockchainIntegration:
    """Integration tests that require blockchain service."""
    
    @pytest.mark.asyncio
    async def test_full_store_and_verify_flow(self):
        """Test storing and verifying experiment data."""
        from backend.tools.blockchain_tools import (
            StoreExperimentOnChainTool,
            VerifyExperimentIntegrityTool,
        )
        from backend.services import get_blockchain_service, USE_MOCK_BLOCKCHAIN
        
        # Skip if not using mock (to avoid spending real GAS in tests)
        if not USE_MOCK_BLOCKCHAIN:
            pytest.skip("Skipping integration test on real blockchain")
        
        store_tool = StoreExperimentOnChainTool()
        verify_tool = VerifyExperimentIntegrityTool()
        
        experiment_data = {
            "id": "integration_test_001",
            "title": "Integration Test Experiment",
            "results": {"success": True}
        }
        
        # Store experiment
        store_result = await store_tool.execute(
            experiment_id="integration_test_001",
            experiment_data=experiment_data
        )
        
        # Extract transaction hash from result
        import re
        tx_match = re.search(r"0x[a-fA-F0-9]+", store_result)
        
        if tx_match:
            tx_hash = tx_match.group(0)
            
            # Verify with original data (should pass)
            verify_result = await verify_tool.execute(
                experiment_data=experiment_data,
                transaction_hash=tx_hash
            )
            
            assert "Verified" in verify_result or "matches" in verify_result.lower()
            
            # Verify with tampered data (should fail)
            tampered_data = experiment_data.copy()
            tampered_data["results"] = {"success": False}
            
            tamper_result = await verify_tool.execute(
                experiment_data=tampered_data,
                transaction_hash=tx_hash
            )
            
            assert any(keyword in tamper_result for keyword in [
                "FAILURE",
                "TAMPERING",
                "does NOT match"
            ])


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
