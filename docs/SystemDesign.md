# ProofAI — System Design & Architecture

## 1. Architecture Goal

ProofAI must support one reliable end-to-end workflow:

```text
User creates task
      ↓
Reward locked on Monad
      ↓
AI agent receives task
      ↓
Claude generates code fix
      ↓
Fix runs inside isolated Docker environment
      ↓
Automated tests verify result
      ↓
Proof hash recorded on Monad
      ↓
Reward released
      ↓
Agent reputation updated
```

The architecture should prioritize:

- Demo reliability
- Clear separation between AI execution and verification
- Minimal blockchain complexity
- Fast development
- Security around running AI-generated code
- Easy debugging
- Easy deployment

---

# 2. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        USER / BROWSER                        │
│                                                              │
│   React + TypeScript + Tailwind                              │
│                                                              │
│   Dashboard                                                  │
│   Create Task                                                │
│   Task Progress                                              │
│   Agent Profile                                              │
│   Work Receipt                                               │
└───────────────────────┬──────────────────────────────────────┘
                        │
               ┌────────┴─────────┐
               │                  │
               ▼                  ▼

        FastAPI Backend        Wallet
                              MetaMask /
                             WalletConnect

               │                  │
               │                  ▼
               │            ┌─────────────┐
               │            │    Monad    │
               │            │             │
               │            │ Smart       │
               │            │ Contracts   │
               │            └──────┬──────┘
               │                   │
               │ blockchain events│
               ▼                   │
┌──────────────────────────────┐   │
│       FastAPI Backend        │◄──┘
│                              │
│ Task Service                 │
│ Agent Service                │
│ AI Orchestrator              │
│ Verification Service         │
│ Blockchain Service           │
│ Reputation Service           │
│ Receipt Service              │
└─────────────┬────────────────┘
              │
     ┌────────┼─────────────┐
     │        │             │
     ▼        ▼             ▼

 PostgreSQL  Claude API   Docker Sandbox
                              │
                              ▼
                       Build / Unit Tests
                              │
                              ▼
                        Verification
                           Result
```

---

# 3. Core Architecture Principle

ProofAI should be divided into three major layers.

## Layer 1 — Application Layer

React + FastAPI.

Responsible for:

- User interface
- Task orchestration
- AI integration
- Logs
- Application state
- Database
- Verification orchestration

---

## Layer 2 — Verification Layer

Docker sandbox.

Responsible for answering:

> Did the AI actually complete the task?

The AI cannot decide whether its own answer is correct.

Therefore:

```text
Claude
=
Worker

Docker + Automated Tests
=
Verifier
```

This separation is fundamental to ProofAI.

---

## Layer 3 — Trust & Settlement Layer

Monad smart contracts.

Responsible for:

- Task ownership
- Escrowed funds
- Agent identity
- Verification proof
- Payment
- Reputation history

Monad should not execute AI.

Monad should not store source code.

Monad should not run tests.

Blockchain is used only where decentralized trust provides value.

---

# 4. What Goes On-Chain vs Off-Chain

This is one of the most important architectural decisions.

## On-Chain

Store only information that benefits from being publicly verifiable.

### Task

```text
taskId

creator

agent

reward

status

taskHash
```

### Verification

```text
resultHash

verified

timestamp
```

### Agent Reputation

```text
agentId

completedTasks

successfulTasks

failedTasks

totalEarned
```

### Payment

Handled completely through smart contract.

---

## Off-Chain

PostgreSQL stores larger application data.

```text
Task title

Task description

GitHub repository URL

AI prompts

AI responses

Execution logs

Build logs

Test results

Code patch

Error messages

Agent metadata

UI state
```

---

# 5. Why Not Store Everything On-Chain?

Suppose Claude generates:

```text
500 lines of code
```

and Docker produces:

```text
5,000 lines of test/build logs
```

Putting this data directly on-chain would be unnecessary.

Instead:

```text
Full Result
     ↓
SHA-256
     ↓
0xa837bc92...
```

Only this fingerprint is written to Monad.

Later the full result can be hashed again.

If:

```text
stored hash
=
newly generated hash
```

the result has not changed.

---

# 6. Frontend Architecture

Recommended:

```text
React
TypeScript
Tailwind CSS
React Router
TanStack Query
Viem
WalletConnect-compatible wallet library
```

Suggested folder structure:

```text
frontend/

