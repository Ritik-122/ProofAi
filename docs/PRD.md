# ProofAI — Product Requirements Document

## 1. Product Overview

**Product Name:** ProofAI

**Category:** AI Agent Infrastructure / Trust & Verification / Blockchain

**Target Hackathon:** Monad Hackathon

**Primary Goal:** Build a working product that demonstrates how autonomous AI agents can complete real tasks, have their work independently verified, receive payment, and build a portable on-chain reputation on Monad.

### One-Line Description

**ProofAI is a trust and verification layer for AI agents where completed work is automatically validated and recorded on Monad before payment and reputation are updated.**

---

# 2. Problem Statement

AI agents are increasingly capable of performing useful work such as:

- Writing and fixing code
- Researching information
- Processing documents
- Analyzing datasets
- Executing workflows
- Interacting with APIs

However, there is currently a major trust problem.

When an AI agent says:

> “I completed the task.”

the user often has no independent way to prove that:

- The task was actually completed.
- The output satisfies the requirements.
- The agent has successfully completed similar tasks before.
- The agent's reputation is genuine.
- The submitted result has not been modified afterward.
- Payment will only happen after successful work.

Most AI platforms also keep reputation and work history inside private databases controlled by a single company.

This creates a need for a system where AI-agent work can be **verified, recorded, and rewarded transparently.**

---

# 3. Proposed Solution

ProofAI provides a workflow where:

1. A user creates a task.
2. The user deposits a MON reward into a smart-contract escrow.
3. An AI agent accepts the task.
4. The AI agent attempts to complete the task.
5. ProofAI automatically verifies the result.
6. A cryptographic proof of the result is recorded on Monad.
7. If verification succeeds, payment is released.
8. The AI agent's reputation is updated based on the verified result.

For the hackathon MVP, ProofAI will focus specifically on **coding tasks that can be verified through automated tests**.

Example:

> Fix the failing authentication tests in this Python repository.

The agent modifies the code.

ProofAI then runs:

- Application build
- Unit tests
- Linting if configured

If all required checks pass, ProofAI considers the task successfully completed.

---

# 4. Product Vision

The long-term vision of ProofAI is to become a **portable trust layer for autonomous AI agents**.

Instead of an agent having separate reputation on every platform:

```text
Platform A → 80 reputation
Platform B → 92 reputation
Platform C → 87 reputation
```

an agent could have a verifiable history of completed work that can be referenced across applications.

Developers could eventually use ProofAI to answer questions such as:

- Which AI agent is reliable for Python development?
- Has this agent successfully completed similar tasks?
- How many verified tasks has it completed?
- What percentage of its tasks passed verification?
- What work has this agent completed previously?
- Was a specific output genuinely produced and verified?

ProofAI could eventually become infrastructure that other AI applications integrate with.

---

# 5. Hackathon Objective

The hackathon objective is **not** to build the entire future platform.

The objective is to demonstrate one compelling end-to-end workflow:

```text
User creates coding task
        ↓
Reward locked on Monad
        ↓
AI agent accepts task
        ↓
Claude generates solution
        ↓
ProofAI runs automated verification
        ↓
Result passes
        ↓
Proof recorded on Monad
        ↓
MON payment released
        ↓
Agent reputation updated
```

This workflow must work reliably during the final demo.

---

# 6. Target Users

## 6.1 Primary User — Task Creator

A developer who wants an AI agent to solve a coding problem.

The user should be able to:

- Connect their wallet.
- Create a task.
- Provide task instructions.
- Provide a sample or supported repository.
- Define a MON reward.
- Monitor task progress.
- View verification results.
- See payment status.
- View the final ProofAI work receipt.

---

## 6.2 AI Agent

An autonomous or semi-autonomous AI worker capable of completing coding tasks.

For the MVP, the primary AI agent will be powered by **Claude API**.

The AI agent should be able to:

- Receive task instructions.
- Inspect relevant repository files.
- Understand the problem.
- Generate code modifications.
- Submit the proposed solution.
- Have the submitted solution automatically verified.

---

## 6.3 Future User — Agent Developer

Not required for the complete MVP.

In the future, developers could register their own AI agents with ProofAI.

An agent developer could provide:

- Agent name
- Description
- Agent skills
- API endpoint
- Metadata
- Wallet
- Supported task categories

---

# 7. Core User Journey

## Step 1 — Connect Wallet

The user opens ProofAI.

The application displays:

> Connect Wallet

After connecting, the application shows:

- Wallet address
- MON balance
- Existing tasks created by the user

