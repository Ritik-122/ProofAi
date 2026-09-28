# ProofAI
## Database Design + REST API Design + Solidity Contract Interfaces

**Version:** Hackathon MVP  
**Target:** Monad Hackathon — October 13  
**Architecture:** React + FastAPI + PostgreSQL + Claude + Docker + Solidity + Monad

---

# 1. Design Principles

ProofAI uses two sources of truth.

### PostgreSQL

Source of truth for application-level data:

- Task title and description
- Repository URL
- AI execution information
- Claude responses
- Code patches
- Verification logs
- Test results
- UI progress
- Transaction references

### Monad

Source of truth for trust-sensitive state:

- Who created a task
- Amount escrowed
- Assigned agent
- Task hash
- Verification result hash
- Payment status
- Agent's verified work statistics
- Immutable work receipt

The core rule is:

> **PostgreSQL explains what happened. Monad proves that the trusted outcome happened.**

---

# PART I — DATABASE DESIGN

# 2. Entity Relationship Model

```text
┌─────────────┐
│    USER     │
└─────┬───────┘
      │ 1
      │
      │ creates
      │
      ▼ *
┌─────────────┐
│    TASK     │◄────────────────┐
└─────┬───────┘                 │
      │                         │
      │ assigned to             │
      ▼                         │
┌─────────────┐                 │
│    AGENT    │                 │
└─────────────┘                 │
                                │
TASK                            │
 │                              │
 ├────< EXECUTION               │
 │                              │
 ├────< VERIFICATION            │
 │                              │
 ├────< BLOCKCHAIN_TRANSACTION  │
 │                              │
 └───── RECEIPT ────────────────┘
```

---

# 3. Enum Definitions

## TaskStatus

```text
DRAFT
AWAITING_FUNDING
OPEN
ASSIGNED
EXECUTING
SUBMITTED
VERIFYING
VERIFIED
FAILED
PAID
CANCELLED
REFUNDED
```

Not every status needs to exist on-chain.

Temporary statuses such as:

```text
EXECUTING
VERIFYING
```

are application-level statuses.

---

## ExecutionStatus

```text
PENDING
CLONING_REPOSITORY
RUNNING_BASELINE
ANALYZING
GENERATING_PATCH
PATCH_GENERATED
COMPLETED
FAILED
```

---

## VerificationStatus

```text
PENDING
RUNNING
VERIFIED
FAILED
BUILD_FAILED
TIMEOUT
SYSTEM_ERROR
```

---

## BlockchainTransactionType

```text
CREATE_TASK
ACCEPT_TASK
SUBMIT_RESULT
VERIFY_AND_RELEASE
CANCEL_TASK
REFUND
REGISTER_AGENT
```

---

## BlockchainTransactionStatus

```text
PENDING
CONFIRMED
FAILED
```

---

# 4. Users Table

The user's wallet is their primary identity.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,

    wallet_address VARCHAR(42) NOT NULL UNIQUE,

    nonce VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Example

```text
id
550e8400-e29b...

wallet_address
0x742d35Cc...

nonce
proofai_login_74291
```

The nonce is used for wallet-signature authentication.

---

# 5. Agents Table

Stores application metadata about registered AI agents.

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,

    onchain_agent_id BIGINT UNIQUE,

    name VARCHAR(100) NOT NULL,

    slug VARCHAR(100) NOT NULL UNIQUE,

    wallet_address VARCHAR(42) NOT NULL,

    description TEXT,

    skills JSONB NOT NULL DEFAULT '[]',

    metadata_uri TEXT,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Example:

```json
{
  "name": "CodeWolf",
  "skills": [
    "python",
    "fastapi",
    "react",
    "testing"
  ]
}
```

Do **not** duplicate reputation as authoritative values here.

The authoritative verified statistics are read from `AgentRegistry`.

The backend may cache them if needed.

---

# 6. Tasks Table

This is the main application entity.

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,

    onchain_task_id BIGINT UNIQUE,

    creator_id UUID NOT NULL
        REFERENCES users(id),

    agent_id UUID
        REFERENCES agents(id),

    title VARCHAR(200) NOT NULL,

    description TEXT NOT NULL,

    repository_url TEXT NOT NULL,

    repository_branch VARCHAR(255)
        DEFAULT 'main',

    verification_command VARCHAR(255),

    reward_wei NUMERIC(78, 0) NOT NULL,

    task_hash VARCHAR(66),

    status VARCHAR(40) NOT NULL,

    create_tx_hash VARCHAR(66),

    funded_at TIMESTAMPTZ,

    assigned_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW()
);
```

---

# 7. Why Store reward_wei?

Never store blockchain currency internally as:

```text
1.5
```

floating-point.

Instead:

```text
reward_wei
```

stores the smallest denomination as an integer.

Example:

```text
1 MON

