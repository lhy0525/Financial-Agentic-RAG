# Financial Agentic RAG 技术亮点库

用于按岗位方向选择 4-6 个亮点生成简历项目经历；每个亮点包含技术要点、简历话术方向、量化角度、诚实边界。

---

## 亮点 1：Modular RAG / MCP 底座

### 技术要点

- 基于统一类型合同组织 RAG 核心对象，降低模块间耦合。
- 实现 MCP stdio server，以 JSON-RPC/MCP 方式对外暴露检索能力。
- 提供 `query_knowledge_hub`、`list_collections`、`get_document_summary` 等工具接口。
- 将知识库查询能力工具化，便于接入支持 MCP 的 Agent 或本地客户端。

### 简历话术方向

设计并实现 Modular RAG / MCP 底座，将私有知识库检索封装为标准 MCP 工具，支持 Agent 通过 JSON-RPC stdio 调用查询、集合列表与文档摘要能力。

### 量化角度

- MCP 工具数量与覆盖场景
- 工具调用成功率
- 单次查询端到端延迟
- 支持的 collection / document 数量

### 诚实边界

不要声称云端生产部署；该亮点主要体现本地 MCP server、协议封装和工具化能力。

---

## 亮点 2：Hybrid Search 检索链路

### 技术要点

- 检索链路支持 Dense Retrieval 与 BM25 Sparse Retrieval 双路召回。
- 使用 RRF 融合稠密向量检索与关键词检索结果，兼顾语义匹配与精确词匹配。
- 支持可选 rerank，对融合结果进行二阶段排序。
- 检索或 rerank 失败时提供回退路径，保证基础查询能力可用。

### 简历话术方向

实现 Hybrid Search 检索链路，结合 Dense Retrieval、BM25 与 RRF 融合策略，并通过可选 rerank 与失败回退提升本地金融文档查询的鲁棒性。

### 量化角度

- Hit Rate@K
- MRR / NDCG
- Rerank 前后 Top-K 命中变化
- Dense、BM25、Hybrid 三种策略对比
- 查询延迟与失败回退次数

### 诚实边界

没有真实评测数据时，只写可使用 Hit Rate@K、MRR 等指标评估，不编造提升比例或线上效果。

---

## 亮点 3：配置驱动 Provider 架构

### 技术要点

- 为 LLM、Embedding、VectorStore、Reranker、Evaluator 定义 base interface。
- 使用 factory 根据配置创建具体 provider，实现组件级可插拔。
- Prompt 外置管理，便于在不改业务代码的情况下调整模型行为。
- 支持通过配置切换代码中已实现的模型、向量库、重排与评测组件。

### 简历话术方向

设计配置驱动的 Provider 架构，通过 base interface + factory 解耦 LLM、Embedding、VectorStore、Reranker 与 Evaluator，使不同后端能够按配置切换并复用同一条业务链路。

### 量化角度

- 已实现 provider 类型数量
- 配置切换覆盖的组件数
- 新增 provider 需要修改的文件数
- Prompt 模板数量与复用场景

### 诚实边界

只声称代码支持的 provider；不要声称所有 provider 都经过真实 API 回归或生产级验证。

---

## 亮点 4：Ingestion Pipeline 与本地索引

### 技术要点

- Ingestion pipeline 覆盖 integrity、load、split、transform、embed、upsert 阶段。
- 使用 SHA256 与 SQLite ingestion history 记录处理历史，支持去重和增量处理。
- 本地索引包含 Chroma、BM25 与 ImageStorage，支撑文本和图像相关证据管理。
- 对本地招股书场景支持关闭 transform / image extraction，以降低处理成本。

### 简历话术方向

实现面向本地金融文档的 Ingestion Pipeline，串联完整性校验、解析、切分、增强、向量化与入库，并通过 SHA256 + SQLite 历史记录减少重复处理。

### 量化角度

- 处理文件数与 chunk 数
- 去重命中次数或跳过率
- 单文档摄取耗时
- Chroma / BM25 索引规模
- transform 与 image extraction 的成本对比

### 诚实边界

主要围绕 PDF/TXT 文档；不要声称支持所有 Office 格式或复杂版式的完整解析。

---

## 亮点 5：Financial Question Planner

### 技术要点

- `FinancialQuestionPlanner` 以规则优先方式解析问题中的实体、时间、公式和输出约束。
- 输出结构化 `QuestionPlan`，为后续工具选择与证据组织提供统一输入。
- 支持 `pdf_rag`、`text_to_sql`、`hybrid` route，按问题类型选择证据路径。
- 将金融问答中的规划逻辑显式化，减少后续链路的隐式判断。

### 简历话术方向

实现规则优先的 Financial Question Planner，将自然语言问题解析为包含实体、时间、公式、输出约束和 route 的 `QuestionPlan`，支撑 PDF RAG、Text-to-SQL 与 Hybrid 证据路径编排。

### 量化角度

- 支持的 route 类型数量
- 可解析的实体、时间、公式模式数量
- Planner 命中率或回退率
- 不同问题类型的路由准确率

### 诚实边界

不要写成通用 LLM router；当前是规则优先规划器，重点是金融问答场景下的结构化规划。

---

## 亮点 6：规则编译型 Text-to-SQL Evidence Path

### 技术要点

- `TextToSQLEvidenceTool` 根据 `QuestionPlan` 编译 SELECT SQL，而不是让 LLM 自由生成 SQL。
- `FinancialSchemaRegistry` 管理金融数据表、字段与可查询结构。
- `EntityResolver` 将问题中的实体映射到可执行查询条件。
- 查询结果包装为 `EvidencePackage`，包含 SQL、表、列、行、耗时与 safety metadata。

