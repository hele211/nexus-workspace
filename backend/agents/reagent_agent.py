"""
Reagent Agent for discovery, registration, and inventory management.

This agent provides reagent capabilities for lab experiments:
- Search for reagents online via Tavily
- Get detailed product information
- Register reagents in inventory
- Track usage and low-inventory alerts

Follows SpoonOS ToolCallAgent pattern from Quick Start guide.
The framework handles tool selection, execution, and error cases automatically.
"""

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from backend import config
from backend.schemas.common import PageContext
from backend.tools.reagent_tools import (
    SearchReagentOnlineTool,
    GetReagentDetailsFromWebTool,
    AddReagentToInventoryTool,
    RecordReagentUsageTool,
    ListLowInventoryReagentsTool,
)


class ReagentAgent(ToolCallAgent):
    """
    Reagent agent for discovery, registration, and inventory tracking.
    
    Assists researchers with finding reagents, adding them to inventory,
    tracking usage, and monitoring low-inventory alerts.
    
    Usage:
        agent = ReagentAgent(workspace_id="ws_123", user_id="user_456")
        response = await agent.process("Find mouse CD64 antibody", page_context)
    """
    
    name: str = "reagent_agent"
    description: str = "Assists with reagent discovery, registration, and inventory tracking for lab experiments"
    
    system_prompt: str = """You are a reagent assistant for the lab workspace.
You help researchers find, register, and track reagents for their experiments.

## Your Tools

### 1. Search Reagent Online (search_reagent_online)
Use when: User asks to find, search for, or look up a reagent.
Examples: "find mouse CD64 antibody", "search for FITC conjugated anti-human CD45"

Before calling: Say "I'm searching for reagent products..."
After success: Present the ranked list with the Top Recommendation clearly marked.

### 2. Get Reagent Details (get_reagent_details_from_web)
Use when: User selects a specific product and wants more details.
Examples: "get details for that Abcam antibody", "tell me more about catalog AB-12345"

Before calling: Say "I'm getting detailed information..."
After success: Show storage conditions, pack size, and other specs.

### 3. Add Reagent to Inventory (add_reagent_to_inventory)
Use when: User wants to register/add a reagent to their inventory.
Examples: "add this to my inventory", "register 100 µL of this antibody"

Before calling: Confirm the details with the user if not all fields are provided.
After success: Show the assigned reagent_id and remind them to use it for tracking.

### 4. Record Reagent Usage (record_reagent_usage)
Use when: User reports using a reagent in an experiment.
Examples: "I used 5 µL of reagent_abc123", "log 10 mg usage for experiment exp_001"

Before calling: Say "I'm recording the usage..."
After success: Show before/after quantities. If <10% remaining, emphasize the LOW INVENTORY warning.

### 5. List Low Inventory (list_low_inventory_reagents)
Use when: User asks about inventory status or what's running low.
Examples: "what reagents are low?", "check my inventory", "what needs reordering?"

Before calling: Say "I'm checking inventory levels..."
After success: List all reagents below 10% or confirm all is well.

## Workflow Guidelines

1. **Finding a reagent**: Start with search_reagent_online, then offer to get details.
2. **Adding to inventory**: After getting details, ask for quantity and unit if not provided.
3. **Recording usage**: Always confirm the reagent_id and unit match.
4. **Low inventory**: Proactively mention if a reagent drops below 10% after usage.

## Response Style

- Be helpful and conversational
- Always show the reagent_id after adding to inventory
- Clearly warn about low inventory (<10%)
- Suggest next steps (e.g., "Would you like to add this to inventory?")
"""

    available_tools: ToolManager = ToolManager([
        SearchReagentOnlineTool(),
        GetReagentDetailsFromWebTool(),
        AddReagentToInventoryTool(),
        RecordReagentUsageTool(),
        ListLowInventoryReagentsTool()
    ])

    def __init__(self, workspace_id: str, user_id: str):
        """
        Initialize ReagentAgent with workspace context.
        
        Args:
            workspace_id: ID of the current workspace
            user_id: ID of the authenticated user
        """
        # Create ChatBot with configured LLM provider
        llm = ChatBot(
            llm_provider=config.LLM_PROVIDER,
            model_name=config.MODEL_NAME
        )
        
        # Initialize parent ToolCallAgent
        super().__init__(llm=llm)
        
        # Store instance context
        self.workspace_id = workspace_id
        self.user_id = user_id

    async def process(self, message: str, page_context: PageContext) -> str:
        """
        Process a user message with page context awareness.
        
        Args:
            message: User's query or request
            page_context: Current page state from frontend
            
        Returns:
            Agent's response as a string
        """
        # Build context-aware prompt
        context_prompt = f"""
Current workspace: {self.workspace_id}
Current page: {page_context.route}
Visible experiments: {page_context.experiment_ids}
Active filters: {page_context.filters}

User query: {message}
"""
        
        # Run the agent - framework handles tool selection and execution
        response = await self.run(context_prompt)
        
        return response
