"""
Protocol tools for finding, creating, and managing lab protocols.

Provides tools for:
- FindProtocolOnlineTool: Search web for protocols via Tavily
- FindProtocolInLiteratureTool: Search literature for protocol methods
- CreateProtocolTool: Create local protocols
- UpdateProtocolTool: Modify existing protocols
- GetProtocolTool: Retrieve a protocol by ID
- ListProtocolsTool: List available protocols
- FindProtocolForAgentTool: Machine-friendly protocol lookup for other agents

All tools follow SpoonOS BaseTool patterns with async execute methods.
"""

import asyncio
from typing import Any, Dict, List, Optional

import requests
from spoon_ai.tools.base import BaseTool

from backend import config
from backend.services.protocol_service import get_protocol_service


# =============================================================================
# Tavily Extraction Helper
# =============================================================================

async def _extract_protocol_from_url_helper(
    url: str,
    context: str = "",
    extract_depth: str = "advanced"
) -> dict:
    """
    Shared helper for extracting protocol content from a URL using Tavily.
    
    Uses Tavily's extract API with advanced depth for complex protocol pages.
    Returns structured data with title, summary, key parameters, and source info.
    
    Args:
        url: URL to extract content from
        context: Optional context hint (e.g., "staining mouse brain slides")
        extract_depth: "basic" or "advanced" (default: advanced for complex pages)
        
    Returns:
        dict with keys: success, title, summary, key_parameters, steps_overview, source_url, error
    """
    if not config.TAVILY_API_KEY:
        return {
            "success": False,
            "error": "Tavily API not configured. Set ELEVENLABS_API_KEY in backend .env",
            "title": None,
            "summary": None,
            "key_parameters": [],
            "steps_overview": None,
            "source_url": url
        }
    
    try:
        from tavily import TavilyClient
        import asyncio
        
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        # Run blocking Tavily call in executor
        loop = asyncio.get_event_loop()
        
        def do_extract():
            return client.extract(
                urls=url,
                extract_depth=extract_depth,
                format="markdown",
                timeout=30
            )
        
        result = await loop.run_in_executor(None, do_extract)
        
        # Parse extraction results
        results = result.get("results", [])
        
        if not results:
            return {
                "success": False,
                "error": "No content could be extracted from the URL",
                "title": None,
                "summary": None,
                "key_parameters": [],
                "steps_overview": None,
                "source_url": url
            }
        
        # Get first result (single URL extraction)
        extracted = results[0]
        raw_content = extracted.get("raw_content", "")
        
        if not raw_content or len(raw_content) < 50:
            return {
                "success": False,
                "error": "Extracted content too short or empty (page may be blocked or require login)",
                "title": None,
                "summary": None,
                "key_parameters": [],
                "steps_overview": None,
                "source_url": url
            }
        
        # Parse the content to extract protocol-relevant info
        # We do NOT copy exact steps - only high-level summary
        title = _extract_title_from_content(raw_content, url)
        summary = _extract_protocol_summary(raw_content, context)
        key_params = _extract_key_parameters(raw_content)
        steps_overview = _extract_steps_overview(raw_content)
        
        return {
            "success": True,
            "error": None,
            "title": title,
            "summary": summary,
            "key_parameters": key_params,
            "steps_overview": steps_overview,
            "source_url": url
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "Tavily package not installed. Run: pip install tavily-python",
            "title": None,
            "summary": None,
            "key_parameters": [],
            "steps_overview": None,
            "source_url": url
        }
    except Exception as e:
        error_msg = str(e)
        # Handle common errors gracefully
        if "timeout" in error_msg.lower():
            error_msg = "Request timed out - the page may be slow or unavailable"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            error_msg = "Access forbidden - the page may require authentication"
        elif "404" in error_msg:
            error_msg = "Page not found - check the URL"
        
        return {
            "success": False,
            "error": f"Extraction failed: {error_msg}",
            "title": None,
            "summary": None,
            "key_parameters": [],
            "steps_overview": None,
            "source_url": url
        }


def _extract_title_from_content(content: str, url: str) -> str:
    """Extract a title from the content or URL."""
    import re
    
    # Try to find a title in markdown headers
    title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()[:100]
    
    # Try first line if it looks like a title
    first_line = content.split('\n')[0].strip()
    if first_line and len(first_line) < 150 and not first_line.startswith('http'):
        return first_line[:100]
    
    # Fall back to URL-based title
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    if path_parts:
        return path_parts[-1].replace('-', ' ').replace('_', ' ').title()[:100]
    
    return "Protocol Page"


