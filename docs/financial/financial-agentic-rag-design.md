# Financial Agentic RAG Engineering Design

本文档描述一个面向金融问答场景的 Agentic RAG 工程设计。系统在现有 Modular RAG MCP Server 的基础上增量扩展，不推翻既有 RAG 管线，而是在 Agent 层增加 Router、Text-to-SQL Path、Hybrid 编排、Evidence Merger 和 Verifier。

设计目标：

- 处理招股说明书 PDF 的文本、表格、图片、图表证据。
- 处理 SQLite 金融数据库中的结构化查询。
- 支持 PDF 证据和 DB 证据的联合推理。
- 保留现有 MCP RAG 服务的稳定边界。
- 沿用项目现有的可插拔、本地优先、可观测、轻量存储风格。

## 1. Existing Engineering Baseline

现有项目的核心 RAG 管线来自 `DEV_SPEC.md` 和当前代码实现。

### 1.1 Current Ingestion Pipeline

现有摄取链路：

```text
File Integrity Check
  ↓
PdfLoader
  ↓
Document
  ↓
DocumentChunker
  ↓
ChunkRefiner
  ↓
MetadataEnricher
  ↓
ImageCaptioner
  ↓
DenseEncoder + SparseEncoder
  ↓
VectorUpserter + BM25Indexer + ImageStorage
```

对应现有模块：

- `src/libs/loader/pdf_loader.py`
- `src/ingestion/pipeline.py`
- `src/ingestion/chunking/document_chunker.py`
- `src/ingestion/transform/image_captioner.py`
- `src/ingestion/storage/vector_upserter.py`
- `src/ingestion/storage/bm25_indexer.py`
- `src/ingestion/storage/image_storage.py`

现有核心数据类型：

- `Document`
- `Chunk`
- `ChunkRecord`
- `ProcessedQuery`
- `RetrievalResult`

这些类型位于 `src/core/types.py`。

### 1.2 Current Query Pipeline

现有查询链路：

```text
query_knowledge_hub
  ↓
QueryProcessor
  ↓
DenseRetriever + SparseRetriever
  ↓
RRF Fusion
  ↓
CoreReranker
  ↓
ResponseBuilder
  ↓
MCP Tool Response
```

对应现有模块：

- `src/mcp_server/tools/query_knowledge_hub.py`
- `src/core/query_engine/query_processor.py`
- `src/core/query_engine/hybrid_search.py`
- `src/core/response/response_builder.py`

### 1.3 Extension Principle

新金融问答管线不应该把所有能力塞进 MCP Server 内部。系统边界是：

```text
Agent Layer:
  Router / Hybrid Orchestration / Evidence Merger / Verifier

MCP RAG Server:
  PDF evidence retrieval capability

Text-to-SQL Tool:
  Structured DB evidence capability
```

## 2. Target Architecture

顶层流程：

```text
User Question
  ↓
Query Understanding / Agent Router
  ↓
┌──────────────────┬──────────────────┬──────────────────┐
│ PDF RAG Path     │ Text-to-SQL Path │ Hybrid Path      │
│ 招股书理解        │ DB 数据查询       │ 文档 + DB 联合    │
└──────────────────┴──────────────────┴──────────────────┘
  ↓
Evidence Merger / Verifier
  ↓
Final Answer with Sources
```

路径职责：

- `PDF RAG Path`：处理招股说明书 PDF 证据，内部区分 text/table/image/chart evidence type。
- `Text-to-SQL Path`：处理 SQLite 数据库查询，生成、校验、执行 SQL，并返回结构化证据。
- `Hybrid Path`：Agent 编排策略，分为 `doc_first` 和 `sql_first`。
- `Evidence Merger / Verifier`：统一合并证据、处理冲突、生成最终答案。

## 3. Data Structures

本节定义新增数据结构。它们可以放在 `src/core/financial_types.py` 或 `src/agentic/types.py`，避免污染现有通用 RAG 类型。

### 3.1 DocumentElement

