"""
Protocol Agent for finding, creating, and managing lab protocols.

This agent demonstrates the SpoonOS hackathon pattern:
    Agent → SpoonOS → LLM → ToolCalls

Key SpoonOS integrations:
- Uses spoon_ai.agents.toolcall.ToolCallAgent for agent framework
- Uses spoon_ai.chat.ChatBot for LLM invocation (OpenAI/Gemini)
- Uses spoon_ai.tools.BaseTool pattern for all tools
- Uses memory tools (SetConversationContextTool, GetConversationContextTool)
  for conversation continuity

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
from backend.tools.memory_tools import (
    SetConversationContextTool,
    GetConversationContextTool,
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

## ⭐⭐ RULE 1: TRACK THE CURRENT PROTOCOL ⭐⭐

You maintain a "current protocol" - the last protocol created or referenced.
- After creating a protocol → it becomes the current protocol
- After user says "get protocol X" → X becomes the current protocol
- When user says "the protocol", "it", "add details" → they mean the CURRENT protocol

## ⭐⭐ RULE 2: NEVER ASK USER TO RESTATE - USE TOOLS ⭐⭐

When user gives follow-up commands like:
- "add more details"
- "add reagents and waiting times"  
- "find reference protocol for this"
- "modify the steps"

You MUST NOT ask "which protocol?" or "please provide the protocol content".
Instead, ALWAYS do this:

```
1. get_conversation_context(conversation_id) → get current_protocol_id
2. get_protocol(current_protocol_id) → see current steps/description
3. [optional] find_protocol_online or find_protocol_in_literature → get reference info
4. update_protocol(current_protocol_id, steps=[enriched steps], ...) → save changes
5. Respond with what you updated
```

## ⭐⭐ RULE 3: CREATE vs UPDATE - NEVER CONFUSE THEM ⭐⭐

**Use create_protocol ONLY when user explicitly says:**
- "Create a new protocol for X"
- "Make a protocol for Y"
- "Start a new protocol"

**Use update_protocol for EVERYTHING ELSE:**
- "Add details" → UPDATE current protocol
- "Add reagents" → UPDATE current protocol  
- "Add waiting times" → UPDATE current protocol
- "Find reference for this" → search, then UPDATE current protocol
- "Modify the steps" → UPDATE current protocol

**NEVER create a new protocol when user wants to modify the existing one!**

## WORKFLOW: Creating a New Protocol

```
1. create_protocol(name="X", description="...", steps=[...])
2. Tool returns: {"id": "protocol_abc123", ...}
3. set_conversation_context(conversation_id, current_protocol_id="protocol_abc123")
4. Respond: "Created protocol_abc123 with N steps."
```

## WORKFLOW: Enriching/Updating Current Protocol

When user says "add reagents", "add details", "find reference protocol":

```
1. get_conversation_context(conversation_id) → current_protocol_id = "protocol_abc123"
2. get_protocol("protocol_abc123") → see current steps
3. [optional] find_protocol_online("reagents for PCR fish identification") → get reference
4. Build enriched steps with reagents, timings, details
5. update_protocol("protocol_abc123", steps=[enriched_steps])
6. Respond: "Updated protocol_abc123: added reagents and timing to steps 1-4."
```

## WORKFLOW: Finding Reference for Current Protocol

When user says "find reference protocol for this":

```
1. get_conversation_context(conversation_id) → current_protocol_id
2. get_protocol(current_protocol_id) → see what the protocol is about
3. find_protocol_online or find_protocol_in_literature → search for references
4. update_protocol(current_protocol_id, source_reference="...", steps=[enriched])
5. Respond with what you found and updated
```

## Available Tools

**Memory (USE FIRST for follow-ups):**
- get_conversation_context - Get current_protocol_id
- set_conversation_context - Set current_protocol_id after creating

**Protocol Management:**
- create_protocol - Create NEW protocol (only for explicit "create" requests)
- update_protocol - Modify EXISTING protocol (for all "add/modify" requests)
- get_protocol - Retrieve protocol details
- list_protocols - List all protocols

**Discovery (for enrichment):**
- find_protocol_online - Web search for reference protocols
- find_protocol_in_literature - Academic paper search
- extract_protocol_from_url - Extract from specific URL
- extract_protocol_from_literature - Extract from DOI/PMID

## Response Style

- Show protocol_id in responses
- After updates, summarize what changed
- Never copy exact steps from sources - provide high-level summaries
"""

    available_tools: ToolManager = ToolManager([
        # Memory tools for conversation continuity (USE THESE!)
        GetConversationContextTool(),
        SetConversationContextTool(),
        # Protocol discovery
        FindProtocolOnlineTool(),
        FindProtocolInLiteratureTool(),
        ExtractProtocolFromUrlTool(),
        ExtractProtocolFromLiteratureLinkTool(),
        # Protocol management
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

    async def process(
        self, 
        message: str, 
        page_context: PageContext,
        conversation_id: str = "default",
        history: list = None
    ) -> str:
        """
        Process a user message with page context awareness.
        
        Demonstrates: Agent → SpoonOS → LLM → ToolCalls pattern.
        
        Args:
            message: User's query or request
            page_context: Current page state from frontend
            conversation_id: Session ID for memory continuity
            history: Previous messages in conversation
            
        Returns:
            Agent's response as a string
        """
        # Build context-aware prompt with conversation_id for memory tools
        history_text = ""
        if history:
            history_text = "\n\nRecent conversation:\n"
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]  # Truncate long messages
                history_text += f"- {role}: {content}\n"
        
        context_prompt = f"""Current workspace: {self.workspace_id}
Current page: {page_context.route}
Conversation ID: {conversation_id}
Visible protocols: {page_context.protocol_ids}
{history_text}
User query: {message}

REMEMBER: If user refers to "the protocol" or gives vague commands, call get_conversation_context first!
"""
        
        # Run the agent - framework handles tool selection and execution
        # This demonstrates: Agent → SpoonOS → LLM → ToolCalls
        response = await self.run(context_prompt)
        
        return response
