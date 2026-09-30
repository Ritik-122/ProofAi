import { useEffect, useState, useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './lib/api';
import { AuthController, discoverWallets, network, type WalletChoice } from './lib/auth-controller';
import { TaskWorkspace } from './TaskWorkspace';

function Mark({ small = false }: { small?: boolean }) {
  return <svg width={small ? 26 : 48} height={small ? 26 : 48} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M24 3 42 13v22L24 45 6 35V13L24 3Z" stroke="#818cf8" strokeWidth="2" />
    <path d="m16 24 6 6 11-13" stroke="#e3e2e8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}

export function App() {
  const [controller] = useState(() => new AuthController());
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot);
  const [wallets, setWallets] = useState<WalletChoice[]>([]);
  const [selected, setSelected] = useState('');
  const health = useQuery({ queryKey: ['health'], queryFn: () => api<{ status: string }>('/health'), staleTime: 30000 });
  useEffect(() => {
    const stop = discoverWallets(wallet => setWallets(previous => {
      if (previous.some(item => item.provider === wallet.provider || item.id === wallet.id)) return previous;
      return [...previous, wallet];
    }));
    return () => { stop(); controller.disconnect(); };
  }, [controller]);
  const wallet = wallets.find(item => item.id === selected) ?? wallets[0];
  const onNetwork = state.chainId === network.id;
  const authenticated = !!state.user;
  const steps = [
    { title: 'Connect your wallet', detail: 'Choose the account you’ll use on ProofAI.', done: !!state.address },
    { title: 'Select Monad Testnet', detail: 'Your workspace runs on the Monad network.', done: !!state.address && onNetwork },
    { title: 'Verify ownership', detail: 'Sign a message to securely start your session.', done: authenticated },
  ];

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="topbar">
      <a className="brand" href="/" aria-label="ProofAI home"><Mark small /><span>Proof<span className="brand-ai">AI</span></span></a>
      <span className="environment">MONAD TESTNET</span>
      <div className="header-right"><span className="network-label"><i className="dot" /> Monad Testnet</span><span className="header-divider" /><span className="muted text-sm">Your agent. Verified.</span></div>
    </header>
    <main id="main" className="main">
      {authenticated ? <TaskWorkspace key={state.user!.id} controller={controller} wallet={state.user!.walletAddress} /> : <>
      <div className="eyebrow"><span className="tiny-square" /> PROOFAI WORKSPACE <span className="slash">/</span> WALLET ACCESS</div>
      <div className="access-grid">
        <section className="intro">
          <span className="overline">TRUST STARTS WITH PROOF</span>
          <h1>{authenticated ? <>You’re connected.<br /><span>Identity verified.</span></> : <>Your work.<br />Your wallet.<br /><span>Verified.</span></>}</h1>
          <p className="intro-copy">A workspace for AI coding tasks, independent verification, and on-chain settlement. Connect your wallet to get started.</p>
          <div className="steps">{steps.map((step, index) => <div className={`step ${step.done ? 'step-done' : ''}`} key={step.title}>
            <div className="step-number">{step.done ? '✓' : `0${index + 1}`}</div><div><h2>{step.title}</h2><p>{step.detail}</p></div>
          </div>)}</div>
          <div className="trust-note"><svg width="18" height="20" viewBox="0 0 18 20" fill="none" aria-hidden="true"><path d="m9 1 7 3v6c0 4-7 9-7 9S2 14 2 10V4l7-3Z" stroke="currentColor" /><path d="m5 9 3 3 5-5" stroke="currentColor" /></svg><span>Your keys stay in your wallet. Signing in costs no gas.</span></div>
        </section>
        <section className="access-card" aria-labelledby="access-title">
          <div className="card-top"><span className="overline">SECURE ACCESS</span><span className={`badge ${authenticated ? 'success' : ''}`}>{authenticated ? '● VERIFIED' : '○ NOT SIGNED IN'}</span></div>
          <div className="card-body">
            <div className="mark-tile"><Mark /></div>
            <h2 id="access-title">{authenticated ? 'Welcome to ProofAI' : 'Connect to ProofAI'}</h2>
            <p className="card-copy">{authenticated ? 'Your wallet ownership has been verified. Your session is now active.' : 'Use your browser wallet to establish your identity. You’ll then sign a short login message.'}</p>
            {state.address ? <div className="account-box"><span className="overline">CONNECTED ACCOUNT</span><span className="wallet-address">{state.address}</span><div className="account-network"><span className={`dot ${onNetwork ? '' : 'warning-dot'}`} />{onNetwork ? 'Monad Testnet' : `Wrong network · Chain ${state.chainId}`}</div></div> : <div className="wallet-field"><label htmlFor="wallet">Browser wallet</label>{wallets.length > 0 ? <select id="wallet" value={wallet?.id ?? ''} onChange={event => setSelected(event.target.value)} disabled={!!state.busy}>{wallets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select> : <div className="empty-wallet">No browser wallet detected.<p>Open this page in a browser with an EVM wallet extension, then refresh.</p></div>}</div>}
            {state.error && <p className="error-box" role="alert">{state.error}</p>}
            {authenticated ? <div className="session-box" role="status"><span className="check-circle">✓</span><div><strong>Signed in successfully</strong><p>Session ends at {new Date(state.user!.expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.</p></div></div> : <button className="primary-button" disabled={!!state.busy || (!state.address && !wallet)} onClick={() => {
              if (!state.address && wallet) void controller.connect(wallet.provider);
              else if (!onNetwork) void controller.switchNetwork();
              else void controller.signIn();
            }}>{state.busy ? <><span className="spinner" />{state.busy === 'sign' ? 'Confirm in your wallet…' : state.busy === 'switch' ? 'Switching network…' : 'Connecting…'}</> : !state.address ? <>Connect wallet <span>↗</span></> : !onNetwork ? 'Switch to Monad Testnet' : <>Sign in with wallet <span>→</span></>}</button>}
            {state.address && <button className="secondary-button" onClick={() => controller.disconnect()}>{authenticated ? 'Sign out & disconnect' : 'Disconnect wallet'}</button>}
            <p className="signing-note">{authenticated ? 'For your security, refreshing this page requires a new sign-in.' : 'A login signature confirms wallet ownership. It does not move funds or approve spending.'}</p>
          </div>
          <div className="card-bottom"><span className="lock-icon">◇</span> WALLET SIGNATURE AUTHENTICATION <span className="mono">EIP-191</span></div>
        </section>
      </div>
      <div className="principle"><span className="overline">THE PROOFAI PRINCIPLE</span><p>AI performs the work.<span> Software verifies it.</span> Monad records the outcome.</p><span className="principle-arrow" aria-hidden="true">↗</span></div>
      </>}
    </main>
    <footer><span><i className={`dot ${health.isSuccess ? '' : 'neutral-dot'}`} />{health.isSuccess ? 'API connected' : health.isPending ? 'Checking API…' : 'API unavailable'}</span><span className="footer-right">ProofAI <span className="slash">/</span> Built for verifiable work</span></footer>
  </div>;
}
