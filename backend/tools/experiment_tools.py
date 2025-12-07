"""
Experiment tools for designing, recording, and analyzing experiments.

Provides tools for:
- PlanExperimentWithLiteratureTool: Plan experiments using literature + protocols
- CreateExperimentTool: Create new experiments
- AttachProtocolToExperimentTool: Link protocols to experiments
- MarkExperimentStatusTool: Update status with auto reagent deduction
- AddManualReagentUsageToExperimentTool: Log manual reagent usage
- StoreExperimentOnChainForExperimentTool: Store provenance on blockchain
- AnalyzeExperimentResultsWithLiteratureTool: Analyze results with literature
- GetExperimentTool: Retrieve experiment details
- ListExperimentsTool: List all experiments

All tools follow SpoonOS BaseTool patterns with async execute methods.
"""

import asyncio
from typing import Any, Dict, List, Optional

import requests
from spoon_ai.tools.base import BaseTool

from backend.services.experiment_service import get_experiment_service
from backend.services.protocol_service import get_protocol_service
from backend.services.reagent_service import get_reagent_service


# =============================================================================
# Planning Tools
# =============================================================================

class PlanExperimentWithLiteratureTool(BaseTool):
    """
    Plan an experiment using literature search and protocol discovery.
    
    Searches academic literature for relevant papers and finds candidate
    protocols to address the scientific question.
    """
    
    name: str = "plan_experiment_with_literature"
    description: str = """Plan an experiment starting from a scientific question.
Searches literature for relevant papers and suggests candidate protocols.
Returns a structured plan with rationale, key papers, and protocol suggestions.
Use when user asks to design or plan an experiment."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "scientific_question": {
                "type": "string",
                "description": "The scientific question to investigate"
            },
            "high_level_goal": {
                "type": "string",
                "description": "Optional high-level goal or context"
            }
        },
        "required": ["scientific_question"]
    }
    
    async def execute(
        self,
        scientific_question: str,
        high_level_goal: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Plan an experiment based on literature and protocols.
        
        Args:
            scientific_question: The question to investigate
            high_level_goal: Optional additional context
            
        Returns:
            Formatted experiment plan
        """
        try:
            # Search literature via Semantic Scholar
            literature_results = await self._search_literature(scientific_question)
            
            # Search for protocols
            protocol_results = await self._search_protocols(scientific_question)
            
            # Build response
            response_lines = [
                f"📋 **Experiment Plan**\n",
                f"**Scientific Question:** {scientific_question}",
            ]
            
            if high_level_goal:
                response_lines.append(f"**Goal:** {high_level_goal}")
            
            response_lines.append("\n---\n")
            
            # Literature rationale
            response_lines.append("## 📚 Literature-Based Rationale\n")
            if literature_results:
                response_lines.append("Based on recent literature, this question can be addressed by:")
                for i, paper in enumerate(literature_results[:3], 1):
                    title = paper.get("title", "Unknown")[:70]
                    year = paper.get("year", "N/A")
                    doi = paper.get("doi", "")
                    response_lines.append(f"  {i}. **{title}** ({year})")
                    if doi:
                        response_lines.append(f"     DOI: https://doi.org/{doi}")
            else:
                response_lines.append("No directly relevant papers found. Consider refining the question.")
            
            response_lines.append("\n---\n")
            
            # Suggested protocols
            response_lines.append("## 🧪 Suggested Protocols\n")
            if protocol_results:
                for i, protocol in enumerate(protocol_results[:3], 1):
                    name = protocol.get("name", "Unknown Protocol")
                    source = protocol.get("source", "")
                    protocol_id = protocol.get("id", "")
                    response_lines.append(f"  {i}. **{name}**")
                    if protocol_id:
                        response_lines.append(f"     ID: {protocol_id}")
                    if source:
                        response_lines.append(f"     Source: {source}")
            else:
                response_lines.append("No matching protocols found locally.")
                response_lines.append("Consider searching online with `find_protocol_online`.")
            
            response_lines.append("\n---\n")
            
            # Key considerations
            response_lines.append("## ⚠️ Key Considerations\n")
            response_lines.append("- Include appropriate controls (positive/negative)")
            response_lines.append("- Consider sample size and statistical power")
            response_lines.append("- Document all reagent lots and conditions")
            response_lines.append("- Plan for data backup and provenance tracking")
            
            response_lines.append("\n---\n")
            response_lines.append("💡 **Next Step:** Use `create_experiment` to start this experiment.")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error planning experiment:** {str(e)}"
    
    async def _search_literature(self, query: str) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for relevant papers."""
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": 5,
                "fields": "title,abstract,authors,year,externalIds"
            }
            
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            
            data = await loop.run_in_executor(None, do_request)
            papers = data.get("data", [])
            
            results = []
            for paper in papers:
                external_ids = paper.get("externalIds", {}) or {}
                results.append({
                    "title": paper.get("title", ""),
                    "year": paper.get("year"),
                    "doi": external_ids.get("DOI", ""),
                    "abstract": paper.get("abstract", "")[:200] if paper.get("abstract") else ""
                })
            return results
            
        except Exception:
            return []
    
    async def _search_protocols(self, query: str) -> List[Dict[str, Any]]:
        """Search local protocols."""
        try:
            service = get_protocol_service()
            results = service.search_protocols_by_query(query)
            
            protocols = []
            for r in results[:3]:
                p = r["protocol"]
                protocols.append({
                    "id": p["id"],
                    "name": p["name"],
                    "source": p.get("source_type", "local")
                })
            return protocols
            
        except Exception:
            return []


# =============================================================================
# Experiment CRUD Tools
# =============================================================================

class CreateExperimentTool(BaseTool):
    """Create a new experiment."""
    
    name: str = "create_experiment"
    description: str = """Create a new experiment record.