→ base units

→ integer representation
```

Frontend converts it for display.

---

# 8. Executions Table

Every AI attempt gets an execution record.

```sql
CREATE TABLE executions (
    id UUID PRIMARY KEY,

    task_id UUID NOT NULL
        REFERENCES tasks(id),

    agent_id UUID NOT NULL
        REFERENCES agents(id),

    attempt_number INTEGER NOT NULL DEFAULT 1,

    status VARCHAR(50) NOT NULL,

    baseline_tests_total INTEGER,
    baseline_tests_passed INTEGER,
    baseline_tests_failed INTEGER,

    prompt TEXT,

    model VARCHAR(100),

    ai_response JSONB,

    patch TEXT,

    patch_hash VARCHAR(66),

    error_message TEXT,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW(),

    UNIQUE(task_id, attempt_number)
);
```

---

# 9. Important Security Decision

For production we would probably avoid storing the complete model prompt indefinitely.

For the hackathon, storing it makes debugging much easier.

Never include:

```text
Claude API keys
wallet private keys
database credentials
AWS credentials
```

inside the stored prompt.

---

# 10. Verifications Table

```sql
CREATE TABLE verifications (
    id UUID PRIMARY KEY,

    task_id UUID NOT NULL
        REFERENCES tasks(id),

    execution_id UUID NOT NULL
        REFERENCES executions(id),

    status VARCHAR(50) NOT NULL,

    build_passed BOOLEAN,

    baseline_tests_total INTEGER,
    baseline_tests_passed INTEGER,
    baseline_tests_failed INTEGER,

    final_tests_total INTEGER,
    final_tests_passed INTEGER,
    final_tests_failed INTEGER,

    execution_time_ms BIGINT,

    logs TEXT,

    result_payload JSONB,

    result_hash VARCHAR(66),

    verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW()
);
```

---

# 11. Example Verification

```json
{
  "status": "VERIFIED",

  "baseline": {
    "total": 24,
    "passed": 21,
    "failed": 3
  },

  "final": {
    "total": 24,
    "passed": 24,
    "failed": 0
  },

  "buildPassed": true,

  "executionTimeMs": 12840
}
```

---

# 12. Result Payload

Before hashing, create a canonical object.

```json
{
  "version": 1,

  "taskId": "42",

  "agentId": "1",

  "patchHash":
    "0xabc...",

  "baseline": {
    "total": 24,
    "passed": 21,
    "failed": 3
  },

  "final": {
    "total": 24,
    "passed": 24,
    "failed": 0
  },

  "verified": true
}
```

Then:

```text
canonical JSON
      ↓
keccak256
      ↓
resultHash
```

Because the blockchain works naturally with `bytes32`, I recommend using:

```text
keccak256
```

rather than mixing SHA-256 and Solidity unnecessarily.

---

# 13. Blockchain Transactions Table

```sql
CREATE TABLE blockchain_transactions (
    id UUID PRIMARY KEY,

    task_id UUID
        REFERENCES tasks(id),

    agent_id UUID
        REFERENCES agents(id),

    transaction_type VARCHAR(50)
        NOT NULL,

    tx_hash VARCHAR(66)
        NOT NULL UNIQUE,

    block_number BIGINT,

    status VARCHAR(30)
        NOT NULL,

    error_message TEXT,

    created_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW(),

    confirmed_at TIMESTAMPTZ
);
```

This table is not blockchain truth.

It exists to help:

- Display transaction history
- Recover from failures
- Debug
- Link explorer transactions
- Prevent duplicate submissions

---

# 14. Work Receipts Table

```sql
CREATE TABLE work_receipts (
    id UUID PRIMARY KEY,

    task_id UUID NOT NULL UNIQUE
        REFERENCES tasks(id),

    onchain_receipt_id BIGINT UNIQUE,

    agent_id UUID NOT NULL
        REFERENCES agents(id),

    result_hash VARCHAR(66) NOT NULL,

    verification_id UUID NOT NULL
        REFERENCES verifications(id),

    verification_tx_hash VARCHAR(66),

    payment_tx_hash VARCHAR(66),

    created_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW()
);
```

---

# 15. Recommended Indexes

```sql
CREATE INDEX idx_tasks_creator
ON tasks(creator_id);

CREATE INDEX idx_tasks_agent
ON tasks(agent_id);

CREATE INDEX idx_tasks_status
ON tasks(status);

CREATE INDEX idx_tasks_onchain
ON tasks(onchain_task_id);

CREATE INDEX idx_executions_task
ON executions(task_id);

CREATE INDEX idx_verifications_task
ON verifications(task_id);