def _extract_protocol_summary(content: str, context: str) -> str:
    """
    Extract a high-level summary of the protocol.
    
    IMPORTANT: Does NOT copy exact steps - only provides overview.
    """
    import re
    
    # Look for abstract/overview sections
    summary_patterns = [
        r'(?:abstract|overview|introduction|summary|description)[:\s]*(.{100,500})',
        r'(?:this protocol|this method|this procedure)[:\s]*(.{100,400})',
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            summary = match.group(1).strip()
            # Clean up and truncate
            summary = re.sub(r'\s+', ' ', summary)
            if len(summary) > 300:
                summary = summary[:300] + "..."
            return summary
    
    # Fall back to first substantial paragraph
    paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 100]
    if paragraphs:
        summary = paragraphs[0][:300]
        if len(paragraphs[0]) > 300:
            summary += "..."
        return summary
    
    return f"Protocol related to: {context}" if context else "Protocol details available at source URL"


def _extract_key_parameters(content: str) -> list:
    """
    Extract key parameters like temperatures, times, concentrations.
    
    Returns list of parameter strings (e.g., ["37°C incubation", "10 min wash"]).
    """
    import re
    
    parameters = []
    
    # Temperature patterns
    temp_matches = re.findall(r'(\d+)\s*°?\s*[Cc](?:elsius)?', content)
    for temp in set(temp_matches[:3]):  # Limit to 3 unique temps
        parameters.append(f"{temp}°C")
    
    # Time patterns
    time_matches = re.findall(r'(\d+)\s*(min(?:ute)?s?|hours?|hrs?|seconds?|secs?|overnight)', content, re.IGNORECASE)
    for time_val, unit in time_matches[:3]:
        parameters.append(f"{time_val} {unit}")
    
    # Concentration patterns
    conc_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(mM|µM|nM|mg/ml|µg/ml|%)', content, re.IGNORECASE)
    for val, unit in conc_matches[:3]:
        parameters.append(f"{val} {unit}")
    
    # Sample type patterns
    sample_matches = re.findall(r'(tissue|cells?|blood|serum|plasma|brain|liver|kidney|mouse|rat|human)', content, re.IGNORECASE)
    for sample in set(sample_matches[:2]):
        parameters.append(sample.lower())
    
    return list(set(parameters))[:8]  # Dedupe and limit


def _extract_steps_overview(content: str) -> str:
    """
    Extract a HIGH-LEVEL overview of protocol steps.
    
    IMPORTANT: Does NOT copy exact step text - only counts and categorizes.
    """
    import re
    
    # Count numbered steps
    step_matches = re.findall(r'(?:^|\n)\s*(?:step\s*)?(\d+)[.):]\s*', content, re.IGNORECASE)
    num_steps = len(set(step_matches)) if step_matches else 0
    
    # Look for major phases/sections
    phases = []
    phase_patterns = [
        r'(preparation|setup|fixation|staining|washing|incubation|imaging|analysis|harvest)',
        r'(day\s*\d+|phase\s*\d+|part\s*\d+)',
    ]
    
    for pattern in phase_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        phases.extend([m.lower() for m in matches])
    
    phases = list(set(phases))[:5]
    
    if num_steps > 0:
        overview = f"~{num_steps} steps"
        if phases:
            overview += f" covering: {', '.join(phases)}"
        return overview
    elif phases:
        return f"Protocol phases: {', '.join(phases)}"
    else:
        return "Multi-step protocol (see source for details)"


# =============================================================================
# Web Search Tools
# =============================================================================