src/

├── components/
│   ├── common/
│   ├── task/
│   ├── agent/
│   ├── verification/
│   └── blockchain/
│
├── pages/
│   ├── LandingPage.tsx
│   ├── DashboardPage.tsx
│   ├── CreateTaskPage.tsx
│   ├── TaskDetailsPage.tsx
│   ├── AgentProfilePage.tsx
│   └── ReceiptPage.tsx
│
├── services/
│   ├── api.ts
│   └── blockchain.ts
│
├── hooks/
│   ├── useTask.ts
│   ├── useWallet.ts
│   └── useTransaction.ts
│
├── contracts/
│   ├── AgentRegistryABI.ts
│   ├── TaskEscrowABI.ts
│   └── WorkReceiptABI.ts
│
├── types/
│
├── utils/
│
└── App.tsx
```

---

# 7. Frontend ↔ Blockchain Communication

Some blockchain actions should happen directly from the browser.

Example:

```text
User
 ↓
React
 ↓
Wallet
 ↓
Monad
```

Examples:

```text
connectWallet()

createTask()

depositReward()

cancelTask()
```

The user's wallet signs these transactions.

The backend should never hold the user's private key.

---

# 8. Frontend ↔ Backend Communication

Application operations go through FastAPI.

```text
React
 ↓
FastAPI
```

Examples:

```http
GET /tasks

GET /tasks/{id}

POST /tasks/{id}/execute

GET /tasks/{id}/status

GET /tasks/{id}/verification

GET /agents/{id}

GET /receipts/{id}
```

---

# 9. Backend Architecture

Use a **modular monolith**.

Do not create multiple microservices.

One FastAPI application is sufficient.

```text
FastAPI
│
├── Task Module
├── Agent Module
├── AI Module
├── Verification Module
├── Blockchain Module
├── Reputation Module
└── Receipt Module
```

This keeps development simple while maintaining clean separation.

---

# 10. Suggested Backend Structure

```text
backend/

app/

├── main.py
│
├── api/
│   ├── tasks.py
│   ├── agents.py
│   ├── verification.py
│   └── receipts.py
│
├── services/
│   ├── task_service.py
│   ├── ai_service.py
│   ├── github_service.py
│   ├── verification_service.py
│   ├── blockchain_service.py
│   ├── reputation_service.py
│   └── receipt_service.py
│
├── models/
│   ├── task.py
│   ├── agent.py
│   ├── execution.py
│   ├── verification.py
│   └── transaction.py
│
├── schemas/
│
├── repositories/
│
├── blockchain/
│   ├── contracts/
│   └── client.py
│
├── docker/
│   └── sandbox.py
│
├── core/
│   ├── config.py
│   └── security.py
│
└── db/
    └── database.py
```

---

# 11. Task Lifecycle

Each task moves through a state machine.

```text
CREATED
   ↓
FUNDED
   ↓
ASSIGNED
   ↓
EXECUTING
   ↓
SUBMITTED
   ↓
VERIFYING
   ↓
   ├───────────────┐
   │               │
   ▼               ▼

VERIFIED          FAILED
   │
   ▼
PAID
```

Blockchain does not necessarily need every temporary UI state.

For example:

```text
EXECUTING
VERIFYING
```

can remain off-chain.

Blockchain states can stay simpler:

```text
OPEN
ASSIGNED
SUBMITTED
VERIFIED
FAILED
PAID
CANCELLED
```

---

# 12. Task Creation Flow

User enters:

```text
Title

Description

Repository URL

Reward
```

React first sends metadata to FastAPI.

```text
React
   ↓
POST /tasks
   ↓
FastAPI
   ↓
PostgreSQL
```

Backend calculates:

```text
taskHash
```

Example:

```text
SHA256(
    title +
    description +
    repositoryURL
)
```

Backend returns:

```json
{
  "taskId": 42,
  "taskHash": "0x..."
}
```

Frontend then calls the smart contract.

```text
createTask(
    taskHash
)
```

and sends MON as transaction value.

---

# 13. Why Create Database Entry Before Blockchain Transaction?

Because large task metadata remains off-chain.

Flow:

```text
PostgreSQL Task
       │
       │ taskHash
       ▼
Monad Task
```

Both are connected through:

```text
taskId
taskHash
transactionHash
```

---

# 14. Smart Contract Architecture

Recommended contracts:

```text
AgentRegistry.sol

