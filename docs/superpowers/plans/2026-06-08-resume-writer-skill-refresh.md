# Resume Writer Skill Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh `.codex/skills/resume-writer` into a role-targeted Financial Agentic RAG resume-writing skill.

**Architecture:** Keep `SKILL.md` as a compact workflow and navigation file. Move project knowledge into focused references so future agents load only what a resume task needs.

**Tech Stack:** Codex skill Markdown, reference Markdown files, local project docs, Financial Agentic RAG architecture, Git.

---

## File Structure

- Modify: `.codex/skills/resume-writer/SKILL.md`
  - Responsibility: trigger definition, workflow, reference loading rules, output contract, honesty guardrails.
- Modify: `.codex/skills/resume-writer/references/resume_principles.md`
  - Responsibility: concise resume writing standards, four-part structure, quantification, anti-patterns.
- Create: `.codex/skills/resume-writer/references/project_overview.md`
  - Responsibility: current Financial Agentic RAG project narrative and boundaries.
- Modify: `.codex/skills/resume-writer/references/project_highlights.md`
  - Responsibility: canonical technical highlight library with resume wording and metrics angles.
- Create: `.codex/skills/resume-writer/references/role_profiles.md`
  - Responsibility: target-role-to-highlight mapping.
- Create: `.codex/skills/resume-writer/references/interview_followups.md`
  - Responsibility: likely interview questions and defensible answer directions.

## Implementation Tasks

### Task 1: Clean Resume Principles Reference

**Files:**
- Modify: `.codex/skills/resume-writer/references/resume_principles.md`

- [ ] **Step 1: Replace the existing reference with clean UTF-8 Chinese content**

Use this structure:

```markdown
# 简历编写原则（AI / RAG / Agent 项目方向）

## 1. 四段式项目结构

简历项目经历必须按“背景 -> 目标 -> 过程 -> 结果”组织。

- 背景：说明业务场景、服务对象、信息来源、痛点。
- 目标：说明要解决什么问题，要建设什么能力。
- 过程：用 4-6 条 bullet 描述个人主导的关键技术实现。
- 结果：用 2-3 句汇总可量化成果。

## 2. Bullet 写法

每条 bullet 使用“动作 + 技术方案 + 工程细节 + 结果”的结构。

推荐动词：

- 设计
- 实现
- 构建
- 优化
- 集成
- 主导
- 建立

避免动词：

- 参与
- 协助
- 了解
- 负责相关工作

## 3. 量化原则

优先使用用户提供的真实数据。没有真实数据时，只能给“建议指标”，并明确提示用户确认。

可量化维度：

- 检索质量：Hit Rate@K、MRR、Top-1 命中率。
- 响应性能：端到端延迟、SQL 查询耗时、索引耗时。
- 工程规模：文档数、chunk 数、测试用例数、支持 provider 数。
- 稳定性：失败回退路径、SQL 安全拦截、重复摄取跳过率。
- 交付效率：自动化测试覆盖、CLI/API/UI 入口数量。

## 4. 技术标签

根据岗位选择关键词，不要堆无关工具。

- RAG：Hybrid Search、BM25、Dense Retrieval、RRF、Rerank、Chroma、Embedding。
- Agent：Planner、Orchestrator、Tool Calling、Evidence Package、Verifier、MCP。
- Backend：FastAPI、SQLite、JSON-RPC、配置驱动、工厂模式、CLI。
- Financial AI：Text-to-SQL、SQL Safety、Schema Registry、Entity Resolution、Golden Evaluation。
- Frontend Demo：React、Vite、本地无登录平台、上传索引状态、Trace 展示。

## 5. 诚实包装边界

允许强调：

- 本地优先金融问答系统。
- SQL-first evidence path。
- 招股书 PDF/TXT 上传与索引。
- MCP 标准工具服务。
- 证据合并、校验与可追溯来源。

禁止声称：

- 已上线生产 SaaS。
- 已实现 OAuth/JWT、多租户隔离或云端托管。
- 使用 CLIP、FAISS 或未实现的向量库。
- 直接用 LLM 生成 SQL。
- 有真实业务指标但用户未提供数据。

## 6. 输出前检查

生成结果前逐项检查：

- 是否包含背景、目标、过程、结果。
- bullet 是否以主动动词开头。
- 是否体现个人贡献。
- 是否有至少 3 个量化点或建议量化点。
- 是否没有虚构生产能力。
- 技术栈是否与岗位方向匹配。
```