class FindProtocolOnlineTool(BaseTool):
    """
    Search the GENERAL WEB for protocols via Tavily API.
    
    Uses the Tavily search API (tavily-python client) to find practical protocol
    writeups from:
    - Protocol repositories (protocols.io, bio-protocol.org)
    - Vendor application notes and technical guides
    - Lab blogs and method tutorials
    - JoVE video protocols
    
    This is complementary to FindProtocolInLiteratureTool which searches
    academic papers. Use BOTH tools together for comprehensive protocol discovery.
    
    Note: Only returns high-level summaries to respect copyright.
    Does NOT copy step-by-step procedures verbatim.
    """
    
    name: str = "find_protocol_online"
    description: str = """Search the GENERAL WEB via Tavily for practical protocol writeups.
Searches protocol repositories, vendor application notes, lab blogs, and tutorials.
Use alongside find_protocol_in_literature for comprehensive protocol discovery.
Returns a ranked list of web-based protocol candidates with URLs and brief summaries.
Does NOT copy exact steps - only provides high-level overviews."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Task or protocol to search for (e.g., 'stain mouse brain slides')"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, **kwargs) -> str:
        """
        Search for protocols online.
        
        Args:
            query: Task or protocol description
            
        Returns:
            Formatted string with protocol candidates
        """
        if not config.TAVILY_API_KEY:
            return """❌ **Tavily API not configured**

To enable protocol search, add your Tavily API key to `.env`:
```
TAVILY_API_KEY=your_api_key_here
```

Get an API key at: https://tavily.com/"""
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=config.TAVILY_API_KEY)
            
            # Search with focus on protocol content
            search_query = f"{query} protocol method procedure steps"
            
            response = client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_domains=[
                    "protocols.io",
                    "nature.com",
                    "springer.com",
                    "ncbi.nlm.nih.gov",
                    "bio-protocol.org",
                    "jove.com",
                    "currentprotocols.com"
                ]
            )
            
            results = response.get("results", [])
            
            if not results:
                return f"""🔍 **No protocols found for:** {query}

Try:
- Using more specific terms (e.g., "immunofluorescence staining protocol mouse brain")
- Including the technique name
- Checking spelling"""
            
            # Format results
            response_lines = [f"🌐 **Web Protocol Search (Tavily) for:** {query}\n"]
            
            for i, result in enumerate(results, 1):
                title = result.get("title", "Unknown Protocol")[:80]
                url = result.get("url", "")
                content = result.get("content", "")
                
                # Extract brief description (first ~150 chars)
                description = content[:150] + "..." if len(content) > 150 else content
                
                response_lines.append(f"**{i}. {title}**")
                response_lines.append(f"   {description}")
                response_lines.append(f"   🔗 {url}")
                response_lines.append("")
            
            response_lines.append("---")
            response_lines.append("💡 To create a local protocol based on one of these, say \"create a protocol based on #1\" or describe the steps you want.")
            
            return "\n".join(response_lines)
            
        except ImportError:
            return "❌ **Tavily package not installed.** Run: `pip install tavily-python`"
        except Exception as e:
            return f"❌ **Search error:** {str(e)}"


class FindProtocolInLiteratureTool(BaseTool):
    """
    Search ACADEMIC LITERATURE for protocols via Semantic Scholar API.
    
    Uses the Semantic Scholar API to find peer-reviewed methods papers
    containing established protocols. Best for:
    - Validated, peer-reviewed methodologies
    - Protocols with citations and reproducibility data
    - Methods sections from high-impact journals
    
    This is complementary to FindProtocolOnlineTool which searches the
    general web. Use BOTH tools together for comprehensive protocol discovery.
    
    Note: Only returns high-level summaries and DOIs to respect copyright.
    Does NOT copy full methods sections verbatim.
    """
    
    name: str = "find_protocol_in_literature"
    description: str = """Search ACADEMIC LITERATURE via Semantic Scholar for peer-reviewed protocols.
Finds established methods from published papers with DOIs and citations.
Use alongside find_protocol_online for comprehensive protocol discovery.
Returns papers containing protocols/methods - only summaries, not full text."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Protocol or method to search for"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, **kwargs) -> str:
        """
        Search literature for protocols.
        
        Args:
            query: Protocol or method description
            
        Returns:
            Formatted string with literature candidates
        """
        try:
            # Search Semantic Scholar for methods papers
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": f"{query} protocol method",
                "limit": 5,
                "fields": "title,abstract,authors,year,url,externalIds"
            }
            
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            
            data = await loop.run_in_executor(None, do_request)
            papers = data.get("data", [])
            
            if not papers:
                return f"""🔍 **No literature protocols found for:** {query}

