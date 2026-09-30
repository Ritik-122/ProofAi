# Understanding ProofAI in simple terms

This guide explains the project without assuming programming or blockchain knowledge.
It describes the application as of features 1 and 2: wallet sign-in and task creation.

## What is ProofAI?

ProofAI is being built to help people give coding work to an AI agent and check that work before paying for it.

Imagine hiring someone to repair a machine. You would want to test the machine before paying the repair person. ProofAI applies that idea to software:

> AI performs the work. Deterministic software verifies it. Monad records and settles the verified outcome.

An **AI agent** is a program that uses an AI model to carry out a task. Our planned coding agent is called **CodeWolf**, powered by Claude.

The important separation is that the AI writes a proposed fix, but does not get to declare its own work successful. A separate program runs predefined checks.

## What can the application do today?

| Available now | Planned for later features |
| --- | --- |
| Connect a browser wallet, such as MetaMask | Deposit a reward into escrow |
| Sign a login message to prove wallet ownership | Assign a task to CodeWolf |
| Create and save a coding task | Ask Claude to generate a fix |
| Enter a proposed reward | Run the fix in an isolated Docker environment |
| Select the bundled Python demo | Record the verification result on Monad |
| Save the exact demo version and test rules | Release payment after successful verification |
| View saved task details and check their fingerprint | Update agent reputation and issue a work receipt |

**Saving a task today does not call Claude, run its tests, send money, or create a blockchain transaction.**

The current saved-task state is `AWAITING_FUNDING`. Funding is the next feature to build.

## A simple example of the intended finished experience

Suppose a small application should allow active administrators and editors to enter a workspace. It should reject viewers and suspended users, but its code currently gets those rules wrong.

1. You create a task asking for that access-control bug to be fixed.
2. You offer a reward, such as 0.1 MON.
3. Once funding is implemented, you deposit that reward into the escrow contract.
4. CodeWolf reads the task and relevant code, then proposes a change.
5. A separate verification program runs the protected tests against the changed code.
6. If the required checks pass, the authorized verifier submits the outcome for on-chain settlement.
7. The contract records the receipt, updates the agent's statistics, and releases payment together.
8. If verification fails, the agent does not receive the reward. The creator can reclaim it under the implemented refund rules.

Only the task-saving part of this journey is available today. The remaining steps describe the agreed direction, not completed functionality.

## How signing in works

Your wallet acts as your identity. Its public address is similar to an account identifier.

When you sign in:

1. ProofAI creates a short, temporary login message.
2. MetaMask asks whether you want to sign that message.
3. Your wallet creates a digital signature. ProofAI does not receive your private key.
4. The server checks that the signature belongs to the claimed wallet.
5. If it matches, the server creates a temporary authenticated session.

Signing a ProofAI login message is not a payment or a spending approval. It costs no blockchain gas. The current login message expires after five minutes and can be used only once. A signed-in session lasts up to thirty minutes.

Signing out or changing wallet accounts/networks clears the session in the app. Refreshing the page requires a new sign-in because we keep the login token only in browser memory.

## What happens when you save a task?

The visible form is only the beginning. Behind it, the application does the following:

1. **Checks your identity.** The server requires a valid signed-in session. Merely connecting a wallet is not enough.
2. **Checks your inputs.** The task needs a title, requirements, a supported demo, and a positive reward amount.
3. **Records the exact project version.** It saves a copy of the bundled demo files, so later edits to the demo do not change this task's starting point.
4. **Attaches the test rules.** The server chooses the permitted source file and required tests. The task creator cannot replace those rules with an easy command that always succeeds.
5. **Creates a digital fingerprint.** It hashes the saved task details using a consistent format.
6. **Stores the record in PostgreSQL.** This is the application's database, which acts like an organized filing cabinet.
7. **Shows the saved task.** The browser displays the requirements, proposed reward, repository version, and task hash.

The creator is taken from the authenticated session. A person cannot claim another wallet owns a task by changing a form field.

