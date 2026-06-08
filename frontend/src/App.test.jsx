import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import App from './App.jsx';

const platformPayload = {
  session: { label: 'Local demo session', mode: 'no-login', user: 'Local Financial Analyst' },
  system_status: { label: 'SQL-first local financial Agentic RAG', ready: true, status: 'ready' },
  feature_flags: { upload_pdf: false, numeric_confidence: false },
  knowledge_base: {
    sql_database: { ready: true, path: 'financial.db', source: 'FINANCIAL_DEMO_DB_PATH' },
    prospectus_evidence: { ready: false, enabled: false, status: 'disabled' },
    local_upload: { ready: false, enabled: false, status: 'coming_next' },
  },
  architecture_docs: {
    available: true,
    links: [
      { label: 'Financial Platform README', path: 'docs/financial/README.md', available: true },
      {
        label: 'Financial Agentic RAG design',
        path: 'docs/financial/financial-agentic-rag-design.md',
        available: true,
      },
    ],
  },
};

const healthPayload = {
  status: 'ready',
  ready: true,
  dependencies: platformPayload.knowledge_base,
  configuration: { sql_db_path_source: 'FINANCIAL_DEMO_DB_PATH' },
};

function uploadEnabledPlatform(overrides = {}) {
  return {
    ...platformPayload,
    feature_flags: { ...platformPayload.feature_flags, upload_pdf: true },
    knowledge_base: {
      ...platformPayload.knowledge_base,
      prospectus_evidence: { ready: true, enabled: true, status: 'ready' },
      prospectus_index: { ready: true, enabled: true, status: 'ready' },
      local_upload: { ready: true, enabled: true, status: 'ready' },
      local_upload_indexing: { ready: true, enabled: true, status: 'ready' },
      ...overrides,
    },
  };
}

function mockPlatformForUpload(uploadPlatform, uploadPayload, refreshedPlatform = uploadPlatform) {
  let uploaded = false;
  fetch.mockImplementation((url, options = {}) => {
    if (url === '/api/health') {
      const activePlatform = uploaded ? refreshedPlatform : uploadPlatform;
      return jsonResponse({ ...healthPayload, dependencies: activePlatform.knowledge_base });
    }
    if (url === '/api/platform') return jsonResponse(uploaded ? refreshedPlatform : uploadPlatform);
    if (url === '/api/history') return jsonResponse({ messages: [] });
    if (url === '/api/prospectus/upload' && options.method === 'POST') {
      uploaded = true;
      return jsonResponse(uploadPayload);
    }
    return jsonResponse({});
  });
}

function jsonResponse(body, init = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status: init.status || 200,
    headers: { 'Content-Type': 'application/json' },
  }));
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal('fetch', vi.fn((url, options = {}) => {
    if (url === '/api/health') return jsonResponse(healthPayload);
    if (url === '/api/platform') return jsonResponse(platformPayload);
    if (url === '/api/history') return jsonResponse({ messages: [] });
    if (url === '/api/chat' && options.method === 'POST') {
      return jsonResponse({
        id: 'chat-1',
        question: JSON.parse(options.body).question,
        answer: '**Revenue increased** based on SQL evidence.',
        sources: [
          {
            id: 'sql-1',
            kind: 'sql_result',
            source_type: 'db',
            source: 'financial.db',
            content: '[{"revenue": 10}]',
            metadata: { sql: 'select revenue from financials', rows: [{ revenue: 10 }] },
          },
        ],
        question_plan: { route: 'text_to_sql', task_type: 'point_lookup' },
        verification_report: { status: 'pass', notes: ['Matched SQL evidence'] },
        trace: { tool_sequence: ['plan', 'text_to_sql', 'verify'], stages: [{ stage: 'planning' }] },
        latency_ms: 12,
        error: null,
      });
    }
    if (url === '/api/history' && options.method === 'DELETE') {
      return jsonResponse({ cleared: true });
    }
    if (url === '/api/prospectus/upload' && options.method === 'POST') {
      return jsonResponse({
        status: 'uploaded_parsed_not_indexed',
        filename: 'prospectus.txt',
        document_id: 'txt_abc123',
        doc_type: 'prospectus_txt',
        text_length: 34,
        table_placeholders: ['TABLE_0001_0000.xlsx'],
        indexed: false,
        searchable: false,
      });
    }
    return jsonResponse({}, { status: 404 });
  }));
});