Try searching online with `find_protocol_online` or using different keywords."""
            
            # Format results
            response_lines = [f"📚 **Literature Protocol Search for:** {query}\n"]
            
            for i, paper in enumerate(papers, 1):
                title = paper.get("title", "Unknown")[:80]
                year = paper.get("year", "N/A")
                
                # Get DOI if available
                external_ids = paper.get("externalIds", {}) or {}
                doi = external_ids.get("DOI", "")
                doi_url = f"https://doi.org/{doi}" if doi else paper.get("url", "No URL")
                
                # Authors (first 2)
                authors = paper.get("authors", [])
                author_names = [a.get("name", "") for a in authors[:2]]
                authors_str = ", ".join(author_names)
                if len(authors) > 2:
                    authors_str += " et al."
                
                # Abstract snippet
                abstract = paper.get("abstract", "") or ""
                description = abstract[:150] + "..." if len(abstract) > 150 else abstract
                if not description:
                    description = "No abstract available"
                
                response_lines.append(f"**{i}. {title}** ({year})")
                response_lines.append(f"   Authors: {authors_str}")
                response_lines.append(f"   {description}")
                response_lines.append(f"   📄 DOI: {doi_url}")
                response_lines.append("")
            
            response_lines.append("---")
            response_lines.append("💡 These papers contain protocols/methods. To create a local version, describe the steps you want to save.")
            
            return "\n".join(response_lines)
            
        except requests.exceptions.Timeout:
            return "❌ **Literature search timed out.** Try again or use `find_protocol_online`."
        except Exception as e:
            return f"❌ **Literature search error:** {str(e)}"


# =============================================================================
# Local Protocol Management Tools
# =============================================================================

class CreateProtocolTool(BaseTool):
    """
    Create a local protocol that can be modified and reused.
    """
    
    name: str = "create_protocol"
    description: str = """Create a new local protocol.