The application also gives each save request a unique identifier. If a connection problem makes the browser retry the same request, the server returns the existing task instead of creating a duplicate.

## Understanding the saved-task screen

| Screen label | Plain-language meaning |
| --- | --- |
| Task saved | Your task details have been stored in the application database. |
| Awaiting funding | The task is saved but has not received an escrow deposit. |
| Proposed reward: 0.1 MON | This is the amount you offered. It has not been charged or transferred. |
| Escrow: Not funded | There is no deposited reward associated with this task yet. |
| `bundled://python-access` | A small example code project included with ProofAI, not a GitHub download or a webpage. |
| Pinned version | The fingerprint of the exact example files saved for this task. |
| Required tests: 5 | Five checks belong to this template. This does not mean they have run or passed. |
| Allowed source changes: `access.py` | The planned agent may change this file, while the verification tests remain protected. |
| Task metadata hash | A fingerprint of the saved requirements, reward, repository version, and test policy. |
| Hash matches the saved metadata | The browser recalculated the fingerprint and obtained the same value as the server. |
| Task ID | The unique reference used to find this saved task. |

Keep the saved page URL. After refreshing and signing in again with the same wallet, you can reopen the task. Another wallet should not be able to read that task through the API.

## An important limitation of the current demo

The current demo checks a Python access-control function. It asks questions such as:

- Is an active administrator allowed in?
- Is an active editor allowed in?
- Is a viewer denied access?
- Is a suspended administrator denied access?
- Is an unknown role denied access?

It does **not** inspect colors, spacing, alignment, or whether a webpage looks modern.

For example, a task titled **“Fix Frontend Issue”** with requirements such as **“make the UI aligned, polished, and modern”** can currently be saved as text. However, those requirements do not match this demo's tests. Saving the text does not establish that ProofAI can solve or verify that request.

For the intended demo, use **“Fix workspace access permissions”**, or click **Use demo instructions**. The requested work should match what the selected tests actually check.

This is a product limitation to address before execution and payment are enabled: unsupported requirements must not be presented as verified simply because an unrelated test suite passes.

## What is a hash?

A **hash** is a digital fingerprint calculated from some data. Changing the data will normally produce a different fingerprint.

ProofAI currently uses fingerprints for two related purposes:

- **Repository version:** identifies the saved collection of demo files.
- **Task metadata hash:** identifies the saved task details, including the reward and verification rules.

Later, a **result hash** will identify the evidence associated with completed work.

A hash is not encryption, does not hide the data, and does not tell us whether the work is correct. It helps compare data against a previously recorded fingerprint.

Today the task fingerprint is stored off-chain. A matching hash on the screen is not an on-chain receipt, and it is not proof that an AI has completed the task.

## What will automated verification do?

An automated test is a small program that checks a specific expected behavior. For example: “a suspended user must be denied access.”

**Deterministic** means that, under the same controlled conditions, the same input should produce the same result. Instead of asking another AI whether the answer looks good, ProofAI will run fixed software checks.

The planned verification flow compares the original code with the proposed fix:

1. Run the trusted tests on the original code and record existing failures.
2. Apply the agent's permitted source changes to a fresh working copy.
3. Run the same protected tests again in a controlled environment.
4. Require the complete mandatory suite to run and pass, along with any required build checks.

The agent must not make a failing test disappear, weaken its expectations, or substitute a fake success report. Missing tests and skipped mandatory checks cannot count as success.

Passing tests proves only that those checks passed under the recorded conditions. It does not prove that every possible bug is gone or that every sentence in a task description has been satisfied. Choosing the right tests is essential.

## Why use Docker?

The planned verifier must run code that an AI has changed. That code should not run freely on the application's host machine.

Think of Docker as a controlled workshop for the job. The verifier will give the code limited time, memory, and processing power, with no access to application secrets, wallet keys, or unrestricted network connections.

