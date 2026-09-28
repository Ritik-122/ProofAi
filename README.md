# ProofAI

AI performs the work. Deterministic software verifies it. Monad records and settles the verified outcome.

## Current feature: wallet connection and sign-in

This feature includes a responsive Stitch-inspired wallet-access screen, browser-wallet discovery (EIP-6963 with injected-wallet fallback), Monad Testnet switching, signed login challenges, protected API identity, and logout.

Authentication supports ordinary EOA browser wallets. Smart-contract wallet signatures and WalletConnect are not implemented. A network check guides the UI; a login signature proves account ownership, not the wallet's currently selected network.

No task creation, execution, funding, or settlement is connected to this feature. The earlier `contracts/` files are preliminary work and are not deployed or used here.

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

`app.db` explicitly creates the feature's two tables. API startup never changes schema. Introduce versioned migrations when the next feature changes this schema.

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

Validated during feature-1 implementation: 15 API tests on PostgreSQL (including concurrent replay), 7 frontend controller tests, the production frontend build, and the live signature/API/database smoke test. The browser-control connection was unavailable, so visual browser review and a real extension confirmation still require the manual checks below.

Manual wallet acceptance:

1. Connect an unlocked wallet; the displayed address must match.
2. If on another chain, switch to Monad Testnet; declining remains recoverable.
3. Sign the ProofAI message. No transaction or spending approval should appear.
4. The screen shows the verified account and session expiry.
5. Change account/network or disconnect: the session clears.
6. Sign out, then reload: a new signature is required.
7. With no extension or an unavailable API, the page provides an actionable error.

## Authentication behavior

- Five-minute challenges bind the exact configured origin, chain, checksum address, random nonce, timestamps, and request ID. The client signs the server's exact EIP-191 message.
- `challengeId` is required in `/auth/verify` to distinguish replaced messages. A database compare-and-consume update prevents replay, including concurrent requests.
- A five-second per-wallet nonce cooldown avoids accidental repeated prompts. Add deployment-level IP rate limiting before exposing the API publicly.
- Thirty-minute JWTs are restricted by issuer, audience, chain, and a persisted session ID. Logout revokes that session. Tokens stay in memory, not local storage; refresh requires signing in again.
- Account/network changes invalidate in-flight login results. Late issued tokens are revoked. If the API is unreachable during logout, the local token is cleared immediately and the server session expires normally.
- `GET /api/v1/auth/me` demonstrates protected API access; connecting a wallet alone never authenticates a request.

API routes: `POST /auth/nonce`, `POST /auth/verify`, `GET /auth/me`, `POST /auth/logout`, under `/api/v1`. `/api/v1/health` is process liveness only, not a database readiness check.

Implementation references: [viem signing](https://viem.sh/docs/actions/wallet/signMessage), [ERC-4361 message fields](https://eips.ethereum.org/EIPS/eip-4361), [Monad network information](https://docs.monad.xyz/developer-essentials/testnet).
