# 岗位画像与亮点映射

用于帮助 resume-writer 根据目标岗位选择 Financial Agentic RAG 的技术亮点。所有亮点编号与名称必须对齐 `project_highlights.md`，不要扩写成虚构的生产 SaaS、多租户、云部署或真实商业指标。

---

## RAG Engineer

### 优先亮点

1. 亮点 2：Hybrid Search 检索链路
2. 亮点 4：Ingestion Pipeline 与本地索引
3. 亮点 1：Modular RAG / MCP 底座
4. 亮点 3：配置驱动 Provider 架构
5. 亮点 11：金融评测与边界用例

### 关键词

Hybrid Search, Dense Retrieval, BM25, RRF, Rerank, Chroma, BM25 Index, Ingestion Pipeline, Chunking, Embedding, MCP, Retrieval Evaluation, Hit Rate@K, MRR

### 叙事角度

简历应突出从文档摄取、本地索引、混合检索到离线评测的完整 RAG 链路建设能力。重点说明如何通过 Dense + BM25 + RRF、可选 rerank 和失败回退提升本地金融文档检索的鲁棒性。

### 弱化内容

不要突出前端 UI、本地演示视觉效果、云端生产部署或真实线上指标；没有评测数据时不要编造召回率提升比例。

---

## Agent Engineer

### 优先亮点

1. 亮点 5：Financial Question Planner
2. 亮点 8：Evidence Merger / Financial Verifier
3. 亮点 6：规则编译型 Text-to-SQL Evidence Path
4. 亮点 9：Prospectus Evidence 与上传索引
5. 亮点 1：Modular RAG / MCP 底座

### 关键词

Agent Tooling, Question Planning, Tool Routing, MCP, JSON-RPC, Evidence Path, Text-to-SQL, Evidence Merger, Financial Verifier, Traceability, PDF RAG, Hybrid Route

### 叙事角度

简历应讲清楚如何把金融问题拆成结构化计划，并编排 PDF RAG、Text-to-SQL 和 Hybrid 证据路径。强调 Planner、Evidence Merger 与 Verifier 让 Agent 输出更可追溯、更容易校验。

### 弱化内容

不要突出模型训练、微调、RLHF 或通用大模型能力；不要把规则优先 planner 写成完全由 LLM 自主决策的通用 router。

---

## Backend Engineer

### 优先亮点

1. 亮点 10：FastAPI + React 本地演示平台
2. 亮点 7：SQL Safety 与执行保护
3. 亮点 3：配置驱动 Provider 架构
4. 亮点 4：Ingestion Pipeline 与本地索引
5. 亮点 1：Modular RAG / MCP 底座

### 关键词

FastAPI, API Design, Health Check, Upload API, Chat API, Lazy Initialization, SQL Safety, SELECT-only Guard, Provider Factory, Config-driven Architecture, SQLite, Chroma, MCP Server

### 叙事角度

简历应以后端服务化和工程边界为主线，突出 FastAPI 本地 API、Provider 可插拔架构、摄取索引流程和 SQL 执行保护。可以说明 React 只是演示入口，核心价值在 API、服务编排和安全防护。

### 弱化内容

不要突出深度学习模型本身、模型训练效果或大规模云运维；不要声称平台具备企业级鉴权、租户隔离或线上 SLA。

---

## LLM Application Engineer

### 优先亮点

1. 亮点 5：Financial Question Planner
2. 亮点 8：Evidence Merger / Financial Verifier
3. 亮点 2：Hybrid Search 检索链路
4. 亮点 9：Prospectus Evidence 与上传索引
5. 亮点 3：配置驱动 Provider 架构
6. 亮点 11：金融评测与边界用例

### 关键词

LLM Application, RAG, Tool Orchestration, Question Planner, Evidence-grounded Answering, Hybrid Search, Provider Abstraction, Prompt Management, Financial Verifier, Offline Evaluation, Golden Cases

### 叙事角度

简历应强调把 LLM 应用工程化接入私有知识、结构化数据和可追溯证据，而不是只调用模型接口。重点说明规划、检索、证据合并、验证和评测如何共同降低幻觉风险。

### 弱化内容

不要突出底层训练、微调、模型自研或线上 A/B 实验；不要把 verifier 描述成可以完全消除幻觉。

---

## Financial AI / Data Engineer

### 优先亮点

1. 亮点 6：规则编译型 Text-to-SQL Evidence Path
2. 亮点 7：SQL Safety 与执行保护
3. 亮点 5：Financial Question Planner
4. 亮点 11：金融评测与边界用例
5. 亮点 8：Evidence Merger / Financial Verifier

### 关键词

Financial Data, Text-to-SQL, Rule-compiled SQL, Schema Registry, Entity Resolver, SQL Safety, SELECT-only, Financial Formula, Evidence Package, Verification, Golden Cases, Data Quality

### 叙事角度

简历应围绕金融数据表、实体解析、公式约束、SQL safety 和证据校验来讲，突出结构化数据问答的可控性。可以强调规则编译型 SQL 比自由生成 SQL 更适合本地金融 demo 的边界控制。

### 弱化内容

不要突出通用文档 RAG 的多模态包装、视觉演示或泛化到所有金融业务场景；不要写成 LLM 自动生成任意 SQL。

---

## Full-stack AI Demo / AI Product Engineer

### 优先亮点

1. 亮点 10：FastAPI + React 本地演示平台
2. 亮点 9：Prospectus Evidence 与上传索引
3. 亮点 5：Financial Question Planner
4. 亮点 8：Evidence Merger / Financial Verifier
5. 亮点 1：Modular RAG / MCP 底座

### 关键词

FastAPI, React, Vite, Local Demo, End-to-end AI App, Upload Flow, Chat UI, Sources, Plan, Verification, Trace, Prospectus Evidence, MCP, Product Prototype

### 叙事角度

简历应突出端到端交付能力：从上传招股书、本地索引、问题规划、证据检索到前端展示 sources、plan、verification 和 trace。强调这是面向演示、调试和产品验证的可解释 AI 应用原型。

### 弱化内容

不要突出大规模生产运维、云部署、多租户、商业化指标或复杂权限体系；不要把本地演示平台包装成生产 Web SaaS。
