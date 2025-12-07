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


# Export all tools
__all__ = [
    "FindProtocolOnlineTool",
    "FindProtocolInLiteratureTool",
    "CreateProtocolTool",
    "UpdateProtocolTool",
    "GetProtocolTool",
    "ListProtocolsTool",
    "FindProtocolForAgentTool",
]