`DocumentElement` 表示从 PDF 中解析出来的最小可索引证据单元。

```python
@dataclass
class DocumentElement:
    element_id: str
    doc_id: str
    source_path: str
    page: int
    element_type: Literal["text", "table", "image", "chart"]
    index_content: str
    raw_content: str
    bbox: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

字段含义：

- `element_id`：全局唯一 ID，用于从 docstore 回填原始证据。
- `doc_id`：父文档 ID，建议沿用 PDF 文件 SHA256 hash。
- `source_path`：原始 PDF 路径。
- `page`：PDF 页码，从 1 开始。
- `element_type`：文档内部证据类型。
- `index_content`：写入向量库和 BM25 的轻量检索文本。
- `raw_content`：原始证据，生成答案时使用。
- `bbox`：元素在 PDF 页面上的坐标，可选。
- `metadata`：公司名、表格标题、图片 ID、置信度等扩展字段。

### 3.2 Evidence

`Evidence` 是路径返回给 Merger 的证据项。

```python
@dataclass
class Evidence:
    evidence_id: str
    evidence_type: Literal["text", "table", "image", "chart", "sql_result"]
    source_type: Literal["pdf", "db"]
    content: str
    source: str
    score: Optional[float] = None
    page: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

PDF evidence 的 `metadata` 至少包含：

- `element_id`
- `doc_id`
- `source_path`
- `page`
- `bbox`
- `element_type`

SQL evidence 的 `metadata` 至少包含：

- `sql`
- `database`
- `table_names`
- `columns`
- `row_count`

### 3.3 EvidencePackage

所有 evidence path 都返回 EvidencePackage，而不是最终自然语言答案。

```python
@dataclass
class EvidencePackage:
    path: Literal["pdf_rag", "text_to_sql"]
    question: str
    evidences: list[Evidence]
    trace_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 3.4 RoutingDecision

Agent Router 输出结构化 Routing Decision。

```python
@dataclass
class RoutingDecision:
    route: Literal["pdf_rag", "text_to_sql", "hybrid"]
    hybrid_mode: Optional[Literal["doc_first", "sql_first"]]
    intent: Literal["prospectus_understanding", "db_query", "joint_reasoning"]
    entities: dict[str, list[str]]
    evidence_need: list[Literal["text", "table", "image", "chart", "sql_result"]]
    sub_questions: list[dict[str, str]]
    reason: str
```

示例：

```json
{
  "route": "hybrid",
  "hybrid_mode": "sql_first",
  "intent": "joint_reasoning",
  "entities": {
    "company_names": [],
    "stock_codes": [],
    "fund_names": ["某基金"],
    "dates": ["2021Q2"]
  },
  "evidence_need": ["sql_result", "text", "table"],
  "sub_questions": [
    {
      "target_path": "text_to_sql",
      "question": "找出该基金 2021Q2 第一大重仓股"
    },
    {
      "target_path": "pdf_rag",
      "question": "查询该股票对应公司的主营业务和风险因素"
    }
  ],
  "reason": "问题先需要数据库确定股票实体，再需要 PDF 解释公司背景"
}
```

### 3.5 VerificationReport

Verifier 输出校验报告。

```python
@dataclass
class VerificationReport:
    status: Literal["pass", "partial", "conflict", "insufficient"]
    selected_evidence_ids: list[str]
    conflicts: list[dict[str, Any]]
    missing_evidence: list[str]
    notes: list[str]