CREATE INDEX idx_transactions_task
ON blockchain_transactions(task_id);
```

---

# PART II — API DESIGN

# 16. Base API

```text
/api/v1
```

Example:

```text
https://api.proofai.dev/api/v1
```

---

# 17. API Groups

```text
/auth
/tasks
/agents
/verifications
/receipts
/blockchain
```

---

# 18. Wallet Authentication

Use wallet-signature authentication.

Flow:

```text
React
 ↓
request nonce

FastAPI
 ↓
nonce

Wallet
 ↓
sign nonce

FastAPI
 ↓
verify signature

JWT
 ↓
React
```

---

# 19. Get Authentication Nonce

```http
POST /api/v1/auth/nonce
```

### Request

```json
{
  "walletAddress":
    "0x742d35Cc..."
}
```

### Response

```json
{
  "message":
    "Sign in to ProofAI\nNonce: a7cb91..."
}
```

---

# 20. Verify Wallet Signature

```http
POST /api/v1/auth/verify
```

### Request

```json
{
  "walletAddress":
    "0x742d35Cc...",

  "signature":
    "0x94af..."
}
```

### Response

```json
{
  "accessToken":
    "eyJ...",

  "tokenType":
    "bearer"
}
```

---

# 21. Create Task Metadata

```http
POST /api/v1/tasks
Authorization: Bearer <JWT>
```

Important:

This does **not yet fund the task**.

It creates the off-chain representation.

### Request

```json
{
  "title":
    "Fix authentication tests",

  "description":
    "Fix all failing tests in the authentication module.",

  "repositoryUrl":
    "https://github.com/proofai/demo-auth",

  "repositoryBranch":
    "main",

  "rewardWei":
    "1000000000000000000"
}
```

### Response

```json
{
  "id":
    "uuid",

  "taskHash":
    "0xa912...",

  "status":
    "AWAITING_FUNDING"
}
```

---

# 22. Task Hash Construction

The backend generates a deterministic canonical payload:

```json
{
  "version": 1,

  "taskId": "uuid",

  "creator":
    "0x...",

  "repositoryUrl":
    "...",

  "repositoryBranch":
    "main",

  "title":
    "...",

  "description":
    "..."
}
```

Then:

```text
keccak256(canonical_payload)
```

produces:

```text
taskHash
```

That hash gets submitted to Monad.

---

# 23. Create On-Chain Task

This is **not** a FastAPI endpoint.

React calls the Solidity contract directly:

```text
TaskEscrow.createTask(taskHash)
```

with:

```text
msg.value = reward
```

Wallet signs the transaction.

---

# 24. Confirm Funding

After the wallet transaction succeeds:

```http
POST /api/v1/tasks/{taskId}/funding
```

### Request

```json
{
  "transactionHash":
    "0xabc..."
}
```

Backend performs:

```text
fetch transaction receipt

↓

validate contract address

↓

validate TaskCreated event

↓

validate creator

↓

validate taskHash

↓

validate reward

↓

store onChainTaskId

↓

status = OPEN
```

### Response

```json
{
  "status": "OPEN",
  "onchainTaskId": 12
}
```

The backend must **never trust only the transaction hash submitted by React**.

It validates it against Monad.

---

# 25. List Tasks

```http
GET /api/v1/tasks
```

Optional filters:

```text
?status=OPEN

?creator=0x...

?agentId=1

?page=1

?limit=20
```

---

# 26. Get Task

```http
GET /api/v1/tasks/{taskId}
```

### Example Response

```json
{
  "id": "uuid",

  "onchainTaskId": 12,

  "title":
    "Fix authentication tests",

  "description":
    "...",

  "repositoryUrl":
    "...",

  "rewardWei":
    "1000000000000000000",

  "status":
    "EXECUTING",

  "agent": {
    "id": "uuid",
    "name": "CodeWolf"
  },

  "progress": {
    "stage": "GENERATING_PATCH",
    "message":
      "CodeWolf is generating a fix."
  }
}
```

---

# 27. Start Task

For hackathon automation:

```http
POST /api/v1/tasks/{taskId}/execute
```

Protected internal/user endpoint.

The backend verifies:

```text
task funded?

agent assigned?

