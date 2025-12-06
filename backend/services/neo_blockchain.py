"""
Neo X Blockchain Service for verifiable scientific data storage.

Neo X is an EVM-compatible sidechain of Neo blockchain.
This service provides:
- Connection to Neo X network (testnet/mainnet)
- Experiment data hashing and storage
- Transaction verification for data integrity

Uses Web3.py for all blockchain interactions.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from eth_account import Account
from web3 import Web3

# web3.py v6+ uses different import path for PoA middleware
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
    except ImportError:
        # Fallback: define a no-op if middleware not available
        geth_poa_middleware = None

from backend import config

logger = logging.getLogger(__name__)


class NeoBlockchainService:
    """
    Service for interacting with Neo X blockchain.
    
    Provides methods for:
    - Storing experiment data hashes on-chain
    - Verifying data integrity against stored hashes
    - Reading transaction history
    
    Usage:
        service = NeoBlockchainService()
        
        # Check connection
        if service.is_connected():
            info = service.get_network_info()
            print(f"Connected to {info['network']}")
        
        # Store experiment hash
        data_hash = service.hash_experiment_data(experiment_data)
        tx_hash = await service.store_experiment_hash("exp_001", data_hash)
        
        # Verify integrity later
        is_valid = await service.verify_experiment_integrity(experiment_data, tx_hash)
    """
    
    _instance: Optional["NeoBlockchainService"] = None
    
    def __new__(cls) -> "NeoBlockchainService":
        """Singleton pattern - only one instance needed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize Web3 connection to Neo X network."""
        # Skip if already initialized (singleton)
        if getattr(self, "_initialized", False):
            return
        
        self._initialized = True
        
        # Initialize Web3 with Neo X RPC
        self.w3 = Web3(Web3.HTTPProvider(config.NEO_X_RPC_URL))
        
        # Add PoA middleware (Neo X uses dBFT consensus, needs this for block handling)
        if geth_poa_middleware is not None:
            try:
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            except Exception as e:
                logger.warning(f"Could not inject PoA middleware: {e}")
        
        # Store configuration
        self.chain_id = config.NEO_X_CHAIN_ID
        self.contract_address = config.NEO_X_LAB_DATA_CONTRACT
        
        # Load account from private key if provided
        self.account: Optional[Account] = None
        if config.NEO_X_PRIVATE_KEY:
            try:
                self.account = Account.from_key(config.NEO_X_PRIVATE_KEY)
                logger.info(f"Neo X account loaded: {self.account.address}")
            except Exception as e:
                logger.error(f"Failed to load Neo X private key: {e}")
        else:
            logger.info("Neo X running in read-only mode (no private key configured)")
    
    def is_connected(self) -> bool:
        """
        Check if connected to Neo X network.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            return self.w3.is_connected()
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Get comprehensive network information.
        
        Returns:
            Dictionary containing:
            - network: Current network (testnet/mainnet)
            - chain_id: Chain ID
            - rpc_url: RPC endpoint URL
            - connected: Connection status
            - latest_block: Latest block number (if connected)
            - account_address: Loaded account address (if available)
            - gas_balance: Account GAS balance in wei (if account loaded)
            - gas_balance_ether: Account GAS balance in GAS units
        """
        info: Dict[str, Any] = {
            "network": config.NEO_X_NETWORK,
            "chain_id": self.chain_id,
            "rpc_url": config.NEO_X_RPC_URL,
            "connected": self.is_connected(),
            "latest_block": None,
            "account_address": None,
            "gas_balance": None,
            "gas_balance_ether": None,
        }
        
        if info["connected"]:
            try:
                info["latest_block"] = self.w3.eth.block_number
            except Exception as e:
                logger.error(f"Failed to get block number: {e}")
        
        if self.account:
            info["account_address"] = self.account.address
            if info["connected"]:
                try:
                    balance_wei = self.w3.eth.get_balance(self.account.address)
                    info["gas_balance"] = balance_wei
                    info["gas_balance_ether"] = self.w3.from_wei(balance_wei, "ether")
                except Exception as e:
                    logger.error(f"Failed to get balance: {e}")
        
        return info
    
    def hash_experiment_data(self, experiment_data: Dict) -> str:
        """
        Create deterministic SHA-256 hash of experiment data.
        
        The hash is deterministic because:
        - Dictionary keys are sorted
        - JSON serialization is consistent
        
        Args:
            experiment_data: Dictionary containing experiment data
            
        Returns:
            Hex string hash prefixed with "0x"
        """
        # Sort keys for deterministic hashing
        sorted_json = json.dumps(experiment_data, sort_keys=True, default=str)
        hash_bytes = hashlib.sha256(sorted_json.encode()).digest()
        return "0x" + hash_bytes.hex()
    
    async def store_experiment_hash(
        self,
        experiment_id: str,
        data_hash: str,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Store experiment hash on Neo X blockchain.
        
        Creates a transaction with the experiment hash embedded in the
        transaction data field. This provides immutable proof that the
        data existed at a specific point in time.
        
        Args:
            experiment_id: Unique identifier for the experiment
            data_hash: SHA-256 hash of the experiment data
            metadata: Optional additional metadata to store
            
        Returns:
            Transaction hash if successful, None if failed or no private key
        """
        if not self.account:
            logger.warning(
                "Cannot store on blockchain: No private key configured. "
                "Set NEO_X_PRIVATE_KEY in .env to enable write operations."
            )
            return None
        
        if not self.is_connected():
            logger.error("Cannot store on blockchain: Not connected to Neo X network")
            return None
        
        try:
            # Build transaction data payload
            tx_data = json.dumps({
                "type": "lab_experiment",
                "version": "1.0",
                "id": experiment_id,
                "hash": data_hash,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            })
            
            # Use run_in_executor for blocking Web3 calls
            loop = asyncio.get_event_loop()
            tx_hash = await loop.run_in_executor(None, self._send_transaction, tx_data)
            
            logger.info(f"Stored experiment {experiment_id} on blockchain: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Failed to store experiment on blockchain: {e}")
            return None
    
    def _send_transaction(self, data: str) -> str:
        """
        Send transaction to blockchain (blocking - called from executor).
        
        Sends a transaction to self with data embedded in the input field.
        This is a cost-effective way to store small amounts of data on-chain.
        
        Args:
            data: String data to embed in transaction
            
        Returns:
            Transaction hash as hex string
            
        Raises:
            Exception: If transaction fails
        """
        # Get current nonce
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        # Encode data as hex
        data_hex = "0x" + data.encode().hex()
        
        # Build transaction (send to self for data storage)
        tx = {
            "nonce": nonce,
            "to": self.account.address,  # Send to self
            "value": 0,  # No value transfer
            "gas": 100000,  # Gas limit
            "gasPrice": self.w3.eth.gas_price,
            "chainId": self.chain_id,
            "data": data_hex
        }
        
        # Sign transaction
        signed_tx = self.account.sign_transaction(tx)
        
        # Send transaction (web3.py v6+ uses raw_transaction, v5 uses rawTransaction)
        raw_tx = getattr(signed_tx, 'raw_transaction', None) or getattr(signed_tx, 'rawTransaction', None)
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        
        # Wait for receipt (confirms transaction was mined)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] != 1:
            raise Exception(f"Transaction failed with status {receipt['status']}")
        
        return receipt["transactionHash"].hex()
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction details including decoded data.
        
        Args:
            tx_hash: Transaction hash (with or without 0x prefix)
            
        Returns:
            Dictionary containing:
            - tx_hash: Transaction hash
            - block_number: Block number
            - timestamp: Block timestamp as datetime
            - from_address: Sender address
            - to_address: Recipient address
            - data: Decoded transaction data (if JSON)
            - raw_data: Raw hex data
            
            Returns None if transaction not found
        """
        try:
            # Ensure 0x prefix
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            
            loop = asyncio.get_event_loop()
            
            # Get transaction
            tx = await loop.run_in_executor(
                None, 
                self.w3.eth.get_transaction, 
                tx_hash
            )
            
            if not tx:
                return None
            
            # Get block for timestamp
            block = await loop.run_in_executor(
                None,
                self.w3.eth.get_block,
                tx["blockNumber"]
            )
            
            # Decode data from hex
            raw_data = tx.get("input", "0x")
            decoded_data = None
            
            if raw_data and raw_data != "0x":
                try:
                    # Remove 0x prefix and decode
                    data_bytes = bytes.fromhex(raw_data[2:])
                    data_str = data_bytes.decode("utf-8")
                    decoded_data = json.loads(data_str)
                except (ValueError, json.JSONDecodeError):
                    # Not JSON data, keep as string
                    try:
                        decoded_data = data_bytes.decode("utf-8")
                    except:
                        decoded_data = raw_data
            
            return {
                "tx_hash": tx_hash,
                "block_number": tx["blockNumber"],
                "timestamp": datetime.fromtimestamp(block["timestamp"]),
                "from_address": tx["from"],
                "to_address": tx.get("to"),
                "data": decoded_data,
                "raw_data": raw_data,
                "gas_used": tx.get("gas"),
                "value": tx.get("value", 0),
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction {tx_hash}: {e}")
            return None
    
    async def verify_experiment_integrity(
        self,
        experiment_data: Dict,
        tx_hash: str
    ) -> bool:
        """
        Verify experiment data hasn't been tampered with.
        
        Compares the hash of current experiment data against the hash
        stored on the blockchain at the given transaction.
        
        Args:
            experiment_data: Current experiment data to verify
            tx_hash: Transaction hash where original hash was stored
            
        Returns:
            True if data matches stored hash, False otherwise
        """
        try:
            # Calculate current hash
            current_hash = self.hash_experiment_data(experiment_data)
            
            # Get stored transaction
            tx = await self.get_transaction(tx_hash)
            
            if not tx:
                logger.warning(f"Transaction not found: {tx_hash}")
                return False
            
            # Parse stored data
            stored_data = tx.get("data")
            
            if not isinstance(stored_data, dict):
                logger.warning(f"Transaction data is not a dictionary: {type(stored_data)}")
                return False
            
            stored_hash = stored_data.get("hash")
            
            if not stored_hash:
                logger.warning("No hash found in transaction data")
                return False
            
            # Compare hashes
            is_valid = current_hash == stored_hash
            
            if is_valid:
                logger.info(f"Experiment integrity verified for tx {tx_hash}")
            else:
                logger.warning(
                    f"Experiment integrity check FAILED for tx {tx_hash}. "
                    f"Current hash: {current_hash}, Stored hash: {stored_hash}"
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify experiment integrity: {e}")
            return False


# Convenience function to get singleton instance
def get_blockchain_service() -> NeoBlockchainService:
    """Get the singleton NeoBlockchainService instance."""
    return NeoBlockchainService()