- [ ] **Step 2: Review the file for concise wording**

Run: `Get-Content -Path .codex\skills\resume-writer\references\resume_principles.md`

Expected: the file is readable UTF-8 Chinese and contains the six sections above.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\references\resume_principles.md
git commit -m "docs: refresh resume writing principles"
```

Expected: one commit containing only `resume_principles.md`.

### Task 2: Add Current Project Overview Reference

**Files:**
- Create: `.codex/skills/resume-writer/references/project_overview.md`

- [ ] **Step 1: Create the overview reference**

Write this content:

```markdown
# Financial Agentic RAG 项目总览

## 当前定位

Financial Agentic RAG 是一个本地优先的金融问答系统，建立在 Modular RAG MCP Server 底座之上。项目将通用 RAG 检索、MCP 工具服务、结构化 SQL 证据、招股书文档证据、Agent 编排、证据校验和本地演示平台组合成一套可解释、可测试、可扩展的金融 AI 应用。

## 核心链路

```text
User Question
  -> FinancialQuestionPlanner
  -> FinancialOrchestrator
  -> Text-to-SQL Evidence / Prospectus Evidence / Hybrid Path
  -> EvidenceMerger
  -> FinancialVerifier
  -> Answer with sources, question plan, verification report, trace
```

## 通用 RAG / MCP 底座

- `src/core`：配置、类型合同、Hybrid Search、响应构建、Trace。
- `src/ingestion`：PDF 摄取、chunk、transform、embedding、Chroma/BM25/image storage。
- `src/libs`：LLM、Embedding、VectorStore、Reranker、Evaluator 等 provider 抽象。
- `src/mcp_server`：MCP stdio server 与 `query_knowledge_hub`、`list_collections`、`get_document_summary` 工具。

## 金融 Agent 层

- `src/agentic/planner.py`：规则优先的问题规划器，输出 `QuestionPlan`。
- `src/agentic/orchestrator.py`：根据 route 调用 SQL、招股书或混合路径。
- `src/agentic/merger.py`：合并证据并保留 duplicate/source/trace 元数据。
- `src/agentic/verifier.py`：检查证据充分性、冲突、公式一致性和输出格式。

## SQL Evidence Path

- `src/financial_sql/text_to_sql_tool.py`：根据 plan 编译 SELECT SQL，执行并包装成 `EvidencePackage`。
- `src/financial_sql/sql_safety.py`：禁止写操作、多语句和注释，只允许 SELECT。
- `src/financial_sql/sql_executor.py`：SQLite 查询执行、行数限制、可选日志。
- `src/financial_sql/schema_registry.py`：金融数据表、字段和 join hint 注册。
- `src/financial_sql/entity_resolver.py`：股票、基金实体解析。

## Prospectus Evidence Path

- `src/prospectus_evidence`：招股书 TXT/PDF 检索结果包装为 evidence。
- `src/local_platform/prospectus_index.py`：上传文件索引、Chroma/BM25 readiness 检查、构建检索工具。

## Local Platform

- `src/local_platform/api.py`：FastAPI 提供健康检查、聊天、上传、历史 API。
- `src/local_platform/service.py`：懒创建 Orchestrator，报告 SQL 和招股书索引状态。
- `frontend/src/App.jsx`：React/Vite 本地无登录演示界面。

## Runtime Entry Points

- `python scripts/financial_query.py "question" --db path/to.sqlite`
- `python scripts/start_local_platform.py`
- `cd frontend && npm run dev`
- `python -m src.mcp_server.server`
- `python scripts/ingest.py --path ... --financial-prospectus`

## 简历包装边界

可包装为：

- 本地优先金融 Agentic RAG 系统。
- SQL-first 结构化证据问答。
- 招股书文档证据检索。
- MCP + RAG 知识工具底座。
- FastAPI/React 本地演示平台。

不可包装为：

- 已生产上线的多租户 SaaS。
- 云端托管服务。
- 完整权限系统。
- 直接 LLM 生成 SQL。
- 已验证真实商业指标。
```

- [ ] **Step 2: Review the file**

Run: `Get-Content -Path .codex\skills\resume-writer\references\project_overview.md`

Expected: the file describes the updated Financial Agentic RAG project and contains no claims of production SaaS deployment.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\references\project_overview.md
git commit -m "docs: add financial rag resume overview"
```