task not already running?
```

Then starts background execution.

### Response

```json
{
  "executionId": "uuid",

  "status":
    "PENDING"
}
```

---

# 28. Get Task Status

```http
GET /api/v1/tasks/{taskId}/status
```

This endpoint is designed specifically for frontend polling.

### Response

```json
{
  "taskStatus":
    "EXECUTING",

  "executionStatus":
    "GENERATING_PATCH",

  "message":
    "CodeWolf is generating a patch.",

  "steps": [
    {
      "name":
        "Repository cloned",

      "status":
        "COMPLETED"
    },

    {
      "name":
        "Baseline tests",

      "status":
        "COMPLETED"
    },

    {
      "name":
        "AI analysis",

      "status":
        "COMPLETED"
    },

    {
      "name":
        "Generate patch",

      "status":
        "RUNNING"
    },

    {
      "name":
        "Verification",

      "status":
        "PENDING"
    }
  ]
}
```

Frontend can poll this every:

```text
2 seconds
```

during execution.

---

# 29. Get Execution

```http
GET /api/v1/tasks/{taskId}/execution
```

### Response

```json
{
  "agent":
    "CodeWolf",

  "baseline": {
    "passed": 21,
    "failed": 3,
    "total": 24
  },

  "patchGenerated": true,

  "status":
    "COMPLETED"
}
```

Do not expose internal Claude chain-of-thought.

The UI should show task progress and useful execution summaries only.

---

# 30. Get Generated Patch

```http
GET /api/v1/tasks/{taskId}/patch
```

Response:

```json
{
  "patch":
    "... unified diff ...",

  "patchHash":
    "0x..."
}
```

This is useful for the judge demo.

---

# 31. Verification Endpoint

Normal users should **not** provide the verification result.

The backend verification engine creates it.

Internal call:

```http
POST /api/v1/tasks/{taskId}/verify
```

This triggers Docker verification.

It does not accept:

```json
{
  "passed": true
}
```

from the user.

That would destroy the trust model.

---

# 32. Verification Result

```http
GET /api/v1/tasks/{taskId}/verification
```

### Response

```json
{
  "status":
    "VERIFIED",

  "buildPassed":
    true,

  "baseline": {
    "passed": 21,
    "failed": 3,
    "total": 24
  },

  "final": {
    "passed": 24,
    "failed": 0,
    "total": 24
  },

  "improvement": {
    "testsFixed": 3
  },

  "resultHash":
    "0x934...",

  "executionTimeMs":
    12840
}
```

---

# 33. Verification Rule

For the MVP:

```text
baseline.failed > 0

AND

final.failed == 0

AND

final.total >= baseline.total

AND

buildPassed == true
```

then:

```text
VERIFIED
```

This makes the demo defensible.

---

# 34. Blockchain Settlement Endpoint

After successful Docker verification:

```http
POST /api/v1/tasks/{taskId}/settle
```

This should be:

```text
internal-only
```

or accessible only to an administrator/verifier process.

Backend:

```text
loads verification

↓

creates resultHash

↓

signs verifier transaction

↓

calls verifyAndRelease()

↓

waits for receipt

↓

updates database
```

---

# 35. Agent List

```http
GET /api/v1/agents
```

Response:

```json
[
  {
    "id": "uuid",

    "onchainAgentId": 1,

    "name": "CodeWolf",

    "skills": [
      "Python",
      "FastAPI",
      "Testing"
    ],

    "statistics": {
      "completed": 28,
      "successful": 26,
      "failed": 2,
      "totalEarnedWei": "..."
    }
  }
]
```

Statistics should preferably be read from blockchain or synchronized from it.

---

# 36. Agent Detail

```http
GET /api/v1/agents/{agentId}
```

Include:

```text
metadata

skills

verified work

success rate

total rewards

recent receipts
```

---

# 37. Work Receipt

```http
GET /api/v1/receipts/{taskId}
```

Response:

```json
{
  "receiptId": 18,

  "task": {
    "id": 12,
    "title":
      "Fix authentication tests"
  },

  "agent": {
    "id": 1,
    "name":
      "CodeWolf"
  },

  "verification": {
    "status":
      "VERIFIED",

    "testsPassed":
      24,

    "testsTotal":
      24
  },

  "rewardWei":
    "1000000000000000000",

  "resultHash":
    "0x...",

  "transactionHash":
    "0x...",

  "blockNumber":
    123456
}
```

---

# 38. Health Endpoint

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",

  "services": {
    "database": "ok",
    "claude": "ok",
    "monadRpc": "ok",
    "docker": "ok"
  }
}
```

Very useful before the hackathon demo.

---

# 39. API Error Format

All endpoints should return the same error structure.

```json
{
  "error": {
    "code":
      "TASK_NOT_FUNDED",

    "message":
      "The task must be funded before execution.",

    "requestId":
      "req_123"
  }
}
```

Examples:

```text
TASK_NOT_FOUND

TASK_ALREADY_RUNNING

TASK_NOT_FUNDED

INVALID_TRANSACTION

REPOSITORY_NOT_SUPPORTED

AI_EXECUTION_FAILED

VERIFICATION_FAILED

BLOCKCHAIN_TRANSACTION_FAILED
```

---

# PART III — SOLIDITY DESIGN

# 40. Contracts

The MVP has three contracts:

```text
AgentRegistry.sol

TaskEscrow.sol

WorkReceipt.sol
```

Their responsibilities must remain separate.

---

# 41. Contract Relationship

