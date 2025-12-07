"""
Experiment Agent for designing, recording, and analyzing experiments.

This agent demonstrates the SpoonOS hackathon pattern:
    Agent → SpoonOS → LLM → ToolCalls

Key SpoonOS integrations:
- Uses spoon_ai.agents.toolcall.ToolCallAgent for agent framework
- Uses spoon_ai.chat.ChatBot for LLM invocation (OpenAI/Gemini)
- Uses spoon_ai.tools.BaseTool pattern for all tools
- Uses memory tools for conversation continuity

Provides a conversational interface for:
- Planning experiments from scientific questions (using literature + protocols)
- Creating and managing experiment records
- Tracking reagent usage (manual and auto-deduced from protocols)
- Storing experiment provenance on Neo X blockchain
- Analyzing results in the context of existing literature
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
from backend.tools.protocol_tools import (
    ExtractProtocolFromUrlTool,
    ExtractProtocolFromLiteratureLinkTool,
)
from backend.tools.memory_tools import (
    SetConversationContextTool,
    GetConversationContextTool,
)
from backend import config
from backend.schemas.common import PageContext


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

## ⭐⭐ RULE 1: TRACK CURRENT EXPERIMENT AND PROTOCOL ⭐⭐

You maintain:
- "current experiment" - the last experiment created or referenced
- "current protocol" - the last protocol created or referenced (may be linked to experiment)

When user says "the experiment", "it", "add protocol to it" → they mean the CURRENT experiment.
When user says "the protocol", "attach it" → they mean the CURRENT protocol.

## ⭐⭐ RULE 2: NEVER ASK USER TO RESTATE - USE TOOLS ⭐⭐

When user gives follow-up commands like:
- "add the protocol"
- "attach reagents"
- "store on blockchain"
- "mark as done"

You MUST NOT ask "which experiment?" or "please provide the experiment ID".
Instead, ALWAYS do this:

```
1. get_conversation_context(conversation_id) → get current_experiment_id, current_protocol_id
2. get_experiment(current_experiment_id) → see current state
3. Perform the operation using those IDs
4. Respond with confirmation
```

## ⭐⭐ RULE 3: CREATE vs MODIFY - NEVER CONFUSE THEM ⭐⭐

**Use create_experiment ONLY when user explicitly says:**
- "Create an experiment for X"
- "Start a new experiment"
- "Plan an experiment to test Y"

**Use existing tools for EVERYTHING ELSE:**
- "Add the protocol" → attach_protocol_to_experiment(current_experiment_id, current_protocol_id)
- "Store on blockchain" → store_experiment_on_chain(current_experiment_id)
- "Mark as done" → mark_experiment_status(current_experiment_id, "completed")

**NEVER create a new experiment when user wants to modify the existing one!**

## WORKFLOW: Creating a New Experiment

```
1. create_experiment(title="X", question="...", description="...")
2. Tool returns: {"id": "exp_abc123", ...}
3. set_conversation_context(conversation_id, current_experiment_id="exp_abc123")
4. Respond: "Created experiment exp_abc123."
```

## WORKFLOW: Follow-up Operations

When user says "add the protocol", "store on blockchain", etc:

```
1. get_conversation_context(conversation_id) → current_experiment_id, current_protocol_id
2. get_experiment(current_experiment_id) → see current state
3. Perform operation (attach_protocol, store_on_chain, etc.)
4. Respond with confirmation
```

## Available Tools

**Memory (USE FIRST for follow-ups):**
- get_conversation_context - Get current_experiment_id, current_protocol_id
- set_conversation_context - Set IDs after creating

**Experiment Management:**
- create_experiment - Create NEW experiment (only for explicit "create" requests)
- get_experiment - Retrieve experiment details
- list_experiments - List all experiments
- attach_protocol_to_experiment - Link protocol to experiment
- mark_experiment_status - Update status (completed, etc.)
- add_manual_reagent_usage - Log reagent usage
- store_experiment_on_chain - Blockchain provenance
- analyze_experiment_results - Literature-based analysis

**Planning:**
- plan_experiment_with_literature - Design from scientific question

**Protocol Extraction:**
- extract_protocol_from_url - Extract from URL
- extract_protocol_from_literature - Extract from DOI/PMID

## Response Style

- Show experiment_id in responses
- After operations, confirm what was done
- Guide users through the experiment lifecycle
"""

    available_tools: ToolManager = ToolManager([
        # Memory tools for conversation continuity (USE THESE!)
        GetConversationContextTool(),
        SetConversationContextTool(),
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
        # Protocol extraction tools (for URL/paper-based experiment design)
        ExtractProtocolFromUrlTool(),
        ExtractProtocolFromLiteratureLinkTool(),
        # Raw blockchain tools for direct access
        StoreExperimentOnChainTool(),
        VerifyExperimentIntegrityTool(),
        GetBlockchainStatusTool(),
    ])
    
    def __init__(self, workspace_id: str = "", user_id: str = ""):
        """
        Initialize ExperimentAgent.
        
        Demonstrates: Agent → SpoonOS → LLM pattern.
        
        Args:
            workspace_id: Current workspace ID
            user_id: Current user ID
        """
        # Create ChatBot with configured LLM provider (SpoonOS LLM invocation)
        llm = ChatBot(
            llm_provider=config.LLM_PROVIDER,
            model_name=config.MODEL_NAME
        )
        
        # Initialize parent ToolCallAgent with LLM
        super().__init__(llm=llm)
        
        self.workspace_id = workspace_id
        self.user_id = user_id
    
    async def process(
        self,
        message: str,
        page_context: PageContext = None,
        conversation_id: str = "default",
        history: list = None
    ) -> str:
        """
        Process a user message about experiments.
        
        Demonstrates: Agent → SpoonOS → LLM → ToolCalls pattern.
        
        Args:
            message: User's query
            page_context: Current page state from frontend
            conversation_id: Session ID for memory continuity
            history: Previous messages in conversation
            
        Returns:
            Agent response
        """
        # Build context-aware prompt with conversation_id for memory tools
        history_text = ""
        if history:
            history_text = "\n\nRecent conversation:\n"
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]  # Truncate long messages
                history_text += f"- {role}: {content}\n"
        
        context_parts = [f"Conversation ID: {conversation_id}"]
        
        if page_context:
            if hasattr(page_context, 'experiment_ids') and page_context.experiment_ids:
                context_parts.append(f"Experiments in view: {page_context.experiment_ids}")
            if hasattr(page_context, 'protocol_ids') and page_context.protocol_ids:
                context_parts.append(f"Available protocols: {page_context.protocol_ids}")
        
        context_str = "; ".join(context_parts)
        
        full_prompt = f"""Context: {context_str}
{history_text}
User: {message}

REMEMBER: If user refers to "the experiment" or gives vague commands, call get_conversation_context first!
"""
        
        # Run the agent - framework handles tool selection and execution
        # This demonstrates: Agent → SpoonOS → LLM → ToolCalls
        response = await self.run(full_prompt)
        return response


# Export
__all__ = ["ExperimentAgent"]
