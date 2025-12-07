"""
Tests for ProtocolAgent and protocol tools.

Tests the protocol agent's ability to:
1. Create protocols via CreateProtocolTool
2. Retrieve protocols via GetProtocolTool
3. Update protocols via UpdateProtocolTool
4. List protocols via ListProtocolsTool
5. Find protocols for other agents via FindProtocolForAgentTool

Run with:
    pytest backend/tests/test_protocol_agent.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.agents.protocol_agent import ProtocolAgent
from backend.schemas.common import PageContext
from backend.main import classify_intent
from backend.services.protocol_service import ProtocolService, get_protocol_service


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


@pytest.fixture
def protocol_agent():
    """Create a ProtocolAgent instance."""
    return ProtocolAgent(
        workspace_id="test-workspace",
        user_id="test-user"
    )


@pytest.fixture
def fresh_protocol_service():
    """Create a fresh protocol service for testing."""
    # Reset singleton for clean test state
    service = get_protocol_service()
    service._protocols = {}
    return service


# =============================================================================
# Intent Router Tests
# =============================================================================

class TestIntentRouter:
    """Test intent classification for protocol queries."""
    
    def test_protocol_keywords(self):
        """Test that protocol keywords route to protocol_agent."""
        protocol_queries = [
            "find a protocol for staining mouse brain slides",
            "staining mouse brain tissue",
            "PCR protocol for gene amplification",
            "western blot protocol",
            "immunostaining procedure",
            "how to perform cell lysis",
            "create a protocol for DNA extraction",
            "modify my staining protocol",
            "list my protocols",
            "show saved protocols",
        ]
        
        for query in protocol_queries:
            agent_name, intent = classify_intent(query)
            assert agent_name == "protocol_agent", f"Failed for: {query}"
            assert intent == "protocol_operation", f"Failed for: {query}"
    
    def test_literature_keywords_not_protocol(self):
        """Test that literature keywords don't route to protocol_agent."""
        literature_queries = [
            "find papers on CRISPR",
            "search PubMed for gene editing",
        ]
        
        for query in literature_queries:
            agent_name, _ = classify_intent(query)
            assert agent_name == "literature_agent", f"Failed for: {query}"


# =============================================================================
# ProtocolAgent Tests
# =============================================================================

class TestProtocolAgent:
    """Test ProtocolAgent functionality."""
    
    def test_agent_initialization(self, protocol_agent):
        """Test agent initializes correctly."""
        assert protocol_agent.name == "protocol_agent"
        assert protocol_agent.workspace_id == "test-workspace"
        assert protocol_agent.user_id == "test-user"
        assert protocol_agent.available_tools is not None
    
    def test_agent_has_tools(self, protocol_agent):
        """Test agent has all required tools."""
        tool_names = [tool.name for tool in protocol_agent.available_tools.tools]
        assert "find_protocol_online" in tool_names
        assert "find_protocol_in_literature" in tool_names
        assert "create_protocol" in tool_names
        assert "update_protocol" in tool_names
        assert "get_protocol" in tool_names
        assert "list_protocols" in tool_names
        assert "find_protocol_for_agent" in tool_names


# =============================================================================
# Tool Tests
# =============================================================================

class TestCreateProtocolTool:
    """Test CreateProtocolTool."""
    
    @pytest.mark.asyncio
    async def test_create_protocol(self, fresh_protocol_service):
        """Test creating a protocol."""
        from backend.tools.protocol_tools import CreateProtocolTool
        
        tool = CreateProtocolTool()
        result = await tool.execute(
            name="Mouse Brain Staining Protocol",
            description="Standard immunostaining protocol for mouse brain sections",
            steps=[
                {"index": 1, "text": "Fix tissue in 4% PFA for 24 hours"},
                {"index": 2, "text": "Wash 3x with PBS"},
                {"index": 3, "text": "Block with 10% serum for 1 hour"},
            ],
            tags=["immunostaining", "mouse brain", "histology"],
            source_type="manual"
        )
        
        # Should confirm creation
        assert "Protocol Created" in result
        assert "protocol_" in result  # Should have protocol_id
        assert "Mouse Brain Staining" in result
        assert "3 steps" in result
    
    @pytest.mark.asyncio
    async def test_create_protocol_stored_in_service(self, fresh_protocol_service):
        """Test that protocol is actually stored in service."""
        from backend.tools.protocol_tools import CreateProtocolTool
        
        tool = CreateProtocolTool()
        await tool.execute(
            name="Test Protocol",
            description="A test protocol",
            steps=[{"index": 1, "text": "Step one"}],
            tags=["test"]
        )
        
        # Check service has the protocol
        protocols = fresh_protocol_service.list_protocols()
        assert len(protocols) == 1
        assert protocols[0]["name"] == "Test Protocol"