Use after finding a protocol online/literature to save a local version.
Requires name, description, and steps."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Protocol name"
            },
            "description": {
                "type": "string",
                "description": "Brief description of the protocol"
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "text": {"type": "string"}
                    }
                },
                "description": "List of steps with index and text"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization"
            },
            "source_type": {
                "type": "string",
                "description": "Source type: 'manual', 'web', 'literature', 'derived'"
            },
            "source_reference": {
                "type": "string",
                "description": "Source URL or DOI if derived from another source"
            }
        },
        "required": ["name", "description", "steps"]
    }
    
    async def execute(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        source_type: str = "manual",
        source_reference: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create a new protocol.
        
        Args:
            name: Protocol name
            description: Brief description
            steps: List of step objects
            tags: Optional tags
            source_type: Source type
            source_reference: Optional source URL/DOI
            
        Returns:
            Confirmation with protocol ID
        """
        try:
            service = get_protocol_service()
            
            protocol = service.create_protocol(
                name=name,
                description=description,
                source_type=source_type,
                source_reference=source_reference,
                steps=steps,
                tags=tags
            )
            
            # Format response
            tags_str = ", ".join(protocol.get("tags", [])) if protocol.get("tags") else "None"
            
            return f"""✅ **Protocol Created**

**ID:** `{protocol['id']}`
**Name:** {protocol['name']}
**Description:** {protocol['description']}
**Steps:** {len(protocol['steps'])} steps
**Tags:** {tags_str}
**Source:** {protocol['source_type']}{f" ({protocol['source_reference']})" if protocol.get('source_reference') else ""}

---
💡 Use `get_protocol {protocol['id']}` to view full steps, or `update_protocol` to modify."""
            
        except Exception as e:
            return f"❌ **Error creating protocol:** {str(e)}"


class UpdateProtocolTool(BaseTool):
    """
    Modify an existing protocol.
    """
    
    name: str = "update_protocol"
    description: str = """Update an existing protocol.
Use to modify steps, description, or tags of a saved protocol."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "protocol_id": {
                "type": "string",
                "description": "Protocol ID to update"
            },
            "updated_name": {
                "type": "string",
                "description": "New name (optional)"
            },
            "updated_description": {
                "type": "string",
                "description": "New description (optional)"
            },
            "updated_steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "text": {"type": "string"}
                    }
                },
                "description": "New steps list (replaces all steps)"
            },
            "updated_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "New tags list (replaces all tags)"
            }
        },
        "required": ["protocol_id"]
    }
    
    async def execute(
        self,
        protocol_id: str,
        updated_name: Optional[str] = None,
        updated_description: Optional[str] = None,
        updated_steps: Optional[List[Dict[str, Any]]] = None,
        updated_tags: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Update an existing protocol.
        
        Args:
            protocol_id: Protocol ID
            updated_name: New name
            updated_description: New description
            updated_steps: New steps
            updated_tags: New tags
            
        Returns:
            Summary of changes
        """
        try:
            service = get_protocol_service()
            
            result = service.update_protocol(
                protocol_id=protocol_id,
                name=updated_name,
                description=updated_description,
                steps=updated_steps,
                tags=updated_tags
            )
            
            protocol = result["protocol"]
            changes = result["changes"]
            
            if not changes:
                return f"ℹ️ No changes made to protocol `{protocol_id}`."
            
            changes_str = ", ".join(changes)
            tags_str = ", ".join(protocol.get("tags", [])) if protocol.get("tags") else "None"
            
            return f"""✅ **Protocol Updated**

**ID:** `{protocol['id']}`
**Name:** {protocol['name']}
**Version:** {protocol['version']}
**Changes:** {changes_str}
**Tags:** {tags_str}

---
💡 Use `get_protocol {protocol['id']}` to view the updated protocol."""
            
        except ValueError as e:
            return f"❌ **Error:** {str(e)}"
        except Exception as e:
            return f"❌ **Error updating protocol:** {str(e)}"


class GetProtocolTool(BaseTool):
    """
    Retrieve a stored protocol for review.
    """
    
    name: str = "get_protocol"
    description: str = """Get a stored protocol by ID.
Use to view full protocol details including all steps."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "protocol_id": {
                "type": "string",
                "description": "Protocol ID to retrieve"
            }
        },
        "required": ["protocol_id"]
    }
    
    async def execute(self, protocol_id: str, **kwargs) -> str:
        """
        Get a protocol by ID.
        
        Args:
            protocol_id: Protocol ID
            
        Returns:
            Full protocol details
        """
        try:
            service = get_protocol_service()
            protocol = service.get_protocol(protocol_id)
            
            if not protocol:
                return f"❌ **Protocol not found:** `{protocol_id}`"
            
            # Format steps
            steps_lines = []
            for step in protocol.get("steps", []):
                step_text = f"**Step {step['index']}:** {step['text']}"
                if step.get("duration_minutes"):
                    step_text += f" _(~{step['duration_minutes']} min)_"
                steps_lines.append(step_text)
            
            steps_str = "\n".join(steps_lines) if steps_lines else "No steps defined"
            tags_str = ", ".join(protocol.get("tags", [])) if protocol.get("tags") else "None"
            
            source_info = protocol.get("source_type", "manual")
            if protocol.get("source_reference"):
                source_info += f" ({protocol['source_reference']})"
            
            return f"""📋 **Protocol: {protocol['name']}**

**ID:** `{protocol['id']}`
**Description:** {protocol['description']}
**Source:** {source_info}
**Tags:** {tags_str}
**Version:** {protocol['version']}

## Steps

{steps_str}

---
_Last updated: {protocol.get('updated_at', 'N/A')}_"""
            
        except Exception as e:
            return f"❌ **Error retrieving protocol:** {str(e)}"


class ListProtocolsTool(BaseTool):
    """
    List available local protocols.
    """
    
    name: str = "list_protocols"
    description: str = """List all saved protocols.
Optionally filter by tag."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "tag_filter": {
                "type": "string",
                "description": "Optional tag to filter by"
            }
        },
        "required": []
    }
    
    async def execute(self, tag_filter: Optional[str] = None, **kwargs) -> str:
        """
        List protocols.
        
        Args:
            tag_filter: Optional tag filter
            
        Returns:
            List of protocols
        """
        try:
            service = get_protocol_service()
            protocols = service.list_protocols(tag_filter=tag_filter)
            
            if not protocols:
                if tag_filter:
                    return f"📋 **No protocols found with tag:** {tag_filter}"
                return """📋 **No protocols saved yet**