TaskEscrow.sol

WorkReceipt.sol
```

Keep them small.

Avoid complex contract inheritance during the hackathon.

---

# 15. AgentRegistry Contract

Purpose:

Maintain AI-agent identity and statistics.

Example:

```solidity
struct Agent {
    address owner;
    string metadataURI;

    uint256 totalTasks;
    uint256 successfulTasks;
    uint256 failedTasks;

    uint256 totalEarned;

    bool active;
}
```

Mapping:

```solidity
mapping(uint256 => Agent) public agents;
```

Possible functions:

```text
registerAgent()

getAgent()

updateMetadata()

recordSuccess()

recordFailure()
```

---

# 16. Agent Identity

For the MVP, only one AI agent is necessary.

Example:

```text
Agent ID:
1

Agent Name:
CodeWolf

Owner:
ProofAI

Skills:
Python
FastAPI
React
Testing
```

Agent metadata can live in PostgreSQL.

Blockchain only needs:

```text
Agent ID

Owner

Metadata URI/hash

Statistics
```

---

# 17. TaskEscrow Contract

TaskEscrow is the most important smart contract.

Example:

```solidity
enum TaskStatus {
    Open,
    Assigned,
    Submitted,
    Verified,
    Failed,
    Paid,
    Cancelled
}
```

Task:

```solidity
struct Task {
    uint256 id;

    address creator;

    uint256 agentId;

    uint256 reward;

    bytes32 taskHash;

    bytes32 resultHash;

    TaskStatus status;
}
```

---

# 18. TaskEscrow Functions

Required functions:

```text
createTask()

acceptTask()

submitResult()

verifyTask()

releasePayment()

cancelTask()
```

Possible combined functions can reduce complexity.

For example:

```text
verifyAndRelease()
```

could:

```text
mark verified

record resultHash

release funds

update agent stats
```

This may be simpler for the hackathon.

---

# 19. Creating Task

Pseudo-flow:

```solidity
function createTask(
    bytes32 taskHash
) external payable
```

Requirements:

```text
msg.value > 0
```

Contract stores:

```text
creator = msg.sender

reward = msg.value

taskHash = supplied hash

status = OPEN
```

---

# 20. Reward Escrow

Suppose:

```text
Reward = 2 MON
```

When task is created:

```text
User wallet
      ↓
    2 MON
      ↓
TaskEscrow Contract
```

The contract controls the funds.

Not:

```text
React

FastAPI

PostgreSQL
```

This ensures ProofAI itself cannot simply take the user's reward.

---

# 21. AI Agent Assignment

For MVP:

```text
Backend automatically assigns CodeWolf.
```

You do not need competing agents.

Backend detects:

```text
TaskCreated event
```

and associates the configured agent.

Then:

```text
acceptTask(taskId)
```

is called.

---

# 22. Blockchain Event Architecture

Smart contracts should emit events.

Example:

```solidity
event TaskCreated(
    uint256 indexed taskId,
    address indexed creator,
    uint256 reward
);
```

Others:

```text
TaskAssigned

ResultSubmitted

TaskVerified

TaskFailed

PaymentReleased
```

FastAPI listens for these events.

Conceptually:

```text
Monad Contract
      ↓
Blockchain Event
      ↓
FastAPI Listener
      ↓
PostgreSQL Update
      ↓
Frontend
```

---

# 23. Hackathon Simplification for Events

A production system would run a persistent blockchain indexer.

For the hackathon, you can simplify.

After a frontend transaction completes:

```text
React
 ↓
gets transaction receipt
 ↓
FastAPI
 ↓
sync task status
```

Additionally, FastAPI can periodically check important transactions.

This is easier than building a full indexer.

---

# 24. AI Execution Architecture

Once task is funded and assigned:

```text
Task
 ↓
Execution Service
 ↓
Repository Preparation
 ↓
Claude
 ↓
Patch
```

Detailed flow:

```text
Fetch repository
      ↓
Create isolated working copy
      ↓
Inspect project structure
      ↓
Run initial tests
      ↓
Capture failures
      ↓
Prepare Claude context
      ↓
Call Claude
      ↓
Receive patch
      ↓
