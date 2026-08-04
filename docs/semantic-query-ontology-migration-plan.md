# 企业问数语义层迁移计划

> 文档状态：规划中。
> 更新日期：2026-08-04。
> 目标读者：项目负责人、能够访问真实 Java 工程和货架数据的弱 Agent、云端 Agent / Skill 维护者。
> 前置结论：当前 Phase A/B 继续作为已跑通的兼容链路；新方案以“业务概念模型 + 数据资产注册 + 查询映射 + 语义计划”为目标，不做精确节点命中后的父节点上卷。

## 1. 文档目的

本文把 `metric-ontology-discussion-summary.md` 中确定的新方向编排成一条可逐阶段验收的迁移路径，解决以下问题：

1. 先做哪些事实盘点和测试合同，后写哪些资源与代码。
2. 哪些能力优先复用云端 Agent / Skill，哪些能力必须进入 Java 语义层。
3. 4 个首批真实问数问题如何覆盖解析、规划、资产发现、指标解析和真实查数。
4. 推广、广告点击、`ad` 和小艺当前不同的真实数据能力如何进入测试合同。
5. 新增资源和 Java 代码最终散布在真实工程的哪些现有模块；如何持续登记，避免后续无法定位。
6. 哪些事实尚未确认，必须保留待办而不能由实施 Agent 编造。

本文不是 Java 代码设计终稿。真实类名、包名、Controller、Service、resources 根路径和内部调用方式必须在接触实际 Java 工程后填写。

---

## 2. 已确认原则与非目标

### 2.1 已确认原则

1. `BusinessConcept != ShelfCategory`：业务概念与货架部署节点分离。
2. 真实货架有中文和英文业务 aliases 字段，但绝大部分为空；运行时目录应读取非空 aliases，稳定口语、英文和缩写仍由业务概念模型补充。
3. 货架分类节点由真实运行时目录发现，不再为了覆盖 L2.3/L2.4 手工复制整棵树 YAML。
4. 用户精确命中具体节点时保持具体范围，禁止自动上卷到父节点。
5. 父节点只有在命中的业务概念本身映射到该父节点时才作为查询范围。
6. 未知口语不能静默猜测；候选必须经用户确认，确认结果生成待审核知识提案。
7. 第一阶段由云端 Agent / Skill 抽取结构化意图、执行计划、处理确认并展示结果。
8. Java 第一阶段只承担必须统一治理的语义解析、资产映射、策略校验和计划生成，不重复实现 Agent 已能稳定完成的通用能力。
9. `resolveSemanticQuery` 第一阶段只生成计划，不直接查询指标数据。
10. 现有 `locateNode`、`resolveMetric` 和其他 MCP 工具先保留，作为兼容链路和计划执行能力。

### 2.2 第一轮明确不做

1. 不引入完整 OWL、Protégé、SWRL、SPARQL 或通用 DL reasoner。
2. 不建立持久化图数据库或独立本体服务。
3. 不把所有货架分类节点物化为人工维护的业务概念。
4. 不为语义层重新实现时间自然语言解析；先复用云端 Agent。
5. 不在 Java 新增图表、最终自然语言回答和用户交互逻辑。
6. 不在 Java 第一阶段实现通用 `PlanExecutor`；先让 Skill 严格执行结构化计划。
7. 不删除现有 Phase A/B 资源和接口，直到新链路真实回归通过。
8. 不用假指标、假数值或本地数据库结果代替真实集成验收。

---

## 3. 目标闭环

### 3.1 最终逻辑链路

```text
用户问题
  -> 云端 Agent 抽取 structuredIntent
  -> resolveSemanticQuery(structuredIntent)
       -> 解析稳定业务概念
       -> 必要时发现具体运行时货架节点
       -> 解析指标 / 过滤概念
       -> 读取 Concept -> Asset / Policy / Capability 映射
       -> 校验映射和业务策略
       -> 生成 SemanticQueryPlan
  -> 云端 Agent / Skill 严格执行 plan.steps
       -> 调用现有 getNextLevelNode
       -> 调用现有 resolveMetric（迁移后可接收 metricConceptId）
       -> 调用现有 queryIndicatorDimensionData
  -> Agent 按计划状态完成澄清、确认和展示
```

成熟后若事实证明云端执行不稳定，再评估：

