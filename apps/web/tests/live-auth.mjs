// Explicit local smoke test: creates one throwaway wallet identity, never a transaction.
import assert from 'node:assert/strict';
import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';

const origin = 'http://localhost:5173';
const base = 'http://127.0.0.1:8000/api/v1/auth';
const account = privateKeyToAccount(generatePrivateKey());
async function request(path, body, token) {
  return fetch(base + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Origin: origin, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
  });
}
const nonceResponse = await request('/nonce', { walletAddress: account.address });
assert.equal(nonceResponse.status, 200);
const challenge = await nonceResponse.json();
const signature = await account.signMessage({ message: challenge.message });
const proof = { walletAddress: account.address, challengeId: challenge.challengeId, signature };
const verified = await request('/verify', proof);
assert.equal(verified.status, 200);
const { accessToken } = await verified.json();
const me = await request('/me', undefined, accessToken);
assert.equal(me.status, 200);
assert.equal((await me.json()).walletAddress, account.address);
assert.equal((await request('/verify', proof)).status, 401);
assert.equal((await request('/logout', {}, accessToken)).status, 204);
assert.equal((await request('/me', undefined, accessToken)).status, 401);
console.log('PASS: live viem signature → FastAPI → PostgreSQL → identity → replay rejection → logout revocation.');