Apply patch
```

---

# 25. Repository Strategy

This is an important MVP decision.

### Recommended for Hackathon

Support a small number of prepared public demo repositories.

Example:

```text
proofai-demo-fastapi-auth
```

with intentionally broken tests.

Why?

Arbitrary GitHub repositories introduce problems:

```text
different build systems

different dependencies

huge repositories

malicious scripts

missing tests

private repositories

very long AI context
```

These problems are unnecessary for your demo.

---

# 26. Hackathon Repository Flow

Allow UI field:

```text
Repository URL
```

But initially whitelist:

```text
github.com/proofai/demo-fastapi-auth

github.com/proofai/demo-react-api
```

After the hackathon you can expand support.

---

# 27. Pre-Execution Verification

Before Claude modifies anything:

```text
clone repo

install dependencies

run tests
```

Store:

```text
tests_total

tests_passed_before

tests_failed_before
```

Example:

```text
Before AI

Total:
24

Passed:
21

Failed:
3
```

This is valuable for the demo.

---

# 28. Claude Context

Claude should receive only relevant context.

Example:

```text
SYSTEM

You are CodeWolf, an autonomous software engineering agent.

TASK

Fix failing authentication tests.

TEST FAILURES

test_login_wrong_password
test_expired_token

PROJECT STRUCTURE

/app
/tests

RELEVANT FILES

auth.py
security.py
test_auth.py
```

Avoid sending the entire repository unnecessarily.

---

# 29. Claude Output Format

For initial implementation, Claude can return:

```json
{
  "analysis": "...",
  "files": [
    {
      "path": "app/auth.py",
      "content": "..."
    }
  ]
}
```

Or preferably:

```text
unified diff / patch
```

Example:

```diff
- old code
+ corrected code
```

A patch makes changes easier to review and hash.

---

# 30. Verification Architecture

This is the heart of ProofAI.

```text
AI Patch
   ↓
Docker Sandbox
   ↓
Install
   ↓
Build
   ↓
Tests
   ↓
Result
```

Backend launches isolated container.

---

# 31. Docker Sandbox

Example workflow:

```text
Create temporary directory

Clone repository

Apply AI patch

Build Docker image

Start container

Execute test command

Capture output

Destroy container
```

Potential commands:

Python:

```bash
pytest
```

Node:

```bash
npm test
```

---

# 32. Verification Output

Return normalized data.

Example:

```json
{
  "status": "VERIFIED",
  "buildPassed": true,
  "testsPassed": 24,
  "testsFailed": 0,
  "testsTotal": 24,
  "executionTime": 12.4
}
```

Failure:

```json
{
  "status": "FAILED",
  "buildPassed": true,
  "testsPassed": 22,
  "testsFailed": 2,
  "testsTotal": 24
}
```

---

# 33. Critical Verification Rule

A task succeeds only if:

```text
failed_before > 0

AND

failed_after == 0
```

This prevents a meaningless demo where tests already passed before the AI touched the code.

Example:

```text
Before Claude

21 / 24 ✓


After Claude

24 / 24 ✓


Improvement

+3 tests fixed
```

This should be visually displayed.

---

# 34. Result Hash Generation

Create a canonical result object.

Example:

```json
{
  "taskId": 42,
  "agentId": 1,
  "patchHash": "...",
  "testsPassed": 24,
  "testsTotal": 24,
  "verified": true
}
```

Serialize consistently.

Then:

```text
SHA256(result)
```

produces:

```text
resultHash
```

Store:

```text
full result → PostgreSQL

resultHash → Monad
```

---

# 35. Verification Submission

After successful tests:

```text
FastAPI
 ↓
verification result
 ↓
Blockchain Service
 ↓
TaskEscrow.verifyAndRelease()
 ↓
Monad
```

---

# 36. Critical Blockchain Security Question

Who is allowed to tell the smart contract that verification passed?

For the hackathon:

Use a designated **ProofAI verifier wallet**.

Contract contains:

```solidity
address public verifier;
```

Only:

```text
verifier
```

can call:

```text
verifyTask()
```

This means:

```text
random user
```

cannot mark their own task as verified.

---

# 37. Isn't That Centralized?

Yes.

And that's acceptable for the hackathon.

Do not pretend otherwise.

The architecture provides:

```text
decentralized escrow

public proof

public settlement

portable history
```

while the verification service is initially operated by ProofAI.

Future versions could use:

```text
multiple independent verifiers