Use `find_protocol_online` or `find_protocol_in_literature` to find protocols,
then `create_protocol` to save a local version."""
            
            # Format list
            response_lines = [f"📋 **Saved Protocols** ({len(protocols)} total)\n"]
            
            for p in protocols:
                tags = ", ".join(p.get("tags", [])[:3]) if p.get("tags") else "No tags"
                steps_count = len(p.get("steps", []))
                response_lines.append(f"**{p['name']}** (`{p['id']}`)")
                response_lines.append(f"   {p['description'][:60]}...")
                response_lines.append(f"   📌 {tags} | {steps_count} steps | v{p['version']}")
                response_lines.append("")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error listing protocols:** {str(e)}"


# =============================================================================
# Machine-Friendly Tool for Other Agents
# =============================================================================

class FindProtocolForAgentTool(BaseTool):
    """
    Machine-friendly protocol lookup for other agents (e.g., ExperimentAgent).
    
    Searches multiple sources and returns structured, compact results:
    1. LOCAL: Stored protocols via ProtocolService.search_protocols_by_query
    2. Suggests using Tavily (web) and Semantic Scholar (literature) for more options
    
    This tool is optimized for programmatic consumption by other agents,
    not for direct user display.
    """
    
    name: str = "find_protocol_for_agent"
    description: str = """Find protocols for a query (machine-friendly, for other agents).
Searches LOCAL stored protocols first, then suggests web (Tavily) and literature (Semantic Scholar) sources.
Used by ExperimentAgent or other agents to look up protocols programmatically.
Returns compact, structured results optimized for agent consumption."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Protocol search query"
            },
            "include_external": {
                "type": "boolean",
                "description": "If true, also search web (Tavily) and literature (Semantic Scholar)"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, include_external: bool = False, **kwargs) -> str:
        """
        Find protocols for another agent.
        
        Searches local protocols first. If include_external=True, also searches
        web (Tavily) and literature (Semantic Scholar) for additional options.
        
        Args:
            query: Search query
            include_external: Whether to also search Tavily and Semantic Scholar
            
        Returns:
            Compact structured results for agent consumption
        """
        try:
            service = get_protocol_service()
            
            # Search local protocols
            local_results = service.search_protocols_by_query(query)
            
            # Format compact results
            response_lines = [f"PROTOCOL_SEARCH_RESULTS for: {query}"]
            response_lines.append("SOURCES: local" + (", web (Tavily), literature (Semantic Scholar)" if include_external else ""))
            response_lines.append("---")
            
            # Local protocols
            if local_results:
                response_lines.append("LOCAL_PROTOCOLS:")
                for r in local_results[:3]:
                    p = r["protocol"]
                    response_lines.append(
                        f"  - id={p['id']} | name={p['name']} | "
                        f"steps={len(p.get('steps', []))} | "
                        f"tags={','.join(p.get('tags', [])[:2])}"
                    )
            else:
                response_lines.append("LOCAL_PROTOCOLS: none")
            
            # External search if requested
            if include_external:
                response_lines.append("---")
                response_lines.append("EXTERNAL_SOURCES:")
                response_lines.append("  - WEB (Tavily): Use find_protocol_online for practical writeups")
                response_lines.append("  - LITERATURE (Semantic Scholar): Use find_protocol_in_literature for peer-reviewed methods")
            else:
                response_lines.append("---")
                response_lines.append("TIP: Set include_external=true to also search web (Tavily) and literature (Semantic Scholar).")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"ERROR: {str(e)}"


# =============================================================================
# URL Extraction Tools
# =============================================================================

class ExtractProtocolFromUrlTool(BaseTool):
    """
    Extract protocol content from a specific URL using Tavily.
    
    Uses Tavily's extract API with advanced depth to fetch and parse
    protocol pages from repositories, vendor sites, or publications.
    
    Returns a structured summary (NOT verbatim copy) including:
    - Page title
    - High-level method overview
    - Key parameters (temperatures, times, sample types)
    - Steps overview (count and phases, not exact text)
    
    Respects copyright by only providing summaries, not copying exact steps.
    """
    
    name: str = "extract_protocol_from_url"
    description: str = """Extract protocol content from a specific URL.
Use when user provides a direct link to a protocol page (e.g., protocols.io, vendor site, paper).
Returns a structured summary with title, overview, and key parameters.
Does NOT copy exact steps - only provides high-level summary to respect copyright."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the protocol page to extract"
            },
            "context": {
                "type": "string",
                "description": "Optional context hint (e.g., 'staining mouse brain slides') to help focus extraction"
            }
        },
        "required": ["url"]
    }
    
    async def execute(self, url: str, context: str = "", **kwargs) -> str:
        """
        Extract protocol content from a URL.
        
        Args:
            url: URL to extract from
            context: Optional context hint
            
        Returns:
            Formatted summary of the protocol
        """
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return f"❌ **Invalid URL:** Please provide a valid HTTP/HTTPS URL."
        
        # Call extraction helper
        result = await _extract_protocol_from_url_helper(url, context, extract_depth="advanced")
        
        if not result["success"]:
            return f"""❌ **Extraction Failed**

