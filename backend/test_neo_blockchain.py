"""
Test script for Neo X Blockchain Service.

Works with both mock and real blockchain based on USE_MOCK_BLOCKCHAIN env var.

Run with:
    python -m backend.test_neo_blockchain
"""

import asyncio
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv(override=True)

from backend.services import get_blockchain_service, USE_MOCK_BLOCKCHAIN


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result with indicator."""
    indicator = "✅" if passed else "❌"
    print(f"{indicator} {test_name}")
    if details:
        print(f"   {details}")


async def test_blockchain_service():
    """Run all blockchain service tests."""
    
    results = []
    
    # ==========================================================================
    # 1. Initialize Service
    # ==========================================================================
    print_header("1. BLOCKCHAIN SERVICE INITIALIZATION")
    
    service = get_blockchain_service()
    service_type = type(service).__name__
    
    print(f"Mode: {'MOCK (development)' if USE_MOCK_BLOCKCHAIN else 'REAL (Neo X)'}")
    print(f"Service: {service_type}")
    
    results.append(("Service initialized", True))
    
    # ==========================================================================
    # 2. Network Info
    # ==========================================================================
    print_header("2. NETWORK INFORMATION")
    
    try:
        info = service.get_network_info()
        
        print(f"Network:         {info.get('network', 'N/A')}")
        print(f"Chain ID:        {info.get('chain_id', 'N/A')}")
        print(f"RPC URL:         {info.get('rpc_url', 'N/A')}")
        print(f"Connected:       {info.get('connected', False)}")
        print(f"Latest Block:    {info.get('latest_block', 'N/A')}")
        print(f"Account:         {info.get('account_address', 'Not configured')}")
        
        if info.get('gas_balance_ether') is not None:
            print(f"GAS Balance:     {info.get('gas_balance_ether')} GAS")
        
        if info.get('mock_mode'):
            print(f"Transactions:    {info.get('transactions_stored', 0)} stored")
        
        connected = info.get('connected', False)
        results.append(("Network connection", connected))
        print_result("Network info retrieved", True)
        
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Network connection", False))
    
    # ==========================================================================
    # 3. Test Hashing (Deterministic)
    # ==========================================================================
    print_header("3. EXPERIMENT DATA HASHING")
    
    try:
        # Test data
        experiment_data = {
            "id": "exp_001",
            "title": "CRISPR Gene Editing Test",
            "researcher": "Dr. Smith",
            "date": "2024-01-15",
            "results": {
                "success_rate": 0.85,
                "samples_tested": 100,
                "conclusion": "Positive results observed"
            }
        }
        
        # Hash twice to verify deterministic
        hash1 = service.hash_experiment_data(experiment_data)
        hash2 = service.hash_experiment_data(experiment_data)
        
        print(f"Experiment ID:   {experiment_data['id']}")
        print(f"Title:           {experiment_data['title']}")
        print(f"Hash (1st):      {hash1[:20]}...{hash1[-8:]}")
        print(f"Hash (2nd):      {hash2[:20]}...{hash2[-8:]}")
        
        is_deterministic = hash1 == hash2
        print_result("Hash is deterministic", is_deterministic)
        results.append(("Deterministic hashing", is_deterministic))
        
        # Test that different data produces different hash
        modified_data = experiment_data.copy()
        modified_data["results"] = {"success_rate": 0.50}
        hash3 = service.hash_experiment_data(modified_data)
        
        is_different = hash1 != hash3
        print_result("Different data produces different hash", is_different)
        results.append(("Hash uniqueness", is_different))
        
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Deterministic hashing", False))
        results.append(("Hash uniqueness", False))
    
    # ==========================================================================
    # 4. Store Experiment Hash
    # ==========================================================================
    print_header("4. STORE EXPERIMENT HASH ON BLOCKCHAIN")
    
    tx_hash = None
    try:
        # Store the experiment hash
        tx_hash = await service.store_experiment_hash(
            experiment_id="exp_001",
            data_hash=hash1,
            metadata={
                "researcher": "Dr. Smith",
                "lab": "Genetics Lab",
                "version": 1
            }
        )
        
        if tx_hash:
            print(f"Transaction Hash: {tx_hash[:20]}...{tx_hash[-8:]}")
            print_result("Experiment hash stored", True)
            results.append(("Store experiment hash", True))
        else:
            print("No transaction hash returned (read-only mode?)")
            print_result("Experiment hash stored", False, "No private key configured")
            results.append(("Store experiment hash", False))
            
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Store experiment hash", False))
    
    # ==========================================================================
    # 5. Retrieve Transaction
    # ==========================================================================
    print_header("5. RETRIEVE TRANSACTION")
    
    if tx_hash:
        try:
            tx = await service.get_transaction(tx_hash)
            
            if tx:
                print(f"TX Hash:         {tx.get('tx_hash', 'N/A')[:20]}...")
                print(f"Block Number:    {tx.get('block_number', 'N/A')}")
                print(f"Timestamp:       {tx.get('timestamp', 'N/A')}")
                print(f"From:            {tx.get('from_address', 'N/A')[:20]}...")
                
                # Show stored data
                data = tx.get('data', {})
                if isinstance(data, dict):
                    print(f"Stored Type:     {data.get('type', 'N/A')}")
                    print(f"Stored ID:       {data.get('id', 'N/A')}")
                    print(f"Stored Hash:     {data.get('hash', 'N/A')[:20]}...")
                
                print_result("Transaction retrieved", True)
                results.append(("Retrieve transaction", True))
            else:
                print("Transaction not found")
                print_result("Transaction retrieved", False)
                results.append(("Retrieve transaction", False))
                
        except Exception as e:
            print(f"Error: {e}")
            results.append(("Retrieve transaction", False))
    else:
        print("Skipped (no transaction hash from previous step)")
        results.append(("Retrieve transaction", False))
    
    # ==========================================================================
    # 6. Verify Integrity (Valid Data)
    # ==========================================================================
    print_header("6. VERIFY EXPERIMENT INTEGRITY")
    
    if tx_hash:
        try:
            # Test with original data (should pass)
            print("Testing with ORIGINAL data...")
            is_valid = await service.verify_experiment_integrity(
                experiment_data, 
                tx_hash
            )
            print_result("Original data verification", is_valid, 
                        "Data matches blockchain record" if is_valid else "MISMATCH!")
            results.append(("Verify original data", is_valid))
            
            # Test with tampered data (should fail)
            print("\nTesting with TAMPERED data...")
            tampered_data = experiment_data.copy()
            tampered_data["results"]["success_rate"] = 0.99  # Changed!
            
            is_tampered_valid = await service.verify_experiment_integrity(
                tampered_data,
                tx_hash
            )
            
            # For tampered data, we expect False (so test passes if False)
            tamper_detected = not is_tampered_valid
            print_result("Tamper detection", tamper_detected,
                        "Tampering correctly detected!" if tamper_detected else "FAILED to detect tampering!")
            results.append(("Detect tampering", tamper_detected))
            
        except Exception as e:
            print(f"Error: {e}")
            results.append(("Verify original data", False))
            results.append(("Detect tampering", False))
    else:
        print("Skipped (no transaction hash)")
        results.append(("Verify original data", False))
        results.append(("Detect tampering", False))
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"Service Type: {service_type}")
    print(f"Mode: {'MOCK' if USE_MOCK_BLOCKCHAIN else 'REAL'}")
    print()
    
    for test_name, test_passed in results:
        indicator = "✅" if test_passed else "❌"
        print(f"  {indicator} {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Blockchain service is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check configuration.")
    
    return passed == total


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  NEO X BLOCKCHAIN SERVICE TEST")
    print("="*60)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    
    success = asyncio.run(test_blockchain_service())
    
    sys.exit(0 if success else 1)