Use after planning to formally start tracking an experiment.
Returns experiment_id and initial status."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Experiment title"
            },
            "scientific_question": {
                "type": "string",
                "description": "The scientific question being investigated"
            },
            "description": {
                "type": "string",
                "description": "Detailed experiment description"
            },
            "protocol_id": {
                "type": "string",
                "description": "Optional protocol ID to link"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for categorization"
            }
        },
        "required": ["title", "scientific_question", "description"]
    }
    
    async def execute(
        self,
        title: str,
        scientific_question: str,
        description: str,
        protocol_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Create a new experiment.
        
        Args:
            title: Experiment title
            scientific_question: Question being investigated
            description: Detailed description
            protocol_id: Optional linked protocol
            tags: Optional tags
            
        Returns:
            Confirmation with experiment details
        """
        try:
            service = get_experiment_service()
            
            experiment = service.create_experiment(
                title=title,
                scientific_question=scientific_question,
                description=description,
                protocol_id=protocol_id,
                tags=tags
            )
            
            response_lines = [
                "✅ **Experiment Created**\n",
                f"**ID:** `{experiment['id']}`",
                f"**Title:** {experiment['title']}",
                f"**Status:** {experiment['status']}",
                f"**Question:** {experiment['scientific_question'][:100]}...",
            ]
            
            if protocol_id:
                # Try to get protocol name
                protocol_service = get_protocol_service()
                protocol = protocol_service.get_protocol(protocol_id)
                if protocol:
                    response_lines.append(f"**Linked Protocol:** {protocol['name']} (`{protocol_id}`)")
                else:
                    response_lines.append(f"**Linked Protocol:** `{protocol_id}`")
            
            if tags:
                response_lines.append(f"**Tags:** {', '.join(tags)}")
            
            response_lines.append("\n---")
            response_lines.append("💡 **Next:** Use `mark_experiment_status` to update progress.")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error creating experiment:** {str(e)}"


class AttachProtocolToExperimentTool(BaseTool):
    """Attach a protocol to an existing experiment."""
    
    name: str = "attach_protocol_to_experiment"
    description: str = """Link a protocol to an experiment.
Use when you want to associate a protocol with an existing experiment."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment"
            },
            "protocol_id": {
                "type": "string",
                "description": "ID of the protocol to attach"
            }
        },
        "required": ["experiment_id", "protocol_id"]
    }
    
    async def execute(
        self,
        experiment_id: str,
        protocol_id: str,
        **kwargs
    ) -> str:
        """
        Attach a protocol to an experiment.
        
        Args:
            experiment_id: Experiment to update
            protocol_id: Protocol to attach
            
        Returns:
            Confirmation message
        """
        try:
            exp_service = get_experiment_service()
            protocol_service = get_protocol_service()
            
            # Verify experiment exists
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            # Verify protocol exists
            protocol = protocol_service.get_protocol(protocol_id)
            if not protocol:
                return f"❌ **Protocol not found:** `{protocol_id}`"
            
            # Attach
            exp_service.attach_protocol(experiment_id, protocol_id)
            
            return f"""✅ **Protocol Attached**

**Experiment:** {experiment['title']} (`{experiment_id}`)
**Protocol:** {protocol['name']} (`{protocol_id}`)

The protocol's reagent references will be used to auto-log usage when the experiment is marked completed."""
            
        except Exception as e:
            return f"❌ **Error attaching protocol:** {str(e)}"


