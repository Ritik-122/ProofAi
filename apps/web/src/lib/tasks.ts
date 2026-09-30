import { keccak256, parseEther, stringToHex } from 'viem';

export type Template = { id: string; name: string; repositoryUrl: string; repositoryRevision: string;
  language: string; suggestedTitle: string; suggestedDescription: string;
  verificationPolicy: { id: string; command: string[]; allowedPaths: string[]; requiredTests: string[] } };
export type Task = { id: string; title: string; description: string; rewardWei: string;
  status: 'AWAITING_FUNDING'; taskHash: string; createdAt: string; creatorWallet: string;
  repository: { id: string; url: string; revision: string }; chainId: string;
  verificationPolicy: Template['verificationPolicy']; canonicalPayload: string; fundingAvailable: false };

export function rewardToWei(input: string): string {
  if (!/^(0|[1-9][0-9]*)(\.[0-9]{1,18})?$/.test(input)) {
    throw new Error('Enter a MON amount with up to 18 decimal places.');
  }
  const wei = parseEther(input);
  if (wei <= 0n || wei > 2n ** 256n - 1n) throw new Error('Enter a positive reward within the supported range.');
  return wei.toString();
}

export function hasValidCommitment(task: Task): boolean {
  return keccak256(stringToHex(task.canonicalPayload)).toLowerCase() === task.taskHash.toLowerCase();
}
