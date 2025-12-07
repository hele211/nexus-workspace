"""
Configuration module for Nexus Workspace Backend.

Loads environment variables from the existing .env file in the project root.
All API keys are pre-configured and validated externally.
"""

import os
from dotenv import load_dotenv

# Load .env from project root with override=True to ensure fresh values
load_dotenv(override=True)

# =============================================================================
# LLM Provider Configuration
# =============================================================================

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

MODEL_NAME: str = {
    "openai": "gpt-4",
    "gemini": "gemini-2.0-flash-exp",
    "anthropic": "claude-3-sonnet-20240229",
}.get(LLM_PROVIDER, "gpt-4")

# Provider API Keys
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# =============================================================================
# Voice Integration
# =============================================================================

ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

# =============================================================================
# Academic Search (NCBI/PubMed)
# =============================================================================

NCBI_EMAIL: str = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY: str = os.getenv("NCBI_API_KEY", "")

# =============================================================================
# Database (Supabase)
# =============================================================================

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# =============================================================================
# Memory (Optional)
# =============================================================================

MEM0_API_KEY: str = os.getenv("MEM0_API_KEY", "")

# =============================================================================
# Neo X Blockchain (EVM-compatible sidechain)
# =============================================================================
#
# Neo X is an EVM-compatible sidechain of Neo blockchain.
# It uses the same tools as Ethereum (web3.py, MetaMask, etc.)
#
# Networks:
#   - Testnet: Free for development, get testnet GAS from faucet
#     Faucet: https://neoxwish.ngd.network/
#   - Mainnet: Requires real GAS tokens
#
# Private key is only needed for WRITING transactions (storing data hashes).
# Reading from blockchain is free and doesn't require a private key.
#

NEO_X_NETWORK: str = os.getenv("NEO_X_NETWORK", "testnet")  # "mainnet" or "testnet"

NEO_X_RPC_URLS = {
    "mainnet": "https://mainnet-1.rpc.banelabs.org",
    "testnet": "https://neoxt4seed1.ngd.network"
}

NEO_X_CHAIN_IDS = {
    "mainnet": 47763,
    "testnet": 12227332
}

NEO_X_RPC_URL: str = NEO_X_RPC_URLS.get(NEO_X_NETWORK, NEO_X_RPC_URLS["testnet"])
NEO_X_CHAIN_ID: int = NEO_X_CHAIN_IDS.get(NEO_X_NETWORK, NEO_X_CHAIN_IDS["testnet"])

# Private key for signing transactions (only needed for writing to blockchain)
# SECURITY: Never commit this to version control! Use .env file.
NEO_X_PRIVATE_KEY: str = os.getenv("NEO_X_PRIVATE_KEY", "")

# Smart contract address for lab data storage (set after deployment)
NEO_X_LAB_DATA_CONTRACT: str = os.getenv("NEO_X_LAB_DATA_CONTRACT", "")

# =============================================================================
# Tavily Search API (for reagent discovery)
# =============================================================================

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# =============================================================================
# Debug Flags
# =============================================================================

# Enable verbose debug output in BlockchainAgent responses
# Shows raw tx hashes, network info, and internal state for developers
# Default: False (off in production)
BLOCKCHAIN_AGENT_DEBUG: bool = os.getenv("BLOCKCHAIN_AGENT_DEBUG", "false").lower() == "true"