Expected: one commit containing only `project_overview.md`.

### Task 3: Rewrite Technical Highlight Library

**Files:**
- Modify: `.codex/skills/resume-writer/references/project_highlights.md`

- [ ] **Step 1: Replace the old Modular RAG-only highlights**

Use this content structure and write each highlight with the four subsections shown:

```markdown
# Financial Agentic RAG 技术亮点库

> 用于按岗位方向选择 4-6 个亮点生成简历项目经历。每个亮点包含技术要点、简历话术方向、量化角度和诚实边界。

## 亮点 1：Modular RAG / MCP 底座

### 技术要点

- 基于 Document、Chunk、ChunkRecord、RetrievalResult 等统一类型合同组织 RAG 链路。
- 保留 MCP stdio server，暴露 `query_knowledge_hub`、`list_collections`、`get_document_summary` 三类工具。
- 使用 JSON-RPC / MCP 标准协议，让外部 AI client 调用私有知识检索能力。

### 简历话术方向

设计并实现 MCP 标准知识检索服务，将私有文档检索能力封装为可被 AI Agent 调用的工具接口，支持检索结果、引用来源与多模态内容返回。

### 量化角度

- MCP tools 数量。
- E2E JSON-RPC 协议测试数量。
- 支持的 client 类型。

### 诚实边界

不要声称该 MCP Server 已部署到云端生产环境。

## 亮点 2：Hybrid Search 检索链路

### 技术要点

- Dense Retrieval 使用 embedding + vector store 做语义召回。
- Sparse Retrieval 使用 BM25 做关键词召回。
- HybridSearch 并行执行 dense/sparse，使用 RRF 融合排序。
- Reranker 可配置为 none、cross encoder 或 LLM rerank，并支持失败回退。

### 简历话术方向

构建 Dense + Sparse + RRF 的混合检索架构，兼顾语义召回和关键词精确匹配，并通过可选 rerank 提升 Top-K 结果质量。

### 量化角度

- Hit Rate@K。
- MRR。
- Top-K 延迟。
- rerank 前后命中率变化。

### 诚实边界

没有真实评测数据时，只写“建议用 Hit Rate@K / MRR 衡量”，不要编造提升百分比。

## 亮点 3：配置驱动 Provider 架构

### 技术要点

- LLM、Embedding、VectorStore、Reranker、Evaluator 使用 base interface + factory。
- `config/settings.example.yaml` 支持 OpenAI、Azure、Ollama、DeepSeek、Zhipu 等 provider 配置。
- Prompt 模板外置到 `config/prompts`。

### 简历话术方向

设计配置驱动的可插拔 provider 架构，实现 LLM、Embedding、VectorStore、Reranker 等核心组件的低成本切换。

### 量化角度

- provider 类型数量。
- 核心 factory 数量。
- 配置切换是否零业务代码改动。

### 诚实边界

只声称配置和代码支持的 provider，不声称所有 provider 都经过真实 API 回归。

## 亮点 4：Ingestion Pipeline 与本地索引

### 技术要点

- Pipeline 包含 integrity、load、split、transform、embed、upsert 六阶段。
- 使用 SHA256 和 SQLite ingestion history 支持重复摄取跳过。
- 同步写入 Chroma、BM25、ImageStorage。
- 上传招股书时可关闭 transform 和 image extraction，降低本地演示成本。

### 简历话术方向

实现六阶段文档摄取流水线，完成 PDF 解析、语义切分、向量化、BM25 索引和本地持久化，并通过 SHA256 去重保证增量摄取幂等性。

### 量化角度

- 文档数。
- chunk 数。
- 重复摄取跳过率。
- 单文档索引耗时。

### 诚实边界

不要声称已支持所有 Office 文件格式；当前主要围绕 PDF/TXT。

## 亮点 5：Financial Question Planner

### 技术要点

- `FinancialQuestionPlanner` 使用规则和正则抽取实体、时间、公式、输出约束。
- 输出结构化 `QuestionPlan`，包含 route、task_type、entities、time_scope、formula、evidence_need、sub_questions。
- 支持 `pdf_rag`、`text_to_sql`、`hybrid` 三类 route。

### 简历话术方向

构建规则优先的金融问题规划器，将自然语言问题转化为结构化执行计划，为 SQL evidence、招股书 evidence 和 hybrid 编排提供稳定输入。

### 量化角度

- 支持的 route 数量。
- 支持的公式类型数量。
- boundary case 测试数量。

### 诚实边界

不要写成通用 LLM router；当前主要是规则优先规划器。

## 亮点 6：规则编译型 Text-to-SQL Evidence Path

### 技术要点

- `TextToSQLEvidenceTool` 根据 `QuestionPlan` 编译 SELECT SQL。
- 使用 `FinancialSchemaRegistry` 管理 10 类金融数据表、字段和 join hints。
- 使用 `EntityResolver` 做股票和基金实体解析。
- 查询结果包装为 `EvidencePackage`，包含 SQL、表名、列、行、耗时、安全检查结果。

### 简历话术方向

实现规则编译型 Text-to-SQL 证据路径，根据结构化计划生成安全 SELECT 查询，并将结果封装为可追溯的 SQL EvidencePackage。

### 量化角度

- 支持的金融表数量。
- 支持的 task_type 数量。
- SQL 执行成功率。
- 查询平均耗时。

### 诚实边界

必须写“规则编译型 Text-to-SQL”，不要写“LLM 自动生成 SQL”。

## 亮点 7：SQL Safety 与执行保护

### 技术要点

- `SQLSafetyChecker` 只允许 SELECT。
- 拦截 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、PRAGMA 等危险语句。
- 禁止多语句、SQL 注释和非 SELECT 入口。
- 对非聚合查询自动追加默认 LIMIT。

### 简历话术方向

设计 SQL 安全校验机制，在执行前拦截写操作、多语句和管理语句，并为查询自动施加行数限制，降低本地金融数据库被误操作的风险。

### 量化角度

- 拦截规则数量。
- 安全测试 case 数量。
- row cap 配置。

### 诚实边界

不要声称这是完整数据库安全网关；它是本地 demo 的 SELECT-only safety guard。

## 亮点 8：Evidence Merger / Financial Verifier

### 技术要点

- `EvidenceMerger` 合并多路径 evidence，按 evidence_id 和 source/content 去重。
- 保留 duplicate evidence ids、source、package path、trace ids。
- `FinancialVerifier` 检查证据缺失、事实冲突、公式一致性、单位和格式。
- 根据 verification status 输出 pass、partial、conflict、insufficient。

### 简历话术方向

设计证据合并与校验模块，在最终回答前统一处理 SQL 和文档证据的去重、溯源、缺失与冲突，提升金融问答结果的可解释性和可信度。

### 量化角度

- verifier 覆盖的冲突类型。
- verification status 类型数量。
- merger / verifier 单元测试数量。

### 诚实边界

不要声称完全消除幻觉；应写“降低幻觉风险、增强可追溯性”。

## 亮点 9：Prospectus Evidence 与上传索引

### 技术要点

- 支持 PDF/TXT 招股书上传。
- 上传后保存本地文件、解析文本、尝试索引到 Chroma/BM25。
- `LocalProspectusIndexService` 明确报告 `indexed_searchable`、`already_indexed`、`index_failed` 等状态。
- `ProspectusEvidenceTool` 将检索结果包装为 text/table evidence。

### 简历话术方向

实现招股书证据检索路径，支持本地 PDF/TXT 上传、解析、索引和检索，并通过明确 readiness 状态避免前端误报可搜索能力。

### 量化角度

- 上传文件类型数量。
- readiness 状态数量。
- indexed/searchable 状态测试数量。

### 诚实边界

不要声称已完成完整 native table docstore；当前主要是文本检索和 table placeholder 识别。

## 亮点 10：FastAPI + React 本地演示平台

### 技术要点

- FastAPI 提供 `/api/health`、`/api/platform`、`/api/chat`、`/api/prospectus/upload`、`/api/history`。
- React/Vite 前端展示知识库状态、上传入口、聊天结果、sources、verification 和 trace。
- 平台无登录、local-first，适合项目演示和面试讲解。

### 简历话术方向

构建 FastAPI + React 本地演示平台，将金融 Agentic RAG 的健康检查、文件上传、问答结果、证据来源和执行 trace 可视化呈现。

### 量化角度

- API 端点数量。
- 前端状态面板数量。
- 前端测试和 build 结果。

### 诚实边界

不要声称有登录、权限、多用户隔离或云端部署。

## 亮点 11：金融评测与边界用例

### 技术要点

- `FinancialEvalRunner` 对 agent 输出做 route、verification、source、tool sequence 等评估。
- fixtures 包含 financial boundary planner/eval cases。
- 通用 EvalRunner 仍支持 Hit Rate、MRR 等检索评估。

### 简历话术方向

建立金融问答边界评测体系，用 golden cases 检查路由、SQL safety、证据类型、verification 状态和工具调用顺序，为策略迭代提供回归基线。

### 量化角度

- golden case 数量。
- 评测指标数量。
- 单元/集成/E2E 测试数量。

### 诚实边界

没有真实线上业务反馈时，只写离线评测和回归测试。
```

