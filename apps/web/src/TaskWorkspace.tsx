import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { formatEther } from 'viem';
import { AuthController } from './lib/auth-controller';
import { ApiError } from './lib/api';
import { hasValidCommitment, rewardToWei, type Task, type Template } from './lib/tasks';

type Draft = { title: string; description: string; reward: string; requestId: string; repositoryRevision?: string };
const newDraft = (): Draft => ({ title: '', description: '', reward: '0.1', requestId: crypto.randomUUID() });

function initialDraft(key: string): Draft {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? 'null');
    if (value && ['title', 'description', 'reward', 'requestId'].every(k => typeof value[k] === 'string')) return value;
  } catch { /* Storage may be disabled. The form still works for this page lifetime. */ }
  return newDraft();
}

function selectedTask(): string | null {
  const match = location.hash.match(/^#\/tasks\/([0-9a-f-]{36})$/i);
  return match?.[1] ?? null;
}

export function TaskWorkspace({ controller, wallet }: { controller: AuthController; wallet: string }) {
  const [taskId, setTaskId] = useState(selectedTask);
  useEffect(() => {
    const changed = () => setTaskId(selectedTask());
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  return <div className="task-workspace">
    <div className="workspace-toolbar"><span className="eyebrow">WORKSPACE <span className="slash">/</span> {taskId ? 'SAVED TASK' : 'CREATE TASK'}</span><button className="text-button" onClick={() => controller.disconnect()}>Sign out</button></div>
    {taskId ? <SavedTask key={taskId} controller={controller} id={taskId} wallet={wallet} /> : <CreateTaskForm controller={controller} wallet={wallet} onCreated={task => { location.hash = `/tasks/${task.id}`; setTaskId(task.id); }} />}
  </div>;
}

function CreateTaskForm({ controller, wallet, onCreated }: { controller: AuthController; wallet: string; onCreated: (task: Task) => void }) {
  const storageKey = `proofai:task-draft:${wallet.toLowerCase()}`;
  const [draft, setDraft] = useState(() => initialDraft(storageKey));
  const [validation, setValidation] = useState<string | null>(null);
  const attempted = useRef(false);
  const templates = useQuery({ queryKey: ['task-templates', wallet], queryFn: () => controller.request<Template[]>('/tasks/templates'), retry: false });
  const template = templates.data?.[0];
  const create = useMutation({
    mutationFn: (body: { title: string; description: string; templateId: string; repositoryRevision: string; rewardWei: string; requestId: string }) => {
      const { requestId, ...payload } = body;
      return controller.request<Task>('/tasks', payload, requestId);
    },
    onSuccess: task => {
      try { sessionStorage.removeItem(storageKey); } catch { /* Optional browser storage. */ }
      onCreated(task);
    },
  });
  useEffect(() => {
    try { sessionStorage.setItem(storageKey, JSON.stringify(draft)); } catch { /* Optional browser storage. */ }
  }, [draft, storageKey]);
  function edit(patch: Partial<Draft>) {
    setDraft(previous => ({ ...previous, ...patch, requestId: crypto.randomUUID(), repositoryRevision: undefined }));
    attempted.current = false;
    create.reset(); setValidation(null);
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!template || create.isPending) return;
    try {
      if (!draft.title.trim() || !draft.description.trim()) throw new Error('Add a title and clear task requirements.');
      const rewardWei = rewardToWei(draft.reward);
      const revision = draft.repositoryRevision ?? template.repositoryRevision;
      const submitted = { ...draft, repositoryRevision: revision };
      // Persist before sending, so a lost response can be retried with the same request key.
      setDraft(submitted);
      try { sessionStorage.setItem(storageKey, JSON.stringify(submitted)); } catch { /* Optional browser storage. */ }
      attempted.current = true;
      create.mutate({ title: draft.title, description: draft.description, templateId: template.id,
        repositoryRevision: revision, rewardWei, requestId: draft.requestId });
    } catch (error) { setValidation((error as Error).message); }
  }
  let displayReward = '—';
  try { displayReward = `${formatEther(BigInt(rewardToWei(draft.reward)))} MON`; } catch { /* Show an unset summary for invalid input. */ }

  return <>
    <div className="task-heading"><span className="overline">DEFINE THE WORK. SET THE REWARD.</span><h1>Create a coding task</h1><p>Describe the fix, choose the supported repository, and save your task before funding.</p></div>
    <form onSubmit={submit} className="task-grid">
      <div className="task-sections">
        <section className="task-panel"><h2><span className="section-index">01</span> Task details</h2>
          <label htmlFor="task-title">Task title</label><input id="task-title" required maxLength={200} value={draft.title} disabled={create.isPending} onChange={e => edit({ title: e.target.value })} placeholder="e.g. Fix workspace access permissions" />
          <div className="field-caption"><label htmlFor="task-description">Requirements & acceptance criteria</label><span>{draft.description.length.toLocaleString()} / 10,000</span></div>
          <textarea id="task-description" required maxLength={10000} rows={7} value={draft.description} disabled={create.isPending} onChange={e => edit({ description: e.target.value })} placeholder="Explain the expected behavior and what needs to be fixed." />
          {template && <button className="text-button" type="button" disabled={create.isPending} onClick={() => edit({ title: template.suggestedTitle, description: template.suggestedDescription })}>Use demo instructions ↗</button>}
        </section>
        <section className="task-panel"><h2><span className="section-index">02</span> Repository</h2>
          {templates.isPending ? <p role="status" className="muted">Loading the supported repository…</p> : templates.isError ? <><p role="alert" className="error-box">{templates.error.message}</p><button type="button" className="text-button" onClick={() => void templates.refetch()}>Retry loading</button></> : template ? <>
            <label htmlFor="repository">Supported demo repository</label><select id="repository" value={template.id} disabled={create.isPending} onChange={() => undefined}><option value={template.id}>{template.name} · Python</option></select>
            <p className="field-help">A small bundled project with an intentional access-control bug. Its exact contents are saved with your task.</p>
            <details><summary>Repository version</summary><code className="hash-text">{template.repositoryRevision}</code></details>
          </> : <p className="error-box">No supported repository is configured.</p>}
        </section>
        <section className="task-panel"><h2><span className="section-index">03</span> Verification criteria</h2><div className="policy-card"><span className="policy-icon">✓</span><div><strong>Protected automated tests</strong><p>The planned verifier will check the full test suite in an isolated Docker environment. This step only saves the task.</p></div><span className="badge">DETERMINISTIC</span></div>
          {template && <p className="field-help">{template.verificationPolicy.requiredTests.length} required tests · Allowed change: {template.verificationPolicy.allowedPaths.join(', ')}</p>}
        </section>
        <section className="task-panel"><h2><span className="section-index">04</span> Reward</h2><label htmlFor="reward">Proposed task reward</label><div className="reward-input"><input id="reward" required inputMode="decimal" autoComplete="off" maxLength={80} value={draft.reward} disabled={create.isPending} onChange={e => edit({ reward: e.target.value })} aria-describedby="reward-help" /><span>MON</span></div><p id="reward-help" className="field-help">Greater than zero, with up to 18 decimal places. No funds move when you save.</p>
          <div className="reward-presets">{['0.1', '0.5', '1'].map(amount => <button type="button" disabled={create.isPending} key={amount} onClick={() => edit({ reward: amount })}>{amount} MON</button>)}</div>
        </section>
      </div>
      <aside className="task-summary"><div className="task-panel"><h2>Task summary <span className="badge">UNFUNDED</span></h2><dl><div><dt>Proposed reward</dt><dd className="summary-reward">{displayReward}</dd></div><div><dt>Repository</dt><dd>{template?.name ?? 'Loading…'}</dd></div><div><dt>Network</dt><dd>Monad Testnet</dd></div><div><dt>Escrow balance</dt><dd>Not funded</dd></div><div><dt>Agent assignment</dt><dd>Not assigned</dd></div></dl>
        <div className="save-explainer"><strong>Save now. Fund later.</strong><p>Your task details and their hash will be saved. Funding and execution are not available in this feature yet.</p></div>
        {(validation || create.error) && <p role="alert" className="error-box">{validation ?? create.error?.message}</p>}
        {create.error instanceof ApiError && create.error.code === 'REPOSITORY_REVISION_CHANGED' && <button className="text-button" type="button" onClick={() => { edit({}); void templates.refetch(); }}>Reload repository version</button>}
        <button className="primary-button" disabled={!template || create.isPending} type="submit">{create.isPending ? 'Saving task…' : attempted.current && create.isError ? 'Retry saving task' : 'Save task'} <span>→</span></button><p className="signing-note">No wallet transaction or gas payment is required.</p>
      </div><p className="summary-note">The task belongs to your signed-in wallet. Only you can view its saved details.</p></aside>
    </form>
  </>;
}

function SavedTask({ controller, id, wallet }: { controller: AuthController; id: string; wallet: string }) {
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => controller.request<void>(`/tasks/${id}`, undefined, undefined, 'DELETE'),
    onSuccess: async () => {
      await queryClient.cancelQueries({ queryKey: ['saved-task', wallet, id] });
      queryClient.removeQueries({ queryKey: ['saved-task', wallet, id] });
    },
  });
  const task = useQuery({ queryKey: ['saved-task', wallet, id], queryFn: () => controller.request<Task>(`/tasks/${id}`), retry: false });
  if (remove.isSuccess) return <section className="task-panel"><h1>Task deleted</h1><p role="status">Your unfunded task has been removed. No funds were moved.</p><a className="secondary-button inline-button" href="#/tasks/new">Create a new task</a></section>;
  if (task.isPending) return <p role="status" className="muted">Loading your saved task…</p>;
  if (task.isError) return <section className="task-panel"><p className="error-box" role="alert">{task.error.message}</p><button className="text-button" onClick={() => void task.refetch()}>Retry</button><a className="secondary-button inline-button" href="#/tasks/new">Create a new task</a></section>;
  const data = task.data;
  const validHash = hasValidCommitment(data);
  return <>
    {data.status === 'AWAITING_FUNDING' && <div className="task-panel">
      <button className="secondary-button" disabled={remove.isPending} onClick={() => {
        if (window.confirm(`Delete "${data.title}"? This cannot be undone. The record will be retained for traceability, but the task will no longer be available.`)) remove.mutate();
      }}>{remove.isPending ? 'Deleting task…' : 'Delete task'}</button>
      {remove.error && <p role="alert" className="error-box">{remove.error.message}</p>}
    </div>}
    <div className="task-heading"><span className="overline">TASK SAVED</span><h1>{data.title}</h1><p>Your requirements are saved. No reward has been deposited and execution has not started.</p></div>
    <div className="task-grid"><div className="task-sections"><section className="task-panel"><h2>Requirements <span className="badge">AWAITING FUNDING</span></h2><p className="saved-description">{data.description}</p></section>
      <section className="task-panel"><h2>Repository & verification</h2><dl className="saved-meta"><dt>Repository</dt><dd>{data.repository.url}</dd><dt>Pinned version</dt><dd className="hash-text">{data.repository.revision}</dd><dt>Required tests</dt><dd>{data.verificationPolicy.requiredTests.length}</dd><dt>Allowed source changes</dt><dd>{data.verificationPolicy.allowedPaths.join(', ')}</dd></dl></section>
      <section className="task-panel"><h2>Task metadata hash</h2><code className="hash-text">{data.taskHash}</code><p className={validHash ? 'hash-valid' : 'error-box'} role="status">{validHash ? '✓ Hash matches the saved metadata.' : 'Hash mismatch. Do not fund this task.'}</p><p className="field-help">This fingerprint covers your saved task details. It is not a verification result or an on-chain receipt.</p><details><summary>Inspect committed metadata</summary><pre className="canonical-preview">{JSON.stringify(JSON.parse(data.canonicalPayload), null, 2)}</pre></details></section></div>
      <aside className="task-summary"><section className="task-panel"><h2>Saved task</h2><dl><div><dt>Proposed reward</dt><dd className="summary-reward">{formatEther(BigInt(data.rewardWei))} MON</dd></div><div><dt>Escrow</dt><dd>Not funded</dd></div><div><dt>Created</dt><dd>{new Date(data.createdAt).toLocaleString()}</dd></div></dl><p className="field-help">Funding will be added in the next feature. Keep this page URL to return after signing in.</p><a className="secondary-button inline-button" href="#/tasks/new">Create another task</a><details><summary>Task ID</summary><code className="hash-text">{data.id}</code></details></section></aside>
    </div>
  </>;
}