```text
SemanticQueryPlan
  -> Java PlanExecutor
  -> 真实数据结果
```

该步骤不是本轮默认目标。

### 3.2 最终架构图

```text
┌──────────────────────────────────────────────────────┐
│ 用户 / 云端 Agent / Skill                            │
│ 抽取 structuredIntent；处理澄清、确认、计划执行与展示 │
└───────────────────────────┬──────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────┐
│ resolveSemanticQuery                                 │
│                                                      │
│ BusinessConceptResolver                              │
│ RuntimeShelfAssetResolver                            │
│ MetricConceptResolver                                │
│ FilterConceptResolver                                │
│ MappingResolver                                      │
│ PolicyEvaluator                                      │
│ SemanticPlanBuilder                                  │
└───────────────┬─────────────────────┬────────────────┘
                │                     │
                ▼                     ▼
┌────────────────────────┐  ┌──────────────────────────┐
│ Business Ontology      │  │ Runtime Asset Registry   │
│                        │  │                          │
│ 业务对象概念           │  │ Shelf Category Catalog   │
│ 指标 / 变体概念        │  │ RealModel capability     │
│ 过滤概念               │  │ Indicator query          │
│ 关系与 Policy          │  │ 真实资产状态             │
└────────────┬───────────┘  └────────────┬─────────────┘
             │                           │
             └──────────┬────────────────┘
                        ▼
             ┌─────────────────────┐
             │ Mapping Registry    │
             │                     │
             │ Concept -> Asset    │
             │ Concept -> Filter   │
             │ Concept -> Policy   │
             │ Operation -> Tool   │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ SemanticQueryPlan   │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Cloud Plan Runner   │
             │ 现有 MCP tools      │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ databp / RealModel  │
             │ Indicator Service   │
             └─────────────────────┘
```

---

## 4. 四类核心语义资产

### 4.1 业务概念模型

第一轮只定义闭环所需的有限类型：

```text
BusinessConcept
MetricConcept
MetricVariant
FilterConcept
DataAsset
QueryCapability
```

第一轮关系候选：

```text
partOf
hasVariant
disjointWith
mapsToDataAsset
resolvedByPolicy
implementedByCapability
```

关系是否传递、对称及 domain/range 必须由业务和真实测试决定。未确认前不写默认值。

业务概念至少包含：

```yaml
id: <待填写>
type: <待填写>
canonical_name: <待填写>
aliases: []
definition: <待填写>
relations: []
owner: <待填写>
status: <待填写>
```

其中货架 ID 不进入概念定义，通过 Mapping 单独关联。

### 4.2 运行时数据资产注册

第一轮至少注册：

1. databp 货架分类目录。
2. `getNextLevelNode` 对应的逻辑实体发现能力。
3. RealModel 指标解析能力。
4. `queryIndicatorDimensionData` 对应的真实数据查询能力。

现有 `locateNode` 已经在 databp 进程内复用 `treeModelView()` 的遍历逻辑，过滤逻辑实体并返回具体分类节点。第一轮应优先照搬或抽取这段
已验证逻辑，不另造一套树获取链路；是否已有缓存、索引或刷新机制仍需弱 Agent 检查真实 Java 工程后记录，不能假定已实现。

运行时分类节点最少需要：

```text
id
parentId
nameCn
nameEn
非空中文 aliases
非空英文 aliases
```

真实字段名和父节点来源待确认。

### 4.3 查询映射

映射至少表达：

```text
BusinessConcept -> ShelfCategory asset
MetricConcept -> RealModel resolution policy
FilterConcept -> field/operator/value
SemanticOperation -> QueryCapability
```

业务对象映射示意：

```yaml
- concept: <待填写 concept id>
  target:
    source: databp
    asset_type: ShelfCategory
    asset_id: <待弱 Agent 从真实货架填写>
  scope_policy: EXACT_SUBTREE
  discovery_capability: <待 capability registry 定稿>
```

`EXACT_SUBTREE` 表示使用该概念自己声明的范围，不表示把具体子节点上卷到此节点。

### 4.4 语义查询计划

计划必须是机器可执行的强类型结构，不输出“请先查实体，再查指标”之类自然语言指令。

第一轮计划至少包含：

