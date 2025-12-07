# BlockchainAgent Documentation

## Overview

The **BlockchainAgent** provides experiment provenance and data integrity verification on the **Neo X blockchain** (EVM-compatible testnet).

It enables researchers to:
- Create **immutable records** of experiment data hashes
- **Verify data integrity** against on-chain records
- **Detect tampering** or modifications to original data

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   /api/chat     │────▶│  Intent Router   │────▶│ BlockchainAgent │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 │                                 │
                        ▼                                 ▼                                 ▼
              ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
              │ StoreExperiment │             │ VerifyIntegrity │             │ GetBlockchain   │
              │ OnChainTool     │             │ Tool            │             │ StatusTool      │
              └────────┬────────┘             └────────┬────────┘             └────────┬────────┘
                       │                               │                               │
                       └───────────────────────────────┼───────────────────────────────┘
                                                       ▼
                                            ┌─────────────────────┐
                                            │ NeoBlockchainService│
                                            │ (or MockService)    │
                                            └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │   Neo X Testnet     │
                                            │   (Chain ID: 12227332)
                                            └─────────────────────┘
```

## Tools

### 1. StoreExperimentOnChainTool

**Purpose:** Store experiment data hash on Neo X blockchain for immutable verification.

**When to use:**
- User wants to "store", "notarize", "record", or "save" experiment data on blockchain
- Creating a permanent record of experiment results

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `experiment_id` | string | Yes | Unique identifier for the experiment |
| `experiment_data` | object | Yes | The experiment data to hash and store |
| `metadata` | object | No | Optional metadata (researcher, lab, version) |

**Returns:**
- Transaction hash
- Explorer URL (https://xt4scan.ngd.network/tx/0x...)
- Data hash (SHA-256)

### 2. VerifyExperimentIntegrityTool

**Purpose:** Verify experiment data hasn't been tampered with by comparing against blockchain record.

**When to use:**
- User wants to "verify", "check integrity", "detect tampering", or "validate" data
- Confirming data matches original record

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `experiment_data` | object | Yes | Current experiment data to verify |
| `transaction_hash` | string | Yes | Transaction hash from when data was stored |

**Returns:**
- **MATCH:** Data integrity verified, matches blockchain record
- **MISMATCH:** Tampering detected, data differs from original

### 3. GetBlockchainStatusTool

**Purpose:** Check Neo X blockchain connection status and account information.

**When to use:**
- User asks about "status", "connection", "balance", or "network info"
- Debugging blockchain connectivity

**Parameters:** None

**Returns:**
- Network name (testnet/mainnet)
- Connection status
- Latest block number
- Account address and GAS balance

## Intent Routing

The following keywords trigger routing to BlockchainAgent:

| Keyword Pattern | Example Query |
|-----------------|---------------|
| `blockchain` | "Store this on blockchain" |
| `neo x` | "Check my Neo X balance" |
| `on-chain` | "Put this on-chain" |
| `transaction hash` | "What's the transaction hash?" |
| `verify integrity` | "Verify experiment integrity" |
| `provenance` | "Check data provenance" |
| `tampering` | "Detect any tampering" |
| `notarize` | "Notarize this experiment" |
| `gas balance` | "Check my gas balance" |

## Example User Prompts

### Store Experiment
```
"Store my CRISPR experiment on the blockchain"
"Notarize experiment exp_001 on Neo X"
"Create an immutable record of my results"
```

### Verify Integrity
```
"Verify experiment integrity with tx hash 0x7264657f..."
"Check if my data has been tampered with"
"Validate experiment against blockchain record"
```

### Check Status
```
"What's my blockchain status?"
"Check Neo X connection"
"Show my gas balance"
```

## API Endpoints

### POST /api/chat
Main chat endpoint with intent routing to BlockchainAgent.

### GET /api/blockchain/status
Direct endpoint for blockchain status (no agent required).

```bash
curl http://localhost:8000/api/blockchain/status
```

Response:
```json
{
  "network": "testnet",
  "chain_id": 12227332,
  "connected": true,
  "latest_block": 6130000,
  "account_address": "0x96d04FC0...",
  "gas_balance": 2.5,
  "mock_mode": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Running Tests

```bash
# Run blockchain agent tests only
pytest backend/tests/test_blockchain_agent.py -v

# Run all backend tests
pytest backend/tests/ -v
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_BLOCKCHAIN` | `true` | Use in-memory mock (no real transactions) |
| `NEO_X_NETWORK` | `testnet` | Network selection (testnet/mainnet) |
| `NEO_X_PRIVATE_KEY` | - | Private key for signing transactions |
| `BLOCKCHAIN_AGENT_DEBUG` | `false` | Enable verbose debug logging |

### Debug Mode

Enable `BLOCKCHAIN_AGENT_DEBUG=true` in `.env` to:
- Show detailed log output for all blockchain operations
- Include raw transaction data in responses
- Log full network info on each request

## Neo X Resources

- **Testnet Explorer:** https://xt4scan.ngd.network/
- **Testnet Faucet:** https://neoxwish.ngd.network/
- **Chain ID:** 12227332 (testnet), 47763 (mainnet)
- **RPC URL:** https://neoxt4seed1.ngd.network (testnet)

## Logging

Blockchain operations are logged with structured data:

```
2024-01-15 10:30:00 | INFO | nexus.blockchain | action=store_experiment | agent=blockchain_agent | tool=store_experiment_on_chain | success=True | network=testnet | chain_id=12227332 | experiment_id=exp_001 | tx_hash=0x7264657f...
```

Log fields:
- `action`: Operation type (store_experiment, verify_integrity, status_check)
- `agent`: Always "blockchain_agent"
- `tool`: Tool name used
- `success`: True/False
- `network`: Neo X network
- `chain_id`: Chain ID
- `experiment_id`: Experiment ID (if applicable)
- `tx_hash`: Transaction hash (if applicable)
- `error`: Error message (if failed)
