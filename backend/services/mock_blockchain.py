"""
Mock Neo X Blockchain Service for development without testnet GAS.

This service mimics NeoBlockchainService with in-memory storage.
Use this for development and testing before connecting to real blockchain.

Enable by setting USE_MOCK_BLOCKCHAIN=true in .env
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MockNeoBlockchainService:
    """
    Mock blockchain service for development.
    
    Stores transactions in-memory and provides the same interface
    as NeoBlockchainService. All methods work immediately without
    any Web3 or network calls.
    
    Usage:
        service = MockNeoBlockchainService()
        
        # Works exactly like real service
        data_hash = service.hash_experiment_data(experiment_data)
        tx_hash = await service.store_experiment_hash("exp_001", data_hash)
        is_valid = await service.verify_experiment_integrity(experiment_data, tx_hash)
    """
    
    _instance: Optional["MockNeoBlockchainService"] = None
    
    def __new__(cls) -> "MockNeoBlockchainService":
        """Singleton pattern - only one instance needed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize mock blockchain storage."""
        # Skip if already initialized (singleton)
        if getattr(self, "_initialized", False):
            return
        
        self._initialized = True
        
        # In-memory transaction storage
        self._transactions: Dict[str, Dict[str, Any]] = {}
        
        # Mock block counter
        self._block_number = 1000000
        
        # Mock account address
        self._mock_address = "0x" + "1234567890abcdef" * 2 + "12345678"
        
        logger.info("MockNeoBlockchainService initialized (development mode)")
    
    def is_connected(self) -> bool:
        """
        Check if connected to blockchain.
        
        Returns:
            Always True for mock service
        """
        return True
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Get mock network information.
        
        Returns:
            Dictionary with mock network data
        """
        return {
            "network": "mock-testnet",
            "chain_id": 12227332,
            "rpc_url": "mock://localhost",
            "connected": True,
            "latest_block": self._block_number,
            "account_address": self._mock_address,
            "gas_balance": 1000000000000000000,  # 1 GAS in wei
            "gas_balance_ether": 1.0,
            "mock_mode": True,
            "transactions_stored": len(self._transactions),
        }
    
    def hash_experiment_data(self, experiment_data: Dict) -> str:
        """
        Create deterministic SHA-256 hash of experiment data.
        
        This uses the SAME algorithm as the real service to ensure
        hashes are compatible when switching to real blockchain.
        
        Args:
            experiment_data: Dictionary containing experiment data
            
        Returns:
            Hex string hash prefixed with "0x"
        """
        # Sort keys for deterministic hashing (same as real service)
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
        Store experiment hash in mock blockchain.
        
        Generates a mock transaction hash and stores the data in memory.
        
        Args:
            experiment_id: Unique identifier for the experiment
            data_hash: SHA-256 hash of the experiment data
            metadata: Optional additional metadata to store
            
        Returns:
            Mock transaction hash
        """
        # Generate mock transaction hash
        tx_hash = "0xmock" + uuid.uuid4().hex[:56]
        
        # Increment block number
        self._block_number += 1
        
        # Build transaction data (same structure as real service)
        tx_data = {
            "type": "lab_experiment",
            "version": "1.0",
            "id": experiment_id,
            "hash": data_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store transaction
        self._transactions[tx_hash] = {
            "tx_hash": tx_hash,
            "block_number": self._block_number,
            "timestamp": datetime.utcnow(),
            "from_address": self._mock_address,
            "to_address": self._mock_address,
            "data": tx_data,
            "raw_data": "0x" + json.dumps(tx_data).encode().hex(),
            "gas_used": 21000,
            "value": 0,
        }
        
        logger.info(
            f"[MOCK] Stored experiment {experiment_id} with tx_hash: {tx_hash}"
        )
        
        return tx_hash
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction details from mock storage.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction data if found, None otherwise
        """
        # Ensure 0x prefix
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        
        tx = self._transactions.get(tx_hash)
        
        if tx:
            logger.debug(f"[MOCK] Retrieved transaction: {tx_hash}")
            return tx.copy()  # Return copy to prevent mutation
        
        logger.warning(f"[MOCK] Transaction not found: {tx_hash}")
        return None
    
    async def verify_experiment_integrity(
        self,
        experiment_data: Dict,
        tx_hash: str
    ) -> bool:
        """
        Verify experiment data hasn't been tampered with.
        
        Uses the SAME verification logic as the real service.
        
        Args:
            experiment_data: Current experiment data to verify
            tx_hash: Transaction hash where original hash was stored
            
        Returns:
            True if data matches stored hash, False otherwise
        """
        try:
            # Calculate current hash (same algorithm as real service)
            current_hash = self.hash_experiment_data(experiment_data)
            
            # Get stored transaction
            tx = await self.get_transaction(tx_hash)
            
            if not tx:
                logger.warning(f"[MOCK] Transaction not found: {tx_hash}")
                return False
            
            # Parse stored data
            stored_data = tx.get("data")
            
            if not isinstance(stored_data, dict):
                logger.warning(
                    f"[MOCK] Transaction data is not a dictionary: {type(stored_data)}"
                )
                return False
            
            stored_hash = stored_data.get("hash")
            
            if not stored_hash:
                logger.warning("[MOCK] No hash found in transaction data")
                return False
            
            # Compare hashes
            is_valid = current_hash == stored_hash
            
            if is_valid:
                logger.info(f"[MOCK] Experiment integrity verified for tx {tx_hash}")
            else:
                logger.warning(
                    f"[MOCK] Experiment integrity check FAILED for tx {tx_hash}. "
                    f"Current hash: {current_hash}, Stored hash: {stored_hash}"
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"[MOCK] Failed to verify experiment integrity: {e}")
            return False
    
    def get_all_transactions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all stored transactions (mock-only method for debugging).
        
        Returns:
            Dictionary of all stored transactions
        """
        return {k: v.copy() for k, v in self._transactions.items()}
    
    def clear_transactions(self) -> int:
        """
        Clear all stored transactions (mock-only method for testing).
        
        Returns:
            Number of transactions cleared
        """
        count = len(self._transactions)
        self._transactions.clear()
        logger.info(f"[MOCK] Cleared {count} transactions")
        return count
