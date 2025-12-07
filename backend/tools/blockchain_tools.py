"""
Blockchain tools for verifiable scientific data storage on Neo X.

Provides tools for:
- StoreExperimentOnChainTool: Store experiment hash on blockchain
- VerifyExperimentIntegrityTool: Verify data integrity against blockchain
- GetBlockchainStatusTool: Check blockchain connection and account status

All tools follow SpoonOS BaseTool patterns with async execute methods.
"""

import json
from typing import Any, Dict, Optional

from spoon_ai.tools.base import BaseTool

from backend.services import get_blockchain_service, USE_MOCK_BLOCKCHAIN


# Neo X Testnet Explorer URL
EXPLORER_URL = "https://xt4scan.ngd.network"


class StoreExperimentOnChainTool(BaseTool):
    """
    Store experiment data hash on Neo X blockchain for immutable verification.
    
    Creates a permanent, tamper-proof record of experiment data by storing
    its SHA-256 hash on the blockchain. Returns a transaction hash that
    can be used to verify data integrity at any time.
    """
    
    name: str = "store_experiment_on_chain"
    description: str = """Store experiment data hash on Neo X blockchain for permanent, 
tamper-proof verification. Use this when a researcher wants to create an immutable 
record of their experiment data. Returns a transaction hash and explorer link."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "Unique identifier for the experiment (e.g., 'exp_001')"
            },
            "experiment_data": {
                "type": "object",
                "description": "The experiment data to hash and store (title, results, etc.)"
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata (researcher name, lab, version, etc.)"
            }
        },
        "required": ["experiment_id", "experiment_data"]
    }
    
    async def execute(
        self,
        experiment_id: str,
        experiment_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Store experiment hash on blockchain.
        
        Args:
            experiment_id: Unique experiment identifier
            experiment_data: Dictionary containing experiment data
            metadata: Optional additional metadata
            
        Returns:
            Formatted string with transaction details and explorer link
        """
        try:
            service = get_blockchain_service()
            
            # Check connection
            if not service.is_connected():
                return "❌ **Blockchain Error**: Not connected to Neo X network. Please check your configuration."
            
            # Generate hash
            data_hash = service.hash_experiment_data(experiment_data)
            
            # Store on blockchain
            tx_hash = await service.store_experiment_hash(
                experiment_id=experiment_id,
                data_hash=data_hash,
                metadata=metadata
            )
            
            if not tx_hash:
                return """❌ **Storage Failed**: Could not store on blockchain.

**Possible causes:**
- No private key configured (read-only mode)
- Insufficient GAS balance
- Network connectivity issues

Configure `NEO_X_PRIVATE_KEY` in `.env` to enable blockchain writes."""
            
            # Format tx_hash with 0x prefix for explorer
            tx_hash_formatted = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
            explorer_link = f"{EXPLORER_URL}/tx/{tx_hash_formatted}"
            
            # Build response
            mode = "MOCK" if USE_MOCK_BLOCKCHAIN else "REAL"
            
            return f"""✅ **Experiment Stored on Blockchain!**

**Experiment ID:** {experiment_id}
**Data Hash:** `{data_hash[:20]}...{data_hash[-8:]}`
**Transaction Hash:** `{tx_hash_formatted[:20]}...{tx_hash_formatted[-8:]}`

🔗 **View on Explorer:** {explorer_link}

**Mode:** {mode} Neo X Testnet

---
💡 **Save this transaction hash** to verify data integrity later using the `verify_experiment_integrity` tool."""
            
        except Exception as e:
            return f"❌ **Blockchain Error**: {str(e)}"


class VerifyExperimentIntegrityTool(BaseTool):
    """
    Verify experiment data integrity against blockchain record.
    
    Compares the hash of current experiment data against the hash
    stored on the blockchain. Detects any tampering or modifications
    to the original data.
    """
    
    name: str = "verify_experiment_integrity"
    description: str = """Verify experiment data hasn't been tampered with by comparing 
against the blockchain record. Use this when you need to confirm data integrity 
or detect modifications. Requires the original transaction hash from when data was stored."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "experiment_data": {
                "type": "object",
                "description": "The current experiment data to verify"
            },
            "transaction_hash": {
                "type": "string",
                "description": "The transaction hash from when the experiment was stored on blockchain"
            }
        },
        "required": ["experiment_data", "transaction_hash"]
    }
    
    async def execute(
        self,
        experiment_data: Dict[str, Any],
        transaction_hash: str,
        **kwargs
    ) -> str:
        """
        Verify experiment data against blockchain record.
        
        Args:
            experiment_data: Current experiment data to verify
            transaction_hash: Transaction hash from original storage
            
        Returns:
            Formatted string with verification result
        """
        try:
            service = get_blockchain_service()
            
            # Check connection
            if not service.is_connected():
                return "❌ **Blockchain Error**: Not connected to Neo X network."
            
            # Format transaction hash
            tx_hash = transaction_hash if transaction_hash.startswith("0x") else f"0x{transaction_hash}"
            explorer_link = f"{EXPLORER_URL}/tx/{tx_hash}"
            
            # Get transaction details
            tx = await service.get_transaction(tx_hash)
            
            if not tx:
                return f"""❌ **Transaction Not Found**