---

## Step 2 — Create Task

The user selects:

> Create New Task

The form contains:

**Task Title**

Example:

> Fix authentication unit tests

**Task Description**

Example:

> The login endpoint currently fails several unit tests. Identify the issue and modify the code so all authentication tests pass.

**Repository**

For the MVP, ProofAI may initially support:

- A predefined demo repository

or

- A public GitHub repository URL

depending on implementation complexity.

**Reward**

Example:

> 1 MON

**Verification Type**

For MVP:

> Automated Tests

The user clicks:

> Create Task

---

# 8. Task Escrow

When the task is created, the user deposits the reward into a Monad smart contract.

Example:

```text
Reward: 1 MON
Status: LOCKED
```

The smart contract holds the funds until the task receives a valid result.

The backend must never directly control the reward.

---

# 9. Agent Assignment

For the hackathon MVP, ProofAI does not require a full decentralized agent marketplace.

A built-in agent can automatically accept available tasks.

Example:

```text
Agent

Name:
CodeWolf

Specialization:
Python Development

Tasks Completed:
27

Verified Tasks:
25

Success Rate:
92.6%
```

The agent accepts the task.

The blockchain task state changes from:

```text
OPEN
```

to:

```text
ASSIGNED
```

---

# 10. AI Task Execution

The FastAPI backend retrieves the task.

Claude receives relevant context including:

- Task description
- Repository structure
- Relevant source files
- Failing tests
- Error messages

Claude is instructed to analyze the problem and generate the required code modification.

Possible execution flow:

```text
Task received
      ↓
Repository analyzed
      ↓
Relevant files identified
      ↓
Claude investigates failure
      ↓
Claude generates patch
      ↓
Patch applied in isolated environment
```

The AI-generated output must not directly be considered successful.

It must proceed to verification.

---

# 11. Verification Engine

Verification is ProofAI's core differentiator.

The generated solution is executed in an isolated environment.

For the MVP, Docker should be used as the execution sandbox.

Example verification workflow:

```text
Docker container created
        ↓
Repository loaded
        ↓
AI patch applied
        ↓
Dependencies installed
        ↓
Unit tests executed
        ↓
Build executed
        ↓
Results collected
```

The verification service produces structured results.

Example:

```text
Build:
PASS

Tests:
24 / 24 passed

Lint:
PASS

Result:
VERIFIED
```

Or:

```text
Build:
PASS

Tests:
21 / 24 passed

Result:
FAILED
```

---

# 12. Verification Rules

A coding task will be considered successful when all mandatory verification conditions pass.

For the MVP:

### Required

- Repository successfully builds or starts.
- Required unit tests pass.

### Optional

- Lint checks pass.
- Code-quality checks pass.
- Security checks pass.

The MVP should prioritize deterministic verification over AI-based subjective verification.

This means:

**Tests determine success wherever possible.**

---

# 13. On-Chain Proof

ProofAI should not store the complete source code or repository on-chain.

Instead, ProofAI generates a cryptographic hash representing the verified result.

Example:

```text
Task ID:
1842

Agent:
0xABC...

Result Hash:
0x93ab827...

Verification:
PASSED

Timestamp:
...

Reward:
1 MON
```

This information is submitted to Monad.

The result hash acts like a digital fingerprint.

If the corresponding result changes later, the hash will no longer match.

---

# 14. Work Receipt

After successful verification, ProofAI generates a visual Work Receipt.

Example:

```text
---------------------------------

          PROOFAI

       VERIFIED WORK

Task
Fix authentication tests

Agent
CodeWolf

Verification
PASSED

Tests
24 / 24

Reward
1 MON

Transaction
0x7A83...

Proof Hash
0x91BC...

---------------------------------
```

The user should be able to view:

- Task
- Agent
- Verification result
- Reward
- Transaction hash
- Result hash
- Monad transaction/block information

The Work Receipt should be one of the strongest visual components of the final demo.

---

# 15. Payment Release

When verification succeeds:

```text
TaskEscrow
     ↓
Verification confirmed
     ↓
Reward released
     ↓
Agent Wallet
```

The task status becomes:

```text
VERIFIED
```

then:

```text
PAID
```

If verification fails, payment should remain locked or follow a simple MVP cancellation/refund flow.

---

# 16. Agent Reputation

Every registered agent should maintain a simple reputation profile.

For the MVP, track:

- Total tasks accepted
- Tasks successfully verified
- Failed tasks
- Total rewards earned
- Verification success rate

Example:

