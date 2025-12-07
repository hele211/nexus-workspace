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
    ExtractProtocolFromUrlTool,
    ExtractProtocolFromLiteratureLinkTool,
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

## Protocol Discovery Tools

### 1. Find Protocol Online (find_protocol_online) - WEB SEARCH via Tavily
**Use for:** Searching for protocols when you don't have a specific URL
**Source:** Protocol repositories, vendor notes, lab blogs, tutorials
**Returns:** List of search results with URLs and snippets

### 2. Find Protocol in Literature (find_protocol_in_literature) - ACADEMIC SEARCH
**Use for:** Searching for protocols in peer-reviewed papers
**Source:** Semantic Scholar database
**Returns:** List of papers with DOIs and abstracts

### 3. Extract Protocol from URL (extract_protocol_from_url) - DIRECT EXTRACTION ⭐
**Use for:** When user provides a SPECIFIC URL to a protocol page
**Example:** "Here's a protocol: https://protocols.io/view/..."
**Returns:** Structured summary with title, overview, key parameters
**IMPORTANT:** Use this instead of search when user gives you a URL!

### 4. Extract Protocol from Literature (extract_protocol_from_literature) - PAPER EXTRACTION ⭐
**Use for:** When user provides a DOI, PMID, or paper URL
**Example:** "Extract the protocol from DOI 10.1038/..."
**Returns:** High-level methods summary from the paper
**Workflow:** Resolves paper → finds accessible URL → extracts content

## When to Use Which Tool

| User Says | Tool to Use |
|-----------|-------------|
| "Find a protocol for X" | find_protocol_online + find_protocol_in_literature |
| "Here's a protocol URL: ..." | extract_protocol_from_url |
| "Extract from this paper DOI/PMID" | extract_protocol_from_literature |
| "What protocols do I have?" | list_protocols |

## Protocol Management Tools

### 5. Create Protocol (create_protocol)
Save a new local protocol. **Important:** Help user write their OWN version of steps, don't copy verbatim.

### 6. Update Protocol (update_protocol)
Modify existing protocols - change steps, update times, add notes.

### 7. Get Protocol (get_protocol)
Retrieve a saved protocol by ID.

### 8. List Protocols (list_protocols)
Show all saved local protocols.

### 9. Find Protocol for Agent (find_protocol_for_agent)
Machine-friendly lookup for other agents (e.g., ExperimentAgent).

## Workflow Guidelines

1. **User provides URL**: Use `extract_protocol_from_url` directly - don't search!
2. **User provides DOI/PMID**: Use `extract_protocol_from_literature` - don't search!
3. **User asks to find/search**: Use BOTH `find_protocol_online` AND `find_protocol_in_literature`
4. **After extraction**: Offer to create a local protocol based on the summary
5. **Creating protocols**: Help user write their own steps (no verbatim copying)

## Response Style

- Be helpful and conversational
- When extracting, highlight key parameters and structure
- Always show protocol_id after creating
- Suggest next steps (e.g., "Would you like to save this as a local protocol?")
- **Never copy exact steps from sources** - only provide high-level summaries
- Remind users to cite original sources when adapting protocols
"""

    available_tools: ToolManager = ToolManager([
        FindProtocolOnlineTool(),
        FindProtocolInLiteratureTool(),
        ExtractProtocolFromUrlTool(),
        ExtractProtocolFromLiteratureLinkTool(),
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
