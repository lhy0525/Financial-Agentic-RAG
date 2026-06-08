# Financial Agentic RAG 项目总览

## 当前定位

Financial Agentic RAG 是一个本地优先的金融问答与知识检索项目。它不是单纯的通用 RAG demo，而是在通用 RAG / MCP 底座之上，增加了金融问题规划、结构化 SQL 证据、招股书文档证据、证据合并与校验等 Agentic 层能力。

项目当前更适合被理解为：面向简历、演示和本地验证的 Financial Agentic RAG 系统原型。它支持从用户金融问题出发，规则优先生成结构化查询计划，优先使用结构化金融数据库生成可追溯 SQL Evidence，并在需要时结合招股书 TXT/PDF 检索证据，最终输出带 sources、plan、verification、trace 的答案。

## 核心链路

```text
User Question
  -> FinancialQuestionPlanner
  -> FinancialOrchestrator
  -> Text-to-SQL Evidence / Prospectus Evidence / Hybrid Path
  -> EvidenceMerger
  -> FinancialVerifier
  -> Answer with sources/plan/verification/trace
```

核心链路体现的是“先规划、再取证、后合并校验”的 Agentic RAG 形态：用户问题不会直接交给 LLM 自由生成答案，而是先由 planner 形成 `QuestionPlan`，再由 orchestrator 根据 route 选择 SQL、招股书或 hybrid 路径，最后将 evidence 汇总、校验并构建可追溯响应。

## 通用 RAG / MCP 底座

`src/core` 提供项目的基础类型合同、Hybrid Search、响应构建和 trace 能力，是上层 Agent 与工具之间共享的协议层。它定义了检索、证据、响应和跟踪信息的基本形态，使不同来源的内容可以进入统一回答链路。

`src/ingestion` 负责知识入库流程，包括 PDF 抽取、chunk、transform、embedding，以及 Chroma、BM25、image storage 等存储准备。它支撑了文档知识库和招股书资料的本地化检索能力。

`src/libs` 抽象了 LLM、Embedding、VectorStore、Reranker、Evaluator 等 provider 接口，使项目可以在不同模型、向量库、重排器和评估实现之间切换，而不把业务链路绑定到单一厂商。

`src/mcp_server` 提供 MCP stdio server，将知识检索能力暴露为工具接口，主要包括 `query_knowledge_hub`、`list_collections`、`get_document_summary`。这部分可以作为通用 RAG 知识工具底座，而不仅限于金融 Agent 场景。

## 金融 Agent 层

`src/agentic/planner.py` 中的 `FinancialQuestionPlanner` 负责把用户金融问题解析为 `QuestionPlan`。计划中会包含问题意图、可用证据路径、实体、指标、时间范围、路由建议等信息，为后续 SQL-first 或文档证据检索提供结构化输入。

`src/agentic/orchestrator.py` 是金融 Agent 的运行中枢。它根据 plan 和 route 调用 SQL Evidence Path、Prospectus Evidence Path 或 hybrid 路径，并协调后续 evidence merge、verification 与最终响应构建。

`src/agentic/merger.py` 负责合并来自不同来源的 evidence，同时保留 duplicate、source、trace 等元数据。这让最终答案可以说明证据来自结构化数据库、招股书检索结果，还是混合路径。

`src/agentic/verifier.py` 负责校验证据充分性、冲突、公式一致性和输出格式。它的定位不是替代业务审计，而是在回答生成前增加一层面向证据质量和金融口径一致性的检查。

## SQL Evidence Path

SQL Evidence Path 是项目的结构化证据主链路，适合回答财务指标、基金/股票实体、表格化金融数据和可通过数据库查询验证的问题。

`src/financial_sql/text_to_sql_tool.py` 根据 `QuestionPlan` 编译 `SELECT` SQL，并将查询结果包装为 `EvidencePackage`。简历表述中应强调“根据计划编译受控 SQL 并产出证据包”，不要表述为“直接让 LLM 任意生成 SQL”。

`src/financial_sql/sql_safety.py` 提供 SQL 安全约束：禁止写操作、多语句和注释，只允许 `SELECT`。这体现了项目对本地查询执行边界的控制。

`src/financial_sql/sql_executor.py` 负责 SQLite 查询执行、行数限制和可选日志记录。它是 SQL evidence 真正落地到本地数据库查询的执行层。

`src/financial_sql/schema_registry.py` 注册金融数据表、字段和 join hint，让 planner / SQL 编译过程可以基于已知 schema 和 join 线索工作。

`src/financial_sql/entity_resolver.py` 负责股票、基金实体解析，帮助把自然语言中的实体名称映射到结构化查询可用的标识。

## Prospectus Evidence Path

`src/prospectus_evidence` 将招股书 TXT/PDF 的检索结果包装为 evidence，使非结构化文件内容也能进入统一证据链路。它适合回答条款、风险披露、业务描述、募投信息等需要引用文档来源的问题。

这一链路依赖底层 ingestion 与检索能力，但在 Agent 层会把结果转成与 SQL evidence 兼容的证据结构，便于后续 merger、verifier 和 response builder 统一处理。

## Local Platform

`src/local_platform/prospectus_index.py` 管理上传文件索引，检查 Chroma / BM25 readiness，并构建招股书检索工具。它让本地上传的招股书资料可以进入文档 evidence path。

`src/local_platform/api.py` 提供 FastAPI 本地服务接口，包括健康检查、聊天、上传、历史 API。它是本地演示平台的后端入口，而不是云端多租户 SaaS 服务。

`src/local_platform/service.py` 负责懒创建 Orchestrator，并报告 SQL 与招股书索引状态。这样本地平台可以在启动后按需初始化金融 Agent 运行时，并向前端展示可用能力。

`frontend/src/App.jsx` 是 React / Vite 本地无登录演示界面，用于展示聊天、上传和本地平台状态等交互。它适合包装为本地演示 UI，不应包装为完整权限系统或生产级 Web 产品。

## Runtime Entry Points

常见运行入口包括：

```text
python scripts/financial_query.py "question" --db path/to.sqlite
python scripts/start_local_platform.py
cd frontend && npm run dev
python -m src.mcp_server.server
python scripts/ingest.py --path ... --financial-prospectus
```

这些入口分别覆盖命令行金融问答、本地 FastAPI 平台启动、React / Vite 前端开发服务、MCP stdio server，以及面向招股书的 ingestion 流程。

## 简历包装边界

可包装为：

- 本地优先金融 Agentic RAG 系统。
- SQL-first 结构化证据问答。
- 招股书文档证据检索。
- MCP + RAG 知识工具底座。
- FastAPI / React 本地演示平台。

不可包装为：

- 已生产上线多租户 SaaS。
- 云端托管服务。
- 完整权限系统。
- 直接 LLM 生成 SQL。
- 已验证真实商业指标。

简历表述应突出项目真实能力：本地运行、可追溯证据、受控 SQL、招股书检索、MCP 工具化、FastAPI / React 演示闭环。不要夸大为生产商业平台、真实金融投研系统或已获得线上业务指标的产品。
