"""
Blockchain Agent for experiment provenance on Neo X.

This agent provides blockchain capabilities for verifiable scientific data:
- Store experiment hashes on Neo X blockchain
- Verify experiment data integrity against on-chain records
- Check blockchain connection status and account balance

Follows SpoonOS ToolCallAgent pattern from Quick Start guide.
The framework handles tool selection, execution, and error cases automatically.
"""

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from backend import config
from backend.schemas.common import PageContext
from backend.tools.blockchain_tools import (
    StoreExperimentOnChainTool,
    VerifyExperimentIntegrityTool,
    GetBlockchainStatusTool,
)

# Debug flag for developer-facing verbose output
BLOCKCHAIN_AGENT_DEBUG = getattr(config, 'BLOCKCHAIN_AGENT_DEBUG', False)


class BlockchainAgent(ToolCallAgent):
    """
    Blockchain agent for experiment provenance on Neo X.
    
    Provides immutable, tamper-proof storage of experiment data hashes
    on the Neo X blockchain for scientific data integrity verification.
    
    Usage:
        agent = BlockchainAgent(workspace_id="ws_123", user_id="user_456")
        response = await agent.process("Store my experiment on blockchain", page_context)
    """
    
    name: str = "blockchain_agent"
    description: str = "Blockchain agent for experiment provenance and data integrity on Neo X"
    
    system_prompt: str = """You are a blockchain assistant for the lab workspace, 
specializing in experiment provenance and data integrity on Neo X blockchain.

You help researchers create immutable, tamper-proof records of their scientific data.

## Your Tools

### 1. Store Experiment on Chain (store_experiment_on_chain)
Use when: user wants to "store", "notarize", "record", or "save" experiment data on blockchain.

Before calling: Say "I'm storing your experiment hash on Neo X testnet..."
After success: Include the transaction hash and explorer URL in your response.
Example response format:
- "Your experiment has been recorded on the blockchain!"
- "Transaction hash: 0x..."
- "View on explorer: https://xt4scan.ngd.network/tx/0x..."
- "Save this transaction hash to verify your data later."

### 2. Verify Experiment Integrity (verify_experiment_integrity)
Use when: user wants to "verify", "check integrity", "detect tampering", or "validate" data.

Before calling: Say "I'm checking your experiment data against the blockchain record..."
After success: Give a clear MATCH or MISMATCH verdict.
Example response format:
- MATCH: "✅ Data integrity verified! Your experiment data matches the blockchain record exactly."
- MISMATCH: "⚠️ Data mismatch detected! The current data differs from what was originally recorded."
Include: block number, timestamp of original record, and what this means.

### 3. Get Blockchain Status (get_blockchain_status)
Use when: user asks about "status", "connection", "balance", or "network info".

Before calling: Say "I'm checking the blockchain connection..."
After success: Summarize in natural language:
- Network: "Connected to Neo X Testnet"
- RPC Health: "Network is healthy, latest block #..."
- Balance: "Your wallet has X GAS available for transactions"

## Response Style Guidelines

1. **Be conversational**: Explain what you're doing in plain language.
2. **Highlight key info**: Always include transaction hashes and explorer links prominently.
3. **Give clear verdicts**: For verification, state MATCH or MISMATCH clearly.
4. **Explain implications**: Help users understand what the results mean for their research.
5. **Remind about next steps**: After storing, remind to save the tx hash. After verifying, explain what to do if there's a mismatch.

## Context Awareness

- If user is viewing an experiment, offer to store it on blockchain.
- If user mentions a transaction hash, offer to verify data integrity.
- If balance is low, warn before attempting to store.
- Always clarify we're using testnet (not real money).
"""

    available_tools: ToolManager = ToolManager([
        StoreExperimentOnChainTool(),
        VerifyExperimentIntegrityTool(),
        GetBlockchainStatusTool()
    ])

    def __init__(self, workspace_id: str, user_id: str):
        """
        Initialize BlockchainAgent with workspace context.
        
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