class MarkExperimentStatusTool(BaseTool):
    """
    Update experiment status with automatic reagent deduction.
    
    When status becomes "completed", automatically deduces reagent usage
    from the linked protocol's steps.
    """
    
    name: str = "mark_experiment_status"
    description: str = """Update experiment status (planned/in_progress/completed).
When marking as 'completed', automatically logs reagent usage from the linked protocol.
Also updates reagent inventory."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment"
            },
            "status": {
                "type": "string",
                "enum": ["planned", "in_progress", "completed"],
                "description": "New status"
            }
        },
        "required": ["experiment_id", "status"]
    }
    
    async def execute(
        self,
        experiment_id: str,
        status: str,
        **kwargs
    ) -> str:
        """
        Update experiment status.
        
        Args:
            experiment_id: Experiment to update
            status: New status
            
        Returns:
            Status update confirmation with any auto-logged reagent usages
        """
        try:
            exp_service = get_experiment_service()
            protocol_service = get_protocol_service()
            reagent_service = get_reagent_service()
            
            # Verify experiment exists
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            old_status = experiment["status"]
            
            # Update status
            exp_service.set_status(experiment_id, status)
            
            response_lines = [
                "✅ **Status Updated**\n",
                f"**Experiment:** {experiment['title']}",
                f"**Status:** {old_status} → **{status}**",
            ]
            
            # Auto-deduce reagent usage when completed
            auto_logged = 0
            if status == "completed" and experiment.get("protocol_id"):
                protocol = protocol_service.get_protocol(experiment["protocol_id"])
                
                if protocol and protocol.get("steps"):
                    response_lines.append("\n---\n")
                    response_lines.append("## 🧪 Auto-Logged Reagent Usage\n")
                    
                    for step in protocol["steps"]:
                        # Check both 'reagent_references' and 'reagents' for compatibility
                        reagent_refs = step.get("reagent_references", []) or step.get("reagents", [])
                        for ref in reagent_refs:
                            reagent_id = ref.get("reagent_id")
                            amount = ref.get("amount")
                            unit = ref.get("unit")
                            
                            if reagent_id and amount and unit:
                                # Log to experiment
                                exp_service.add_reagent_usage(
                                    experiment_id,
                                    reagent_id,
                                    amount,
                                    unit,
                                    source="auto_from_protocol"
                                )
                                
                                # Update inventory (may fail if reagent not in inventory)
                                try:
                                    result = reagent_service.record_usage(
                                        reagent_id, amount, unit,
                                        experiment_id=experiment_id
                                    )
                                    reagent_name = result.get("reagent_name", reagent_id)
                                    response_lines.append(f"  - {reagent_name}: {amount} {unit}")
                                    
                                    # Check for low inventory
                                    if result.get("low_inventory"):
                                        response_lines.append(f"    ⚠️ Low inventory warning!")
                                except ValueError:
                                    # Reagent not in inventory - still log to experiment
                                    response_lines.append(f"  - {reagent_id}: {amount} {unit} (not in inventory)")
                                
                                auto_logged += 1
                    
                    if auto_logged > 0:
                        response_lines.append(f"\n📊 Auto-logged **{auto_logged}** reagent usage(s) from protocol `{experiment['protocol_id']}`")
                    else:
                        response_lines.append("No reagent references found in protocol steps.")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error updating status:** {str(e)}"


class AddManualReagentUsageToExperimentTool(BaseTool):
    """Manually log reagent usage for an experiment."""
    
    name: str = "add_manual_reagent_usage"
    description: str = """Manually log reagent usage for an experiment.