```text
                    ┌──────────────────┐
                    │  AgentRegistry   │
                    │                  │
                    │ Agent identity   │
                    │ Reputation       │
                    └────────▲─────────┘
                             │
                             │ update stats
                             │
USER                         │
 │                           │
 │                    ┌──────┴──────────┐
 │ create task        │                 │
 └───────────────────►│   TaskEscrow    │
                      │                 │
                      │ Tasks           │
                      │ Escrow          │
                      │ Verification    │
                      │ Payment         │
                      └────────┬────────┘
                               │
                               │ create receipt
                               ▼
                     ┌──────────────────┐
                     │   WorkReceipt    │
                     │                  │
                     │ Immutable proof  │
                     └──────────────────┘
```

`TaskEscrow` is the orchestrating contract.

---

# 42. IAgentRegistry Interface

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentRegistry {

    struct Agent {
        address owner;
        bytes32 metadataHash;

        uint64 totalTasks;
        uint64 successfulTasks;
        uint64 failedTasks;

        uint256 totalEarned;

        bool active;
    }

    event AgentRegistered(
        uint256 indexed agentId,
        address indexed owner,
        bytes32 metadataHash
    );

    event AgentMetadataUpdated(
        uint256 indexed agentId,
        bytes32 metadataHash
    );

    event AgentStatsUpdated(
        uint256 indexed agentId,
        uint64 totalTasks,
        uint64 successfulTasks,
        uint64 failedTasks,
        uint256 totalEarned
    );

    function registerAgent(
        bytes32 metadataHash
    )
        external
        returns (uint256 agentId);

    function updateMetadata(
        uint256 agentId,
        bytes32 metadataHash
    )
        external;

    function recordSuccess(
        uint256 agentId,
        uint256 reward
    )
        external;

    function recordFailure(
        uint256 agentId
    )
        external;

    function getAgent(
        uint256 agentId
    )
        external
        view
        returns (Agent memory);

    function agentExists(
        uint256 agentId
    )
        external
        view
        returns (bool);
}
```

---

# 43. Why bytes32 metadataHash?

Do not store:

```text
CodeWolf

Python

FastAPI

React

description...
```

inside Solidity.

Store that data off-chain.

Generate:

```text
keccak256(agentMetadata)
```

and save the hash on-chain.

---

# 44. AgentRegistry Access Control

Anyone may eventually register an agent.

But:

```text
recordSuccess()

recordFailure()
```

must only be callable by:

```text
TaskEscrow
```

Otherwise users could fake their own reputation.

Conceptually:

```solidity
modifier onlyTaskEscrow() {
    require(
        msg.sender == taskEscrow,
        "Unauthorized"
    );

    _;
}
```

---

# 45. IWorkReceipt Interface

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IWorkReceipt {

    struct Receipt {
        uint256 taskId;
        uint256 agentId;

        address creator;
        address agentOwner;

        bytes32 taskHash;
        bytes32 resultHash;

        uint256 reward;

        uint64 verifiedAt;
    }

    event ReceiptCreated(
        uint256 indexed receiptId,
        uint256 indexed taskId,
        uint256 indexed agentId,
        bytes32 resultHash
    );

    function createReceipt(
        uint256 taskId,
        uint256 agentId,
        address creator,
        address agentOwner,
        bytes32 taskHash,
        bytes32 resultHash,
        uint256 reward
    )
        external
        returns (uint256 receiptId);

    function getReceipt(
        uint256 receiptId
    )
        external
        view
        returns (Receipt memory);

    function getReceiptByTask(
        uint256 taskId
    )
        external
        view
        returns (Receipt memory);

    function taskHasReceipt(
        uint256 taskId
    )
        external
        view
        returns (bool);
}
```

---

# 46. WorkReceipt Access Control

Only:

```text
TaskEscrow
```

may create a receipt.

A user cannot directly call:

```text
createReceipt()
```

and pretend work passed verification.

---

# 47. ITaskEscrow Interface

