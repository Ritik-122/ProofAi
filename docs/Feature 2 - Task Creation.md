# Feature 2 — Task creation

## Scope

A signed-in user saves coding-task requirements, selects the supported bundled Python repository, and specifies a MON reward. The API persists an unfunded task, snapshots its source files and verification policy, and returns a reproducible metadata hash. Funding and execution remain later features.

## UI

The form follows the existing Stitch creation layout: task details, repository, verification criteria, reward, and a side summary. **Save task** creates no wallet transaction. The saved-task page reports `AWAITING_FUNDING`, verifies the returned canonical bytes using viem, and exposes the metadata for inspection.

The saved URL uses `#/tasks/{uuid}`. On reload, wallet sign-in is required before retrieval. A wallet-scoped session-storage draft preserves inputs and request ID across an interrupted save; tokens remain memory-only. Changing inputs creates a new request ID. No task dashboard or listing is added yet.

## API

- `GET /api/v1/tasks/templates`: authenticated server-controlled template catalog.
- `POST /api/v1/tasks`: authenticated creation with UUID `Idempotency-Key` header. Returns 201 for a new task, 200 for an identical retry, or 409 if the key was already used with different normalized input.
- `GET /api/v1/tasks/{uuid}`: retrieves only the creator's task; another wallet receives 404.

Creation input: title (1–200 characters), description (1–10,000), template ID, expected repository revision, and positive `rewardWei` decimal string no larger than uint256. Client-supplied ownership, status, repository URL, or verification command is rejected. The reward uses PostgreSQL `NUMERIC(78,0)` and is serialized as a string throughout the API.

## Bundled repository

`demo/python-access` contains a dependency-free Python function and five tests. Two tests intentionally fail. The API does not execute this code. Its three fixed files are read as UTF-8 with normalized LF line endings and preserved in the task row.

`repositoryRevision = "sha256:" + SHA256(canonical file map)`

The file map uses relative names as keys and full normalized text as values. No remote URL is fetched. A changed revision between catalog retrieval and save returns a conflict; a successful previous request remains retrievable even if the live template later changes.

## Canonical commitments

Version 1 uses Python JSON serialization with sorted keys, compact separators, unescaped Unicode, no floating-point values, then UTF-8 encoding. Input titles/descriptions are NFC-normalized, trimmed, and normalized to LF. The exact canonical string is persisted rather than reconstructed from mutable fields.

`taskHash = Keccak256(UTF8(canonicalPayload))`

Fields include version/domain, task UUID, lowercase creator address, chain ID as a string, normalized requirements, integer reward string, bundled repository locator and content revision, and the full versioned verification policy plus its Keccak-256 hash. Browser verification hashes the returned exact string.

This is a metadata commitment, not proof of successful work. An escrow contract address is not included because escrow deployment is outside feature 2. Feature 3 must bind this immutable metadata commitment to the selected chain/deployment before enabling funding, using a separate funding commitment if necessary. No current task can be funded through the application.

## Database migration

Run `python -m app.db` using the API virtual environment. Revision `001_wallet_auth` adopts existing auth tables; `002_task_creation` adds tasks. A PostgreSQL advisory lock serializes migration application. Both revisions and their DDL are applied transactionally. Frozen schema definitions prevent later model changes from rewriting these initial migrations.

Feature 3 must explicitly migrate the initial-status constraint when adding new lifecycle states.

## Verification

- PostgreSQL tests cover ownership, invalid/forbidden fields, full uint256 precision, Unicode normalization, stored snapshot/hash reproduction, idempotent and conflicting requests, and concurrent duplicate creation.
- Migration regression preserves existing users and live sessions and allows task creation after the upgrade.
- Frontend tests cover exact MON conversion, rejection of rounding/exponents, tampered metadata, and stale-session API responses.
- `node tests/live-task.mjs` exercises browser-compatible viem signing through the running frontend proxy/API/PostgreSQL, then saves, rehashes, retries, and reloads a task.
- Browser automation has no connected browser, so rendered layout and real extension interaction require manual acceptance.

No feature-3 contracts, payment transactions, AI calls, or Docker execution are included.


## Deleting an unfunded task

On a saved task, choose **Delete task** and confirm. Only the wallet that created the task can delete it, and only while its status is **Awaiting funding**. No wallet transaction or payment is involved.

After deletion, its saved link no longer opens the task. The database keeps the original details and a deletion timestamp for traceability (a soft delete). There is no restore button. Retrying an old save request cannot bring it back; you can create a new task instead. Funded or later-stage tasks cannot use this action.

Technical details: `DELETE /api/v1/tasks/{uuid}` returns 204 on success or an owner retry, 404 for missing tasks or another wallet, and 409 for a non-awaiting status. GET hides deleted tasks; creation replay returns 410 for a deleted request. Run `python -m app.db` to apply revision `003_task_deletion`, which adds nullable `deleted_at` without changing metadata hashes. Future funding and execution transitions must check `deleted_at IS NULL` atomically along with the expected status.