- [ ] **Step 2: Review the rewritten highlight library**

Run: `Get-Content -Path .codex\skills\resume-writer\references\project_highlights.md`

Expected: the file contains 11 highlights and each highlight has 技术要点、简历话术方向、量化角度、诚实边界.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\references\project_highlights.md
git commit -m "docs: refresh financial rag highlights"
```

Expected: one commit containing only `project_highlights.md`.

### Task 4: Add Role Profiles Reference

**Files:**
- Create: `.codex/skills/resume-writer/references/role_profiles.md`

- [ ] **Step 1: Create role mapping reference**

Write this content:

```markdown
# 岗位画像与亮点映射

## RAG Engineer

### 优先亮点

1. Hybrid Search 检索链路。
2. Ingestion Pipeline 与本地索引。
3. Modular RAG / MCP 底座。
4. 配置驱动 Provider 架构。
5. 金融评测与边界用例。

### 关键词

RAG, Hybrid Search, Dense Retrieval, BM25, RRF, Rerank, Chroma, Embedding, MCP, Evaluation.

### 叙事角度

强调检索质量、可插拔架构、索引链路、可观测和评测闭环。

### 弱化内容

弱化前端 UI 细节和本地演示平台视觉实现。

## Agent Engineer

### 优先亮点

1. Financial Question Planner。
2. Evidence Merger / Financial Verifier。
3. 规则编译型 Text-to-SQL Evidence Path。
4. Prospectus Evidence 与上传索引。
5. Modular RAG / MCP 底座。