describe('local financial platform UI', () => {
  test('renders no-login empty state and local platform labels', async () => {
    render(<App />);

    expect(await screen.findByText('Local Financial Analyst')).toBeInTheDocument();
    expect(screen.getByText(/No login required/i)).toBeInTheDocument();
    expect(screen.getByText(/SQL-first local financial Agentic RAG/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload PDF coming next/i })).toBeDisabled();
    expect(screen.getByText(/Ask a SQL-backed financial question/i)).toBeInTheDocument();
  });

  test('submits a prompt and renders answer, evidence, verification, and trace without confidence', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(await screen.findByLabelText('Financial question'), 'Show revenue');
    await user.click(screen.getByRole('button', { name: /Send question/i }));

    expect(await screen.findByText('Show revenue')).toBeInTheDocument();
    expect(await screen.findByText(/Revenue increased/i)).toBeInTheDocument();
    expect(screen.getByText(/Verification: pass/i)).toBeInTheDocument();
    expect(screen.getByText(/sql-1/i)).toBeInTheDocument();
    expect(screen.getByText(/plan -> text_to_sql -> verify/i)).toBeInTheDocument();
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  test('renders readable API errors', async () => {
    fetch.mockImplementation((url, options = {}) => {
      if (url === '/api/health') return jsonResponse(healthPayload);
      if (url === '/api/platform') return jsonResponse(platformPayload);
      if (url === '/api/history') return jsonResponse({ messages: [] });
      if (url === '/api/chat' && options.method === 'POST') {
        return jsonResponse({
          id: 'chat-err',
          question: 'Broken',
          answer: '',
          sources: [],
          question_plan: null,
          verification_report: null,
          trace: [],
          latency_ms: 2,
          error: { code: 'configuration_error', message: 'Set FINANCIAL_DEMO_DB_PATH.' },
        });
      }
      return jsonResponse({});
    });
    const user = userEvent.setup();
    render(<App />);

    await user.type(await screen.findByLabelText('Financial question'), 'Broken');
    await user.click(screen.getByRole('button', { name: /Send question/i }));

    expect(await screen.findByText(/Set FINANCIAL_DEMO_DB_PATH/i)).toBeInTheDocument();
  });

  test('clears visible history through the local endpoint', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(await screen.findByLabelText('Financial question'), 'Show revenue');
    await user.click(screen.getByRole('button', { name: /Send question/i }));
    expect(await screen.findByText('Show revenue')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Clear History/i }));

    await waitFor(() => expect(screen.queryByText('Show revenue')).not.toBeInTheDocument());
    expect(fetch).toHaveBeenCalledWith('/api/history', { method: 'DELETE' });
  });

  test('mobile sidebar can open and close without adding auth-only controls', async () => {
    const user = userEvent.setup();
    window.innerWidth = 390;
    render(<App />);

    await screen.findByText('Local Financial Analyst');
    await user.click(screen.getByRole('button', { name: /Open sidebar/i }));

    expect(document.querySelector('.sidebar')).toHaveClass('sidebar-open');
    expect(screen.queryByText(/Google/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/JWT/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Pinecone/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Close sidebar/i }));
    expect(document.querySelector('.sidebar')).not.toHaveClass('sidebar-open');
  });

  test('uploads a local prospectus file and renders honest parse status', async () => {
    mockPlatformForUpload(uploadEnabledPlatform(), {
      status: 'uploaded_parsed_not_indexed',
      filename: 'prospectus.txt',
      document_id: 'txt_abc123',
      doc_type: 'prospectus_txt',
      text_length: 34,
      table_placeholders: ['TABLE_0001_0000.xlsx'],
      indexed: false,
      searchable: false,
    });
    const user = userEvent.setup();
    render(<App />);

    const uploadInput = await screen.findByLabelText(/Upload PDF or TXT/i);
    await user.upload(
      uploadInput,
      new File(['business table <|TABLE_0001_0000.xlsx|>'], 'prospectus.txt', {
        type: 'text/plain',
      }),
    );

    expect(await screen.findByText(/uploaded_parsed_not_indexed/i)).toBeInTheDocument();
    expect(screen.getByText(/txt_abc123/i)).toBeInTheDocument();
    expect(screen.getByText(/Not indexed/i)).toBeInTheDocument();
    expect(screen.getByText(/Not searchable/i)).toBeInTheDocument();
    expect(screen.queryByText(/Indexed and searchable/i)).not.toBeInTheDocument();
  });

  test('uploads and renders indexed searchable document metadata', async () => {
    mockPlatformForUpload(uploadEnabledPlatform(), {
      status: 'indexed_searchable',
      filename: 'annual-prospectus.pdf',
      collection: 'prospectus_chunks',
      document_id: 'pdf_2026_abc',
      chunk_count: 18,
      vector_count: 18,
      indexed: true,
      searchable: true,
    });
    const user = userEvent.setup();
    render(<App />);

    const uploadInput = await screen.findByLabelText(/Upload PDF or TXT/i);
    await user.upload(uploadInput, new File(['pdf text'], 'annual-prospectus.pdf', { type: 'application/pdf' }));

    expect(await screen.findByText(/Indexed and searchable/i)).toBeInTheDocument();
    expect(screen.getByText(/Collection: prospectus_chunks/i)).toBeInTheDocument();
    expect(screen.getByText(/Document: pdf_2026_abc/i)).toBeInTheDocument();
    expect(screen.getByText(/18 chunks/i)).toBeInTheDocument();
    expect(screen.getByText(/18 vectors/i)).toBeInTheDocument();
  });

  test('refreshes platform readiness after indexed upload succeeds', async () => {
    const beforeUpload = uploadEnabledPlatform({
      prospectus_evidence: { ready: false, enabled: true, status: 'index_not_ready' },
      prospectus_index: { ready: false, enabled: true, status: 'index_not_ready' },
      local_upload_indexing: { ready: true, enabled: true, status: 'ready' },
    });
    const afterUpload = uploadEnabledPlatform({
      prospectus_evidence: { ready: true, enabled: true, status: 'ready' },
      prospectus_index: { ready: true, enabled: true, status: 'ready' },
      local_upload_indexing: { ready: true, enabled: true, status: 'ready' },
    });
    mockPlatformForUpload(
      beforeUpload,
      {
        status: 'indexed_searchable',
        filename: 'annual-prospectus.pdf',
        collection: 'prospectus_uploads',
        document_id: 'pdf_ready',
        chunk_count: 4,
        vector_count: 4,
        indexed: true,
        searchable: true,
      },
      afterUpload,
    );
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText(/Index not ready/i)).toBeInTheDocument();

    const uploadInput = await screen.findByLabelText(/Upload PDF or TXT/i);
    await user.upload(uploadInput, new File(['pdf text'], 'annual-prospectus.pdf', { type: 'application/pdf' }));

    expect(await screen.findByText(/Indexed and searchable/i)).toBeInTheDocument();
    expect(screen.getByText(/Prospectus evidence/i).closest('.status-line')).toHaveTextContent(/Ready/i);
  });

  test('uploads and renders readable indexing failure without claiming searchability', async () => {
    mockPlatformForUpload(uploadEnabledPlatform(), {
      status: 'index_failed',
      filename: 'annual-prospectus.pdf',
      document_id: 'pdf_failed',
      indexed: false,
      searchable: false,
      error: 'Embedding service unavailable.',
      diagnostics: ['Retry after configuring LOCAL_EMBEDDING_MODEL.'],
    });
    const user = userEvent.setup();
    render(<App />);

    const uploadInput = await screen.findByLabelText(/Upload PDF or TXT/i);
    await user.upload(uploadInput, new File(['pdf text'], 'annual-prospectus.pdf', { type: 'application/pdf' }));

    expect(await screen.findByText(/Indexing failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Embedding service unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Retry after configuring LOCAL_EMBEDDING_MODEL/i)).toBeInTheDocument();
    expect(screen.getByText(/Not searchable/i)).toBeInTheDocument();
    expect(screen.queryByText(/Indexed and searchable/i)).not.toBeInTheDocument();
  });

  test('shows prospectus search unavailable when platform metadata reports index unavailable', async () => {
    const searchUnavailablePlatform = uploadEnabledPlatform({
      prospectus_index: {
        ready: false,
        enabled: true,
        status: 'unavailable',
        error: 'Vector store is offline.',
      },
      local_upload_indexing: {
        ready: false,
        enabled: true,
        status: 'unavailable',
      },
    });
    fetch.mockImplementation((url) => {
      if (url === '/api/health') {
        return jsonResponse({ ...healthPayload, dependencies: searchUnavailablePlatform.knowledge_base });
      }
      if (url === '/api/platform') return jsonResponse(searchUnavailablePlatform);
      if (url === '/api/history') return jsonResponse({ messages: [] });
      return jsonResponse({});
    });

    render(<App />);

    expect(await screen.findByText(/Search unavailable/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Upload indexing unavailable/i)).toHaveLength(2);
    expect(screen.getByText(/Vector store is offline/i)).toBeInTheDocument();
  });
});