```text
status
ontologyVersion
mappingVersion
catalogVersion
interpretation
scope
steps
policies
explanations
```

第一轮步骤类型建议限制为：

```text
DISCOVER_LOGIC_ENTITIES
RESOLVE_METRIC
QUERY_METRIC_DATA
```

过滤是放入 `RESOLVE_METRIC`，还是作为独立 `APPLY_FILTER` 步骤，待确认现有 `resolveMetric` 真实响应能否提供并可靠过滤 `level/type` 后再决定。

---

## 5. 首批 4 个问题与能力合同

### 5.1 固定问题集

首批问题固定为：

1. 最近一个月的推广成功率是多少。
2. 点击的一般时延是多少。
3. `ad` 的内存使用率是多少。
4. 给我小艺的所有黄金指标。

### 5.2 为什么测试合同必须先于接口开发

“先确定问题合同”和“第一轮开发 `resolveSemanticQuery`”不是两个竞争顺序：

1. **问题合同是阶段 0 的输入和验收基线**，先定义系统应理解什么。
2. **接口是后续阶段的实现物**，其字段和状态必须由问题合同反推。
3. 若没有合同就先写接口，实施者会自行编造货架 ID、概念关系和计划字段。
4. 合同第一轮不要求所有答案已知；未知内容由能访问真实工程和货架的弱 Agent 调查并填写。

### 5.3 由 Java 弱 Agent 填写的语义真值表

为每个问题建立一行记录，至少填写：

| 字段 | 含义 |
|---|---|
| `question` | 原始问题，不改写 |
| `business_phrase` | 业务对象原话 |
| `metric_phrase` | 指标原话 |
| `filter_phrases` | 过滤条件原话 |
| `time_expression` | 时间原话 |
| `query_mode` | value / trend / comparison / definition |
| `expected_business_concept` | 正确稳定概念；若应走运行时资产则明确标记 |
| `expected_runtime_asset` | 真实货架节点 ID 与路径 |
| `expected_metric_concept` | 正确指标 family / variant |
| `expected_filters` | 规范字段、操作符和值 |
| `expected_policy` | 歧义、聚合、公式等预期策略 |
| `expected_status` | READY / NEEDS_CLARIFICATION / UNKNOWN_CONCEPT 等 |
| `available_logic_entities` | 可用于测试的真实逻辑实体 |
| `real_metric_available` | 是否有真实已部署指标 |
| `real_data_queryable` | 是否能完成最终数据库查数 |
| `evidence` | 真实接口、货架路径或返回摘要 |

弱 Agent 可以按测试需要调整货架节点和逻辑数据实体，但必须记录调整内容，并区分：

- 为测试新增或修改的货架结构；
- 真实生产已有结构；
- 只存在定义指标还是存在已部署 RealModel 指标；
- 是否真的能由指标 ID 查询数据库数据。

### 5.4 当前已知真实数据条件

当前已确认：

1. “最近一个月的推广成功率是多少”能够完成最终数据库数据查询。
2. “点击的一般时延是多少”中，广告点击能够完成最终数据库数据查询；若解析出其他与“点击”相关的节点或实体，它们可能没有数据，不能因而静默选中广告点击。
3. “`ad` 的内存使用率是多少”预期返回广告最小内存使用率、最大内存使用率两种真实数据；不得静默只选一种，也不得把最小、最大合并成一个值。
4. “给我小艺的所有黄金指标”能够取得指标目录，但没有最终数据库数值；正确终点是完整黄金指标列表，而不是 T4 查数。

因此测试分四级：

| 等级 | 验证范围 | 是否要求真实数值 |
|---|---|---|
| T1 | 概念、口语、过滤和状态解析 | 否 |
| T2 | 生成正确 `SemanticQueryPlan` | 否 |
| T3 | 真实货架资产发现 + 真实 RealModel 指标解析 | 否；视真实实体能力而定 |
| T4 | 从问题到 `queryIndicatorDimensionData` 的真实端到端查数 | 是，仅限满足广告真实数据前提的用例 |

4 个问题都必须通过 T1/T2；能否通过 T3/T4 按上述已知条件和弱 Agent 的真实证据填写。问题 2 中“一般时延”的规范 variant、
问题 3 返回两个 variant 的计划表达方式，以及问题 4 应读取哪一种真实指标目录，均由弱 Agent 结合真实接口和现有实现确认，本文不提前编造。