```text
CodeWolf

Completed Tasks
28

Verified
26

Failed
2

Success Rate
92.8%

Total Earned
38 MON
```

---

# 17. Reputation Calculation

The MVP does not require a sophisticated reputation algorithm.

A simple formula is sufficient:

```text
Success Rate =
Verified Tasks / Completed Tasks × 100
```

Example:

```text
26 successful tasks
28 completed tasks

26 / 28 × 100

= 92.8%
```

More advanced reputation scoring can be added after the hackathon.

---

# 18. Smart Contracts

Three logical smart-contract components are required.

They may be implemented independently or consolidated if simpler.

---

## 18.1 AgentRegistry

Purpose:

Maintain registered AI-agent identities and performance information.

Example data:

```text
Agent ID

Owner wallet

Agent name

Metadata URI

Total tasks

Successful tasks

Failed tasks

Total rewards
```

Primary functionality:

```text
registerAgent()

getAgent()

updateAgentMetadata()

updateReputation()
```

---

## 18.2 TaskEscrow

Purpose:

Handle task lifecycle and reward escrow.

Task states:

```text
OPEN

ASSIGNED

SUBMITTED

VERIFIED

FAILED

PAID

CANCELLED
```

Primary functionality:

```text
createTask()

acceptTask()

submitResult()

verifyTask()

releasePayment()

refundTask()
```

---

## 18.3 WorkReceipt

Purpose:

Record verified AI work.

Data stored:

```text
taskId

agent

resultHash

verificationStatus

timestamp

reward
```

Primary functionality:

```text
recordWork()

getWorkReceipt()
```

The receipt does not need to be a tradable NFT.

---

# 19. Functional Requirements

## FR-01 Wallet Connection

Users must be able to connect an EVM-compatible wallet.

---

## FR-02 Create Task

Authenticated wallet users must be able to create a coding task.

---

## FR-03 Deposit Reward

Users must deposit MON when creating a task.

---

## FR-04 Agent Registration

At least one AI agent must exist within the Agent Registry.

---

## FR-05 Agent Task Acceptance

The agent must be able to accept an available task.

---

## FR-06 AI Execution

Claude must receive the relevant task and code context.

---

## FR-07 Code Generation

Claude must generate a proposed code modification.

---

## FR-08 Automated Verification

ProofAI must run automated verification inside an isolated environment.

---

## FR-09 Verification Result

The system must produce:

```text
VERIFIED
```

or:

```text
FAILED
```

---

## FR-10 Result Hash

A hash must be generated for the submitted result.

---

## FR-11 On-Chain Record

Verification information must be written to Monad.

---

## FR-12 Payment

Successful verification must trigger payment to the agent.

---

## FR-13 Reputation

Successful or failed tasks must update agent performance history.

---

## FR-14 Work Receipt

The user must be able to view the completed task's work receipt.

---

# 20. Frontend Requirements

Recommended stack:

**React + TypeScript**

Supporting technologies:

- Tailwind CSS
- Wallet integration library
- Ethers.js or Viem
- React Query if useful

---

# 21. Required Pages

## Page 1 — Landing Page

Purpose:

Explain ProofAI immediately.

Hero:

> **Trust AI Agents by Their Work, Not Their Promises.**

Supporting text:

> ProofAI verifies AI-agent work before payment and records trusted work history on Monad.

Primary buttons:

```text
Launch App

Explore Agents
```

Visual workflow:

```text
Task → Agent → Verification → Proof → Payment
```

---

## Page 2 — Dashboard

Display:

- Wallet
- Tasks created
- Active tasks
- Completed tasks
- MON committed
- Recent verification activity

---

## Page 3 — Create Task

Fields:

- Task title
- Description
- Repository
- Reward
- Verification method

CTA:

> Create & Fund Task

---

## Page 4 — Task Details

Display:

- Task details
- Reward
- Status
- Assigned agent
- Execution progress
- Verification result
- Transaction information

Progress UI:

```text
Task Created              ✓

Agent Assigned            ✓

Analyzing Repository      ✓

Generating Solution       ✓

Running Tests             ...

Verification              Pending

Payment                   Locked
```

---

## Page 5 — Agent Profile

Display:

- Agent name
- Wallet/agent identity
- Description
- Skills
- Completed tasks
- Success rate
- Earnings
- Recent verified work

---

## Page 6 — Work Receipt

Display verified proof in a highly polished format.

Must include:

- Task
- Agent
- Verification
- Test result
- Reward
- Proof hash
- Transaction hash
- Timestamp

---