**URL:** {url}
**Error:** {result['error']}

💡 **Suggestions:**
- Check if the URL is accessible in a browser
- Try a different URL for the same protocol
- Use `find_protocol_online` to search for alternatives"""
        
        # Format successful extraction
        params_str = ", ".join(result["key_parameters"]) if result["key_parameters"] else "Not detected"
        
        return f"""📄 **Protocol Extracted**

**Title:** {result['title']}
**Source:** {result['source_url']}

## Overview
{result['summary']}

## Key Parameters
{params_str}

## Structure
{result['steps_overview']}

---
⚠️ **Note:** This is a high-level summary only. Refer to the source URL for complete details.

💡 **Next Steps:**
- To save this as a local protocol, say "create a protocol based on this"
- I'll help you write your own version of the steps (not copied verbatim)"""


class ExtractProtocolFromLiteratureLinkTool(BaseTool):
    """
    Extract protocol from a literature reference (paper ID, DOI, or URL).
    
    Workflow:
    1. Resolve the paper to find the best available URL (publisher, PMC, etc.)
    2. Use Tavily extract to fetch content from that URL
    3. Summarize only the methods/protocol section at a high level
    
    Respects copyright by only providing summaries, not copying exact text.
    """
    
    name: str = "extract_protocol_from_literature"
    description: str = """Extract protocol/methods from a literature reference.
Use when user provides a paper DOI, PMID, or URL and wants to extract the protocol.
Resolves the paper to find accessible content, then extracts a high-level summary.
Does NOT copy exact methods text - only provides overview to respect copyright."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "paper_id_or_url": {
                "type": "string",
                "description": "Paper identifier: DOI (10.xxxx/...), PMID (12345678), or direct URL"
            },
            "context": {
                "type": "string",
                "description": "What aspect of the protocol to focus on (e.g., 'immunostaining procedure')"
            }
        },
        "required": ["paper_id_or_url"]
    }
    
    async def execute(self, paper_id_or_url: str, context: str = "", **kwargs) -> str:
        """
        Extract protocol from a literature reference.
        
        Args:
            paper_id_or_url: DOI, PMID, or URL
            context: What to focus on
            
        Returns:
            Formatted protocol summary
        """
        import re
        
        # Determine the type of identifier and resolve to URL
        paper_id = paper_id_or_url.strip()
        resolved_url = None
        paper_info = None
        
        # Check if it's already a URL
        if paper_id.startswith(('http://', 'https://')):
            resolved_url = paper_id
        
        # Check if it's a DOI
        elif paper_id.startswith('10.') or 'doi.org' in paper_id:
            # Extract DOI
            doi_match = re.search(r'(10\.\d{4,}/[^\s]+)', paper_id)
            if doi_match:
                doi = doi_match.group(1)
                # Try to get paper info from Semantic Scholar
                paper_info = await self._get_paper_info_by_doi(doi)
                if paper_info:
                    resolved_url = paper_info.get("url") or f"https://doi.org/{doi}"
                else:
                    resolved_url = f"https://doi.org/{doi}"
        
        # Check if it's a PMID
        elif paper_id.isdigit() or paper_id.lower().startswith('pmid'):
            pmid = re.sub(r'\D', '', paper_id)
            if pmid:
                # PubMed Central URL (more likely to have full text)
                paper_info = await self._get_paper_info_by_pmid(pmid)
                if paper_info and paper_info.get("pmc_url"):
                    resolved_url = paper_info["pmc_url"]
                else:
                    resolved_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        else:
            return f"""❌ **Could not parse paper identifier:** {paper_id}

Please provide one of:
- DOI (e.g., `10.1038/s41586-021-03819-2`)
- PMID (e.g., `12345678`)
- Direct URL to the paper"""
        
        if not resolved_url:
            return f"""❌ **Could not resolve paper:** {paper_id}