class TestGetProtocolTool:
    """Test GetProtocolTool."""
    
    @pytest.mark.asyncio
    async def test_get_protocol(self, fresh_protocol_service):
        """Test retrieving a protocol."""
        from backend.tools.protocol_tools import GetProtocolTool
        
        # First create a protocol
        protocol = fresh_protocol_service.create_protocol(
            name="Retrieval Test Protocol",
            description="Protocol for testing retrieval",
            steps=[
                {"index": 1, "text": "First step"},
                {"index": 2, "text": "Second step"},
            ],
            tags=["test"]
        )
        protocol_id = protocol["id"]
        
        # Now retrieve it
        tool = GetProtocolTool()
        result = await tool.execute(protocol_id=protocol_id)
        
        assert "Retrieval Test Protocol" in result
        assert "First step" in result
        assert "Second step" in result
        assert protocol_id in result
    
    @pytest.mark.asyncio
    async def test_get_protocol_not_found(self, fresh_protocol_service):
        """Test retrieving a non-existent protocol."""
        from backend.tools.protocol_tools import GetProtocolTool
        
        tool = GetProtocolTool()
        result = await tool.execute(protocol_id="nonexistent_id")
        
        assert "not found" in result.lower()


class TestUpdateProtocolTool:
    """Test UpdateProtocolTool."""
    
    @pytest.mark.asyncio
    async def test_update_protocol(self, fresh_protocol_service):
        """Test updating a protocol."""
        from backend.tools.protocol_tools import UpdateProtocolTool
        
        # First create a protocol
        protocol = fresh_protocol_service.create_protocol(
            name="Original Name",
            description="Original description",
            steps=[{"index": 1, "text": "Original step"}],
            tags=["original"]
        )
        protocol_id = protocol["id"]
        
        # Update it
        tool = UpdateProtocolTool()
        result = await tool.execute(
            protocol_id=protocol_id,
            updated_name="Updated Name",
            updated_steps=[
                {"index": 1, "text": "Updated step one"},
                {"index": 2, "text": "New step two"},
            ]
        )
        
        assert "Protocol Updated" in result
        assert "Updated Name" in result
        assert "name" in result.lower()
        assert "steps" in result.lower()
        
        # Verify in service
        updated = fresh_protocol_service.get_protocol(protocol_id)
        assert updated["name"] == "Updated Name"
        assert len(updated["steps"]) == 2
        assert updated["version"] == 2


class TestListProtocolsTool:
    """Test ListProtocolsTool."""
    
    @pytest.mark.asyncio
    async def test_list_protocols(self, fresh_protocol_service):
        """Test listing protocols."""
        from backend.tools.protocol_tools import ListProtocolsTool
        
        # Create some protocols
        fresh_protocol_service.create_protocol(
            name="Protocol A",
            description="First protocol",
            steps=[{"index": 1, "text": "Step"}],
            tags=["tag1"]
        )
        fresh_protocol_service.create_protocol(
            name="Protocol B",
            description="Second protocol",
            steps=[{"index": 1, "text": "Step"}],
            tags=["tag2"]
        )
        
        tool = ListProtocolsTool()
        result = await tool.execute()
        
        assert "Protocol A" in result
        assert "Protocol B" in result
        assert "2 total" in result
    
    @pytest.mark.asyncio
    async def test_list_protocols_empty(self, fresh_protocol_service):
        """Test listing when no protocols exist."""
        from backend.tools.protocol_tools import ListProtocolsTool
        
        tool = ListProtocolsTool()
        result = await tool.execute()
        
        assert "No protocols saved" in result