```

## 4. Storage Design

新管线沿用现有本地优先存储设计。

### 4.1 Existing Stores

继续使用：

- Chroma：存 dense vector 和 chunk metadata。
- BM25 JSON index：存 sparse keyword index。
- SQLite ingestion history：存文件摄取状态。
- SQLite image index：存 image_id 到图片路径的映射。
- 文件系统：存图片文件。

### 4.2 New Element Docstore

新增 `ElementDocstore`，推荐使用 SQLite，路径：

```text
data/db/element_docstore.db
```

理由：

- 与现有 `FileIntegrityChecker`、`ImageStorage` 一致。
- 本地可运行，无需额外数据库服务。
- 支持按 `element_id` 回填 raw table、raw image、chart summary。
- 支持文档删除时按 `doc_id` 级联清理。

推荐 schema：

```sql
CREATE TABLE IF NOT EXISTS document_elements (
    element_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    page INTEGER,
    element_type TEXT NOT NULL,
    index_content TEXT NOT NULL,
    raw_content TEXT,
    raw_format TEXT,
    bbox_json TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_elements_doc_id
ON document_elements(doc_id);

CREATE INDEX IF NOT EXISTS idx_elements_type
ON document_elements(element_type);

CREATE INDEX IF NOT EXISTS idx_elements_source_path
ON document_elements(source_path);
```

表格可以额外存一张表，方便后续精确处理：

```sql
CREATE TABLE IF NOT EXISTS table_payloads (
    table_id TEXT PRIMARY KEY,
    element_id TEXT NOT NULL,
    markdown TEXT,
    json_payload TEXT,
    caption TEXT,
    page INTEGER,
    FOREIGN KEY(element_id) REFERENCES document_elements(element_id)
);
```

### 4.3 Vector Store Metadata

Chroma metadata 只支持简单标量，因此复杂结构不要直接塞入 metadata。

写入 Chroma 的 metadata 建议：

```json
{
  "doc_id": "sha256...",
  "source_path": "xxx.pdf",
  "doc_type": "pdf",
  "element_id": "doc_p12_table_01",
  "element_type": "table",
  "page": 12,
  "chunk_index": 42,
  "title": "主要财务数据",
  "has_raw_payload": true
}
```

复杂字段放 docstore：

- full table JSON
- bbox list
- image OCR result
- chart values
- extraction confidence details

### 4.4 SQL Query Log Store

Text-to-SQL 可以新增轻量日志表，方便追踪和评估：

```text
data/db/sql_query_log.db
```

推荐 schema：

```sql
CREATE TABLE IF NOT EXISTS sql_query_log (
    query_id TEXT PRIMARY KEY,
    user_question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    status TEXT NOT NULL,
    error_msg TEXT,
    row_count INTEGER,
    elapsed_ms REAL,
    created_at TEXT NOT NULL
);
```

## 5. Ingestion Details

PDF RAG Path 的摄取应在现有 `IngestionPipeline` 上增量扩展。

### 5.1 Two Implementation Modes

第一版推荐轻量实现，第二版再做原生 element pipeline。

#### Mode A: Lightweight Synthetic Text

不改 `DocumentChunker`，只增强 `PdfLoader` 输出的 `Document.text`。

```text
PDF
  ↓
MarkItDown text
  ↓
pdfplumber table extraction
  ↓
PyMuPDF image extraction
  ↓
VLM image/chart caption
  ↓
Synthetic Markdown Document.text
  ↓
Existing DocumentChunker
```

示例合成文本：

```markdown
[PAGE 25]

[TEXT]
发行人主营业务为...

[PDF_TABLE element_id=doc_p25_table_01 page=25]
表格标题：主要财务数据
表格摘要：包含营业收入、净利润、毛利率等指标。

| 项目 | 2021年 | 2020年 | 2019年 |
| --- | ---: | ---: | ---: |
| 营业收入 | ... | ... | ... |

[IMAGE element_id=doc_p26_image_01 page=26]
图片说明：...
```

优点：

- 最大程度复用现有 RAG 管线。
- 不新增复杂数据类型即可改善表格召回。
- 适合快速验证。

缺点：

- 表格可能被 chunk 切坏。
- 回填原始表格能力有限。
- `element_id` 主要作为文本标记存在。

#### Mode B: Native Element Pipeline

新增 `DocumentElement`，在摄取阶段先生成 elements，再把每个 element 转成可索引 chunk。

```text
PDF
  ↓
PdfElementExtractor
  ↓
List[DocumentElement]
  ↓
ElementProcessor
  ↓
Indexable Chunk
  ↓
VectorStore + BM25
  ↓
ElementDocstore stores raw evidence
```

推荐最终采用 Mode B，但先从 Mode A 起步。

### 5.2 Element Extraction

建议新增模块：

```text
src/ingestion/elements/
  extractor.py
  table_extractor.py
  image_extractor.py
  chart_classifier.py
  element_processor.py
  element_docstore.py
```

抽取策略：

- Text：MarkItDown 作为基础文本，pdfplumber 作为页级辅助。
- Table：pdfplumber 优先，必要时 fallback 到 Camelot/Tabula。
- Image：沿用 PyMuPDF 图片抽取。
- Chart：先通过规则和 VLM prompt 区分 chart 与普通 image。

### 5.3 Table Processing

Table Evidence 使用 summary for retrieval、raw table for generation。

流程：

```text
Raw table cells
  ↓
Normalize rows/columns
  ↓
Markdown table
  ↓
Optional JSON table
  ↓
Rule-based summary
  ↓
Optional LLM summary
  ↓
index_content to Chroma/BM25
raw_content to ElementDocstore
```

规则摘要优先：

- 表格标题。
- 页码。
- 列名。
- 前 20 个关键行名。
- 年份、报告期、金额单位。
- 关键指标词，如营业收入、净利润、毛利率、客户、供应商、存货、募集资金。

只有规则摘要不足时才调用 LLM，保持成本可控。

### 5.4 Image and Chart Processing

普通图片：

```text
Image crop/file
  ↓
VLM caption
  ↓
caption as index_content
  ↓
image path + caption in docstore/image storage
```

图表：

```text
Chart crop/file
  ↓
OCR title/axis/legend
  ↓
VLM chart summary
  ↓
optional chart values
  ↓
summary as index_content
  ↓
raw image + OCR + summary in docstore
```

图表回答原则：

- 有明确数字标签时可以回答具体值。
- 只有视觉趋势时只回答趋势。
- 精确财务数字优先使用 Table Evidence 或 SQL Evidence。

### 5.5 Ingestion Trace

现有 Trace 有 `trace_type="ingestion"`，新管线增加阶段：

```text
element_extract
table_process
element_docstore_upsert
```

示例 trace stage：

```json
{
  "stage": "element_extract",
  "data": {
    "text_count": 120,
    "table_count": 18,
    "image_count": 6,
    "chart_count": 3,
    "failed_pages": [42]
  }
}
```

## 6. Query Details

### 6.1 Agent Router Flow

```text
User Question
  ↓
Normalize question
  ↓
Extract entities/dates/source hints
  ↓
Classify route
  ↓
Build RoutingDecision
```

Router 规则：

- 招股书、发行人、主营业务、风险因素、募投项目、客户供应商：`pdf_rag`
- 基金、股票行情、持仓、净值、份额、行业分类、排名、统计计算：`text_to_sql`
- 既需要文档披露又需要 DB 计算：`hybrid`

Hybrid 子路由：

- `doc_first`：先用 PDF 找实体或披露口径，再查 DB。
- `sql_first`：先用 DB 找对象、排名、日期或异常，再查 PDF 解释。

### 6.2 PDF RAG Query Flow

第一版可以包装现有 `query_knowledge_hub`：

```text
PDF sub-question
  ↓
query_knowledge_hub
  ↓
RetrievalResult/MCP response
  ↓
Agent wrapper converts results to EvidencePackage
```

第二版新增 evidence-native 查询：

```text
PDF sub-question
  ↓
HybridSearch over element index_content
  ↓
Rerank
  ↓
For table evidence: fetch raw table by element_id
  ↓
Return PDF EvidencePackage
```

Evidence 回填规则：

- `text`：直接使用 retrieved text。
- `table`：使用 `element_id` 从 docstore 获取 raw Markdown/JSON。
- `image`：获取 caption 和 image path。
- `chart`：获取 chart summary、OCR text、可选 values。

### 6.3 Text-to-SQL Query Flow

Text-to-SQL Path 是一个完整工具，不只生成 SQL。

```text
SQL sub-question
  ↓
Schema Linking
  ↓
SQL Generation / Candidate Route
  ↓
SQL Safety Check
  ↓
SQL Execution
  ↓
Result Normalization
  ↓
SQL EvidencePackage
```

数据库范围：

- `基金基本信息`
- `基金股票持仓明细`
- `基金债券持仓明细`
- `基金可转债持仓明细`
- `基金日行情表`
- `A股票日行情表`
- `港股票日行情表`
- `A股公司行业划分表`
- `基金规模变动表`
- `基金份额持有人结构`

安全规则：

- 只允许 `SELECT`。
- 禁止多语句执行。
- 禁止 `INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`CREATE`。
- 默认添加 `LIMIT`，聚合查询除外。
- SQL 执行失败时进入 repair，最多重试 2 次。
- 返回行数超过阈值时，先返回摘要和前 N 行。

当前 Text2SQL Agent 路线采用可观测候选链：

```text
rule/lora/api -> safety -> execute error -> repair -> re-execute -> log/eval
```

落地规则：

- `rule` 始终先执行，保持原有规则编译路径为默认能力。
- `lora` 只有在 `financial_platform.text2sql_agent.enable_lora_fallback` 开启并配置本地 HTTP endpoint 后才参与。
- `api` fallback 默认关闭，只有显式配置 `enable_api_fallback`、`api_endpoint` 和 `api_model` 后才参与。
- `sql_examples_path` 支持提供 `{question, sql}` JSON 样例，Text2SQL route 会用轻量关键词匹配取 top-K 样例加入 LoRA/API/repair context。
- 每个候选都必须先过 `SQLSafetyChecker`，再进入 SQLite executor。
- 结果为空默认是可接受终止结果；只有开启 empty-result repair 时才继续 fallback/repair。
- repair source 受 `max_repair_attempts` 约束，修复 SQL 会重新经过 safety 和 execution，并在失败时保留 `repair_exhausted` 等稳定失败码。
- SQL query log 记录 source、attempt id、parent attempt id、repair reason、safety/execution status、selected flag、row count、error、elapsed time。
- SQL evidence 和 orchestrator trace 保留 `sql_source`、`fallback_attempts`、`repair_attempts`、`candidate_count`、`selected_reason`、`sql_route_events`、`final_failure_code`、`accepted_result_kind`。
- 评测层按 `rule/lora/api/repair` 输出 source breakdown、fallback lift、repair metrics，并用 promotion gates 控制 LoRA/API 是否可以成为默认 fallback。

### 6.4 Hybrid Query Flow

doc_first：

```text
User Question
  ↓
Router decides hybrid/doc_first
  ↓
PDF RAG retrieves entity/disclosure evidence
  ↓
Entity normalizer extracts company/stock/fund/date
  ↓
Text-to-SQL queries DB
  ↓
Evidence Merger / Verifier
```

sql_first：

```text
User Question
  ↓
Router decides hybrid/sql_first
  ↓
Text-to-SQL identifies entity/ranking/date/fact
  ↓
Entity normalizer maps DB result to PDF entity
  ↓
PDF RAG retrieves prospectus evidence
  ↓
Evidence Merger / Verifier
```

### 6.5 Query Trace

现有 Trace 有 `trace_type="query"`，新 Agent 查询建议新增 `trace_type="agent_query"`。如果先不改 `TraceContext` 的 Literal 类型，也可以继续用 `query`，在 metadata 中写：

```json
{
  "source": "financial_agent",
  "route": "hybrid",
  "hybrid_mode": "sql_first"
}
```

推荐 trace stages：

```text
router
pdf_rag
text_to_sql
evidence_merge
verifier
answer_generation
```

## 7. Tool Interfaces

### 7.1 Existing MCP Tools

当前 MCP Server 已有：

- `query_knowledge_hub`
- `list_collections`
- `get_document_summary`

这些工具继续保留。

### 7.2 Agent Layer Tools

推荐 Agent 层使用以下工具接口。

#### route_question

```json
{
  "question": "string"
}
```

返回 `RoutingDecision`。

#### query_pdf_evidence

```json
{
  "question": "string",
  "collection": "prospectus",
  "top_k": 5,
  "evidence_need": ["text", "table"]
}
```

返回 `EvidencePackage`。

#### text_to_sql_query

```json
{
  "question": "string",
  "database": "bs_challenge_financial",
  "max_rows": 50
}
```

返回 `SQL EvidencePackage`。

#### get_evidence_by_id

```json
{
  "element_id": "doc_p25_table_01"
}
```

返回 docstore 中的 raw evidence。

#### financial_qa

这是 Agent 的最终入口，不建议作为现有 RAG MCP 内部工具第一版实现。

```json
{
  "question": "string",
  "collection": "prospectus",
  "database": "bs_challenge_financial"
}
```

返回最终答案：

```json
{
  "answer": "string",
  "sources": [],
  "routing_decision": {},
  "verification_report": {}
}
```

### 7.3 MCP Exposure Strategy

第一阶段：

- 保持现有 MCP tools 不变。
- Agent 外部调用 `query_knowledge_hub` 和 `text_to_sql_query`。

第二阶段：

- 可以新增 `query_pdf_evidence`，返回更适合 Agent 消费的结构化 evidence。

第三阶段：

- 如果需要一站式工具，再暴露 `financial_qa`。

## 8. Verifier Rules

Verifier 在生成最终答案前运行。

### 8.1 Source Priority

冲突处理优先级：

1. 用户明确指定来源时，按指定来源优先。
2. 未指定来源时，按任务类型优先。
3. 仍冲突时，并列展示，不强行合并。

具体规则：

- 用户说“招股书披露”“PDF 中”“招股说明书”：优先 PDF Evidence。
- 用户说“数据库中”“行情表中”“基金持仓表中”：优先 SQL Evidence。
- 公司业务、风险、募投、客户供应商：优先 PDF Evidence。
- 行情、持仓、净值、份额、排名、统计计算：优先 SQL Evidence。

### 8.2 Numeric Consistency

数值校验规则：

- 单位必须保留，如元、万元、亿元、%。
- 表格数值和 SQL 数值比较前要做单位归一。
- 百分比和小数不能混用。
- 日期必须按问题要求对齐。
- 聚合口径必须说明，如求和、平均、最大值、报告期末。

### 8.3 Evidence Sufficiency

证据不足时：

- 不编造。
- 说明缺少哪类证据。
- 如果只缺少 PDF 证据但 SQL 有结果，明确“数据库结果如下，但未找到招股书披露依据”。
- 如果只缺少 SQL 证据但 PDF 有内容，明确“招股书披露如下，但未查询到数据库对应结果”。

### 8.4 Multimodal Confidence

图片和图表证据的置信度规则：

- Image caption 可用于语义解释。
- Chart summary 可用于趋势解释。
- 图表精确数值只有在 OCR/VLM 明确识别标签时才可使用。
- 精确财务数值优先使用 Table Evidence 或 SQL Evidence。

## 9. Evaluation

新系统评估要从单一 RAG 扩展为多层评估。

### 9.1 Router Evaluation

指标：

- `route_accuracy`
- `hybrid_mode_accuracy`
- `entity_extraction_f1`
- `evidence_need_accuracy`

Golden case 示例：

```json
{
  "query": "2021年某基金第一大重仓股对应公司的主营业务是什么？",
  "expected_route": "hybrid",
  "expected_hybrid_mode": "sql_first",
  "expected_evidence_need": ["sql_result", "text"]
}
```

### 9.2 PDF Evidence Evaluation

复用现有 `CustomEvaluator` 的 hit rate / MRR 思路，扩展 ground truth：

- `expected_element_ids`
- `expected_source_files`
- `expected_pages`
- `expected_evidence_type`

新增指标：

- `element_hit_rate`
- `page_hit_rate`
- `table_hit_rate`
- `context_precision`

### 9.3 Text-to-SQL Evaluation

指标：

- `sql_exec_success`
- `sql_result_exact_match`
- `sql_result_f1`
- `sql_safety_pass`
- `row_count_match`

SQL 评估要同时看：

- SQL 是否可执行。
- 是否只读。
- 结果是否正确。
- 单位、日期、聚合口径是否正确。

### 9.4 Hybrid Evaluation

指标：

- `sub_question_quality`
- `tool_sequence_accuracy`
- `cross_source_entity_match`
- `final_answer_correctness`
- `source_coverage`

### 9.5 Verifier Evaluation

构造冲突样例：

- PDF 和 SQL 结果一致。
- PDF 和 SQL 单位不同但可换算。
- PDF 和 SQL 口径不同不可合并。
- 用户明确指定来源。

指标：

- `conflict_detection_accuracy`
- `source_priority_accuracy`
- `abstention_accuracy`

### 9.6 EvalRunner Extension

现有 `EvalRunner` 可以扩展为 `FinancialEvalRunner`：

```text
load golden test set
  ↓
run Agent Router
  ↓
run selected evidence paths
  ↓
run Evidence Merger / Verifier
  ↓
compute route/sql/pdf/hybrid/final metrics
```

## 10. Failure Modes

### 10.1 PDF Parsing Failure

场景：

- MarkItDown 失败。
- pdfplumber 表格抽取失败。
- 页面是扫描页。

处理：

- MarkItDown 失败时 fallback 到 PyMuPDF text。
- 表格抽取失败时保留页面文本，不阻塞整篇 PDF。
- 扫描页进入 OCR fallback。
- Trace 记录 failed_pages 和 failed_elements。

### 10.2 Table Extraction Failure

场景：

- 表格跨页。
- 表头识别错误。
- 单元格合并导致列错位。

处理：

- 保留 raw page text。
- 表格 confidence 低时标记 `low_confidence`。
- 生成答案时提醒“表格抽取置信度较低”。
- 精确数值问题优先回查 raw table 或 PDF page。

### 10.3 Image and Chart Hallucination

场景：

- VLM 对图表数值产生幻觉。
- OCR 没识别出坐标轴和标签。

处理：

- caption/chart summary 只能作为解释性证据。
- 没有明确数字标签时禁止输出精确数值。
- Verifier 将 chart numeric evidence 标为低优先级。

### 10.4 Vector and BM25 Mismatch

场景：

- Chroma 写入成功但 BM25 索引失败。
- BM25 chunk_id 和 Chroma vector_id 不一致。

处理：

- 沿用现有逻辑：BM25 stats 在 upsert 后对齐 vector_ids。
- storage stage 失败时 ingestion 标记 failed。
- DocumentManager 删除时同时清理 Chroma、BM25、ImageStorage、Integrity、ElementDocstore。

### 10.5 Docstore Missing Raw Evidence

场景：

- 向量库召回了 element_id，但 docstore 没有 raw_content。

处理：

- fallback 使用 retrieved text。
- Evidence metadata 标记 `raw_fetch_failed=true`。
- Trace 记录 element_id。
- Verifier 降低该 evidence 的可信度。

### 10.6 SQL Failure

场景：

- LLM 生成非法 SQL。
- SQL 执行失败。
- schema linking 错误。
- 查询结果为空。

处理：

- SQL safety check 先于执行。
- 最多 repair 2 次。
- 结果为空时返回 empty evidence package，而不是编造。
- 记录 SQL、错误、repair 次数。

### 10.7 Router Ambiguity

场景：

- 问题同时可能走 PDF 和 DB。
- 实体名称不完整。

处理：

- 如果问题同时包含披露信息和计算/行情词，默认 hybrid。
- 如果实体无法解析，先走更宽的 PDF RAG 或 SQL schema search。
- 仍不确定时返回澄清问题。

### 10.8 Token Overflow

场景：

- 多个表格回填后 prompt 过长。

处理：

- 按 score 和 evidence type 排序。
- 表格只回填最相关行列。
- 超长 raw table 先做 table slice。
- Trace 记录被截断的 evidence_id。

## 11. Implementation Plan

### Phase 1: Table-aware PDF Ingestion

目标：最小改动提升 PDF 表格召回。

任务：

- 在 `PdfLoader` 或预处理脚本中抽取表格。
- 表格转 Markdown。
- 给表格加 page、table_id、element_id 标记。
- 重新 ingest PDF。

不做：

- 不新增 Agent Router。
- 不新增 native docstore。
- 不新增 MCP tool。

### Phase 2: Element Docstore

目标：支持 raw table 回填。

任务：

- 新增 `ElementDocstore`。
- 写入 `DocumentElement`。
- 向量库 metadata 写入 `element_id`。
- 查询时根据 `element_id` 回填 raw evidence。

### Phase 3: Text-to-SQL Path

目标：结构化 DB 查询成为独立 evidence path。

任务：

- 新增 schema registry。
- 新增 SQL generator。
- 新增 SQL safety checker。
- 新增 SQL executor。
- 返回 SQL EvidencePackage。

### Phase 4: Agent Router and Hybrid

目标：完成 Agentic RAG 编排。

任务：

- 新增 Router。
- 新增 doc_first 和 sql_first orchestration。
- 新增 Evidence Merger。
- 新增 Verifier。
- 新增 agent query trace。

### Phase 5: Evaluation and Failure Regression

目标：让系统可量化迭代。

任务：

- 扩展 golden test set。
- 增加 route/sql/pdf/hybrid/verifier 指标。
- 增加 failure mode regression cases。
- 在 Dashboard 或 CLI 中展示结果。

## 12. Recommended Module Layout

建议新增：

```text
src/agentic/
  router.py
  orchestrator.py
  evidence.py
  merger.py
  verifier.py

src/financial_sql/
  schema_registry.py
  sql_generator.py
  sql_safety.py
  sql_executor.py
  text_to_sql_tool.py

src/ingestion/elements/
  extractor.py
  table_extractor.py
  element_processor.py
  element_docstore.py

src/observability/evaluation/
  financial_eval_runner.py
```

尽量不要修改：

- `src/mcp_server/server.py`
- `src/mcp_server/protocol_handler.py`
- 现有 `query_knowledge_hub` 工具协议

## 13. Design Summary

这套新管线的本质是：

```text
现有 RAG MCP Server 继续做文档检索能力；
Agent Router 负责决定用文档、数据库还是混合；
PDF RAG 内部用 element evidence type 提升表格和多模态质量；
Text-to-SQL Path 独立负责数据库证据；
Evidence Merger / Verifier 统一生成可信答案。
```

最关键的工程取舍：

- Router 放 Agent 层，不放 MCP Server。
- Table Evidence 用 summary retrieval 和 raw generation。
- Text/Table/Image/Chart 是 PDF RAG 内部 evidence type，不是顶层 route。
- 所有 path 返回 EvidencePackage，最终答案统一由 Merger/Verifier 生成。

## 14. Implementation Notes

The first implementation pass is additive inside `MODULAR-RAG-MCP-SERVER/src`.
It includes deterministic financial question planning, shared agent contracts,
SQLite schema/formula registries, SELECT-only SQL safety, a safe SQLite executor,
entity resolution, a latest-industry SQL evidence facade, parsed TXT prospectus
evidence wrapping, evidence merge/verification, an orchestrator, evaluation
scaffolding, and a CLI smoke entry point.

This pass is intentionally conservative. Native PDF table recovery, complete
SQL generation for every dataset task family, SQL repair, deep `sql_first` /
`doc_first` hybrid sub-question chaining, full answer synthesis, MCP exposure,
and dashboard integration remain extension points for later iterations.