TEE verification

zk proof systems

decentralized verifier networks

optimistic verification
```

But these should remain future roadmap items.

---

# 38. Backend Blockchain Wallet

FastAPI needs a wallet capable of submitting verification transactions.

Store its private key securely in server environment variables.

Example:

```text
VERIFIER_PRIVATE_KEY
```

Never expose it to:

```text
React

GitHub repository

Docker verification container

logs
```

---

# 39. Payment Flow

Successful task:

```text
TaskEscrow

reward = 2 MON

        ↓

verifyTask()

        ↓

status = VERIFIED

        ↓

releasePayment()

        ↓

Agent Wallet receives 2 MON
```

---

# 40. Hackathon Payment Simplification

Because CodeWolf is your own built-in agent, you can configure:

```text
Agent Wallet
=
separate demo wallet
```

During the demo:

```text
Escrow balance
2 MON

↓

Agent wallet
+2 MON
```

This gives judges visible proof that settlement actually occurred.

---

# 41. Reputation Architecture

Once verification succeeds:

```text
AgentRegistry

successfulTasks += 1

totalTasks += 1

totalEarned += reward
```

If task fails:

```text
failedTasks += 1

totalTasks += 1
```

Frontend calculates:

```text
successRate =
successfulTasks / totalTasks
```

---

# 42. Work Receipt Architecture

After verification, backend creates receipt metadata.

Example:

```json
{
  "taskId": 42,
  "task": "Fix authentication tests",
  "agent": "CodeWolf",
  "verified": true,
  "testsPassed": 24,
  "testsTotal": 24,
  "reward": "2 MON",
  "resultHash": "0x...",
  "transactionHash": "0x..."
}
```

Frontend displays this as a polished ProofAI receipt.

---

# 43. Database Architecture

Use PostgreSQL.

Core relationships:

```text
USER
 │
 └──< TASK
        │
        ├── EXECUTION
        │
        ├── VERIFICATION
        │
        ├── TRANSACTION
        │
        └── RECEIPT

AGENT
 │
 └──< TASK
```

---

# 44. Users Table

```sql
users

id
wallet_address
created_at
updated_at
```

Unique:

```text
wallet_address
```

---

# 45. Agents Table

```sql
agents

id

onchain_agent_id

name

wallet_address

description

skills

metadata_uri

created_at
```

---

# 46. Tasks Table

```sql
tasks

id

onchain_task_id

creator_wallet

agent_id

title

description

repository_url

reward

task_hash

status

create_tx_hash

created_at

updated_at
```

---

# 47. Executions Table

```sql
executions

id

task_id

agent_id

status

prompt

ai_response

patch

started_at

completed_at

error
```

---

# 48. Verifications Table

```sql
verifications

id

task_id

status

build_passed

tests_before_passed

tests_before_failed

tests_after_passed

tests_after_failed

logs

patch_hash

result_hash

execution_time

verified_at
```

---

# 49. Blockchain Transactions Table

```sql
blockchain_transactions

id

task_id

tx_type

tx_hash

block_number

status

created_at
```

Possible:

```text
CREATE_TASK

ACCEPT_TASK

SUBMIT_RESULT

VERIFY

PAYMENT
```

---

# 50. Authentication

For the MVP, wallet ownership acts as identity.

Possible flow:

```text
Connect wallet

↓

Frontend gets address

↓

User signs login message

↓

FastAPI verifies signature

↓

Backend issues JWT
```

JWT can then authenticate normal API calls.

---

# 51. Hackathon Authentication Simplification

If time becomes limited:

You can initially identify users from connected wallet address while protecting sensitive operations through smart-contract signatures.

However, proper wallet-message authentication is preferable if time allows.

---

# 52. Real-Time Task Progress

During execution, frontend should show:

```text
Analyzing repository

↓

Running baseline tests

↓

Agent reasoning

↓

Generating patch

↓

Applying patch

↓

Running verification

↓

Writing proof

↓

Releasing payment
```

Recommended MVP solution:

```text
poll API every 2 seconds
```

Example:

```http
GET /tasks/42/status
```

Do not build WebSockets unless everything else is complete.

Polling is sufficient for the hackathon.

---

# 53. Background Processing

AI generation and Docker verification may take 10–60 seconds.

Do not block normal API processing.

Recommended:

```text
FastAPI endpoint
      ↓
