import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Activity,
  BookOpen,
  CheckCircle2,
  Database,
  FileUp,
  Loader2,
  Menu,
  MessageSquareText,
  RotateCcw,
  Send,
  ShieldCheck,
  X,
} from 'lucide-react';

import { clearHistory, getHealth, getHistory, getPlatform, sendChat, uploadProspectus } from './api.js';

const suggestions = [
  'Show the latest available SQL evidence for stock 000001.',
  'Which holdings are ranked highest for fund 510300 in the latest report period?',
  'Summarize the SQL verification trace for a financial lookup.',
];

const fallbackPlatform = {
  session: { label: 'Local demo session', mode: 'no-login', user: 'Local Financial Analyst' },
  system_status: { label: 'SQL-first local financial Agentic RAG', ready: false, status: 'loading' },
  feature_flags: { upload_pdf: false, numeric_confidence: false },
  knowledge_base: {},
  architecture_docs: { available: false, links: [] },
};

export default function App() {
  const [platform, setPlatform] = useState(fallbackPlatform);
  const [health, setHealth] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [docsOpen, setDocsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    let mounted = true;
    Promise.all([getHealth(), getPlatform(), getHistory()])
      .then(([healthPayload, platformPayload, historyPayload]) => {
        if (!mounted) return;
        setHealth(healthPayload);
        setPlatform(platformPayload);
        setMessages(historyPayload.messages || []);
      })
      .catch((error) => {
        if (mounted) setLoadError(error.message);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const ready = Boolean(health?.ready || platform.system_status?.ready);
  const kb = platform.knowledge_base || {};
  const localUpload = kb.local_upload || {};
  const prospectusStatus = prospectusSearchStatus(kb.prospectus_evidence, kb.prospectus_index);
  const uploadIndexingStatus = uploadIndexStatus(kb.local_upload_indexing);
  const uploadReady = Boolean(platform.feature_flags?.upload_pdf && localUpload.enabled && localUpload.ready);
  const visibleMessages = useMemo(() => messages.filter(Boolean), [messages]);

  async function submitQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || isLoading) return;
    setQuestion('');
    setIsLoading(true);
    setMessages((current) => [
      ...current,
      { id: `pending-${Date.now()}`, question: trimmed, answer: '', pending: true },
    ]);
    try {
      const response = await sendChat(trimmed);
      setMessages((current) => [...current.filter((item) => !item.pending), response]);
    } catch (error) {
      setMessages((current) => [
        ...current.filter((item) => !item.pending),
        {
          id: `error-${Date.now()}`,
          question: trimmed,
          answer: '',
          sources: [],
          trace: [],
          error: { code: 'request_error', message: error.message },
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function onClearHistory() {
    await clearHistory();
    setMessages([]);
  }

  async function onUploadFile(event) {
    const file = event.target.files?.[0];
    if (!file || isUploading) return;
    setUploadError('');
    setUploadResult(null);
    setIsUploading(true);
    try {
      const result = await uploadProspectus(file);
      setUploadResult(result);
      try {
        const [healthPayload, platformPayload] = await Promise.all([getHealth(), getPlatform()]);
        setHealth(healthPayload);
        setPlatform(platformPayload);
      } catch (refreshError) {
        setLoadError(refreshError.message);
      }
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark">
            <Database size={19} aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">Local Platform</p>
            <h1>Financial Agentic RAG</h1>
          </div>
        </div>

        <section className="local-user" aria-label="Local session">
          <div className="avatar">LF</div>
          <div>
            <strong>{platform.session?.user || 'Local Financial Analyst'}</strong>
            <span>No login required</span>
          </div>
        </section>

        <section className="nav-section" aria-label="Knowledge base health">
          <h2>Knowledge Base</h2>
          <StatusLine
            icon={<Database size={16} />}
            label="SQL database"
            state={kb.sql_database?.ready ? 'Ready' : 'Needs config'}
            tone={kb.sql_database?.ready ? 'good' : 'warn'}
          />
          <StatusLine
            icon={<BookOpen size={16} />}
            label="Prospectus evidence"
            state={prospectusStatus.state}
            tone={prospectusStatus.tone}
          />
          <StatusLine
            icon={<Database size={16} />}
            label="Upload indexing"
            state={uploadIndexingStatus.state}
            tone={uploadIndexingStatus.tone}
          />
          <StatusLine
            icon={<FileUp size={16} />}
            label="Local upload"
            state={uploadReady ? 'Accepting files' : 'Coming next'}
            tone={uploadReady ? 'good' : 'muted'}
          />
        </section>

        <nav className="nav-section" aria-label="Platform tools">
          {uploadReady ? (
            <div className="upload-panel">
              <label className="tool-button upload-label" htmlFor="prospectus-upload">
                <FileUp size={18} aria-hidden="true" />
                <span>Upload PDF or TXT</span>
                <small>{isUploading ? 'Indexing...' : uploadIndexingStatus.shortLabel}</small>
              </label>
              <input
                id="prospectus-upload"
                className="file-input"
                type="file"
                accept=".pdf,.txt,application/pdf,text/plain"
                onChange={onUploadFile}
                disabled={isUploading}
              />
              <p className={`upload-readiness ${uploadIndexingStatus.tone}`}>
                {uploadIndexingStatus.description}
              </p>
              {prospectusStatus.message ? (
                <p className={`upload-readiness ${prospectusStatus.tone}`}>{prospectusStatus.message}</p>
              ) : null}
              {uploadError ? <div className="upload-error">{uploadError}</div> : null}
              {uploadResult ? <UploadStatus result={uploadResult} /> : null}
            </div>
          ) : (
            <button className="tool-button" type="button" disabled aria-label="Upload PDF coming next">
              <FileUp size={18} aria-hidden="true" />
              <span>Upload PDF</span>
              <small>Coming next</small>
            </button>
          )}
          <button className="tool-button" type="button" onClick={() => setDocsOpen(true)}>
            <BookOpen size={18} aria-hidden="true" />
            <span>Architecture Docs</span>
            <small>Local repo</small>
          </button>
          <button className="tool-button" type="button" onClick={onClearHistory}>
            <RotateCcw size={18} aria-hidden="true" />
            <span>Clear History</span>
            <small>Local session</small>
          </button>
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>
          <div>
            <p className="eyebrow">No-login demo</p>
            <h2>{platform.system_status?.label || 'SQL-first local financial Agentic RAG'}</h2>
          </div>
          <div className={`readiness ${ready ? 'ready' : 'not-ready'}`}>
            {ready ? <CheckCircle2 size={17} /> : <Activity size={17} />}
            <span>{ready ? 'Ready' : 'Configuration needed'}</span>
          </div>
        </header>

        {loadError ? <div className="banner">Platform metadata could not load: {loadError}</div> : null}

        <section className="chat-surface" aria-label="Financial chat">
          {visibleMessages.length === 0 ? (
            <EmptyState onPick={submitQuestion} disabled={isLoading} />
          ) : (
            <div className="message-list">
              {visibleMessages.map((message) => (
                <Message key={message.id || message.question} message={message} />
              ))}
            </div>
          )}
        </section>

        <form
          className="input-bar"
          onSubmit={(event) => {
            event.preventDefault();
            submitQuestion();
          }}
        >
          <label htmlFor="financial-question">Financial question</label>
          <textarea
            id="financial-question"
            aria-label="Financial question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about local SQL-backed financial evidence..."
            rows={1}
          />
          <button className="send-button" type="submit" aria-label="Send question" disabled={isLoading}>
            {isLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            <span>Send</span>
          </button>
        </form>
      </main>

      {sidebarOpen ? <button className="scrim" aria-label="Close sidebar" onClick={() => setSidebarOpen(false)} /> : null}
      {docsOpen ? <ArchitectureDocs docs={platform.architecture_docs} onClose={() => setDocsOpen(false)} /> : null}
    </div>
  );
}

function prospectusSearchStatus(evidence, index) {
  if (evidence?.ready && (index?.ready || !index)) {
    return { state: 'Ready', tone: 'good', message: '' };
  }
  if (index?.status === 'unavailable' || evidence?.status === 'unavailable') {
    return {
      state: 'Search unavailable',
      tone: 'warn',
      message: index?.error || evidence?.error || 'Prospectus search is unavailable.',
    };
  }
  if (index?.status === 'indexing') {
    return { state: 'Indexing', tone: 'warn', message: 'Prospectus search will be ready after indexing completes.' };
  }
  if (index?.status === 'index_not_ready' || evidence?.status === 'index_not_ready') {
    return { state: 'Index not ready', tone: 'warn', message: 'Prospectus search is not ready yet.' };
  }
  if (index?.enabled === false || evidence?.enabled === false) {
    return { state: 'Disabled', tone: 'muted', message: 'Prospectus search is disabled in this local platform.' };
  }
  return { state: 'Disabled', tone: 'muted', message: '' };
}

function uploadIndexStatus(indexing) {
  if (indexing?.ready) {
    return {
      state: 'Ready',
      tone: 'good',
      shortLabel: 'Index on upload',
      description: 'Small local uploads are indexed for chat search. Use the CLI workflow for large PDF batches.',
    };
  }
  if (indexing?.status === 'unavailable') {
    return {
      state: 'Upload indexing unavailable',
      tone: 'warn',
      shortLabel: 'Index unavailable',
      description: 'Upload indexing unavailable. Uploaded files may parse, but search readiness is not claimed.',
    };
  }
  if (indexing?.status === 'indexing') {
    return {
      state: 'Indexing',
      tone: 'warn',
      shortLabel: 'Indexing',
      description: 'Indexing is in progress; chat search becomes ready after indexing succeeds.',
    };
  }
  if (indexing?.enabled === false) {
    return {
      state: 'Disabled',
      tone: 'muted',
      shortLabel: 'Parse only',
      description: 'Browser upload is parse-only here. Use the CLI workflow for bulk local PDF directories.',
    };
  }
  return {
    state: 'Not ready',
    tone: 'muted',
    shortLabel: 'Local only',
    description: 'Local upload indexing is not ready yet.',
  };
}

function UploadStatus({ result }) {
  const status = uploadResultStatus(result);
  const summary = uploadVectorSummary(result);
  const diagnostics = Array.isArray(result.diagnostics) ? result.diagnostics : result.diagnostics ? [result.diagnostics] : [];

  return (
    <section className={`upload-status ${status.tone}`} aria-label="Upload indexing status">
      <strong>{status.label}</strong>
      {status.showRaw ? <span>{result.status || 'uploaded_parsed_not_indexed'}</span> : null}
      {result.collection ? <span>Collection: {result.collection}</span> : null}
      {result.document_id ? <span>Document: {result.document_id}</span> : <span>{result.filename}</span>}
      {summary.length ? (
        <div className="upload-summary">
          {summary.map((item) => (
            <small key={item}>{item}</small>
          ))}
        </div>
      ) : null}
      <div>
        <small>{result.indexed ? 'Indexed' : 'Not indexed'}</small>
        <small>{result.searchable ? 'Searchable' : 'Not searchable'}</small>
      </div>
      {result.error ? <p className="upload-failure">{result.error}</p> : null}
      {diagnostics.length ? (
        <ul className="upload-diagnostics">
          {diagnostics.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function uploadResultStatus(result) {
  if (result.status === 'indexed_searchable') return { label: 'Indexed and searchable', tone: 'good', showRaw: false };
  if (result.status === 'already_indexed' || result.status === 'skipped') {
    return { label: 'Already indexed', tone: 'good', showRaw: true };
  }
  if (result.status === 'index_failed') return { label: 'Indexing failed', tone: 'error', showRaw: true };
  if (result.status === 'indexing') return { label: 'Indexing in progress', tone: 'warn', showRaw: true };
  return { label: result.status || 'uploaded_parsed_not_indexed', tone: 'warn', showRaw: false };
}

function uploadVectorSummary(result) {
  const summary = [];
  if (Number.isFinite(result.chunk_count)) summary.push(`${result.chunk_count} chunks`);
  if (Number.isFinite(result.vector_count)) summary.push(`${result.vector_count} vectors`);
  return summary;
}

function StatusLine({ icon, label, state, tone }) {
  return (
    <div className={`status-line ${tone}`}>
      {icon}
      <span>{label}</span>
      <strong>{state}</strong>
    </div>
  );
}

function EmptyState({ onPick, disabled }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <MessageSquareText size={34} aria-hidden="true" />
      </div>
      <p className="eyebrow">SQL-first evidence</p>
      <h2>Ask a SQL-backed financial question</h2>
      <p className="empty-copy">
        Answers use the local financial planner, Text-to-SQL evidence, verification report, and trace metadata.
      </p>
      <div className="suggestions">
        {suggestions.map((item) => (
          <button key={item} type="button" onClick={() => onPick(item)} disabled={disabled}>
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function Message({ message }) {
  const traceText = Array.isArray(message.trace?.tool_sequence)
    ? message.trace.tool_sequence.join(' -> ')
    : Array.isArray(message.trace)
      ? message.trace.join(' -> ')
      : '';
  const verificationStatus = message.verification_report?.status;

  return (
    <article className="message-item">
      <div className="user-bubble">{message.question}</div>
      <div className="assistant-bubble">
        {message.pending ? (
          <div className="loading-line">
            <Loader2 className="spin" size={18} />
            <span>Running local financial pipeline...</span>
          </div>
        ) : message.error ? (
          <div className="error-box">{message.error.message}</div>
        ) : (
          <>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.answer || ''}</ReactMarkdown>
            <div className="meta-grid">
              {verificationStatus ? (
                <div className="meta-pill">
                  <ShieldCheck size={15} aria-hidden="true" />
                  <span>Verification: {verificationStatus}</span>
                </div>
              ) : null}
              {message.latency_ms != null ? (
                <div className="meta-pill">
                  <Activity size={15} aria-hidden="true" />
                  <span>{message.latency_ms} ms</span>
                </div>
              ) : null}
            </div>
            <EvidenceList sources={message.sources || []} />
            {traceText ? (
              <details className="trace-box" open>
                <summary>Trace</summary>
                <code>{traceText}</code>
              </details>
            ) : null}
          </>
        )}
      </div>
    </article>
  );
}

function EvidenceList({ sources }) {
  if (!sources.length) return null;
  return (
    <div className="evidence-list">
      <h3>Sources</h3>
      {sources.map((source) => (
        <details key={source.id || source.source} open>
          <summary>
            <span>{source.id || 'source'}</span>
            <small>{source.kind || source.source_type || 'evidence'}</small>
          </summary>
          <p>{source.source}</p>
          <pre>{JSON.stringify(source.metadata?.rows || source.metadata || source.content, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}

function ArchitectureDocs({ docs, onClose }) {
  const links = docs?.links || [];
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="docs-title">
      <section className="docs-modal">
        <header>
          <div>
            <p className="eyebrow">Local repo documentation</p>
            <h2 id="docs-title">Architecture Docs</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close architecture docs">
            <X size={20} />
          </button>
        </header>
        <div className="doc-links">
          {links.map((link) => (
            <a key={link.path} href={`/${link.path}`} target="_blank" rel="noreferrer">
              <BookOpen size={17} aria-hidden="true" />
              <span>{link.label}</span>
              <small>{link.available ? link.path : 'not found locally'}</small>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
