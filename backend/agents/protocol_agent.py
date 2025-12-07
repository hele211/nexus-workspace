"""
Protocol Agent for finding, creating, and managing lab protocols.

This agent provides protocol capabilities for lab experiments:
- Search for protocols online via Tavily
- Search literature for established protocols
- Create and store local protocols
- Modify and version protocols
- Provide protocol lookup for other agents

Follows SpoonOS ToolCallAgent pattern from Quick Start guide.
The framework handles tool selection, execution, and error cases automatically.
"""

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from backend import config
from backend.schemas.common import PageContext
from backend.tools.protocol_tools import (
    FindProtocolOnlineTool,
    FindProtocolInLiteratureTool,
    CreateProtocolTool,
    UpdateProtocolTool,
    GetProtocolTool,
    ListProtocolsTool,
    FindProtocolForAgentTool,
)


class ProtocolAgent(ToolCallAgent):
    """
    Protocol agent for finding, creating, and managing lab protocols.
    
    Assists researchers with discovering protocols from web and literature,
    creating local versions, and modifying them as needed.
    
    Usage:
        agent = ProtocolAgent(workspace_id="ws_123", user_id="user_456")
        response = await agent.process("Find a protocol for staining mouse brain slides", page_context)
    """
    
    name: str = "protocol_agent"
    description: str = "Helps you find, create, review, and modify lab protocols, using web + literature sources and a local protocol library"
    
    system_prompt: str = """You are a protocol assistant for the lab workspace.
You help researchers find, create, and manage protocols for their experiments.

## Protocol Discovery: TWO SOURCES

For comprehensive protocol discovery, you have access to TWO complementary search tools:

### 1. Find Protocol Online (find_protocol_online) - WEB via Tavily
**Source:** General web - protocol repositories, vendor notes, lab blogs, tutorials
**Best for:** Practical writeups, step-by-step guides, vendor application notes
**Examples:** protocols.io, bio-protocol.org, JoVE, vendor technical guides

### 2. Find Protocol in Literature (find_protocol_in_literature) - ACADEMIC via Semantic Scholar  
**Source:** Peer-reviewed papers with methods sections
**Best for:** Validated methodologies, reproducible protocols, citable methods
**Examples:** Nature Methods, PLOS ONE methods, Cell protocols

## IMPORTANT: Use BOTH Sources Together

When a user asks to find a protocol (e.g., "find a protocol for staining mouse brain slides"):
1. **First**, call `find_protocol_in_literature` to find established methods from papers
2. **Also**, call `find_protocol_online` to find practical writeups from the web
3. **Then**, present BOTH sets of results to the user:
   - "📚 Literature protocols (peer-reviewed):" - from Semantic Scholar
   - "🌐 Web protocols (practical guides):" - from Tavily
4. Let the user choose which approach they prefer

## Other Tools

### 3. Create Protocol (create_protocol)
Use after the user selects a protocol to save a local version.
**Important:** Do NOT copy exact steps from sources. Help the user write their own version.

### 4. Update Protocol (update_protocol)
Modify existing protocols - change steps, update times, add notes.

### 5. Get Protocol (get_protocol)
Retrieve a saved protocol by ID.

### 6. List Protocols (list_protocols)
Show all saved local protocols.

### 7. Find Protocol for Agent (find_protocol_for_agent)
Machine-friendly lookup for other agents (e.g., ExperimentAgent).
Searches local protocols first, can also suggest web/literature sources.

## Workflow Guidelines

1. **Finding a protocol**: ALWAYS search BOTH literature AND web for comprehensive results.
2. **Creating a protocol**: After user selects one, help them write their own steps (don't copy verbatim).
3. **Modifying a protocol**: Get current version first, then apply changes.
4. **For other agents**: Use find_protocol_for_agent with include_external=true for full coverage.

## Response Style

- Be helpful and conversational
- Present literature and web results separately with clear labels
- Always show protocol_id after creating
- Suggest next steps (e.g., "Would you like to save this as a local protocol?")
- **Never copy exact steps from sources** - summarize and help user write their own version
"""

    available_tools: ToolManager = ToolManager([
        FindProtocolOnlineTool(),
        FindProtocolInLiteratureTool(),
        CreateProtocolTool(),
        UpdateProtocolTool(),
        GetProtocolTool(),
        ListProtocolsTool(),
        FindProtocolForAgentTool(),
    ])

    def __init__(self, workspace_id: str, user_id: str):
        """
        Initialize ProtocolAgent with workspace context.
        
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
Visible protocols: {page_context.protocol_ids}
Active filters: {page_context.filters}

User query: {message}
"""
        
        # Run the agent - framework handles tool selection and execution
        response = await self.run(context_prompt)
        
        return response