---

## 6. 分阶段迁移路线

每阶段都有进入条件、工作内容、产物和退出门禁。前一阶段没有通过，不进入下一阶段的大规模编码。

### 阶段 0：真实工程盘点与问题合同

**目标：** 在写新接口前固定事实边界，消除未知项。

工作内容：

1. Java 弱 Agent 按 `stage-0-semantic-query-investigation.md` 填写 §5 的 4 问语义真值表。
2. 调查真实 Java 工程中的 Controller、Service、DTO、resources 根路径和现有 ontology loader。
3. 调查 `treeModelView()` 的真实节点/逻辑实体区分字段和父子字段。
4. 确认是否已有可复用的 category-only 遍历或缓存。
5. 调查 `resolveMetric`、RealModel 内部 service 和真实查数接口的实际代码位置。
6. 建立 §8 的文件登记表，先登记现有相关文件，再登记未来新增文件。
7. 记录 4 问分别能达到 T1/T2/T3/T4 的哪一级，不承诺未知能力。

产物：

- 4 问语义真值表。
- 真实 Java 文件清单。
- 未决事项清单。
- 第一版 `structuredIntent` 和状态枚举草案。

退出门禁：

- 没有编造的货架 ID、实体 ID、指标 ID 或 Java 包路径。
- 每个问题的预期状态明确，或显式标为 `TBD` 并有负责人。
- 广告真实查数可用范围已有证据。

### 阶段 1：资源合同与只读校验，不改变现有运行链路

**目标：** 先证明四类语义资产能表达 4 问，不急于改接口。

工作内容：

1. 在实际 Java resources 根目录下新增统一语义资源目录。
2. 定义最小 schema：business concepts、metric concepts、filters、mappings、capabilities、policies。
3. 从现有 Phase A aliases、真实树非空 aliases 和 Phase B Metric Family 中只迁移 4 问需要的稳定知识，并记录来源与冲突处理。
4. 不复制 L2.3/L2.4 整树节点。
5. 编写 YAML 加载与静态校验测试；具体是复用现有 loader 还是新增 loader，由阶段 0 调查决定。
6. 用离线测试将 4 问人工真值编译为预期 interpretation 和 plan 快照。

建议的 resources 相对结构如下；`<java-resources-root>` 必须由阶段 0 填写：

```text
<java-resources-root>/ontology/semantic-query/
├── model.yaml
├── business-concepts.yaml
├── metric-concepts.yaml
├── filter-concepts.yaml
├── mappings.yaml
├── capabilities.yaml
└── policies.yaml
```

文件是否需要进一步拆分，等真实规模出现后再决定。

退出门禁：

- 4 问所需稳定概念均可表达。
- alias 冲突、未知引用、非法关系、失效 mapping 可被检测。
- 不需要为每个真实中低层节点创建 `base.yaml`。
- 现有 Phase A/B 行为不变。

### 阶段 2：运行时 Shelf Category Catalog

**目标：** 解决 YAML 只到 L2.2 时，真实 L2.3/L2.4 无法按节点名称发现的问题。

工作内容：

1. 在 databp 进程内基于 `treeModelView()` 生成只包含分类节点的目录。
2. 构建 `id`、规范化 `nameCn/nameEn`、parent/children 索引。
3. 提供业务概念映射目标的存在性和类型健康检查。
4. 实现运行时节点精确名称解析：稳定业务概念未命中时，允许命中真实 L2.3/L2.4。
5. 精确命中子节点后保持子节点范围，禁止上卷。
6. 两边都未命中时返回 `UNKNOWN_CONCEPT`；相似候选仅作为 `NEEDS_CLARIFICATION`，不得直接查数。
7. 先作为 Java 内部能力供后续 `resolveSemanticQuery` 使用；是否新增独立外部接口待实际调试需要确认。

云端 Agent 继续使用现有 Phase A/B，不在本阶段切流。

退出门禁：

- 测试中新建 L2.3 后，不改业务 YAML 即可按真实名称命中。
- 改名、删除和移动节点后的行为可解释。
- 未知口语不被静默猜成某个节点。
- 无任何具体节点到父节点的自动上卷。

### 阶段 3：`resolveSemanticQuery` 计划生成接口