The paper could not be found or accessed. Try:
- Providing a direct URL to the paper
- Checking the DOI/PMID is correct
- Using `find_protocol_in_literature` to search for the paper"""
        
        # Build context for extraction
        extraction_context = context or "methods protocol procedure"
        if paper_info and paper_info.get("title"):
            extraction_context = f"{paper_info['title']} - {extraction_context}"
        
        # Extract content from the resolved URL
        result = await _extract_protocol_from_url_helper(
            resolved_url, 
            extraction_context, 
            extract_depth="advanced"
        )
        
        if not result["success"]:
            # Try alternative URLs if available
            alt_urls = []
            if paper_info:
                if paper_info.get("pmc_url"):
                    alt_urls.append(paper_info["pmc_url"])
                if paper_info.get("doi"):
                    alt_urls.append(f"https://doi.org/{paper_info['doi']}")
            
            # Try alternatives
            for alt_url in alt_urls:
                if alt_url != resolved_url:
                    result = await _extract_protocol_from_url_helper(alt_url, extraction_context)
                    if result["success"]:
                        resolved_url = alt_url
                        break
        
        if not result["success"]:
            return f"""❌ **Could not extract protocol from paper**

**Paper:** {paper_id}
**Resolved URL:** {resolved_url}
**Error:** {result['error']}

💡 **This often happens because:**
- The paper is behind a paywall
- The page requires authentication
- The methods section is in a supplementary file

**Suggestions:**
- Try accessing the paper directly and copy the URL of the methods section
- Look for a preprint version on bioRxiv or medRxiv
- Use `find_protocol_online` to search for related protocols"""
        
        # Format successful extraction
        paper_title = paper_info.get("title", result["title"]) if paper_info else result["title"]
        params_str = ", ".join(result["key_parameters"]) if result["key_parameters"] else "Not detected"
        
        return f"""📚 **Protocol Extracted from Literature**

**Paper:** {paper_title}
**Source:** {resolved_url}

## Methods Overview
{result['summary']}

## Key Parameters
{params_str}

## Protocol Structure
{result['steps_overview']}

---
⚠️ **Note:** This is a high-level summary of the methods section.
Refer to the original paper for complete details and proper citation.

💡 **Next Steps:**
- To adapt this for your experiment, say "create a protocol based on this"
- I'll help you write your own version (not copied verbatim)"""
    
    async def _get_paper_info_by_doi(self, doi: str) -> Optional[dict]:
        """Get paper info from Semantic Scholar by DOI."""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            params = {"fields": "title,url,externalIds,isOpenAccess,openAccessPdf"}
            
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return response.json()
                return None
            
            data = await loop.run_in_executor(None, do_request)
            
            if data:
                external_ids = data.get("externalIds", {}) or {}
                return {
                    "title": data.get("title"),
                    "url": data.get("url"),
                    "doi": external_ids.get("DOI"),
                    "pmid": external_ids.get("PubMed"),
                    "pmc_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{external_ids['PubMedCentral']}/" 
                              if external_ids.get("PubMedCentral") else None,
                    "open_access_pdf": data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None
                }
        except Exception:
            pass
        return None
    
    async def _get_paper_info_by_pmid(self, pmid: str) -> Optional[dict]:
        """Get paper info from Semantic Scholar by PMID."""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/PMID:{pmid}"
            params = {"fields": "title,url,externalIds,isOpenAccess,openAccessPdf"}
            
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return response.json()
                return None
            
            data = await loop.run_in_executor(None, do_request)
            
            if data:
                external_ids = data.get("externalIds", {}) or {}
                return {
                    "title": data.get("title"),
                    "url": data.get("url"),
                    "doi": external_ids.get("DOI"),
                    "pmid": external_ids.get("PubMed"),
                    "pmc_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{external_ids['PubMedCentral']}/" 
                              if external_ids.get("PubMedCentral") else None,
                    "open_access_pdf": data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None
                }
        except Exception:
            pass
        return None


# Export all tools
__all__ = [
    "FindProtocolOnlineTool",
    "FindProtocolInLiteratureTool",
    "CreateProtocolTool",
    "UpdateProtocolTool",
    "GetProtocolTool",
    "ListProtocolsTool",
    "FindProtocolForAgentTool",
    "ExtractProtocolFromUrlTool",
    "ExtractProtocolFromLiteratureLinkTool",
]