Updates both the experiment record and reagent inventory.
Returns confirmation with any low-inventory warnings."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment"
            },
            "reagent_id": {
                "type": "string",
                "description": "ID of the reagent used"
            },
            "amount": {
                "type": "number",
                "description": "Amount used"
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (e.g., µL, mL, mg)"
            }
        },
        "required": ["experiment_id", "reagent_id", "amount", "unit"]
    }
    
    async def execute(
        self,
        experiment_id: str,
        reagent_id: str,
        amount: float,
        unit: str,
        **kwargs
    ) -> str:
        """
        Log manual reagent usage.
        
        Args:
            experiment_id: Experiment to update
            reagent_id: Reagent used
            amount: Amount used
            unit: Unit of measurement
            
        Returns:
            Confirmation with inventory status
        """
        try:
            exp_service = get_experiment_service()
            reagent_service = get_reagent_service()
            
            # Verify experiment exists
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            # Log to experiment
            exp_service.add_reagent_usage(
                experiment_id, reagent_id, amount, unit, source="manual"
            )
            
            # Update inventory
            try:
                result = reagent_service.record_usage(
                    reagent_id, amount, unit,
                    experiment_id=experiment_id
                )
                
                response_lines = [
                    "✅ **Reagent Usage Logged**\n",
                    f"**Experiment:** {experiment['title']}",
                    f"**Reagent:** {result['reagent_name']}",
                    f"**Used:** {amount} {unit}",
                    f"**Remaining:** {result['after_quantity']} {result['unit']}",
                ]
                
                if result.get("low_inventory"):
                    response_lines.append(f"\n⚠️ **Low Inventory Warning!** Only {result['remaining_percentage']}% remaining.")
            except ValueError:
                # Reagent not in inventory
                return f"""⚠️ **Reagent Usage Logged (Inventory Not Found)**

Logged {amount} {unit} of `{reagent_id}` to experiment `{experiment_id}`.
Note: Reagent not found in inventory - add it with `add_reagent_to_inventory`."""
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error logging usage:** {str(e)}"


# =============================================================================
# Blockchain Integration Tool
# =============================================================================

class StoreExperimentOnChainForExperimentTool(BaseTool):
    """Store experiment provenance on the Neo X blockchain."""
    
    name: str = "store_experiment_on_chain"
    description: str = """Store experiment provenance on the Neo X blockchain.
Creates a tamper-proof record of the experiment metadata.
Use when user wants to make experiment data immutable."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment to store on chain"
            }
        },
        "required": ["experiment_id"]
    }
    
    async def execute(self, experiment_id: str, **kwargs) -> str:
        """
        Store experiment on blockchain.
        
        Args:
            experiment_id: Experiment to store
            
        Returns:
            Confirmation with transaction hash
        """
        try:
            from backend.services import get_blockchain_service
            
            exp_service = get_experiment_service()
            blockchain_service = get_blockchain_service()
            
            # Get experiment
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            # Build compact metadata (no raw data)
            experiment_data = {
                "id": experiment["id"],
                "title": experiment["title"],
                "status": experiment["status"],
                "protocol_id": experiment.get("protocol_id"),
                "reagent_ids": [u["reagent_id"] for u in experiment.get("reagent_usages", [])],
                "tags": experiment.get("tags", []),
                "results_summary": experiment.get("results_summary"),
                "created_at": experiment["created_at"],
            }
            
            # Store on blockchain
            result = await blockchain_service.store_experiment_hash(
                experiment_id=experiment_id,
                experiment_data=experiment_data
            )
            
            if result.get("success"):
                tx_hash = result.get("tx_hash", "")
                
                # Save tx_hash to experiment
                exp_service.set_blockchain_tx_hash(experiment_id, tx_hash)
                
                explorer_url = result.get("explorer_url", "")
                
                return f"""✅ **Experiment Stored on Blockchain**

**Experiment:** {experiment['title']} (`{experiment_id}`)
**Transaction Hash:** `{tx_hash}`
**Explorer:** {explorer_url}

