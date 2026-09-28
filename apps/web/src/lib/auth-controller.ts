import { createWalletClient, custom, getAddress, type EIP1193Provider } from 'viem';
import { monadTestnet } from 'viem/chains';
import { authApi, type User } from './api.js';

export const network = monadTestnet;
export type Provider = EIP1193Provider;
export type WalletChoice = { id: string; name: string; provider: Provider };
type State = { address: string | null; chainId: number | null; user: User | null;
  busy: 'connect' | 'switch' | 'sign' | null; error: string | null };

function readableError(error: unknown): string {
  const e = error as { code?: number; shortMessage?: string; message?: string; cause?: { code?: number } };
  if (e?.code === 4001 || e?.cause?.code === 4001) return 'Request declined in your wallet. You can try again when ready.';
  if (e?.code === -32002 || e?.cause?.code === -32002) return 'A request is already open. Check your wallet extension.';
  return e?.shortMessage ?? e?.message ?? 'Wallet request failed. Please try again.';
}

export class AuthController {
  private state: State = { address: null, chainId: null, user: null, busy: null, error: null };
  private listeners = new Set<() => void>();
  private provider: Provider | null = null;
  private token: string | null = null;
  private epoch = 0;
  private expiryTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(private api = authApi) {}
  snapshot = () => this.state;
  subscribe = (fn: () => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  private set(patch: Partial<State>) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach(fn => fn());
  }
  private clearSession() {
    clearTimeout(this.expiryTimer);
    const old = this.token;
    this.token = null;
    this.set({ user: null });
    // Clear locally immediately; server expiry is the fallback if logout cannot reach it.
    if (old) void this.api.logout(old).catch(() => undefined);
  }
  private accountsChanged = (accounts: string[]) => {
    this.epoch++;
    this.clearSession();
    this.set({ address: accounts[0] ? getAddress(accounts[0]) : null, busy: null, error: null });
  };
  private chainChanged = (chain: string) => {
    this.epoch++;
    this.clearSession();
    this.set({ chainId: Number(chain), busy: null, error: null });
  };
  private disconnected = () => this.disconnect();
  private detach() {
    this.provider?.removeListener('accountsChanged', this.accountsChanged);
    this.provider?.removeListener('chainChanged', this.chainChanged);
    this.provider?.removeListener('disconnect', this.disconnected);
  }

  async connect(provider: Provider) {
    if (this.state.busy) return;
    this.detach();
    this.clearSession();
    this.provider = provider;
    const epoch = ++this.epoch;
    this.set({ address: null, chainId: null, busy: 'connect', error: null });
    try {
      const client = createWalletClient({ transport: custom(provider) });
      const accounts = await client.requestAddresses();
      const chainId = await client.getChainId();
      if (epoch !== this.epoch) return;
      if (!accounts[0]) throw new Error('Your wallet did not provide an account. Unlock it and try again.');
      this.set({ address: getAddress(accounts[0]), chainId });
      provider.on('accountsChanged', this.accountsChanged);
      provider.on('chainChanged', this.chainChanged);
      provider.on('disconnect', this.disconnected);
    } catch (error) {
      if (epoch === this.epoch) this.set({ error: readableError(error) });
    } finally {
      if (epoch === this.epoch) this.set({ busy: null });
    }
  }

  async switchNetwork() {
    if (!this.provider || this.state.busy) return;
    const provider = this.provider;
    this.set({ busy: 'switch', error: null });
    try {
      const client = createWalletClient({ transport: custom(provider) });
      try { await client.switchChain({ id: network.id }); }
      catch (error) {
        const e = error as { code?: number; cause?: { code?: number } };
        if (e.code !== 4902 && e.cause?.code !== 4902) throw error;
        await client.addChain({ chain: network });
        await client.switchChain({ id: network.id });
      }
      const chainId = await client.getChainId();
      if (provider === this.provider) {
        this.clearSession();
        this.set({ chainId });
        if (chainId !== network.id) throw new Error('Select Monad Testnet in your wallet to continue.');
      }
    } catch (error) {
      if (provider === this.provider) this.set({ error: readableError(error) });
    } finally {
      if (provider === this.provider) this.set({ busy: null });
    }
  }

  async signIn() {
    if (!this.provider || !this.state.address || this.state.busy || this.state.chainId !== network.id) return;
    const provider = this.provider;
    const address = getAddress(this.state.address);
    const epoch = ++this.epoch;
    this.set({ busy: 'sign', error: null });
    let issuedToken: string | undefined;
    try {
      const client = createWalletClient({ transport: custom(provider) });
      const challenge = await this.api.nonce(address);
      if (epoch !== this.epoch) return;
      if (challenge.chainId !== network.id) throw new Error('The API and wallet network settings do not match.');
      const signature = await client.signMessage({ account: address, message: challenge.message });
      if (epoch !== this.epoch) return;
      const accounts = await client.getAddresses();
      const chainId = await client.getChainId();
      if (epoch !== this.epoch) return;
      if (accounts[0]?.toLowerCase() !== address.toLowerCase() || chainId !== network.id) {
        throw new Error('Your wallet account or network changed. Reconnect and try again.');
      }
      const result = await this.api.verify(address, challenge.challengeId, signature);
      issuedToken = result.accessToken;
      const user = await this.api.me(issuedToken);
      if (epoch !== this.epoch) return;
      if (user.walletAddress.toLowerCase() !== address.toLowerCase() || user.chainId !== network.id) {
        throw new Error('The authenticated account does not match your connected wallet.');
      }
      this.token = issuedToken;
      issuedToken = undefined;
      this.set({ user });
      this.expiryTimer = setTimeout(() => {
        this.epoch++;
        this.clearSession();
        this.set({ busy: null, error: 'Your session expired. Sign in again to continue.' });
      }, Math.max(0, Date.parse(result.expiresAt) - Date.now()));
    } catch (error) {
      if (epoch === this.epoch) this.set({ error: readableError(error) });
    } finally {
      if (issuedToken) void this.api.logout(issuedToken).catch(() => undefined);
      if (epoch === this.epoch) this.set({ busy: null });
    }
  }

  disconnect() {
    this.epoch++;
    this.detach();
    this.provider = null;
    this.clearSession();
    this.set({ address: null, chainId: null, busy: null, error: null });
  }
}

export function discoverWallets(onWallet: (wallet: WalletChoice) => void): () => void {
  const announce = (event: Event) => {
    const detail = (event as CustomEvent).detail;
    if (detail?.info?.uuid && typeof detail.info.name === 'string' && detail.provider?.request) {
      onWallet({ id: detail.info.uuid, name: detail.info.name, provider: detail.provider });
    }
  };
  window.addEventListener('eip6963:announceProvider', announce);
  window.dispatchEvent(new Event('eip6963:requestProvider'));
  const fallback = setTimeout(() => {
    const provider = (window as unknown as { ethereum?: Provider }).ethereum;
    if (provider) onWallet({ id: 'injected', name: 'Browser wallet', provider });
  }, 300);
  return () => { clearTimeout(fallback); window.removeEventListener('eip6963:announceProvider', announce); };
}
