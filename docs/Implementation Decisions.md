# Approved MVP implementation approach

The user approved the review recommendations on September 29, 2026. These decisions resolve conflicts in the existing designs; they do not expand the product scope.

- React/TypeScript/Tailwind/TanStack Query/viem frontend; FastAPI/SQLAlchemy/PostgreSQL modular monolith; Claude coding agent; Docker tests; Solidity/Foundry/OpenZeppelin on Monad.
- One controlled Python demo repository and one built-in agent, CodeWolf.
- Versioned canonical UTF-8 JSON commitments using Keccak-256. Pin repository revision and verification policy before funding. Preserve exact commitment bytes.
- Keep application progress separate from authoritative chain status.
- Verify first, then submit the final evidence hash and adjudicate that same hash. The evidence includes the patch hash. Submission itself does not authorize payment.
- Atomic verification, receipt, reputation, and payment through `verifyAndRelease`.
- Wallet-signature authentication with expiring, single-use nonces.
- Reputation denominator is successful plus failed adjudications. Infrastructure errors are not agent failures.
- Fixed task expiry provides creator recovery for unfinished work; late settlement is disallowed. Cancellation before assignment and refund after cancellation/failure remain available.
- Fixed, protected tests and execution policy; no agent edits to tests, dependencies, or Docker configuration. No network or secrets inside execution containers.
- Persist stages and transaction intent in PostgreSQL. Reconcile receipts and chain state after restarts. Retry settlement without rerunning the agent.

## Feature-by-feature delivery

The user subsequently requested separate feature approvals instead of implementing the whole initial milestone at once. Feature 1 is implemented; the user approved feature 2 on September 30, 2026. Later features still require approval.

1. Wallet connection and sign-in (implemented).
2. Task creation (current feature).
3. Escrow funding and refunds.
4. Task dashboard and details.
5. CodeWolf registration and assignment.
6. Deterministic verification engine.
7. Claude coding execution.
8. On-chain results and settlement.
9. Agent reputation and profile.
10. Verifiable work receipt.
11. Landing page and demo readiness.

The initial escrow contract and tests predate this narrower scope; feature 1 does not modify, deploy, or integrate them.

### Feature 1 decisions

- Discover browser wallets using viem/EIP-6963, with an injected-provider fallback; use Monad Testnet.
- Five-minute server-defined login challenges; lowercase database identity and checksum display addresses.
- Bind messages to configured origin and chain. Atomically consume challenges and issue a thirty-minute JWT tied to a revocable database session.
- Keep tokens only in browser memory. Disconnect, account/network changes, expiry, and reload require a new sign-in.
- PostgreSQL runtime; an isolated SQLite test fixture is used only for fast API tests. PostgreSQL integration tests use a separate database and temporary schemas.
- The user requested local PostgreSQL setup. Use project-local official binaries, loopback-only port 55432, password authentication, and a non-superuser app role. No system service.
- React build uses the previously discussed Vite tooling. Database bootstrap is explicit for this first schema; migrations are deferred until schema evolution is needed. web3.py is not needed for signature recovery in this feature.

### Feature 2 decisions

- The user selected a bundled Python demo instead of an external repository. Use `demo/python-access`, with five fixed tests and an intentionally broken access-control function. This is separate from application authentication.
- Store the demo file snapshot alongside each task and identify it by SHA-256 of its canonical file map. This is a content revision, not a Git commit. Task/policy commitments continue to use Keccak-256.
- Server owns the template, allowed paths, and test policy. Task creation accepts no arbitrary URL, branch, command, owner, or status.
- Save `AWAITING_FUNDING` tasks; no on-chain calls, claims of funded escrow, or agent assignment.
- Scope UUID idempotency keys to the authenticated creator. Same payload returns the existing task; changed payload with the same key returns a conflict.
- Use frozen, numbered SQLAlchemy migrations for the existing authentication schema and new task table. No additional migration dependency is introduced.
- Current `taskHash` commits to metadata, creator, chain, exact reward, repository snapshot revision, and test policy. Because no escrow deployment exists yet, this is explicitly a metadata commitment, not a contract-bound funding authorization. Feature 3 must define the deployment-bound funding commitment before accepting money; preserve this metadata hash and do not silently rewrite it.

## Design reference

Stitch project: `11517766256081342826` — ProofAI Agent Verification Platform.

The project exposes 12 assets, including dashboard variants, task creation variants, landing page, live execution, verification result, receipt, agent profile, discovery, and logo.

Selected creation reference: `f4fd2cb21980490eb19f40d50f8cfbe7` (Create a Verified AI Task). Its original HTML and screenshot are stored in `design-reference/` as reference artifacts, not executable application code.

Use the dark panels, violet actions, monospace metadata, and escrow summary layout. Product behavior remains governed by the MVP documents and decisions above. Replace illustrative statistics, guarantee claims, and unsupported features with real data or accurate empty states.