Transaction hash: `{tx_hash[:20]}...{tx_hash[-8:]}`

**Possible causes:**
- Invalid transaction hash
- Transaction not yet confirmed
- Wrong network (check testnet vs mainnet)

🔗 **Check Explorer:** {explorer_link}"""
            
            # Calculate current hash
            current_hash = service.hash_experiment_data(experiment_data)
            
            # Get stored hash
            stored_data = tx.get("data", {})
            stored_hash = stored_data.get("hash", "") if isinstance(stored_data, dict) else ""
            
            # Compare
            is_valid = current_hash == stored_hash
            
            if is_valid:
                return f"""✅ **Data Integrity Verified!**

**Status:** Data matches blockchain record
**Current Hash:** `{current_hash[:20]}...{current_hash[-8:]}`
**Stored Hash:** `{stored_hash[:20]}...{stored_hash[-8:]}`

**Transaction Details:**
- Block: {tx.get('block_number', 'N/A')}
- Timestamp: {tx.get('timestamp', 'N/A')}
- Experiment ID: {stored_data.get('id', 'N/A') if isinstance(stored_data, dict) else 'N/A'}

🔗 **View on Explorer:** {explorer_link}

---
✅ This data has NOT been tampered with since it was recorded on the blockchain."""
            else:
                return f"""⚠️ **DATA INTEGRITY FAILURE - TAMPERING DETECTED!**

**Status:** Data does NOT match blockchain record

**Hash Comparison:**
- Current Hash: `{current_hash[:20]}...{current_hash[-8:]}`
- Stored Hash:  `{stored_hash[:20]}...{stored_hash[-8:]}`

**Original Record:**
- Block: {tx.get('block_number', 'N/A')}
- Timestamp: {tx.get('timestamp', 'N/A')}
- Experiment ID: {stored_data.get('id', 'N/A') if isinstance(stored_data, dict) else 'N/A'}

🔗 **View Original on Explorer:** {explorer_link}

---
⚠️ **WARNING:** The data has been modified since it was recorded on the blockchain.
This could indicate tampering, data corruption, or accidental changes."""
            
        except Exception as e:
            return f"❌ **Verification Error**: {str(e)}"


class GetBlockchainStatusTool(BaseTool):
    """
    Get Neo X blockchain connection status and account information.
    
    Shows network connectivity, account balance, and configuration details.
    Useful for debugging and monitoring blockchain integration.
    """
    
    name: str = "get_blockchain_status"
    description: str = """Check Neo X blockchain connection status, account balance, 
and network information. Use this to verify the blockchain integration is working 
or to check GAS balance before storing data."""
    
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    async def execute(self, **kwargs) -> str:
        """
        Get blockchain status and account information.
        
        Returns:
            Formatted string with network and account details
        """
        try:
            service = get_blockchain_service()
            info = service.get_network_info()
            
            # Determine mode
            is_mock = info.get("mock_mode", USE_MOCK_BLOCKCHAIN)
            mode = "🧪 MOCK (Development)" if is_mock else "⛓️ REAL (Neo X Testnet)"
            
            # Connection status
            connected = info.get("connected", False)
            connection_status = "✅ Connected" if connected else "❌ Disconnected"
            
            # Account info
            account = info.get("account_address")
            if account:
                account_display = f"`{account[:10]}...{account[-8:]}`"
                balance = info.get("gas_balance_ether", 0)
                balance_status = f"{balance:.6f} GAS"
                
                # Balance warning
                if balance == 0:
                    balance_warning = "\n⚠️ **Warning:** No GAS balance. Cannot write to blockchain."
                elif balance < 0.01:
                    balance_warning = "\n⚠️ **Low Balance:** Consider adding more testnet GAS."
                else:
                    balance_warning = ""
            else:
                account_display = "Not configured"
                balance_status = "N/A"
                balance_warning = "\n⚠️ **Read-Only Mode:** No private key configured."
            
            # Explorer link for account
            explorer_account = f"{EXPLORER_URL}/address/{account}" if account else ""
            
            # Build response
            response = f"""**Neo X Blockchain Status**

**Mode:** {mode}
**Connection:** {connection_status}

**Network:**
- Name: {info.get('network', 'N/A')}
- Chain ID: {info.get('chain_id', 'N/A')}
- RPC URL: `{info.get('rpc_url', 'N/A')}`
- Latest Block: {info.get('latest_block', 'N/A')}

**Account:**
- Address: {account_display}
- Balance: {balance_status}{balance_warning}"""
            
            if explorer_account:
                response += f"\n\n🔗 **View Account:** {explorer_account}"
            
            if is_mock:
                tx_count = info.get("transactions_stored", 0)
                response += f"\n\n**Mock Storage:** {tx_count} transactions in memory"
            
            return response
            
        except Exception as e:
            return f"❌ **Status Error**: {str(e)}"


# Export all tools
__all__ = [
    "StoreExperimentOnChainTool",
    "VerifyExperimentIntegrityTool",
    "GetBlockchainStatusTool",
]