start background task
      ↓
return immediately
```

Hackathon options:

```text
FastAPI BackgroundTasks
```

or a lightweight worker.

---

# 54. Do We Need Redis?

Not initially.

Redis would be useful for:

```text
job queue

distributed workers

progress state

caching
```

But:

```text
FastAPI
+
PostgreSQL
```

is sufficient for MVP.

Add Redis only after the core flow works.

---

# 55. Deployment Architecture

Recommended simple deployment:

```text
                     Internet
                        │
          ┌─────────────┴─────────────┐
          │                           │

       Vercel                     Backend VM
       React                       FastAPI
                                   Docker
                                      │
                           ┌──────────┼──────────┐
                           │          │          │

                       PostgreSQL   Claude     Monad
```

---

# 56. Why Backend Should Run on a VM

Because ProofAI needs to execute Docker containers.

Serverless platforms can make this difficult.

For the hackathon, deploy backend to something that supports Docker execution.

Possible architecture:

```text
Ubuntu VM

Docker

FastAPI Container

Verification Containers
```

---

# 57. AWS Architecture — Optional

Since you already know AWS, an alternative:

```text
Route53
   ↓
Frontend — Vercel

Backend
   ↓
EC2

Database
   ↓
RDS PostgreSQL

Logs
   ↓
CloudWatch
```

Do not introduce:

```text
ECS

EKS

Kafka

multiple Lambdas
```

unless absolutely necessary.

---

# 58. CI/CD

GitHub repository structure:

```text
proofai/

frontend/

backend/

contracts/

demo-repositories/

docs/
```

GitHub Actions:

```text
Pull Request

↓

Frontend lint

Backend tests

Smart contract tests

↓

Merge
```

Deployment can initially remain simple.

---

# 59. Smart Contract Testing

Use Solidity development tooling such as:

```text
Foundry
```

or:

```text
Hardhat
```

Choose whichever you learn faster.

Tests must cover at least:

```text
create task

deposit escrow

assign agent

successful verification

payment release

failed verification

unauthorized verification

refund
```

---

# 60. Security Architecture

Major security risk:

ProofAI executes code.

Therefore:

```text
Docker container

no host filesystem access

no Docker socket access

CPU limit

memory limit

execution timeout

network disabled if possible

temporary filesystem

container deleted after execution
```

---

# 61. Never Put Secrets Inside Sandbox

AI-generated code must never receive:

```text
Claude API key

Verifier wallet key

Database password

AWS credentials

GitHub secrets
```

Sandbox environment should contain only what is necessary to run the repository.

---

# 62. Verification Timeout

Example:

```text
Maximum execution:

60 seconds
```

If timeout occurs:

```text
verificationStatus =
FAILED
```

or:

```text
TIMEOUT
```

---

# 63. Failure Scenarios

## Claude cannot solve task

```text
Verification fails

↓

Task status = FAILED
```

---

## Docker build fails

```text
BUILD_FAILED
```

---

## Tests fail

```text
VERIFICATION_FAILED
```

---

## Blockchain transaction fails

Keep:

```text
verification result in PostgreSQL
```

and allow retrying the blockchain transaction.

---

## Claude API fails

Retry once.

If still failing:

```text
AI_EXECUTION_FAILED
```

---

# 64. Observability

Keep logs for:

```text
task creation

AI execution

Docker execution

verification

blockchain transaction

payment
```

Example:

```text
[TASK 42]

Repository cloned

Baseline tests:
21/24

Claude execution:
SUCCESS

Patch applied

Verification:
24/24

Blockchain proof:
0x82...

Payment:
SUCCESS
```

These logs will help enormously during hackathon debugging.

---

# 65. Demo Architecture

For the actual judging demo, use a controlled repository.

Example:

```text
proofai-demo-auth
```

Initial bug:

```python
def verify_password(password, stored_password):
    return password == stored_password
```

But the tests expect proper password verification.

Baseline:

```text
21 / 24 tests
```

Claude fixes the function.

Verification:

```text
24 / 24 tests
```

Then:

```text
VERIFIED
```

Blockchain transaction appears.

Payment releases.

Receipt appears.

---

# 66. Demo UI Flow

The ideal visual sequence:

```text
CREATE TASK
     ↓

"Fix failing authentication tests"

Reward:
2 MON

     ↓

