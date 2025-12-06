"""
Literature Agent for academic research assistance.

This agent provides literature search capabilities using:
- PubMed (biomedical, life sciences, clinical studies)
- Semantic Scholar (all disciplines: CS, physics, chemistry, general)

Follows SpoonOS ToolCallAgent pattern from Quick Start guide.
The framework handles tool selection, execution, and error cases automatically.
"""

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from backend import config
from backend.schemas.common import PageContext
from backend.tools.literature_tools import PubMedSearchTool, SemanticScholarTool


class LiteratureAgent(ToolCallAgent):
    """
    Academic literature search assistant for lab research.
    
    Searches PubMed and Semantic Scholar to find relevant papers
    based on user queries and current page context.
    
    Usage:
        agent = LiteratureAgent(workspace_id="ws_123", user_id="user_456")
        response = await agent.process("Find CRISPR papers", page_context)
    """
    
    name: str = "literature_agent"
    description: str = "Academic literature search assistant for lab research"
    
    system_prompt: str = """You are a research literature assistant for the lab workspace.

Your capabilities:
- Search PubMed (biomedical, life sciences, clinical studies)
- Search Semantic Scholar (all disciplines: CS, physics, chemistry, general research)

Guidelines:
1. For medical/biology topics → use search_pubmed
2. For CS/physics/general topics → use search_semantic_scholar
3. If one search returns no results, automatically try the other database
4. Summarize key findings from papers
5. Always include URLs so users can access full papers
6. Be concise but informative

Context awareness:
- Consider the user's current page and workflow
- If viewing experiments: suggest protocol-related papers
- If viewing protocols: find relevant methodology papers
- Tailor recommendations to their current research context
"""

    available_tools: ToolManager = ToolManager([
        PubMedSearchTool(),
        SemanticScholarTool()
    ])

    def __init__(self, workspace_id: str, user_id: str):
        """
        Initialize LiteratureAgent with workspace context.
        
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
