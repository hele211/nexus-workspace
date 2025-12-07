"""
Experiment Agent for designing, recording, and analyzing experiments.

Provides a conversational interface for:
- Planning experiments from scientific questions (using literature + protocols)
- Creating and managing experiment records
- Tracking reagent usage (manual and auto-deduced from protocols)
- Storing experiment provenance on Neo X blockchain
- Analyzing results in the context of existing literature

Usage:
    agent = ExperimentAgent(workspace_id="ws_123", user_id="user_456")
    response = await agent.process("Plan an experiment to test if Gene X regulates Y", page_context)
"""

from typing import Any, Dict, Optional

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from backend.tools.experiment_tools import (
    PlanExperimentWithLiteratureTool,
    CreateExperimentTool,
    AttachProtocolToExperimentTool,
    MarkExperimentStatusTool,
    AddManualReagentUsageToExperimentTool,
    StoreExperimentOnChainForExperimentTool,
    AnalyzeExperimentResultsWithLiteratureTool,
    GetExperimentTool,
    ListExperimentsTool,
)
from backend.tools.blockchain_tools import (
    StoreExperimentOnChainTool,
    VerifyExperimentIntegrityTool,
    GetBlockchainStatusTool,
)


class ExperimentAgent(ToolCallAgent):
    """
    Agent for experiment design, recording, and analysis.
    
    Helps researchers:
    - Design experiments starting from scientific questions
    - Link experiments to protocols and reagents
    - Track execution and reagent usage
    - Store provenance on blockchain
    - Analyze results with literature context
    
    Usage:
        agent = ExperimentAgent(workspace_id="ws_123", user_id="user_456")
        response = await agent.process("Plan an experiment to test X", page_context)
    """
    
    name: str = "experiment_agent"
    description: str = "Helps design, record, and analyze experiments: planning from literature, linking protocols and reagents, logging execution, and storing provenance on the Neo X blockchain."
    
    system_prompt: str = """You are an experiment assistant for the lab workspace.
You help researchers design, record, and analyze experiments.

## Workflow

### 1. Planning (from scientific question)
When user asks "How can I test whether X regulates Y?" or "Plan an experiment for...":
- Use `plan_experiment_with_literature` to propose an experiment plan
- This searches literature for relevant papers and suggests protocols
- Present the plan and ask if they want to create the experiment

### 2. Creating Experiments
When user confirms they want to proceed:
- Use `create_experiment` with title, question, description, and optional protocol_id
- If they want to attach a protocol separately, use `attach_protocol_to_experiment`

### 3. During Execution
When user logs reagent usage explicitly ("I used 5 µL of reagent R1"):
- Use `add_manual_reagent_usage` to log it
- This updates both the experiment record AND reagent inventory

### 4. Marking Completion
When user says "mark experiment as done" or "completed":
- Use `mark_experiment_status` with status="completed"
- This AUTO-DEDUCES reagent usage from the linked protocol's steps
- Inventory is automatically updated for each reagent reference

### 5. Blockchain Provenance
When user asks to "make this tamper-proof" or "store on blockchain":
- Use `store_experiment_on_chain` to create immutable record
- Returns transaction hash and explorer URL

### 6. Results Analysis
When user asks "analyze the results" or provides outcome data:
- Use `analyze_experiment_results` with the results summary
- This searches literature for related findings and provides interpretation

### 7. Retrieval
- Use `get_experiment` to show details of a specific experiment
- Use `list_experiments` to show all experiments (with optional status filter)

## Response Style

- Be helpful and guide users through the experiment lifecycle
- Always show experiment_id after creating
- Explain what auto-deduction means when marking complete
- Suggest next steps (e.g., "Would you like to store this on the blockchain?")
- When analyzing results, reference papers by title/DOI only (no copied text)
"""

    available_tools: ToolManager = ToolManager([
        # Experiment-specific tools
        PlanExperimentWithLiteratureTool(),
        CreateExperimentTool(),
        AttachProtocolToExperimentTool(),
        MarkExperimentStatusTool(),
        AddManualReagentUsageToExperimentTool(),
        StoreExperimentOnChainForExperimentTool(),
        AnalyzeExperimentResultsWithLiteratureTool(),
        GetExperimentTool(),
        ListExperimentsTool(),
        # Raw blockchain tools for direct access
        StoreExperimentOnChainTool(),
        VerifyExperimentIntegrityTool(),
        GetBlockchainStatusTool(),
    ])
    
    def __init__(self, workspace_id: str = "", user_id: str = ""):
        """
        Initialize ExperimentAgent.
        
        Args:
            workspace_id: Current workspace ID
            user_id: Current user ID
        """
        super().__init__()
        self.workspace_id = workspace_id
        self.user_id = user_id
    
    async def process(
        self,
        message: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user message about experiments.
        
        Args:
            message: User's query
            page_context: Optional context from the UI
            
        Returns:
            Agent response
        """
        # Build context-aware prompt
        context_parts = []
        
        if page_context:
            if page_context.get("experiment_ids"):
                context_parts.append(
                    f"Current experiments in view: {page_context['experiment_ids']}"
                )
            if page_context.get("protocol_ids"):
                context_parts.append(
                    f"Available protocols: {page_context['protocol_ids']}"
                )
        
        # Combine context with message
        if context_parts:
            full_prompt = f"Context: {'; '.join(context_parts)}\n\nUser: {message}"
        else:
            full_prompt = message
        
        # Run the agent
        response = await self.run(full_prompt)
        return response


# Export
__all__ = ["ExperimentAgent"]