Docker isolation reduces risk; it is not a guarantee that any arbitrary code is safe. This is why the MVP starts with a small controlled demo instead of accepting every repository on the internet.

Docker verification is not implemented yet.

## Why use Monad and escrow?

**Monad** is the blockchain selected for ProofAI. A blockchain provides a shared record that people can inspect independently of the application database.

**MON** is the reward unit shown in the application. The current app is configured for Monad Testnet, a development network. Seeing its name in the header does not mean a task has been recorded on-chain.

**Escrow** means holding a payment until agreed conditions are met. In the planned flow, a smart contract holds the reward and enforces the allowed payment and refund transitions.

A **smart contract** is a program on the blockchain. ProofAI plans three:

| Contract | Simple responsibility |
| --- | --- |
| AgentRegistry | Records agent identities and their verified task statistics. |
| TaskEscrow | Holds rewards and controls assignment, settlement, and refunds. |
| WorkReceipt | Records a reference to successfully verified work. |

The user's wallet will approve funding transactions. The application does not need the user's private key. Large files, prompts, and test logs will stay in the ordinary database; the blockchain will hold compact records such as hashes, payment state, and agent statistics.

These contracts are not connected to the current task-creation feature. MetaMask's **Add funds** button is a wallet feature, not a ProofAI task-funding action. You do not need to use it to test saving a task.

## Who decides whether a result passed?

For the MVP, ProofAI operates the verification service. It runs the tests separately from Claude and uses an authorized verifier wallet to submit the result.

Monad will enforce who may report the outcome and how payment follows that report. Monad itself does not run the Python tests or read the entire codebase.

This means the MVP still trusts the ProofAI-operated verifier to report honestly. The blockchain makes its recorded claims, settlement, and reputation history inspectable; it does not magically remove that trust requirement.

## How the main parts fit together

| Part | Everyday comparison | What it does |
| --- | --- | --- |
| React frontend | Reception desk | Shows forms, wallet status, and saved results in your browser. |
| FastAPI backend | Coordinator | Checks identity and inputs, saves records, and will coordinate the later work stages. |
| PostgreSQL | Filing cabinet | Stores users, sessions, task details, and eventually execution evidence. |
| MetaMask / wallet | Identity and approval tool | Signs login messages and will approve user transactions. |
| Claude / CodeWolf | Coding worker | Will propose changes to solve the coding task. |
| Docker and automated tests | Controlled workshop and inspection checklist | Will run the proposed code and check the required behavior. |
| Monad contracts | Public settlement record | Will hold rewards, record outcomes, and update reputation. |

The current working path is:

```text
Browser + wallet
      |
      | Sign a login message
      v
Backend checks the signature
      |
      | User submits task details
      v
Backend validates, snapshots, and hashes the task
      |
      v
Database stores the unfunded task
      |
      v
Browser displays it and checks the metadata hash
```

## What your manual test confirms

Reaching the saved-task screen after signing in is the expected result for feature 2. The screenshot shows a saved title, requirements, a proposed reward of 0.1 MON, the bundled repository, and an unfunded status. Those visible values are consistent with the current feature.

The screenshot alone cannot establish that every backend check works, that the data survives a restart, or that the metadata hash matches: the hash section is below the visible area. It also cannot demonstrate AI execution, verification, or payment, which are not implemented yet.

For a useful manual check, scroll to the hash section, reload and sign in with the same wallet to reopen the saved URL, then check that a different wallet cannot access it. For a task we can eventually verify, use requirements that match the Python access-control demo.


## Deleting an unfunded task

On a saved task, choose **Delete task** and confirm. Only the wallet that created the task can delete it, and only while its status is **Awaiting funding**. No wallet transaction or payment is involved.

After deletion, its saved link no longer opens the task. The database keeps the original details and a deletion timestamp for traceability (a soft delete). There is no restore button. Retrying an old save request cannot bring it back; you can create a new task instead. Funded or later-stage tasks cannot use this action.
