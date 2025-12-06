# Services module

import os
from typing import Union

from backend.services.neo_blockchain import NeoBlockchainService
from backend.services.mock_blockchain import MockNeoBlockchainService

# Toggle between real and mock blockchain
# Set USE_MOCK_BLOCKCHAIN=true in .env for development without testnet GAS
USE_MOCK_BLOCKCHAIN = os.getenv("USE_MOCK_BLOCKCHAIN", "true").lower() == "true"

# Singleton instances
_blockchain_service: Union[NeoBlockchainService, MockNeoBlockchainService, None] = None


def get_blockchain_service() -> Union[NeoBlockchainService, MockNeoBlockchainService]:
    """
    Get the blockchain service instance.
    
    Returns MockNeoBlockchainService if USE_MOCK_BLOCKCHAIN=true,
    otherwise returns NeoBlockchainService for real blockchain.
    
    Returns:
        Blockchain service instance (singleton)
    """
    global _blockchain_service
    
    if _blockchain_service is None:
        if USE_MOCK_BLOCKCHAIN:
            _blockchain_service = MockNeoBlockchainService()
        else:
            _blockchain_service = NeoBlockchainService()
    
    return _blockchain_service


__all__ = [
    "NeoBlockchainService",
    "MockNeoBlockchainService", 
    "get_blockchain_service",
    "USE_MOCK_BLOCKCHAIN",
]