### 关键词

Agentic RAG, Planner, Orchestrator, Tool Calling, Evidence Package, Verifier, Hybrid Path, MCP.

### 叙事角度

强调 Agent 层如何规划问题、选择工具、合并证据、校验答案，并解释为什么 Router 放在 Agent 层。

### 弱化内容

弱化传统模型训练和微调叙事。

## Backend Engineer

### 优先亮点

1. FastAPI + React 本地演示平台中的 FastAPI API。
2. SQL Safety 与执行保护。
3. 配置驱动 Provider 架构。
4. Ingestion Pipeline 与本地索引。
5. MCP stdio server。

### 关键词

FastAPI, SQLite, API Design, SQL Safety, JSON-RPC, MCP, Configuration, Factory Pattern, Local-first.

### 叙事角度

强调接口设计、状态管理、错误处理、配置驱动和本地可靠性。

### 弱化内容

弱化深度学习模型本身。

## LLM Application Engineer

### 优先亮点

1. Financial Agentic RAG 总体架构。
2. Hybrid Search 检索链路。
3. Evidence Merger / Financial Verifier。
4. Prospectus Evidence 与上传索引。
5. 配置驱动 Provider 架构。

### 关键词

LLM Application, RAG, Agentic Workflow, Prompt Templates, Provider Abstraction, Traceability, Evaluation.

### 叙事角度

强调把 LLM 能力工程化接入私有知识、结构化数据和可追溯证据。

### 弱化内容

弱化底层训练框架和模型微调。

## Financial AI / Data Engineer

### 优先亮点

1. 规则编译型 Text-to-SQL Evidence Path。
2. SQL Safety 与执行保护。
3. Financial Question Planner。
4. 金融评测与边界用例。
5. Evidence Merger / Financial Verifier。

### 关键词

Financial QA, Text-to-SQL, SQLite, Schema Registry, Entity Resolution, SQL Safety, Golden Cases, Verification.

### 叙事角度

强调金融数据表、实体解析、公式计算、安全查询和证据校验。

### 弱化内容

弱化通用文档 RAG 的多模态包装。