class TestFindProtocolForAgentTool:
    """Test FindProtocolForAgentTool."""
    
    @pytest.mark.asyncio
    async def test_find_protocol_for_agent(self, fresh_protocol_service):
        """Test finding protocols for another agent."""
        from backend.tools.protocol_tools import FindProtocolForAgentTool
        
        # Create a protocol that matches the query
        fresh_protocol_service.create_protocol(
            name="Mouse Brain Staining",
            description="Immunostaining protocol for mouse brain tissue",
            steps=[{"index": 1, "text": "Fix tissue"}],
            tags=["staining", "mouse", "brain"]
        )
        
        tool = FindProtocolForAgentTool()
        result = await tool.execute(query="mouse brain staining")
        
        assert "PROTOCOL_SEARCH_RESULTS" in result
        assert "LOCAL_PROTOCOLS" in result
        assert "Mouse Brain Staining" in result
    
    @pytest.mark.asyncio
    async def test_find_protocol_for_agent_no_match(self, fresh_protocol_service):
        """Test finding protocols when none match."""
        from backend.tools.protocol_tools import FindProtocolForAgentTool
        
        tool = FindProtocolForAgentTool()
        result = await tool.execute(query="nonexistent protocol type")
        
        assert "PROTOCOL_SEARCH_RESULTS" in result
        assert "LOCAL_PROTOCOLS: none" in result
    
    @pytest.mark.asyncio
    async def test_find_protocol_for_agent_with_external_sources(self, fresh_protocol_service):
        """Test that include_external flag suggests web and literature sources."""
        from backend.tools.protocol_tools import FindProtocolForAgentTool
        
        tool = FindProtocolForAgentTool()
        result = await tool.execute(query="staining protocol", include_external=True)
        
        # Should indicate external sources are available
        assert "SOURCES:" in result
        assert "Tavily" in result or "web" in result.lower()
        assert "Semantic Scholar" in result or "literature" in result.lower()
        assert "EXTERNAL_SOURCES" in result


class TestFindProtocolOnlineTool:
    """Test FindProtocolOnlineTool with mocked Tavily."""
    
    @pytest.mark.asyncio
    async def test_find_protocol_online_no_api_key(self):
        """Test search handles missing API key gracefully."""
        from backend.tools.protocol_tools import FindProtocolOnlineTool
        
        with patch("backend.tools.protocol_tools.config") as mock_config:
            mock_config.TAVILY_API_KEY = ""
            
            tool = FindProtocolOnlineTool()
            result = await tool.execute(query="test protocol")
            
            assert "Tavily API not configured" in result
    
    @pytest.mark.asyncio
    async def test_find_protocol_online_with_tavily_mock(self):
        """Test that FindProtocolOnlineTool returns web-based protocol candidates via Tavily."""
        from backend.tools.protocol_tools import FindProtocolOnlineTool
        
        # Mock Tavily response with protocol-like results
        mock_results = {
            "results": [
                {
                    "title": "Mouse Brain Immunostaining Protocol - protocols.io",
                    "url": "https://www.protocols.io/view/mouse-brain-staining",
                    "content": "A detailed protocol for immunostaining mouse brain sections. Includes fixation, blocking, and antibody incubation steps."
                },
                {
                    "title": "Brain Tissue Staining Guide - Abcam",
                    "url": "https://www.abcam.com/protocols/brain-staining",
                    "content": "Vendor application note for staining brain tissue with fluorescent antibodies."
                },
                {
                    "title": "Immunofluorescence Protocol for Brain Sections - JoVE",
                    "url": "https://www.jove.com/methods/brain-if",
                    "content": "Video protocol demonstrating immunofluorescence staining of mouse brain."
                }
            ]
        }
        
        with patch("backend.tools.protocol_tools.config") as mock_config:
            mock_config.TAVILY_API_KEY = "test_key"
            
            # Mock the tavily import inside the execute method
            with patch.dict("sys.modules", {"tavily": MagicMock()}):
                import sys
                mock_tavily_module = sys.modules["tavily"]
                mock_client = MagicMock()
                mock_client.search.return_value = mock_results
                mock_tavily_module.TavilyClient.return_value = mock_client
                
                tool = FindProtocolOnlineTool()
                result = await tool.execute(query="stain mouse brain slides")
                
                # Should indicate this is a web search via Tavily
                assert "Web Protocol Search" in result or "Tavily" in result
                # Should have protocol candidates
                assert "protocols.io" in result or "Mouse Brain" in result
                assert "Abcam" in result or "Brain Tissue" in result
                # Should have URLs
                assert "http" in result