This is the central contract.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ITaskEscrow {

    enum TaskStatus {
        Open,
        Assigned,
        Submitted,
        Verified,
        Failed,
        Paid,
        Cancelled,
        Refunded
    }

    struct Task {
        address creator;

        uint256 agentId;

        uint256 reward;

        bytes32 taskHash;

        bytes32 resultHash;

        TaskStatus status;

        uint64 createdAt;
        uint64 completedAt;
    }

    event TaskCreated(
        uint256 indexed taskId,
        address indexed creator,
        bytes32 indexed taskHash,
        uint256 reward
    );

    event TaskAssigned(
        uint256 indexed taskId,
        uint256 indexed agentId
    );

    event ResultSubmitted(
        uint256 indexed taskId,
        uint256 indexed agentId,
        bytes32 resultHash
    );

    event TaskVerified(
        uint256 indexed taskId,
        uint256 indexed agentId,
        bytes32 resultHash
    );

    event TaskFailed(
        uint256 indexed taskId,
        uint256 indexed agentId,
        bytes32 resultHash
    );

    event PaymentReleased(
        uint256 indexed taskId,
        uint256 indexed agentId,
        address indexed recipient,
        uint256 amount
    );

    event TaskCancelled(
        uint256 indexed taskId
    );

    event RefundIssued(
        uint256 indexed taskId,
        address indexed recipient,
        uint256 amount
    );

    function createTask(
        bytes32 taskHash
    )
        external
        payable
        returns (uint256 taskId);

    function assignTask(
        uint256 taskId,
        uint256 agentId
    )
        external;

    function submitResult(
        uint256 taskId,
        bytes32 resultHash
    )
        external;

    function verifyAndRelease(
        uint256 taskId,
        bytes32 resultHash
    )
        external;

    function rejectResult(
        uint256 taskId,
        bytes32 resultHash
    )
        external;

    function cancelTask(
        uint256 taskId
    )
        external;

    function refundTask(
        uint256 taskId
    )
        external;

    function getTask(
        uint256 taskId
    )
        external
        view
        returns (Task memory);

    function nextTaskId()
        external
        view
        returns (uint256);
}
```

---

# 48. createTask()

User calls:

```solidity
createTask(taskHash)
```

and supplies:

```solidity
msg.value
```

Requirements:

```text
taskHash != bytes32(0)

msg.value > 0
```

Produces:

```text
TaskStatus.Open
```

---

# 49. assignTask()

For the MVP, assignment should be controlled by ProofAI.

Reason:

There is only one built-in agent.

Later this can become permissionless.

Required:

```text
task.status == Open

agent exists

agent active
```

Result:

```text
Open
→
Assigned
```

---

# 50. Who Calls assignTask?

Recommended MVP:

```text
ProofAI operator/verifier wallet
```

Alternative:

Backend automatically submits assignment.

Do not require the user to sign another transaction just to assign CodeWolf.

---

# 51. submitResult()

Called when the AI execution finishes.

For the MVP, either:

```text
agent owner wallet
```

or the trusted ProofAI execution wallet can submit it.

Requirements:

```text
status == Assigned

resultHash != 0
```

Transition:

```text
Assigned
→
Submitted
```

This represents:

> The agent claims this is its result.

It does **not** mean the result has passed verification.

---

# 52. verifyAndRelease()

Most important function.

Only the authorized:

```text
verifier
```

may call it.

Pseudo-behavior:

```solidity
require(
    task.status == TaskStatus.Submitted
);

require(
    task.resultHash == resultHash
);
```

Then:

```text
status = Verified

↓

AgentRegistry.recordSuccess()

↓

WorkReceipt.createReceipt()

↓

send reward

↓

status = Paid
```

---

# 53. Why Combine Verification + Release?

Previously we had:

```text
verifyTask()

releasePayment()
```

as separate calls.

For the hackathon, I recommend:

```text
verifyAndRelease()
```

because it reduces the possibility of:

```text
VERIFIED
but payment never happened
```

and saves one transaction.

Semantically:

> A successful verification automatically settles the task.

---

# 54. Payment Algorithm

Pseudo-Solidity:

```solidity
function verifyAndRelease(
    uint256 taskId,
    bytes32 resultHash
)
    external
    onlyVerifier
    nonReentrant
{
    Task storage task = tasks[taskId];

    require(
        task.status == TaskStatus.Submitted,
        "Invalid state"
    );

    require(
        task.resultHash == resultHash,
        "Result mismatch"
    );

    IAgentRegistry.Agent memory agent =
        agentRegistry.getAgent(
            task.agentId
        );

    uint256 reward = task.reward;

    task.status =
        TaskStatus.Verified;

    task.completedAt =
        uint64(block.timestamp);

    agentRegistry.recordSuccess(
        task.agentId,
        reward
    );

    workReceipt.createReceipt(
        taskId,
        task.agentId,
        task.creator,
        agent.owner,
        task.taskHash,
        resultHash,
        reward
    );

    task.status =
        TaskStatus.Paid;

    (bool success, ) =
        payable(agent.owner).call{
            value: reward
        }("");

    require(
        success,
        "Payment failed"
    );

    emit PaymentReleased(
        taskId,
        task.agentId,
        agent.owner,
        reward
    );
}
```

Implementation should use:

```text
OpenZeppelin ReentrancyGuard
```

and follow checks-effects-interactions carefully.

---

# 55. rejectResult()

If Docker verification fails:

```text
Submitted
→
Failed
```

AgentRegistry:

```text
failedTasks += 1
totalTasks += 1
```

Payment is **not** sent to the agent.

---

# 56. What Happens to Escrow After Failure?

For the hackathon MVP:

```text
FAILED
      ↓
creator can refund
      ↓
