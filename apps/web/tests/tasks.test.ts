import { test } from 'node:test';
import assert from 'node:assert/strict';
import { keccak256, stringToHex } from 'viem';
import { hasValidCommitment, rewardToWei, type Task } from '../src/lib/tasks.js';

test('reward conversion preserves all 18 decimals', () => {
  assert.equal(rewardToWei('0.100000000000000001'), '100000000000000001');
  assert.equal(rewardToWei('0.000000000000000001'), '1');
  assert.equal(rewardToWei('9007199254740993'), '9007199254740993000000000000000000');
});

test('reward conversion rejects rounding, exponents and invalid amounts', () => {
  for (const value of ['0', '-1', '1e3', '0.0000000000000000001', '1,000', 'NaN', '', '.1', '01', '1.', '9'.repeat(80)]) {
    assert.throws(() => rewardToWei(value), /Enter/, value);
  }
});

test('altered task metadata fails hash verification', () => {
  const canonicalPayload = '{"description":"Fix café access","version":1}';
  const task = { canonicalPayload, taskHash: keccak256(stringToHex(canonicalPayload)) } as Task;
  assert.equal(hasValidCommitment(task), true);
  assert.equal(hasValidCommitment({ ...task, canonicalPayload: canonicalPayload.replace('Fix', 'Skip') }), false);
});