class TestFindProtocolInLiteratureTool:
    """Test FindProtocolInLiteratureTool with mocked Semantic Scholar."""
    
    @pytest.mark.asyncio
    async def test_find_protocol_in_literature_with_mock(self):
        """Test that FindProtocolInLiteratureTool returns literature-based protocols."""
        from backend.tools.protocol_tools import FindProtocolInLiteratureTool
        
        # Mock Semantic Scholar response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "Optimized immunostaining protocol for mouse brain tissue",
                    "abstract": "We present an optimized protocol for immunofluorescence staining of mouse brain sections...",
                    "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
                    "year": 2023,
                    "url": "https://semanticscholar.org/paper/123",
                    "externalIds": {"DOI": "10.1038/s41596-023-0001"}
                },
                {
                    "title": "A standardized method for brain histology",
                    "abstract": "This paper describes a reproducible method for preparing and staining brain tissue...",
                    "authors": [{"name": "Brown K"}],
                    "year": 2022,
                    "url": "https://semanticscholar.org/paper/456",
                    "externalIds": {"DOI": "10.1016/j.methods.2022.01.001"}
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.tools.protocol_tools.requests.get", return_value=mock_response):
            tool = FindProtocolInLiteratureTool()
            result = await tool.execute(query="mouse brain staining")
            
            # Should indicate this is a literature search
            assert "Literature" in result
            # Should have paper results
            assert "immunostaining" in result.lower() or "Optimized" in result
            assert "Smith" in result or "2023" in result
            # Should have DOI
            assert "DOI" in result or "doi.org" in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestProtocolWorkflow:
    """Test complete protocol workflow."""
    
    @pytest.mark.asyncio
    async def test_create_update_retrieve_workflow(self, fresh_protocol_service):
        """Test full workflow: create, update, retrieve protocol."""
        from backend.tools.protocol_tools import (
            CreateProtocolTool,
            UpdateProtocolTool,
            GetProtocolTool,
        )
        
        # 1. Create protocol
        create_tool = CreateProtocolTool()
        create_result = await create_tool.execute(
            name="Workflow Test Protocol",
            description="Protocol for workflow testing",
            steps=[
                {"index": 1, "text": "Initial step 1"},
                {"index": 2, "text": "Initial step 2"},
            ],
            tags=["workflow", "test"]
        )
        assert "Protocol Created" in create_result
        
        # Extract protocol_id from result
        import re
        match = re.search(r"protocol_\w+", create_result)
        assert match, "Should have protocol_id in result"
        protocol_id = match.group(0)
        
        # 2. Update protocol
        update_tool = UpdateProtocolTool()
        update_result = await update_tool.execute(
            protocol_id=protocol_id,
            updated_steps=[
                {"index": 1, "text": "Updated step 1"},
                {"index": 2, "text": "Updated step 2"},
                {"index": 3, "text": "New step 3"},
            ]
        )
        assert "Protocol Updated" in update_result
        assert "steps (3 steps)" in update_result
        
        # 3. Retrieve and verify
        get_tool = GetProtocolTool()
        get_result = await get_tool.execute(protocol_id=protocol_id)
        assert "Workflow Test Protocol" in get_result
        assert "Updated step 1" in get_result
        assert "New step 3" in get_result
        assert "Version:** 2" in get_result


# =============================================================================
# Protocol Extraction Tool Tests
# =============================================================================

class TestExtractProtocolFromUrlTool:
    """Test ExtractProtocolFromUrlTool."""
    
    @pytest.mark.asyncio
    async def test_extract_from_url_success(self):
        """Test successful extraction from a URL."""
        from backend.tools.protocol_tools import ExtractProtocolFromUrlTool
        
        tool = ExtractProtocolFromUrlTool()
        
        # Mock Tavily extract response
        mock_extract_result = {
            "results": [{
                "raw_content": """# Immunofluorescence Staining Protocol
                
## Overview
This protocol describes immunofluorescence staining of mouse brain tissue sections
for visualization of neuronal markers.

## Materials
- Primary antibody (1:500 dilution)
- Secondary antibody (1:1000 dilution)
- PBS buffer

## Steps
1. Fix tissue in 4% PFA for 15 minutes at room temperature
2. Wash 3x with PBS for 5 minutes each
3. Block with 5% BSA for 1 hour at 37°C
4. Incubate with primary antibody overnight at 4°C
5. Wash 3x with PBS
6. Incubate with secondary antibody for 2 hours
7. Mount and image
"""
            }]
        }
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = "test-key"
            
            with patch.dict('sys.modules', {'tavily': MagicMock()}):
                import sys
                mock_tavily = sys.modules['tavily']
                mock_client = MagicMock()
                mock_client.extract.return_value = mock_extract_result
                mock_tavily.TavilyClient.return_value = mock_client
                
                result = await tool.execute(
                    url="https://protocols.io/view/immunofluorescence-staining",
                    context="mouse brain staining"
                )
                
                # Verify result contains expected sections
                assert "Protocol Extracted" in result
                assert "Overview" in result
                assert "Key Parameters" in result
                assert "Structure" in result
                assert "protocols.io" in result
    
    @pytest.mark.asyncio
    async def test_extract_from_url_invalid_url(self):
        """Test extraction with invalid URL."""
        from backend.tools.protocol_tools import ExtractProtocolFromUrlTool
        
        tool = ExtractProtocolFromUrlTool()
        
        result = await tool.execute(url="not-a-valid-url")
        
        assert "Invalid URL" in result
    
    @pytest.mark.asyncio
    async def test_extract_from_url_no_api_key(self):
        """Test extraction when Tavily API key is not configured."""
        from backend.tools.protocol_tools import ExtractProtocolFromUrlTool
        
        tool = ExtractProtocolFromUrlTool()
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = ""
            
            result = await tool.execute(url="https://example.com/protocol")
            
            assert "Extraction Failed" in result
            assert "not configured" in result.lower()
    
    @pytest.mark.asyncio
    async def test_extract_from_url_extraction_failure(self):
        """Test handling of extraction failures."""
        from backend.tools.protocol_tools import ExtractProtocolFromUrlTool
        
        tool = ExtractProtocolFromUrlTool()
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = "test-key"
            
            with patch.dict('sys.modules', {'tavily': MagicMock()}):
                import sys
                mock_tavily = sys.modules['tavily']
                mock_client = MagicMock()
                mock_client.extract.return_value = {"results": []}  # Empty results
                mock_tavily.TavilyClient.return_value = mock_client
                
                result = await tool.execute(url="https://example.com/blocked-page")
                
                assert "Extraction Failed" in result
                assert "Suggestions" in result


class TestExtractProtocolFromLiteratureLinkTool:
    """Test ExtractProtocolFromLiteratureLinkTool."""
    
    @pytest.mark.asyncio
    async def test_extract_from_doi(self):
        """Test extraction from a DOI."""
        from backend.tools.protocol_tools import ExtractProtocolFromLiteratureLinkTool
        
        tool = ExtractProtocolFromLiteratureLinkTool()
        
        # Mock Semantic Scholar response
        mock_paper_info = {
            "title": "A Novel Staining Protocol for Brain Tissue",
            "url": "https://www.semanticscholar.org/paper/abc123",
            "doi": "10.1038/s41586-021-03819-2",
            "pmc_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8123456/"
        }
        
        # Mock Tavily extract response
        mock_extract_result = {
            "results": [{
                "raw_content": """# Methods
                
## Tissue Preparation
Brain tissue was prepared using standard fixation protocols.
Samples were incubated at 37°C for 30 minutes.

## Staining Procedure
1. Preparation phase
2. Fixation phase  
3. Staining phase
4. Imaging phase
"""
            }]
        }
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = "test-key"
            
            with patch.object(tool, '_get_paper_info_by_doi', return_value=mock_paper_info):
                with patch.dict('sys.modules', {'tavily': MagicMock()}):
                    import sys
                    mock_tavily = sys.modules['tavily']
                    mock_client = MagicMock()
                    mock_client.extract.return_value = mock_extract_result
                    mock_tavily.TavilyClient.return_value = mock_client
                    
                    result = await tool.execute(
                        paper_id_or_url="10.1038/s41586-021-03819-2",
                        context="staining procedure"
                    )
                    
                    # Verify result contains expected sections
                    assert "Protocol Extracted from Literature" in result
                    assert "Methods Overview" in result
                    assert "Key Parameters" in result
    
    @pytest.mark.asyncio
    async def test_extract_from_pmid(self):
        """Test extraction from a PMID."""
        from backend.tools.protocol_tools import ExtractProtocolFromLiteratureLinkTool
        
        tool = ExtractProtocolFromLiteratureLinkTool()
        
        # Mock paper info
        mock_paper_info = {
            "title": "Test Paper",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "pmc_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456/"
        }
        
        mock_extract_result = {
            "results": [{
                "raw_content": "# Methods\nSample protocol content with 4°C incubation for 10 minutes."
            }]
        }
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = "test-key"
            
            with patch.object(tool, '_get_paper_info_by_pmid', return_value=mock_paper_info):
                with patch.dict('sys.modules', {'tavily': MagicMock()}):
                    import sys
                    mock_tavily = sys.modules['tavily']
                    mock_client = MagicMock()
                    mock_client.extract.return_value = mock_extract_result
                    mock_tavily.TavilyClient.return_value = mock_client
                    
                    result = await tool.execute(paper_id_or_url="12345678")
                    
                    assert "Protocol Extracted" in result or "Could not extract" in result
    
    @pytest.mark.asyncio
    async def test_extract_from_direct_url(self):
        """Test extraction when user provides a direct URL."""
        from backend.tools.protocol_tools import ExtractProtocolFromLiteratureLinkTool
        
        tool = ExtractProtocolFromLiteratureLinkTool()
        
        mock_extract_result = {
            "results": [{
                "raw_content": "# Protocol\nStep 1: Prepare samples at 25°C for 15 minutes."
            }]
        }
        
        with patch('backend.tools.protocol_tools.config') as mock_config:
            mock_config.TAVILY_API_KEY = "test-key"
            
            with patch.dict('sys.modules', {'tavily': MagicMock()}):
                import sys
                mock_tavily = sys.modules['tavily']
                mock_client = MagicMock()
                mock_client.extract.return_value = mock_extract_result
                mock_tavily.TavilyClient.return_value = mock_client
                
                result = await tool.execute(
                    paper_id_or_url="https://www.nature.com/articles/s41586-021-03819-2"
                )
                
                # Should attempt extraction from the URL directly
                assert "Protocol Extracted" in result or "Could not extract" in result
    
    @pytest.mark.asyncio
    async def test_extract_invalid_identifier(self):
        """Test extraction with invalid paper identifier."""
        from backend.tools.protocol_tools import ExtractProtocolFromLiteratureLinkTool
        
        tool = ExtractProtocolFromLiteratureLinkTool()
        
        result = await tool.execute(paper_id_or_url="invalid-identifier")
        
        assert "Could not parse" in result
        assert "DOI" in result
        assert "PMID" in result


class TestProtocolExtractionHelpers:
    """Test the helper functions for protocol extraction."""
    
    def test_extract_key_parameters(self):
        """Test extraction of key parameters from content."""
        from backend.tools.protocol_tools import _extract_key_parameters
        
        content = """
        Incubate at 37°C for 30 minutes.
        Add 10 mM buffer solution.
        Use mouse brain tissue samples.
        Wash for 5 min with PBS.
        """
        
        params = _extract_key_parameters(content)
        
        # Should extract temperatures, times, concentrations, sample types
        assert any("37" in p for p in params)  # Temperature
        assert any("30" in p or "5" in p for p in params)  # Time
        assert any("mM" in p for p in params)  # Concentration
        assert any("mouse" in p.lower() or "brain" in p.lower() for p in params)  # Sample type
    
    def test_extract_steps_overview(self):
        """Test extraction of steps overview."""
        from backend.tools.protocol_tools import _extract_steps_overview
        
        content = """
        1. Preparation step
        2. Fixation step
        3. Staining step
        4. Washing step
        5. Imaging step
        """
        
        overview = _extract_steps_overview(content)
        
        # Should detect ~5 steps
        assert "5" in overview or "step" in overview.lower()
    
    def test_extract_protocol_summary(self):
        """Test extraction of protocol summary."""
        from backend.tools.protocol_tools import _extract_protocol_summary
        
        content = """
        Abstract: This protocol describes a method for immunofluorescence staining
        of mouse brain tissue sections for visualization of neuronal markers.
        The procedure takes approximately 2 days to complete.
        
        Step 1: Fix tissue...
        """
        
        summary = _extract_protocol_summary(content, "brain staining")
        
        # Should extract from abstract section
        assert len(summary) > 50
        assert len(summary) <= 350  # Should be truncated


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