REFUNDED
```

This is much easier to explain than automatically retrying agents.

---

# 57. cancelTask()

Creator may cancel only while:

```text
Open
```

Meaning an agent has not started working.

After cancellation:

```text
Open
→
Cancelled
```

Then refund.

---

# 58. Access Control Matrix

| Function | User | Agent | ProofAI Operator | Verifier |
|---|---:|---:|---:|---:|
| createTask | ✓ | | | |
| assignTask | | | ✓ | |
| submitResult | | ✓/execution wallet | ✓ | |
| verifyAndRelease | | | | ✓ |
| rejectResult | | | | ✓ |
| cancelTask | creator | | | |
| refundTask | creator | | | |
| registerAgent | | ✓ | ✓ | |
| recordSuccess | | | TaskEscrow only | |
| createReceipt | | | TaskEscrow only | |

For the first hackathon implementation, the operator and verifier may technically use the same backend wallet.

Architecturally, keep the roles separate so they can be split later.

---

# 59. Recommended Solidity Dependencies

Use:

```text
OpenZeppelin
```

for:

```text
Ownable / Ownable2Step

AccessControl

ReentrancyGuard
```

Do not reinvent access control.

---

# 60. Contract Role Definitions

Recommended:

```solidity
bytes32 public constant
    OPERATOR_ROLE =
        keccak256("OPERATOR_ROLE");

bytes32 public constant
    VERIFIER_ROLE =
        keccak256("VERIFIER_ROLE");
```

Then:

```text
OPERATOR_ROLE

assignTask()
```

and:

```text
VERIFIER_ROLE

verifyAndRelease()
rejectResult()
```

---

# 61. Contract Deployment Dependency Order

Deploy:

```text
1. AgentRegistry

2. WorkReceipt

3. TaskEscrow
```

Then configure:

```text
AgentRegistry.taskEscrow =
    TaskEscrow

WorkReceipt.taskEscrow =
    TaskEscrow
```

Final:

```text
          TaskEscrow
          /        \
         /          \
        ▼            ▼

AgentRegistry    WorkReceipt
```

---

# 62. Minimum Solidity Test Cases

## AgentRegistry

```text
register agent ✓

duplicate/invalid registration handling ✓

owner updates metadata ✓

random address cannot update statistics ✓
```

---

## TaskEscrow

```text
create task with MON ✓

cannot create zero-value task ✓

assign existing agent ✓

cannot assign invalid agent ✓

submit result ✓

unauthorized verification fails ✓

result-hash mismatch fails ✓

successful verification releases payment ✓

successful verification updates reputation ✓

successful verification creates receipt ✓

failed verification doesn't pay agent ✓

failed task can refund creator ✓

cannot double-pay task ✓

cannot verify twice ✓

cannot refund paid task ✓
```

---

## WorkReceipt

```text
receipt creation ✓

receipt immutable ✓

one receipt per task ✓

unauthorized receipt creation fails ✓
```

---

# PART IV — COMPLETE END-TO-END FLOW

# 63. Successful Task Sequence

```text
USER
 │
 │ POST /tasks
 ▼
FASTAPI
 │
 │ create PostgreSQL task
 │ create taskHash
 ▼
REACT
 │
 │ createTask(taskHash)
 │ + 1 MON
 ▼
MONAD
 │
 │ TaskCreated event
 ▼
REACT
 │
 │ POST /tasks/{id}/funding
 ▼
FASTAPI
 │
 │ validate transaction
 │
 │ assign CodeWolf
 ▼
MONAD
 │
 │ assignTask()
 ▼
FASTAPI
 │
 │ clone repository
 │
 │ baseline tests
 ▼
DOCKER
 │
 │ 21 / 24 tests
 ▼
CLAUDE
 │
 │ analyze failure
 │
 │ generate patch
 ▼
FASTAPI
 │
 │ patchHash
 │
 │ submitResult()
 ▼
MONAD
 │
 │ result submitted
 ▼
DOCKER
 │
 │ verification
 │
 │ 24 / 24 tests
 ▼
FASTAPI
 │
 │ canonical result
 │
 │ resultHash
 │
 │ verifyAndRelease()
 ▼
MONAD
 │
 ├── update reputation
 │
 ├── create work receipt
 │
 └── release MON
      ↓
 CODEWOLF WALLET
```

---

# 64. Failed Task Sequence

```text
Claude generates patch
        ↓
Docker verification
        ↓
22 / 24 tests
        ↓
FAILED
        ↓
rejectResult()
        ↓
Agent failure recorded
        ↓
No payment
        ↓
Creator refunds escrow
```

---

# 65. Critical Consistency Rule

Never update the database to:

```text
PAID
```

before Monad confirms the transaction.

Correct sequence:

```text
send transaction

↓

transaction hash

↓

wait for receipt

↓

confirm event

↓

