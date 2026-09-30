// Local integration test using a throwaway wallet. No chain transactions are submitted.
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';
import { keccak256, stringToHex } from 'viem';

const account = privateKeyToAccount(generatePrivateKey());
const base = 'http://localhost:5173/api/v1';
let token;
async function request(path, body, key) {
  return fetch(base + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Origin: 'http://localhost:5173', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(key ? { 'Idempotency-Key': key } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(10000),
  });
}
const nonce = await request('/auth/nonce', { walletAddress: account.address });
assert.equal(nonce.status, 200);
const challenge = await nonce.json();
const signature = await account.signMessage({ message: challenge.message });
const login = await request('/auth/verify', { walletAddress: account.address, challengeId: challenge.challengeId, signature });
assert.equal(login.status, 200);
token = (await login.json()).accessToken;
try {
  const catalog = await request('/tasks/templates');
  assert.equal(catalog.status, 200);
  const template = (await catalog.json())[0];
  const body = { title: 'Integration check: fix access rules', description: template.suggestedDescription,
    templateId: template.id, repositoryRevision: template.repositoryRevision, rewardWei: '100000000000000001' };
  const key = randomUUID();
  const created = await request('/tasks', body, key);
  assert.equal(created.status, 201);
  const task = await created.json();
  assert.equal(task.rewardWei, body.rewardWei);
  assert.equal(task.status, 'AWAITING_FUNDING');
  assert.equal(keccak256(stringToHex(task.canonicalPayload)), task.taskHash);
  const retry = await request('/tasks', body, key);
  assert.equal(retry.status, 200);
  assert.equal((await retry.json()).id, task.id);
  const saved = await request(`/tasks/${task.id}`);
  assert.equal(saved.status, 200);
  assert.equal((await saved.json()).taskHash, task.taskHash);
  console.log('PASS: sign in → template → save unfunded task → reproduce hash with viem → retry without duplicate → reload saved task.');
} finally {
  await request('/auth/logout', {});
}