**目标：** 提供统一语义入口，但仍由 Skill 执行现有工具。

工作内容：

1. 定稿 `StructuredIntent`、`SemanticQueryPlan`、状态和错误合同。
2. 实现业务概念、运行时资产、指标概念、过滤概念解析。
3. 实现 Concept -> Asset / Policy / Capability mapping。
4. 实现计划静态校验和解释依据。
5. 新增 `resolveSemanticQuery` Controller/Service；注解、鉴权、返回外壳和 Swagger 契约遵守现有云上约束。
6. 保留 `locateNode`、`resolveMetric` 和现有工具，不做破坏性删除。
7. 第一版不在 Java 解析自由文本时间；计划保留原始 `timeExpression`，由 Skill 转换明确时间。
8. 第一版不在 Java 执行计划。

建议状态至少包括：

```text
READY
NEEDS_CLARIFICATION
UNKNOWN_CONCEPT
AMBIGUOUS_CONCEPT
BROKEN_MAPPING
ASSET_NOT_FOUND
METRIC_NOT_FOUND
METRIC_AMBIGUOUS
UNSUPPORTED_QUERY
POLICY_BLOCKED
```

具体枚举以 4 问合同为准，多余状态不要提前发明。

退出门禁：

- 4 问全部有稳定的 T1/T2 结果。
- 同一输入和同一资源版本生成确定性计划。
- 返回包含 ontology/mapping/catalog 版本和解释依据。
- 计划中不存在 Agent 需要猜测的自然语言步骤。

### 阶段 4：云端 Skill 试运行计划

**目标：** 最小 Java 工作量下验证统一语义入口是否足够稳定。

工作内容：

1. Skill 从用户问题抽取 `structuredIntent`。
2. Skill 只调用一次 `resolveSemanticQuery` 完成语义规划。
3. `READY` 时严格按 `plan.steps` 调现有 MCP 工具。
4. `NEEDS_CLARIFICATION` 时只展示服务端候选，不自行创造新候选。
5. Skill 继续处理时间表达、用户确认、批次/并发和结果展示。
6. Skill 不修改 plan 中的 scope、concept ID、真实 asset ID、指标策略和过滤条件。
7. 新旧链路双跑，对比语义选择、调用次数、失败状态和最终结果。

退出门禁：

- 4 问在云端 Agent 中达到各自允许的最高测试等级。
- 推广成功率完成 T4；点击一般时延和 `ad` 内存使用率按真实调查结果完成所有可执行 T4 查询。
- 其他问题在不具备真实数据时停在正确层级并明确说明，不伪造成功。
- 新链路的歧义和失败状态优于或不劣于现有链路。

### 阶段 5：知识提案与旧 Phase A 资源收缩

**目标：** 降低人工整树维护，同时建立未知口语的治理闭环。

工作内容：

1. 对业务概念和真实货架 aliases 都无法解析的未知口语返回候选和确认请求。
2. 用户确认后生成 `AliasProposal`，但不自动修改生产 YAML。
3. 定义 owner、审核、版本、发布和回滚流程。
4. 停止为新 L2.3/L2.4 复制 `base.yaml`。
5. 对旧 Phase A 数据分类：稳定业务 aliases 迁入 concepts，货架 ID 迁入 mappings，可从真实树获得的镜像数据不迁移。
6. 保留旧链路一段回归期；删除范围和日期待真实运行数据决定。

退出门禁：

- 新增动态节点不再要求人工复制 YAML。
- 未知口语有可审计的提案记录。
- 旧 aliases 的去向可追踪，无静默丢失。
- 回滚策略已经验证。

### 阶段 6：是否下沉计划执行的决策门

**目标：** 用事实决定是否新增 Java `PlanExecutor`，而不是默认扩张范围。

只有出现以下至少一种已测问题时才进入实现：

1. 云端 Agent 经常不按计划执行。
2. 节点下逐实体 MCP 调用成本或失败率不可接受。
3. 必须在服务端做原子执行、统一权限或完整审计。
4. 需要在服务端安全组合跨实体公式或聚合。

如果没有上述证据，继续使用 Skill 执行计划，不新增 Java 执行器。

如需实施，再单独编写 `PlanExecutor` 设计文档，不能直接在本迁移文档中假定包名、并发模型和事务边界。