## Full-stack AI Demo / AI Product Engineer

### 优先亮点

1. FastAPI + React 本地演示平台。
2. Prospectus Evidence 与上传索引。
3. Financial Agentic RAG 总体架构。
4. Evidence Merger / Financial Verifier。
5. MCP / RAG 底座。

### 关键词

FastAPI, React, Vite, Local Demo, Upload, Health Check, Sources, Trace, Verification Report.

### 叙事角度

强调从后端问答链路到前端可视化交互的端到端交付能力。

### 弱化内容

弱化大规模生产运维和云部署能力。
```

- [ ] **Step 2: Review role coverage**

Run: `Get-Content -Path .codex\skills\resume-writer\references\role_profiles.md`

Expected: the file contains six role profiles and each has 优先亮点、关键词、叙事角度、弱化内容.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\references\role_profiles.md
git commit -m "docs: add resume role profiles"
```

Expected: one commit containing only `role_profiles.md`.

### Task 5: Add Interview Follow-up Reference

**Files:**
- Create: `.codex/skills/resume-writer/references/interview_followups.md`

- [ ] **Step 1: Create interview follow-up guide**

Write this content:

```markdown
# 简历项目面试追问准备

## 1. 为什么 Router 放在 Agent 层，而不是 MCP Server？

回答方向：

- MCP Server 负责稳定暴露通用知识检索工具。
- 金融问题路由涉及业务意图、SQL 证据、文档证据和 hybrid 编排，更适合放在 Agent 层。
- 这样可以保持 MCP 工具边界稳定，同时让 Agent 根据任务动态组合工具。

## 2. 为什么 Text-to-SQL 用规则编译，而不是直接让 LLM 生成 SQL？

回答方向：

- 金融数据查询需要安全、可解释、可测试。
- 当前问题类型和表结构相对明确，规则编译能降低幻觉和危险 SQL 风险。
- `QuestionPlan` 先结构化实体、时间、公式和 task_type，再编译 SELECT。
- LLM SQL 可以作为未来扩展，但不能替代当前安全边界。

## 3. SQL Safety 怎么保证？

回答方向：

- 只允许 SELECT。
- 禁止多语句、注释、写操作、DDL 和管理语句。
- 对普通查询自动追加 LIMIT。
- 查询执行结果包含 safety metadata，便于审计。

## 4. `sql_first` 和 `doc_first` hybrid 怎么设计？

回答方向：

- `sql_first`：先用数据库解析实体、排名、日期或结构化事实，再查文档解释背景。
- `doc_first`：先用招股书或文档找到披露、实体或业务上下文，再查询数据库。
- Orchestrator 根据 `QuestionPlan.sub_questions` 顺序调用工具，并把前一步 evidence metadata 注入后续问题。

## 5. EvidencePackage 有什么价值？

回答方向：

- 所有路径都返回证据包，而不是直接返回最终自然语言答案。
- EvidencePackage 包含 source、content、metadata、trace_id。
- Merger 和 Verifier 可以统一处理 SQL 和文档证据，避免每条路径各自生成不可比较的答案。

## 6. Verifier 解决了什么问题？

回答方向：

- 检查证据是否缺失。
- 检查事实冲突、公式结果、单位、日期和格式。
- 输出 pass、partial、conflict、insufficient，让前端和用户知道答案可信程度。
- 它不能完全消除幻觉，但能显著提升可追溯性和拒答能力。

## 7. 招股书上传为什么要报告 indexed/searchable 状态？

回答方向：

- 上传成功不等于检索可用。
- 文件可能保存成功但解析失败，也可能解析成功但 embedding provider 不可用。
- 平台明确报告 `indexed_searchable`、`already_indexed`、`index_failed`，避免前端误导用户。

## 8. 这个项目和普通 RAG Demo 的区别是什么？

回答方向：

- 不只做文档检索，还引入结构化 SQL evidence。
- 不只返回答案，还返回 question plan、sources、verification report、trace。
- 有金融领域规则、实体解析、SQL safety 和 golden boundary evaluation。
- 保留 MCP 工具能力，可以被外部 Agent 调用。

## 9. 这个项目离生产系统还差什么？

回答方向：

- 需要鉴权、权限控制、多租户隔离。
- 需要云端部署、监控告警、并发和容量规划。
- 需要真实业务数据评测和人工反馈闭环。
- 需要更强的 PDF table extraction 和 raw evidence docstore。

## 10. 面试中被问量化指标怎么办？

回答方向：

- 区分真实数据和建议指标。
- 已有测试可说单元、集成、E2E 覆盖方向。
- 检索质量建议用 Hit Rate@K、MRR。
- SQL 路径建议用执行成功率、安全拦截率、entity resolution 成功率。
- 本地平台建议用 API 延迟、上传索引耗时、错误状态覆盖率。
```