This experiment's metadata is now tamper-proof and verifiable."""
            else:
                error = result.get("error", "Unknown error")
                return f"❌ **Blockchain storage failed:** {error}"
            
        except Exception as e:
            return f"❌ **Error storing on chain:** {str(e)}"


# =============================================================================
# Analysis Tool
# =============================================================================

class AnalyzeExperimentResultsWithLiteratureTool(BaseTool):
    """Analyze experiment results in the context of existing literature."""
    
    name: str = "analyze_experiment_results"
    description: str = """Analyze experiment results using literature context.
Stores results summary and finds related papers to interpret findings.
Returns narrative analysis with paper references."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment"
            },
            "results_summary": {
                "type": "string",
                "description": "Short description of the experimental outcome"
            }
        },
        "required": ["experiment_id", "results_summary"]
    }
    
    async def execute(
        self,
        experiment_id: str,
        results_summary: str,
        **kwargs
    ) -> str:
        """
        Analyze results with literature context.
        
        Args:
            experiment_id: Experiment to analyze
            results_summary: Description of results
            
        Returns:
            Narrative analysis with literature references
        """
        try:
            exp_service = get_experiment_service()
            
            # Get experiment
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            # Store results summary
            exp_service.set_results_summary(experiment_id, results_summary)
            
            # Search literature for related results
            search_query = f"{experiment['scientific_question']} {results_summary}"
            related_papers = await self._search_related_literature(search_query)
            
            # Build analysis
            response_lines = [
                f"📊 **Results Analysis**\n",
                f"**Experiment:** {experiment['title']}",
                f"**Question:** {experiment['scientific_question']}",
                f"**Results:** {results_summary}\n",
                "---\n",
                "## 📚 Literature Context\n",
            ]
            
            if related_papers:
                for i, paper in enumerate(related_papers[:3], 1):
                    title = paper.get("title", "Unknown")[:70]
                    year = paper.get("year", "N/A")
                    doi = paper.get("doi", "")
                    response_lines.append(f"**{i}. {title}** ({year})")
                    if doi:
                        response_lines.append(f"   DOI: https://doi.org/{doi}")
                    response_lines.append("")
            else:
                response_lines.append("No directly related papers found.")
            
            response_lines.append("---\n")
            response_lines.append("## 🔬 Interpretation\n")
            response_lines.append("Based on the literature context:")
            response_lines.append("- Consider whether results align with existing findings")
            response_lines.append("- Note any unexpected outcomes that may warrant follow-up")
            response_lines.append("- Document potential confounding factors")
            
            response_lines.append("\n---\n")
            response_lines.append("## 🔮 Suggested Follow-up\n")
            response_lines.append("- Replicate key findings with additional controls")
            response_lines.append("- Consider complementary experimental approaches")
            response_lines.append("- Store provenance on blockchain with `store_experiment_on_chain`")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error analyzing results:** {str(e)}"
    
    async def _search_related_literature(self, query: str) -> List[Dict[str, Any]]:
        """Search for related papers."""
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query[:200],  # Limit query length
                "limit": 5,
                "fields": "title,year,externalIds"
            }
            
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            
            data = await loop.run_in_executor(None, do_request)
            papers = data.get("data", [])
            
            results = []
            for paper in papers:
                external_ids = paper.get("externalIds", {}) or {}
                results.append({
                    "title": paper.get("title", ""),
                    "year": paper.get("year"),
                    "doi": external_ids.get("DOI", "")
                })
            return results
            
        except Exception:
            return []


# =============================================================================
# Retrieval Tools
# =============================================================================

class GetExperimentTool(BaseTool):
    """Retrieve experiment details by ID."""
    
    name: str = "get_experiment"
    description: str = """Get details of a specific experiment by ID.