---

## 7. 第一版接口边界

### 7.1 `resolveSemanticQuery` 输入草案

```json
{
  "businessObjectPhrase": "<用户原话>",
  "metricPhrase": "<用户原话>",
  "filterPhrases": ["<用户原话>"],
  "timeExpression": "<用户原话>",
  "queryMode": "<待 4 问合同确认枚举>"
}
```

第一版是否需要支持多个业务对象、多个指标以及 comparison，当前四问不能给出结论；出现真实验收问题后再扩展合同。

### 7.2 输出草案

```json
{
  "status": "READY",
  "ontologyVersion": "<待实现>",
  "mappingVersion": "<待实现>",
  "catalogVersion": "<待实现>",
  "interpretation": {
    "businessConcepts": [],
    "runtimeAssets": [],
    "metricConcepts": [],
    "filters": []
  },
  "scope": [],
  "steps": [],
  "policies": {},
  "explanations": []
}
```

真实 DTO 字段名由阶段 0 调查现有命名规范后定稿。

### 7.3 Agent 与 Java 的第一版职责

| 能力 | 第一版责任方 |
|---|---|
| 从用户问题抽取槽位 | 云端 Agent / Skill |
| 稳定业务概念解析 | Java 语义层 |
| 动态货架节点发现 | Java 语义层，进程内真实目录 |
| 指标概念和不可替代规则 | Java 语义层 |
| 过滤概念到规范条件 | Java 语义层 |
| 时间表达转明确起止时间 | 云端 Agent / Skill |
| 生成查询步骤和策略 | Java 语义层 |
| 执行现有 MCP 工具 | 云端 Agent / Skill |
| 用户澄清和确认 | 云端 Agent / Skill |
| 结果表格和图表 | 云端 Agent / Skill |
| 真实指标和数值 | 现有 Java / 数据服务能力 |

---

## 8. 强制文件登记与交接机制

### 8.1 为什么必须登记

语义资源可以集中放在新的 resources 子目录，但 Java 代码必须进入真实工程已有的 Controller、Service、DTO、loader、resolver、配置和测试位置。
不得为了“方便查找”新建一个脱离现有分层的总代码文件夹。

每个阶段开工前必须创建并维护一份真实工程文件登记文档，建议文件名：

```text
docs/semantic-query-java-file-map.md
```

该文件应由能够访问真实 Java 工程的弱 Agent 在阶段 0 创建。本仓库当前不含目标 Java 工程，无法填写真实路径，因此此处只定义合同，不编造文件。

### 8.2 登记表必填字段

| 字段 | 说明 |
|---|---|
| 逻辑组件 | 例如 BusinessConceptLoader |
| 真实仓库/模块 | Java 工程中的 module |
| 完整相对路径 | 从 Java 仓库根开始 |
| 类或资源名 | 实际名称 |
| 职责 | 一句话边界 |
| 调用方 | 谁使用它 |
| 依赖 | 复用哪些现有类或服务 |
| 配置文件 | 读取哪些 YAML |
| 测试文件 | 对应测试路径 |
| 首次引入阶段 | 阶段编号 |
| 状态 | PLANNED / ADDED / MODIFIED / DEPRECATED |
| 最后验证版本 | commit / build / deployment 信息 |

示意模板：

```markdown
| 逻辑组件 | 真实模块 | 完整相对路径 | 职责 | 调用方 | 测试路径 | 阶段 | 状态 |
|---|---|---|---|---|---|---|---|
| BusinessConceptLoader | TBD | TBD | 加载并校验业务概念 | TBD | TBD | 1 | PLANNED |
```

### 8.3 更新规则

1. 新增或移动 Java 文件的同一提交必须更新文件登记文档。
2. 重命名类后保留旧路径和迁移说明，不能只覆盖成新路径。
3. 每个 YAML 必须登记加载类、校验类和使用方。
4. 每个对外 DTO 必须登记对应 Swagger/schema 位置。
5. 每个运行时索引必须登记构建、刷新和健康检查位置。
6. 阶段验收前按登记表逐个打开真实文件复核，不只检查类名搜索结果。

---

## 9. 未决事项登记

以下内容当前没有足够事实，实施时必须填写；在确认前不得自行给出生产值：

