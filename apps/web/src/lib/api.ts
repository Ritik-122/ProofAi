export type Challenge = { challengeId: string; message: string; expiresAt: string; chainId: number };
export type Token = { accessToken: string; expiresAt: string };
export type User = { id: string; walletAddress: string; chainId: number; expiresAt: string };

export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); }
}

export async function api<T>(path: string, body?: unknown, token?: string, extraHeaders: Record<string, string> = {}, method?: 'DELETE'): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: method ?? (body === undefined ? 'GET' : 'POST'),
      headers: { ...extraHeaders, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new Error('Cannot reach ProofAI. Check that the API is running and try again.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.error?.message ?? 'ProofAI could not complete this request. Please try again.', response.status, data?.error?.code);
  }
  return response.status === 204 ? undefined as T : response.json();
}

export const authApi = {
  nonce: (walletAddress: string) => api<Challenge>('/auth/nonce', { walletAddress }),
  verify: (walletAddress: string, challengeId: string, signature: string) =>
    api<Token>('/auth/verify', { walletAddress, challengeId, signature }),
  me: (token: string) => api<User>('/auth/me', undefined, token),
  logout: (token: string) => api<void>('/auth/logout', {}, token),
};