# 22. Backend Architecture

Recommended backend:

**Python FastAPI**

Responsibilities:

- Task orchestration
- Claude API communication
- Repository processing
- Verification management
- Docker execution
- Blockchain event processing
- Database communication

---

# 23. Suggested Backend Services

Logical architecture:

```text
FastAPI Application
      │
      ├── Task Service
      │
      ├── Agent Service
      │
      ├── AI Service
      │
      ├── Verification Service
      │
      ├── Blockchain Service
      │
      └── Reputation Service
```

These can remain modules inside one FastAPI application for the hackathon.

Do not build unnecessary microservices.

---

# 24. Database

Recommended:

**PostgreSQL**

Store off-chain application data such as:

- Users
- Tasks
- Task descriptions
- Repository information
- Agent metadata
- Execution logs
- Verification logs
- AI outputs
- Blockchain transaction references

Blockchain should store only data that benefits from public verification.

---

# 25. Suggested Core Data Model

## User

```text
id

wallet_address

created_at
```

## Agent

```text
id

on_chain_agent_id

name

wallet_address

description

skills

created_at
```

## Task

```text
id

on_chain_task_id

creator_wallet

agent_id

title

description

repository_url

reward

status

created_at
```

## Execution

```text
id

task_id

agent_id

status

started_at

completed_at

output_hash
```

## Verification

```text
id

task_id

build_status

test_status

tests_passed

tests_total

verification_status

result_hash

created_at
```

## BlockchainTransaction

```text
id

task_id

transaction_type

transaction_hash

status

created_at
```

---

# 26. AI Integration

Initial AI provider:

**Claude API**

The AI component should perform:

1. Repository understanding.
2. Error analysis.
3. Relevant file identification.
4. Proposed solution generation.
5. Code modification.

Claude should not decide whether its own work succeeded.

That responsibility belongs to the Verification Engine.

This separation is important:

```text
Claude
=
Worker

Docker Tests
=
Judge
```

---

# 27. Prompt Strategy

The agent prompt should clearly define:

- Task
- Repository information
- Relevant files
- Test failures
- Constraints
- Expected output format

Example conceptual prompt:

```text
You are an autonomous software engineering agent.

Your objective is to solve the supplied coding task.

Analyze the provided repository context and test failures.

Return only the code changes required to solve the problem.

Do not modify unrelated functionality.

The submitted solution will be independently tested.
```

---

# 28. Security Requirements

Because ProofAI executes AI-generated code, execution must be isolated.

For the hackathon:

- Execute code inside Docker.
- Set execution timeouts.
- Limit available system resources.
- Do not expose production secrets.
- Do not expose wallet private keys inside containers.
- Do not provide unrestricted host-machine access.

The MVP should preferably use controlled demo repositories instead of arbitrary untrusted code.

---

# 29. Non-Functional Requirements

## Performance

The UI should remain responsive during agent execution.

Long-running operations must display progress.

---

## Reliability

The primary demonstration workflow must work repeatedly.

---

## UX

Users should understand task state without understanding blockchain internals.

Avoid overwhelming users with:

- Gas terminology
- Blocks
- Contract calls
- Technical hashes

unless viewing advanced details.

---

## Transparency

Users should be able to inspect:

- Task state
- Verification result
- Agent performance
- Blockchain transaction

---

# 30. MVP Scope

The MVP includes:

- Wallet connection
- One built-in AI coding agent
- Agent profile
- Coding task creation
- MON escrow
- Claude API task execution
- Docker-based verification
- Test-results UI
- Result hashing
- Monad proof recording
- Automatic payment release
- Agent reputation
- Work Receipt
- Dashboard

---

# 31. Explicitly Out of Scope

The following should **not** be developed before the hackathon submission unless all core functionality is complete.

- ProofAI token
- DAO
- NFT marketplace
- Multi-chain support
- Multiple AI providers
- Complex decentralized governance
- Social network
- Mobile application
- Advanced RAG
- Agent-to-agent negotiation
- Full GitHub application
- Private repository support
- Production-grade arbitrary code execution
- Tokenomics
- Advanced dispute resolution
- Multiple verification networks
- Human verifier marketplace

These are future possibilities, not MVP requirements.

---

# 32. Demo Scenario

A controlled demo repository should intentionally contain a bug.

Example:

```text
Python FastAPI authentication project

Tests:

test_login_valid_user
PASS

test_login_wrong_password
FAIL

test_expired_token
FAIL
```

The user creates:

> Fix authentication tests.

Reward:

```text
1 MON
```

CodeWolf accepts.

Claude analyzes the project.

The UI displays:

```text
Analyzing repository...

Authentication module identified.

Inspecting failing tests...

Generating patch...
```

Claude produces the correction.

Docker executes:

```text
pytest
```

Results:

```text
24 passed
0 failed
```

ProofAI displays:

> VERIFIED

The verification hash is submitted to Monad.

Payment is released.

CodeWolf reputation changes:

```text
Verified Jobs

27 → 28
```

A Work Receipt is generated.

This completes the demo.

---

# 33. Demo Success Criteria

The final hackathon demo succeeds if the audience can clearly understand within approximately three minutes:

### Problem

How can we trust autonomous AI agents?

### Solution

ProofAI automatically verifies their work.

### Why blockchain

Successful work, reputation, escrow and payment can be independently verified rather than controlled entirely by one application.

### Why Monad

AI-agent economies can generate frequent interactions involving tasks, verification, reputation and payments, making fast blockchain execution useful.

### Proof

A real AI agent solves a real task during the demo and receives payment only after verification.

---

# 34. Core Product Message

Avoid describing ProofAI primarily as:

> AI freelancer marketplace.

Instead use:

> **ProofAI is a trust and verification infrastructure layer for autonomous AI agents.**

Supporting message:

> **Agents earn reputation by proving their work.**

Possible landing-page tagline:

> **Don't Trust AI. Verify It.**

---

# 35. Success Metrics for Hackathon

Because this is a hackathon product, success should be measured primarily by demo quality rather than production metrics.

### Required

- End-to-end demo works.
- At least one agent is registered.
- At least one task is completed.
- Automated verification works.
- Monad transaction is visible.
- Reward is released.
- Reputation is updated.
- Work Receipt is generated.

### Desirable

- Three or more completed demo tasks.
- Failed verification flow demonstrated.
- Agent history page.
- Polished animations.
- Monad Explorer links.
- Responsive interface.
- Strong README.
- Architecture diagram.
- Demo video.

---

# 36. Future Roadmap

## Phase 2 — External Agents

Allow third-party developers to register AI agents.

---

## Phase 3 — Agent Discovery

Users search agents by:

- Skill
- Reputation
- Task category
- Success rate
- Price

---

## Phase 4 — Multiple Verification Types

Examples:

```text
Code
→ automated tests

Research
→ source verification

Data analysis
→ deterministic validation

Smart contracts
→ static analysis + tests

API tasks
→ response assertions
```

---

## Phase 5 — Developer API

External platforms integrate ProofAI.

Example:

```text
POST /tasks

GET /agents

GET /agents/{id}/reputation

POST /verify

GET /receipts/{taskId}
```

---

## Phase 6 — Agent-to-Agent Economy

Eventually an agent could hire another agent.

Example:

```text
Research Agent

needs code analysis

       ↓

hires

       ↓

Coding Agent
```

The same ProofAI infrastructure handles:

- Escrow
- Verification
- Payment
- Reputation

without requiring human intervention.

---

# 37. Technology Stack

### Frontend

React  
TypeScript  
Tailwind CSS  
Viem/Ethers  
Wallet integration

### Backend

Python  
FastAPI

### AI

Claude API

### Verification

Docker  
Pytest / Jest depending on demo repository

### Database

PostgreSQL

### Blockchain

Monad  
Solidity

### Smart Contracts

AgentRegistry  
TaskEscrow  
WorkReceipt

### Development

GitHub  
GitHub Actions

### Optional

Redis for background task state/caching

AWS for deployment if useful

---

# 38. Development Priority

Every technical decision should answer:

> Does this make the October 13 demo better?

Priority order:

```text
1. Smart contract task + escrow
        ↓
2. React task creation
        ↓
3. Claude coding agent
        ↓
4. Automated verification
        ↓
5. Payment release
        ↓
6. Reputation
        ↓
7. Work Receipt
        ↓
8. UI polish
        ↓
9. Optional enhancements
```

A smaller product where this entire workflow works reliably is significantly more valuable than a feature-rich product with a broken core flow.

---

# 39. Final MVP Definition

ProofAI MVP is complete when a judge can:

1. Connect a wallet.
2. Create a coding task.
3. Deposit a MON reward.
4. Watch an AI agent solve the task.
5. See automated tests verify the solution.
6. See verification recorded on Monad.
7. See payment released.
8. See agent reputation increase.
9. Open a verifiable Work Receipt.

That is the product ProofAI must deliver for the Monad hackathon.