| 未决项 | 需要谁确认 | 最晚确认阶段 |
|---|---|---|
| 目标 Java 仓库、模块和 resources 根路径 | Java 弱 Agent / 项目负责人 | 阶段 0 |
| 现有 ontology loader 的真实类和复用边界 | Java 弱 Agent | 阶段 0 |
| `treeModelView()` 区分分类与逻辑实体的真实字段 | Java 弱 Agent | 阶段 0 |
| 分类节点真实父节点字段及可靠性 | Java 弱 Agent | 阶段 0 |
| 是否已有 category-only 内部能力 | Java 弱 Agent | 阶段 0 |
| 4 问对应的真实货架 ID 和路径 | Java 弱 Agent / 项目负责人 | 阶段 0 |
| 哪些问题可获得真实 RealModel 指标 | Java 弱 Agent | 阶段 0 |
| 广告范围内哪些指标 ID 可完成真实数据查询 | Java 弱 Agent | 阶段 0 |
| “一般时延”的规范 metric variant 和真实匹配依据 | Java 弱 Agent | 阶段 0 |
| `ad` 内存使用率一次返回 min/max 两种指标的计划表示 | Java 弱 Agent / 项目负责人 | 阶段 0 |
| 小艺黄金指标使用的真实指标目录接口和字段 | Java 弱 Agent | 阶段 0 |
| 过滤发生在指标解析内部还是独立步骤 | Java 弱 Agent | 阶段 1 |
| 本体和 mapping 的 owner、审核人与发布流程 | 项目负责人 | 阶段 1 |
| `resolveSemanticQuery` 的实际 HTTP 路径和鉴权标签 | Java 弱 Agent | 阶段 3 |
| 语义资源刷新是随发布还是支持热刷新 | 项目负责人 / Java 弱 Agent | 阶段 3 |
| 动态目录刷新周期和多实例协调方式 | Java 弱 Agent / 运维 | 阶段 2 |
| 旧 Phase A 退役日期和回滚窗口 | 项目负责人 | 阶段 5 |

新增未知项时继续追加本表，不得在代码注释中私下决定。

---

## 10. 阶段总览

| 阶段 | 核心目标 | Java 代码量策略 | 云端 Agent / Skill | 主要门禁 |
|---|---|---|---|---|
| 0 | 真实盘点 + 4 问合同 | 不写生产代码 | 保持现状 | 所有未知项有记录 |
| 1 | 语义资源 schema + 校验 | 只做必要 loader/validator | 保持现状 | 资源能表达 4 问 |
| 2 | 动态分类目录 | 最小进程内目录与索引 | 保持现状 | 新 L2.3 无需 YAML |
| 3 | 计划生成接口 | 实现 resolver/mapping/plan，不执行数据 | 尚未切流 | 4 问 T1/T2 通过 |
| 4 | Skill 计划试运行 | 不新增 Java 执行器 | 严格执行 plan | 广告用例真实 T4 |
| 5 | 知识提案 + 旧资源收缩 | 只做必要治理接口 | 处理确认与展示 | 停止整树手维 |
| 6 | PlanExecutor 决策 | 有证据才实施 | 视结果收缩 | 性能/稳定性证据充分 |

---

## 11. 完成定义

本次迁移达到目标，不以“创建了 TBox/ABox 文件”判断，而以以下结果判断：

1. 4 个固定问题都有经真实货架验证的语义合同和明确测试等级。
2. 稳定业务概念与真实货架节点已分离，通过 Mapping 连接。
3. 新增真实 L2.3/L2.4 后，无需复制节点 YAML 即可按真实节点名称解析。
4. 未知口语进入澄清和知识提案流程，不被静默猜测。
5. 精确命中子节点后保持精确范围，不发生自动上卷。
6. `resolveSemanticQuery` 能返回确定、可解释、可版本化的强类型计划。
7. Skill 不再硬编码 aliases、Metric Family、真实 ID 和查询范围规则，只抽取意图、执行计划、确认和展示。
8. 至少一个满足广告数据限制的用例完成真实端到端查数。
9. 不具备真实数据的用例停在正确测试层级，不使用假数据伪装通过。
10. 所有新增或修改的 Java 文件、YAML、测试和 Swagger 位置均登记在文件映射文档中。
11. 在新链路稳定前，现有 Phase A/B 可回退。