- [ ] **Step 2: Review interview guide**

Run: `Get-Content -Path .codex\skills\resume-writer\references\interview_followups.md`

Expected: the file contains 10 follow-up questions with concrete answer directions.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\references\interview_followups.md
git commit -m "docs: add resume interview followups"
```

Expected: one commit containing only `interview_followups.md`.

### Task 6: Rewrite SKILL.md Workflow and Reference Navigation

**Files:**
- Modify: `.codex/skills/resume-writer/SKILL.md`

- [ ] **Step 1: Replace SKILL.md with a compact workflow**

Write this content:

```markdown
---
name: resume-writer
description: "Generate role-targeted resume project experience, interview talking points, and bilingual resume wording for the Financial Agentic RAG / Modular RAG MCP Server project. Use when the user says 写简历, 简历, resume, write resume, 项目经历, project experience, 简历项目, 面试项目包装, or asks to package this project for RAG Engineer, Agent Engineer, Backend Engineer, LLM Application Engineer, Financial AI, or full-stack AI roles."
---

# Resume Writer

Use this skill to turn the current Financial Agentic RAG project into honest, role-targeted resume content.

## Core Rule

Do not invent production adoption, cloud deployment, authentication, multi-tenant isolation, unsupported model providers, or fake metrics. When metrics are not supplied by the user, label them as suggested metrics and ask the user to confirm.

## Reference Loading

Always read:

1. `references/resume_principles.md`
2. `references/project_overview.md`

Read as needed:

- `references/role_profiles.md` when the user has a target role or asks for role-specific packaging.
- `references/project_highlights.md` when selecting technical bullets.
- `references/interview_followups.md` when preparing interview questions or explaining how to defend the resume.

## Workflow

### Phase 1: Collect User Inputs

Ask concise questions in Chinese unless the user requests English.

Collect:

- Target role: RAG Engineer, Agent Engineer, Backend Engineer, LLM Application Engineer, Financial AI / Data Engineer, Full-stack AI Demo, or custom.
- Business framing: real business background, financial AI demo, or generic enterprise knowledge-base project.
- Technical emphasis: RAG retrieval, Agent orchestration, Text-to-SQL, SQL safety, MCP, local platform, evaluation, or full-stack delivery.
- Output format: Chinese, English, bilingual, bullet-only, full project entry, or interview prep.
- Real metrics if available.

If the user gives incomplete information, make reasonable assumptions and clearly mark them.

### Phase 2: Select Highlights

Use `role_profiles.md` to choose 4-6 relevant highlights.

Then use `project_highlights.md` to extract:

- Technical point.
- Resume wording direction.
- Quantification angle.
- Honesty boundary.

### Phase 3: Generate Resume Content

Use the four-part structure from `resume_principles.md`:

```text
项目名称 | 时间 | 角色

背景：2-3 句
目标：1-2 句
过程：4-6 条 bullet
结果：2-3 句
技术栈：按岗位权重排序
```

Bullet rules:

- Start with an active verb.
- State the technical decision, implementation detail, and impact.
- Include concrete module names when useful.
- Include metrics or suggested metrics.
- Keep each bullet concise enough for a resume.

### Phase 4: Prepare Interview Defense

After generating the resume entry, provide 5-8 likely interview follow-up questions.

Use `interview_followups.md` to choose questions that match the selected highlights.

### Phase 5: Iterate

Ask whether the user wants:

- More backend-oriented wording.
- More Agent-oriented wording.
- More financial-domain wording.
- A shorter resume version.
- An English or bilingual version.
- STAR story expansion for interviews.

## Output Guardrails

Before responding, check:

- The project is described as Financial Agentic RAG, not only generic Modular RAG.
- The resume includes SQL evidence, Agent planning, verification, or local platform details when relevant.
- The wording does not claim direct LLM SQL generation.
- Suggested metrics are clearly marked when not user-provided.
- The final result is suitable for the target role.
```

- [ ] **Step 2: Review trigger and navigation**

Run: `Get-Content -Path .codex\skills\resume-writer\SKILL.md`

Expected: `description` mentions Financial Agentic RAG and role-targeted resume content; body references all five reference files.

- [ ] **Step 3: Commit**

Run:

```powershell
git add .codex\skills\resume-writer\SKILL.md
git commit -m "docs: update resume writer workflow"
```

Expected: one commit containing only `SKILL.md`.

### Task 7: End-to-End Skill Content Review

**Files:**
- Review: `.codex/skills/resume-writer/SKILL.md`
- Review: `.codex/skills/resume-writer/references/resume_principles.md`
- Review: `.codex/skills/resume-writer/references/project_overview.md`
- Review: `.codex/skills/resume-writer/references/project_highlights.md`
- Review: `.codex/skills/resume-writer/references/role_profiles.md`
- Review: `.codex/skills/resume-writer/references/interview_followups.md`

- [ ] **Step 1: Confirm all expected files exist**

Run:

```powershell
rg --files .codex\skills\resume-writer
```

Expected output includes:

```text
.codex\skills\resume-writer\SKILL.md
.codex\skills\resume-writer\references\resume_principles.md
.codex\skills\resume-writer\references\project_overview.md
.codex\skills\resume-writer\references\project_highlights.md
.codex\skills\resume-writer\references\role_profiles.md
.codex\skills\resume-writer\references\interview_followups.md
```

- [ ] **Step 2: Scan for forbidden unresolved markers**

Run:

```powershell
Select-String -Path .codex\skills\resume-writer\SKILL.md,.codex\skills\resume-writer\references\*.md -Pattern 'TODO|TBD|placeholder'
```

Expected: no matches.

- [ ] **Step 3: Scan for forbidden production claims**

Run:

```powershell
Select-String -Path .codex\skills\resume-writer\SKILL.md,.codex\skills\resume-writer\references\*.md -Pattern 'OAuth|JWT|multi-tenant|SaaS|CLIP|FAISS|cloud deployment|LLM 自动生成 SQL'
```

Expected: matches only appear inside honesty-boundary or forbidden-claim sections.

- [ ] **Step 4: Do a manual dry run**

Use the skill instructions to generate a short Chinese project entry for this prompt:

```text
帮我写一版 Agent Engineer 方向的项目经历，业务背景用金融 AI 本地演示平台，强调 Planner、Text-to-SQL、EvidencePackage、Verifier，指标先给建议值。
```

Expected:

- Output uses background, goal, process, result.
- Output mentions Financial Agentic RAG.
- Output does not claim production SaaS or direct LLM SQL generation.
- Output marks metrics as suggested values.
- Output includes interview follow-up questions.

- [ ] **Step 5: Commit review adjustments if any were needed**

If Step 1-4 required edits, commit them:

```powershell
git add .codex\skills\resume-writer
git commit -m "docs: polish resume writer references"
```

Expected: commit only skill reference polish. If no edits were needed, skip this commit.

### Task 8: Final Verification

**Files:**
- Review: `.codex/skills/resume-writer`

- [ ] **Step 1: Check git status**

Run:

```powershell
git status --short
```

Expected: clean working tree.

- [ ] **Step 2: Show recent commits**

Run:

```powershell
git log --oneline -6
```

Expected: recent commits include the design commit and the resume-writer refresh commits.

- [ ] **Step 3: Report completion**

Report:

- Files changed.
- New reference structure.
- Verification commands and results.
- Any metrics still requiring user confirmation.

## Self-Review

### Spec Coverage

- Compact `SKILL.md`: Task 6.
- `resume_principles.md`: Task 1.
- `project_overview.md`: Task 2.
- `project_highlights.md`: Task 3.
- `role_profiles.md`: Task 4.
- `interview_followups.md`: Task 5.
- Honesty rules: Tasks 1, 2, 3, 6, 7.
- Acceptance checks: Tasks 7 and 8.

### Placeholder Scan

The plan contains no unresolved TODO, TBD, or placeholder requirements. The only occurrence of the word `placeholder` is inside the explicit scan command in Task 7.

### Scope Check

The plan only updates `.codex/skills/resume-writer` and does not modify application code, runtime configuration, tests, frontend, or unrelated skills.