CONFIRM WALLET
     ↓

TASK FUNDED
     ↓

CODEWOLF ASSIGNED
     ↓

BEFORE

21 / 24 tests

     ↓

AI WORKING...

     ↓

PATCH GENERATED
     ↓

VERIFICATION

24 / 24 tests

     ↓

✅ VERIFIED

     ↓

PROOF RECORDED

     ↓

2 MON PAID

     ↓

REPUTATION

92% → 93%

     ↓

VIEW WORK RECEIPT
```

---

# 67. Architecture Diagram for Presentation

```text
                        ┌──────────────┐
                        │     User     │
                        └──────┬───────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │   React Web App  │
                     └─────┬───────┬────┘
                           │       │
                      REST │       │ Wallet
                           │       │
                           ▼       ▼
                  ┌────────────┐ ┌────────────┐
                  │  FastAPI   │ │   Monad    │
                  │            │ │            │
                  │Orchestrator│ │ Contracts  │
                  └──────┬─────┘ └─────┬──────┘
                         │             ▲
              ┌──────────┼──────────┐  │
              │          │          │  │
              ▼          ▼          ▼  │
          PostgreSQL   Claude     Docker│
                                   │    │
                                   ▼    │
                                Tests   │
                                   │    │
                                   ▼    │
                              Result Hash
                                   │
                                   └─────┘
```

---

# 68. Smart Contract Interaction Diagram

```text
USER
 │
 │ createTask() + MON
 ▼
TASK ESCROW
 │
 │
 ├──────────────► Task Created
 │
 │
 │ acceptTask()
 ▼
AGENT ASSIGNED
 │
 │
 │ submitResult()
 ▼
RESULT SUBMITTED
 │
 │
 │ verifyTask()
 ▼
VERIFIED
 │
 ├──────────────► WORK RECEIPT
 │
 ├──────────────► AGENT REGISTRY
 │                  Reputation ↑
 │
 ▼
PAYMENT RELEASED
 │
 ▼
AGENT WALLET
```

---

# 69. Technology Choices

## React

Why:

Fast development and matches existing experience.

---

## TypeScript

Why:

Better contract/API typing and safer frontend development.

---

## FastAPI

Why:

Good AI/backend ecosystem and aligns with existing experience.

---

## PostgreSQL

Why:

Tasks, executions and verification records are relational.

---

## Claude API

Why:

Main coding-agent intelligence.

---

## Docker

Why:

Provides isolated and reproducible verification.

---

## Solidity

Why:

Monad smart contracts use EVM-style contracts.

---

## Monad

Why:

Trust, escrow, settlement and portable agent history belong on-chain.

---

# 70. What NOT to Add

Do not add these to the initial architecture:

```text
Kubernetes

Kafka

microservices

GraphQL

multiple AI models

vector database

RAG

agent marketplace

DAO

custom token

NFT

multi-chain support

complex decentralized verifier network
```

They do not improve the core hackathon demo.

---

# 71. Recommended Development Order

## Phase 1

Build Solidity contract:

```text
createTask

escrow

verify

payment
```

---

## Phase 2

Build React:

```text
wallet

create task

transaction UI
```

---

## Phase 3

Build FastAPI:

```text
tasks

database

task state
```

---

## Phase 4

Integrate Claude.

---

## Phase 5

Build controlled demo repository.

---

## Phase 6

Build Docker verification.

---

## Phase 7

Connect:

```text
verification
→
Monad
→
payment
```

---

## Phase 8

Add reputation.

---

## Phase 9

Build Work Receipt.

---

## Phase 10

Polish dashboard and demo flow.

---

# 72. Final Architecture Decision

The hackathon version of ProofAI should therefore be:

```text
React
        │
        ├──────────── Monad
        │
        ▼
FastAPI
        │
   ┌────┼──────────────┐
   │    │              │
   ▼    ▼              ▼
Postgres Claude       Docker
                       │
                       ▼
                    Tests
                       │
                       ▼
                 Result Hash
                       │
                       ▼
                     Monad
                       │
              ┌────────┴────────┐
              ▼                 ▼
         Reputation           Payment
```

The key architectural principle is:

> **AI performs the work. Deterministic software verifies the work. Monad records and settles the verified outcome.**

That separation gives ProofAI a clear technical reason for each major component instead of adding AI or blockchain simply for the sake of the hackathon.