# ProofAI

AI performs the work. Deterministic software verifies it. Monad records and settles the verified outcome.

## Implemented features: wallet sign-in and task creation

This feature includes a responsive Stitch-inspired wallet-access screen, browser-wallet discovery (EIP-6963 with injected-wallet fallback), Monad Testnet switching, signed login challenges, protected API identity, and logout.

Authentication supports ordinary EOA browser wallets. Smart-contract wallet signatures and WalletConnect are not implemented. A network check guides the UI; a login signature proves account ownership, not the wallet's currently selected network.

After signing in, create an unfunded task using the bundled Python access-control demo. Enter requirements and a proposed MON reward, then select **Save task**. The saved page shows the task's metadata hash and checks it in the browser. Retain the page URL to return after a refresh and new sign-in.

Funding, agent execution, and settlement are not implemented. The earlier `contracts/` files remain preliminary and are not deployed or used here.

## Local development on Windows

Prerequisites: Node 22 (the current setup was tested with 22.11), Python 3.12+ (tested with 3.14), and PostgreSQL. Commands below use PowerShell from this repository root.

### API

```powershell
cd apps/api
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
.venv/Scripts/python.exe -m pip install --no-deps -e .
```

For an existing database, copy `.env.example` to `.env`, set `DATABASE_URL`, and generate a random `JWT_SECRET` using the command in that file. The example secret is intentionally rejected. `APP_ORIGIN` must exactly match the frontend origin.

For the project-local database configured during development, `.env` is already generated. Start it from the repository root if necessary:

```powershell
./scripts/local-db.ps1 start
```

Then, from `apps/api`:

```powershell
.venv/Scripts/python.exe -m app.db
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

`app.db` explicitly applies numbered, transactional migrations. It adopts the existing authentication tables and adds tasks without resetting users or sessions. Re-running it is safe. API startup never changes schema. Keep the repository's `demo/python-access` directory alongside `apps/` when deploying; task creation reads only those fixed bundled files.

### Frontend

In a second terminal:

```powershell
cd apps/web
npm.cmd ci
npm.cmd run dev
```

Open **http://localhost:5173** in a browser with an EVM wallet extension. Vite proxies `/api` to port 8000. Use `localhost`, matching `APP_ORIGIN`, rather than `127.0.0.1` in the browser. Production hosting must similarly route `/api` to FastAPI and use HTTPS.

### Project-local PostgreSQL

Official Windows binaries are downloaded from [EDB](https://www.enterprisedb.com/download-postgresql-binaries), as linked by [PostgreSQL](https://www.postgresql.org/download/windows/). Extract the archive so `pg_ctl.exe` resides at `.local/pgsql/bin/pg_ctl.exe`, then run:

```powershell
apps/api/.venv/Scripts/python.exe scripts/setup-local-db.py
```

The setup binds only to `127.0.0.1:55432`, uses SCRAM password authentication, and creates `proofai_dev` and `proofai_test` with a non-superuser application role. Binaries, data, admin credentials, and logs remain in ignored `.local/`; application credentials remain in ignored `apps/api/.env`. It does not install a Windows service or start on boot. Do not delete `.local/` unless you intend to discard these databases.

```powershell
./scripts/local-db.ps1 status
./scripts/local-db.ps1 stop
```

## Verification

From `apps/api`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe tests/run_postgres.py
```

The first command uses an in-memory SQLite fixture for fast endpoint tests; application runtime still requires PostgreSQL. The second runs against local PostgreSQL, including concurrent signature replay. Tests create unique temporary schemas inside `proofai_test` and remove only those schemas. For another dedicated test database, set `TEST_DATABASE_URL` and run pytest instead.

From `apps/web`:

```powershell
npm.cmd test
npm.cmd run build
```

With the API running, `node tests/live-auth.mjs` checks real viem signatures against the local API and database. It creates one throwaway wallet identity in development data, never submits a transaction, and prints no keys or tokens.

For task creation, run `node tests/live-task.mjs` with both local servers running. It saves a task with a throwaway wallet identity in the development database and checks hash reproduction, exact reward storage, retries, and retrieval. It sends no blockchain transaction.

Validation includes PostgreSQL API tests (authentication, task ownership, concurrent replay and concurrent creation), frontend controller/reward/hash tests, the production build, and live signature/task integration checks. Browser automation is unavailable, so visual browser review and a real extension confirmation still require manual checks.

Manual wallet acceptance:

1. Connect an unlocked wallet; the displayed address must match.
2. If on another chain, switch to Monad Testnet; declining remains recoverable.
3. Sign the ProofAI message. No transaction or spending approval should appear.
4. The screen shows the verified account and session expiry.
5. Change account/network or disconnect: the session clears.
6. Sign out, then reload: a new signature is required.
7. With no extension or an unavailable API, the page provides an actionable error.

Manual task-creation acceptance:

1. Sign in and choose **Use demo instructions**, or enter your own title and requirements.
2. Set a positive reward. Inputs with more than 18 decimal places are rejected rather than rounded.
3. Select **Save task**. The result must say awaiting funding, with no wallet transaction.
4. Confirm that the metadata hash matches, then reload and sign in again. The saved URL must reopen the task.
5. Switch wallets: the other wallet cannot read the saved task.
6. Select **Create another task** to return to a fresh form.

Task drafts and retry identifiers use wallet-scoped browser session storage; JWTs remain memory-only. No draft data is shared with an AI provider in this feature.

## Authentication behavior

- Five-minute challenges bind the exact configured origin, chain, checksum address, random nonce, timestamps, and request ID. The client signs the server's exact EIP-191 message.
- `challengeId` is required in `/auth/verify` to distinguish replaced messages. A database compare-and-consume update prevents replay, including concurrent requests.
- A five-second per-wallet nonce cooldown avoids accidental repeated prompts. Add deployment-level IP rate limiting before exposing the API publicly.
- Thirty-minute JWTs are restricted by issuer, audience, chain, and a persisted session ID. Logout revokes that session. Tokens stay in memory, not local storage; refresh requires signing in again.
- Account/network changes invalidate in-flight login results. Late issued tokens are revoked. If the API is unreachable during logout, the local token is cleared immediately and the server session expires normally.
- `GET /api/v1/auth/me` demonstrates protected API access; connecting a wallet alone never authenticates a request.

API routes: `POST /auth/nonce`, `POST /auth/verify`, `GET /auth/me`, `POST /auth/logout`, under `/api/v1`. `/api/v1/health` is process liveness only, not a database readiness check.

Task routes: authenticated `GET /tasks/templates`, `POST /tasks` (UUID `Idempotency-Key` header required), and owner-only `GET /tasks/{uuid}`. The creation body contains `title`, `description`, `templateId`, `repositoryRevision`, and `rewardWei` as a decimal integer string. Repository and verification configuration are server-owned. [Feature 2 details](docs/Feature%202%20-%20Task%20Creation.md) describe canonical hashing and the funding boundary.

Implementation references: [viem signing](https://viem.sh/docs/actions/wallet/signMessage), [ERC-4361 message fields](https://eips.ethereum.org/EIPS/eip-4361), [Monad network information](https://docs.monad.xyz/developer-essentials/testnet).
