import { test } from 'node:test';
import assert from 'node:assert/strict';
import { privateKeyToAccount } from 'viem/accounts';
import { AuthController, network, type Provider } from '../src/lib/auth-controller.js';
import type { Challenge, Token, User } from '../src/lib/api.js';

const account = privateKeyToAccount(`0x${'1'.repeat(64)}`);
const other = privateKeyToAccount(`0x${'2'.repeat(64)}`);
const expiry = () => new Date(Date.now() + 60000).toISOString();

function fixture() {
  let chain = network.id as number;
  let addresses = [account.address];
  const events = new Map<string, Set<(...args: any[]) => void>>();
  let reject = false;
  let sign: () => Promise<string> = () => account.signMessage({ message: 'test challenge' });
  const provider = {
    request: async ({ method, params }: { method: string; params?: any }) => {
      if (reject) throw { code: 4001, message: 'User rejected' };
      if (method === 'eth_requestAccounts' || method === 'eth_accounts') return addresses;
      if (method === 'eth_chainId') return `0x${chain.toString(16)}`;
      if (method === 'personal_sign') return sign();
      if (method === 'wallet_switchEthereumChain') {
        chain = Number(params[0].chainId);
        events.get('chainChanged')?.forEach(fn => fn(params[0].chainId));
        return null;
      }
      throw new Error(`Unexpected method ${method}`);
    },
    on: (event: string, fn: (...args: any[]) => void) => {
      if (!events.has(event)) events.set(event, new Set());
      events.get(event)!.add(fn);
    },
    removeListener: (event: string, fn: (...args: any[]) => void) => { events.get(event)?.delete(fn); },
  } as unknown as Provider;
  let verifies = 0;
  let logouts = 0;
  const api = {
    nonce: async (): Promise<Challenge> => ({ challengeId: 'challenge', message: 'test challenge', expiresAt: expiry(), chainId: network.id }),
    verify: async (): Promise<Token> => { verifies++; return { accessToken: 'token', expiresAt: expiry() }; },
    me: async (): Promise<User> => ({ id: 'user', walletAddress: account.address, chainId: network.id, expiresAt: expiry() }),
    logout: async () => { logouts++; },
  };
  const controller = new AuthController(api);
  return { controller, provider, api, get verifies() { return verifies; }, get logouts() { return logouts; },
    reject: () => { reject = true; }, setChain: (id: number) => { chain = id; },
    changeAccount: () => { addresses = [other.address]; events.get('accountsChanged')?.forEach(fn => fn(addresses)); },
    setSign: (fn: () => Promise<string>) => { sign = fn; },
  };
}

test('connect, sign in, authenticate, and disconnect', async () => {
  const f = fixture();
  await f.controller.connect(f.provider);
  assert.equal(f.controller.snapshot().address, account.address);
  await f.controller.signIn();
  assert.equal(f.controller.snapshot().user?.walletAddress, account.address);
  f.controller.disconnect();
  assert.equal(f.controller.snapshot().user, null);
  assert.equal(f.logouts, 1);
});

test('wrong network prevents login until switched', async () => {
  const f = fixture(); f.setChain(1);
  await f.controller.connect(f.provider);
  await f.controller.signIn();
  assert.equal(f.verifies, 0);
  await f.controller.switchNetwork();
  assert.equal(f.controller.snapshot().chainId, network.id);
  await f.controller.signIn();
  assert.equal(f.verifies, 1);
  f.controller.disconnect();
});

test('declined connection shows recoverable error', async () => {
  const f = fixture(); f.reject();
  await f.controller.connect(f.provider);
  assert.match(f.controller.snapshot().error!, /declined/);
  assert.equal(f.controller.snapshot().busy, null);
});

test('account change clears authenticated session', async () => {
  const f = fixture();
  await f.controller.connect(f.provider); await f.controller.signIn();
  f.changeAccount();
  assert.equal(f.controller.snapshot().user, null);
  assert.equal(f.controller.snapshot().address, other.address);
  assert.equal(f.logouts, 1);
  f.controller.disconnect();
});

test('account change while signing discards stale signature', async () => {
  const f = fixture();
  await f.controller.connect(f.provider);
  f.setSign(async () => { f.changeAccount(); return account.signMessage({ message: 'test challenge' }); });
  await f.controller.signIn();
  assert.equal(f.verifies, 0);
  assert.equal(f.controller.snapshot().user, null);
  f.controller.disconnect();
});

test('disconnect while server is verifying revokes late token', async () => {
  const f = fixture();
  await f.controller.connect(f.provider);
  f.api.verify = async () => {
    f.controller.disconnect();
    return { accessToken: 'late-token', expiresAt: expiry() };
  };
  await f.controller.signIn();
  assert.equal(f.controller.snapshot().user, null);
  assert.equal(f.logouts, 1);
});

test('API outage does not authenticate the wallet', async () => {
  const f = fixture(); await f.controller.connect(f.provider);
  f.api.nonce = async () => { throw new Error('API unavailable'); };
  await f.controller.signIn();
  assert.equal(f.controller.snapshot().user, null);
  assert.match(f.controller.snapshot().error!, /API unavailable/);
  f.controller.disconnect();
});

test('protected task request requires authentication', async () => {
  const f = fixture();
  await assert.rejects(f.controller.request('/tasks/templates'), /Sign in/);
});

test('protected request discards a result after account change', async () => {
  const f = fixture();
  await f.controller.connect(f.provider); await f.controller.signIn();
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      f.changeAccount();
      return new Response(JSON.stringify({ id: 'old-wallet-task' }), { status: 200 });
    };
    await assert.rejects(f.controller.request('/tasks/task-id'), /session changed/);
  } finally {
    globalThis.fetch = original;
    f.controller.disconnect();
  }
});


test('delete sends authenticated DELETE and accepts an empty response', async () => {
  const f = fixture();
  await f.controller.connect(f.provider); await f.controller.signIn();
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(url, '/api/v1/tasks/task-id');
      assert.equal(options?.method, 'DELETE');
      assert.ok(new Headers(options?.headers).get('Authorization')?.startsWith('Bearer '));
      assert.equal(options?.body, undefined);
      return new Response(null, { status: 204 });
    };
    assert.equal(await f.controller.request('/tasks/task-id', undefined, undefined, 'DELETE'), undefined);
  } finally {
    globalThis.fetch = original;
    f.controller.disconnect();
  }
});