Returns full experiment information including status, protocol, reagent usages."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the experiment to retrieve"
            }
        },
        "required": ["experiment_id"]
    }
    
    async def execute(self, experiment_id: str, **kwargs) -> str:
        """
        Get experiment details.
        
        Args:
            experiment_id: Experiment to retrieve
            
        Returns:
            Formatted experiment details
        """
        try:
            exp_service = get_experiment_service()
            protocol_service = get_protocol_service()
            
            experiment = exp_service.get_experiment(experiment_id)
            if not experiment:
                return f"❌ **Experiment not found:** `{experiment_id}`"
            
            response_lines = [
                f"📋 **Experiment Details**\n",
                f"**ID:** `{experiment['id']}`",
                f"**Title:** {experiment['title']}",
                f"**Status:** {experiment['status']}",
                f"**Question:** {experiment['scientific_question']}",
                f"**Description:** {experiment['description'][:200]}...",
            ]
            
            # Protocol info
            if experiment.get("protocol_id"):
                protocol = protocol_service.get_protocol(experiment["protocol_id"])
                if protocol:
                    response_lines.append(f"**Protocol:** {protocol['name']} (`{experiment['protocol_id']}`)")
                else:
                    response_lines.append(f"**Protocol:** `{experiment['protocol_id']}`")
            
            # Tags
            if experiment.get("tags"):
                response_lines.append(f"**Tags:** {', '.join(experiment['tags'])}")
            
            # Reagent usages
            usages = experiment.get("reagent_usages", [])
            if usages:
                response_lines.append(f"\n**Reagent Usages:** ({len(usages)} total)")
                for u in usages[:5]:
                    source_icon = "🤖" if u["source"] == "auto_from_protocol" else "✋"
                    response_lines.append(f"  {source_icon} {u['reagent_id']}: {u['amount']} {u['unit']}")
                if len(usages) > 5:
                    response_lines.append(f"  ... and {len(usages) - 5} more")
            
            # Results
            if experiment.get("results_summary"):
                response_lines.append(f"\n**Results:** {experiment['results_summary'][:200]}...")
            
            # Blockchain
            if experiment.get("blockchain_tx_hash"):
                response_lines.append(f"\n🔗 **On-Chain:** `{experiment['blockchain_tx_hash'][:20]}...`")
            
            # Timestamps
            response_lines.append(f"\n**Created:** {experiment['created_at']}")
            response_lines.append(f"**Updated:** {experiment['updated_at']}")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error retrieving experiment:** {str(e)}"


class ListExperimentsTool(BaseTool):
    """List all experiments."""
    
    name: str = "list_experiments"
    description: str = """List all experiments with optional status filter.
Returns summary of each experiment including ID, title, status, and protocol link."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "status_filter": {
                "type": "string",
                "enum": ["planned", "in_progress", "completed"],
                "description": "Optional filter by status"
            }
        },
        "required": []
    }
    
    async def execute(
        self,
        status_filter: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        List experiments.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            Formatted list of experiments
        """
        try:
            exp_service = get_experiment_service()
            
            experiments = exp_service.list_experiments(status_filter=status_filter)
            
            if not experiments:
                filter_msg = f" with status '{status_filter}'" if status_filter else ""
                return f"📋 **No experiments found{filter_msg}.**\n\nUse `create_experiment` to start one."
            
            response_lines = [f"📋 **Experiments** ({len(experiments)} total)\n"]
            
            if status_filter:
                response_lines[0] = f"📋 **Experiments** (status: {status_filter}, {len(experiments)} total)\n"
            
            for exp in experiments[:10]:
                status_icon = {"planned": "📝", "in_progress": "🔬", "completed": "✅"}.get(exp["status"], "❓")
                chain_icon = "🔗" if exp.get("blockchain_tx_hash") else ""
                
                response_lines.append(f"{status_icon} **{exp['title']}** {chain_icon}")
                response_lines.append(f"   ID: `{exp['id']}` | Status: {exp['status']}")
                if exp.get("protocol_id"):
                    response_lines.append(f"   Protocol: `{exp['protocol_id']}`")
                response_lines.append("")
            
            if len(experiments) > 10:
                response_lines.append(f"... and {len(experiments) - 10} more")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error listing experiments:** {str(e)}"


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "PlanExperimentWithLiteratureTool",
    "CreateExperimentTool",
    "AttachProtocolToExperimentTool",
    "MarkExperimentStatusTool",
    "AddManualReagentUsageToExperimentTool",
    "StoreExperimentOnChainForExperimentTool",
    "AnalyzeExperimentResultsWithLiteratureTool",
    "GetExperimentTool",
    "ListExperimentsTool",
]