update PostgreSQL
```

Blockchain is authoritative for settlement.

---

# 66. Idempotency

Endpoints such as:

```text
/tasks/{id}/funding

/tasks/{id}/execute

/tasks/{id}/settle
```

must be idempotent.

For example:

Calling:

```text
POST /settle
```

twice must **never send two payments**.

The smart contract state protects settlement, while the backend should also reject duplicate attempts.

---

# 67. Recommended Contract/Event Sync

For the hackathon:

Do not build a full indexer yet.

Use:

```text
transaction receipt validation

+

periodic status reconciliation
```

When the frontend submits a tx hash:

```text
FastAPI
 ↓
Monad RPC
 ↓
transaction receipt
 ↓
event logs
 ↓
PostgreSQL
```

Later, a dedicated indexer can replace this.

---

# 68. Monad Implementation Notes

Monad is EVM-compatible, so these contracts can use standard Solidity/Ethereum development patterns. Current Monad documentation lists both **Foundry** and **viem** among supported developer tooling, making them suitable choices for this architecture.

Recommended:

```text
Solidity
→ Foundry

Frontend blockchain interaction
→ viem

Backend blockchain interaction
→ web3.py
```

The backend does not need Node.js simply for blockchain integration.

---

# 69. Recommended Repository Layout

```text
proofai/

├── apps/
│
│   ├── web/
│   │
│   └── api/
│
├── contracts/
│
│   ├── src/
│   │   ├── AgentRegistry.sol
│   │   ├── TaskEscrow.sol
│   │   └── WorkReceipt.sol
│   │
│   ├── test/
│   │
│   └── script/
│
├── demo/
│
│   └── fastapi-auth/
│
├── docs/
│   ├── PRD.md
│   ├── SYSTEM_DESIGN.md
│   ├── DATABASE_DESIGN.md
│   └── API_DESIGN.md
│
└── README.md
```

---

# 70. MVP Data Boundary

A useful rule while coding:

### Put it on Monad if the answer to this question is YES:

> Would cheating or secretly modifying this data damage ProofAI's trust model?

Examples:

```text
reward escrow → YES

payment → YES

verification hash → YES

agent verified-job count → YES
```

### Keep it off-chain if:

> It's mainly needed by the application.

Examples:

```text
repository URL

Claude prompt

test logs

task description

UI progress

Docker output
```

---

# 71. MVP Contract Boundary

Do not add:

```text
NFTs

tokens

staking

DAO

voting

multi-agent auctions

oracle networks

cross-chain bridging

complex reputation formulas
```

before submission.

The blockchain layer exists for exactly four things:

```text
ESCROW

PROOF

REPUTATION

PAYMENT
```

---

# 72. Final Backend Module Mapping

```text
TASK ROUTER
    ↓
TaskService

AGENT ROUTER
    ↓
AgentService

EXECUTION
    ↓
AgentExecutionService
    ↓
ClaudeService

REPOSITORY
    ↓
RepositoryService

VERIFICATION
    ↓
VerificationService
    ↓
DockerSandbox

BLOCKCHAIN
    ↓
BlockchainService
    ↓
Monad RPC

RECEIPTS
    ↓
ReceiptService

DATABASE
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

---

# 73. Recommended Implementation Sequence

Do not build database, API and contracts independently and hope they integrate later.

Build one vertical slice.

### Slice 1

```text
POST /tasks
      ↓
PostgreSQL
      ↓
createTask()
      ↓
Monad
```

Get this working completely.

### Slice 2

```text
Task
 ↓
assignTask()
 ↓
CodeWolf
```

### Slice 3

```text
Task
 ↓
Claude
 ↓
Patch
```

### Slice 4

```text
Patch
 ↓
Docker
 ↓
Verification
```

### Slice 5

```text
Verification
 ↓
resultHash
 ↓
verifyAndRelease()
 ↓
Payment
```

### Slice 6

```text
Agent reputation
+
Work Receipt
+
UI polish
```

---

# 74. Final Technical Contract Between Components

The entire ProofAI system can ultimately be expressed as:

```text
OFF-CHAIN TASK
      │
      │ keccak256
      ▼
  taskHash
      │
      ▼
    MONAD
   ESCROW
      │
      ▼
   AI AGENT
      │
      ▼
     PATCH
      │
      │ keccak256
      ▼
  patchHash
      │
      ▼
    DOCKER
  VERIFICATION
      │
      ▼
canonical result
      │
      │ keccak256
      ▼
  resultHash
      │
      ▼
    MONAD
      │
  ┌───┼────────────┐
  │   │            │
  ▼   ▼            ▼

Proof Reputation Payment
```

The crucial principle remains:

> **Claude proposes the work. Docker proves whether it works. Monad proves that the verified outcome was recorded and settled.**

That is the technical foundation of ProofAI.