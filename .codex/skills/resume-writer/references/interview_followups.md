# 简历项目面试追问准备

## 亮点到追问映射

resume-writer 生成简历后，可根据简历中选中的项目亮点挑 2-5 个追问，优先覆盖最容易被面试官继续深挖的能力点：
- Agent / Planner：问题 1、4、8。
- Text-to-SQL / SQL Safety：问题 2、3、10。
- EvidencePackage / Verifier：问题 5、6、8。
- Prospectus upload / readiness：问题 7。
- Production boundary / metrics：问题 9、10。

## 为什么 Router / Planner 放在 Agent 层，而不是 MCP Server？

回答方向：
- MCP Server 更适合暴露稳定、通用、可复用的工具能力，比如文档检索、SQL 查询、上传索引状态查询。
- Router / Planner 处理的是金融问题的业务意图、证据路径和回答策略，变化更快，适合放在 Agent 层编排。
- 这样 MCP 工具可以被不同 Agent 复用，Agent 负责把用户问题拆成计划并选择合适工具。
- 边界更清晰：Server 提供能力，Agent 决定为什么调用、按什么顺序调用、如何汇总证据。

## 为什么 Text-to-SQL 用规则编译，而不是直接让 LLM 生成 SQL？

回答方向：
- 当前实现是规则编译 SELECT，不是让 LLM 任意生成 SQL。
- 金融场景里 SQL 结果会成为事实证据，优先保证可控性、可解释性和安全边界。
- 规则编译能限制表、字段、条件、聚合和 LIMIT，降低误查、越权和注入风险。
- 未来可以扩展 LLM SQL，但 LLM 只能辅助生成候选查询，不能替代 SQL Safety 和执行前校验。

## SQL Safety 怎么保证？

回答方向：
- 只允许 SELECT 查询，拒绝写操作、DDL、管理语句等高风险语句。
- 禁止多语句、注释、分号拼接等绕过方式，降低注入和越权风险。
- 自动补充或约束 LIMIT，避免一次查询返回过大结果集。
- 输出 safety metadata，记录是否通过安全检查、是否改写 LIMIT、拒绝原因和 trace 信息。
- 安全边界放在执行前，不依赖模型“自觉”生成安全 SQL。

## `sql_first` 和 `doc_first` hybrid 怎么设计？

回答方向：
- `sql_first`：先查结构化事实，比如财务指标、年份、公司字段，再查招股书或文档解释原因和上下文。
- `doc_first`：先找招股书、公告或文档段落，定位业务语境，再查数据库补充结构化指标。
- Orchestrator 根据 `QuestionPlan.sub_questions` 逐个调用 SQL 和文档工具，而不是一次性混合所有信息。
- Hybrid 的重点是让结构化 evidence 和文档 evidence 互相补强，最终统一进入后续汇总和校验。

## EvidencePackage 有什么价值？

回答方向：
- 统一 SQL 和文档证据的结构，包括 source、content、metadata、trace_id。
- 让不同来源的 evidence 可以比较、合并、排序和校验。
- 回答生成时不只拿纯文本片段，还能保留来源、查询条件、页码、表名、时间等元数据。
- 便于 Verifier 和前端展示追溯链路，知道每个结论来自哪条证据。

## Verifier 解决了什么问题？

回答方向：
- Verifier 用来检查回答和证据之间是否匹配，而不是假设生成结果天然可信。
- 检查证据缺失、事实冲突、公式结果、单位、日期和输出格式等问题。
- 输出 pass、partial、conflict、insufficient 等状态，帮助调用方判断回答可信度。
- 它不能完全消除幻觉，但能把明显缺证据、证据冲突和格式错误暴露出来。

## 招股书上传为什么要报告 indexed/searchable 状态？

回答方向：
- 上传成功不等于检索可用，只能说明文件保存或接收成功。
- 可能出现保存成功但解析失败，或者解析成功但 embedding / index 构建不可用。
- readiness 是一个设计决策，用来聚合 upload、parse、index、searchable 这些状态。
- indexed 表示内容已经进入索引流程，searchable 表示后续检索工具实际能查到。
- readiness 能避免前端或 Agent 在检索还没准备好时，继续假设证据已经可用。
- 这个状态能让用户和系统区分“文件已上传”和“证据可用于回答”，减少静默失败。

## 这个项目和普通 RAG Demo 的区别是什么？

回答方向：
- 不只是文档向量检索，还引入结构化 SQL evidence，用数据库事实补充文档证据。
- 有 question plan，把复杂金融问题拆成可执行的 sub_questions 和证据路径。
- 输出 sources、verification report 和 trace，让回答有来源、有校验、有链路。
- 加入金融规则、实体解析、SQL Safety 和 golden boundary evaluation，用边界问题验证 planner / verifier 不乱答，强调可防守性。
- 保留 MCP 工具能力，使检索、SQL、上传状态等能力能被不同 Agent 或客户端复用。

## 这个项目离生产系统还差什么？

回答方向：
- 还需要鉴权、权限控制、多租户隔离、云部署和运维体系。
- 需要监控告警、并发容量评估、限流、重试和更完整的错误恢复机制。
- 需要真实业务评测集、人工反馈闭环和长期质量回归。
- PDF table extraction 还可以更强，尤其是复杂表格、跨页表格和扫描件场景。
- raw evidence docstore 也需要补强，便于保存原始证据、版本和审计链路。

## 面试中被问量化指标怎么办？

回答方向：
- 先区分真实已测数据和建议指标，不能把建议指标包装成真实商业指标。
- 可以说当前更适合用 Hit Rate@K、MRR 衡量检索命中与排序质量。
- SQL 侧可以看 SQL 执行成功率、安全拦截率和 entity resolution 成功率。
- 工程侧可以看 API 延迟、上传索引耗时、错误状态覆盖率。
- 如果没有生产流量，就说明这些是下一阶段评测指标，而不是已上线商业结果。