### 简历话术方向

实现规则编译型 Text-to-SQL Evidence Path，基于 `QuestionPlan`、金融 schema registry 与实体解析器生成受控 SELECT 查询，并将结果封装为可追溯的证据包。

### 量化角度

- 支持的表与字段数量
- 可编译的问题模板数量
- SQL 执行耗时
- 返回行数、证据包数量
- route 到 text-to-sql 的命中比例

### 诚实边界

必须写“规则编译型 Text-to-SQL”；不要写“LLM 自动生成 SQL”或暗示模型可任意生成数据库查询。

---

## 亮点 7：SQL Safety 与执行保护

### 技术要点

- `SQLSafetyChecker` 只允许 SELECT 查询进入执行环节。
- 拦截 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、PRAGMA 等高风险语句。
- 拦截多语句、注释、非 SELECT 查询，降低误执行风险。
- 自动补充或约束 LIMIT，控制本地 demo 查询结果规模。

### 简历话术方向

为 Text-to-SQL 证据路径实现 SELECT-only SQL Safety Guard，拦截写操作、DDL、多语句和注释类输入，并通过自动 LIMIT 控制查询执行范围。

### 量化角度

- 拦截规则数量
- 安全测试 case 数量
- 被拒绝 SQL 类型覆盖
- 自动 LIMIT 生效次数
- 查询执行耗时与返回行数

### 诚实边界

这是本地 demo 的 SELECT-only safety guard，不是完整数据库安全网关，也不能替代数据库权限、审计和隔离机制。

---

## 亮点 8：Evidence Merger / Financial Verifier

### 技术要点

- Evidence Merger 按 evidence_id 与 source/content 对证据去重。
- 保留 duplicates、source、package path、trace ids 等追踪信息。
- Financial Verifier 检查证据缺失、事实冲突、公式一致性、单位与格式。
- 验证结果使用 pass、partial、conflict、insufficient 等 status 表达可信度。

### 简历话术方向

构建 Evidence Merger 与 Financial Verifier，对多路径证据进行去重、溯源和一致性校验，用 pass / partial / conflict / insufficient 状态增强金融问答结果的可解释性。

### 量化角度

- 合并前后证据数量
- 去重命中数量
- 冲突或证据不足 case 数量
- verifier 规则数量
- trace 覆盖率

### 诚实边界

不要声称完全消除幻觉；应表述为降低幻觉风险、增强证据可追溯与结果校验能力。

---

## 亮点 9：Prospectus Evidence 与上传索引

### 技术要点

- 支持 PDF/TXT 招股书上传、本地保存、解析并索引到 Chroma / BM25。
- `LocalProspectusIndexService` 返回 `indexed_searchable`、`already_indexed`、`index_failed` 等 readiness 状态。
- `ProspectusEvidenceTool` 将招股书检索结果包装为 text / table evidence。
- 将上传、索引 readiness 与证据检索拆开，避免把文件保存误判为可检索。

### 简历话术方向

实现招股书上传索引与证据抽取能力，将本地 PDF/TXT 招股书解析后写入 Chroma / BM25，并通过 readiness 状态区分已上传、已索引和可检索。

### 量化角度

- 上传文件数
- indexed_searchable / already_indexed / index_failed 分布
- 索引耗时
- 文本证据与表格证据数量
- 招股书查询命中率

### 诚实边界

上传成功不等于检索可用；简历中必须强调 readiness 状态，不能把保存成功夸大为索引和检索都成功。

---

## 亮点 10：FastAPI + React 本地演示平台

### 技术要点

- `src/local_platform/api.py` 提供 health、chat、upload、history 等本地 API。
- `service.py` 懒创建 Orchestrator，减少启动时对完整链路的强依赖。
- API 返回 SQL / prospectus 状态，便于前端展示证据路径健康度。
- `frontend/src/App.jsx` 实现本地无登录 React / Vite UI。
- 前端展示 sources、plan、verification、trace 等调试信息。

### 简历话术方向

搭建 FastAPI + React 本地演示平台，提供 health、chat、upload、history API 与无登录 Vite UI，将 sources、plan、verification 和 trace 可视化呈现给调试与演示使用者。

### 量化角度

- API endpoint 数量
- 前端展示的信息模块数量
- 本地启动耗时
- chat / upload 请求耗时
- 演示流程覆盖的证据路径数量

### 诚实边界

这是本地演示平台，不是生产 Web SaaS，也不是完整权限系统；不要声称具备企业级鉴权、租户隔离或线上运维能力。

---

## 亮点 11：金融评测与边界用例

### 技术要点

- `FinancialEvalRunner` 针对 agent 输出评估 route、verification、source、tool sequence。
- 通过 financial fixtures / golden cases 覆盖典型金融问答与边界用例。
- 通用 EvalRunner 支持 Hit Rate、MRR 等检索指标。
- 将离线评测与回归测试结合，用于约束规划、检索、SQL 与验证链路变化。

### 简历话术方向

建设金融问答离线评测与回归测试体系，使用 `FinancialEvalRunner` 检查 route、verification、source 和 tool sequence，并结合 golden cases 约束核心链路迭代质量。

### 量化角度

- Golden case 数量
- 覆盖的问题类型数量
- route / verification / source / tool sequence 通过率
- Hit Rate@K、MRR
- 回归测试执行耗时与失败 case 数量

### 诚实边界

没有真实线上业务反馈时，只写离线评测和回归测试；不要声称线上收益、真实用户反馈或生产 A/B 实验结果。

