# Feature 1 — Wallet connection and sign-in

Scope: wallet identity only. No task, agent, escrow, or settlement operations.

## Delivered

- React/TypeScript/Tailwind wallet access screen using the existing Stitch dark/violet visual direction.
- EIP-6963 wallet discovery and injected-wallet fallback through viem.
- Explicit connect, wrong-network handling, add/switch Monad Testnet, signature prompt, authenticated identity, expiry, and sign-out states.
- FastAPI `/auth/nonce`, `/auth/verify`, `/auth/me`, and `/auth/logout` endpoints.
- PostgreSQL users and revocable authentication sessions.
- Short-lived, origin/chain-bound messages and atomic single-use challenge consumption.
- JWT issuer, audience, chain, expiry, and persisted-session validation.
- In-memory browser tokens and invalidation when the wallet account or network changes.
- Project-local PostgreSQL setup requested by the user, plus setup/start/stop instructions in README.

## API clarification

The original API design returned only `message` from `/nonce`. This feature also returns `challengeId`, `expiresAt`, and `chainId`. `/verify` requires `challengeId` alongside `walletAddress` and `signature`, preventing an old tab's challenge from being confused with a replacement challenge.

Wallets supported: ordinary EOA browser wallets. Contract-wallet signature validation is deferred. Network identity is embedded in the sign-in challenge; the wallet's active network itself cannot be attested by a personal signature.

## Validation

- 15 PostgreSQL API tests passed, including replay, concurrent replay, expiration, wrong signer, tampered message, cross-origin rejection, token validation, and revocation.
- 7 frontend controller tests passed, including declined requests, wrong network, account changes, stale signatures, late token revocation, and API outage.
- TypeScript checking and Vite production build passed.
- Live viem-to-FastAPI-to-PostgreSQL signature smoke test passed.
- Frontend and API proxy returned HTTP 200 locally.
- Browser automation was unavailable. Rendered layout and real wallet extension prompts need manual acceptance in the user's browser.

## Local services

- Frontend: http://localhost:5173
- API documentation: http://127.0.0.1:8000/docs
- PostgreSQL: 127.0.0.1:55432, development database `proofai_dev`, isolated test database `proofai_test`.

Credentials and database files are ignored by Git. No smart contract was deployed. Feature 2 requires the user's next approval.
