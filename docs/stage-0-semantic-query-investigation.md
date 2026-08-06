# 阶段 0：语义查询真实工程盘点与四问合同

> 执行者：能够访问真实 databp Java 工程、真实货架、RealModel 和现有 MCP 接口的弱 Agent。
> 本阶段性质：调查、取证和合同固化，不开发 `resolveSemanticQuery`，不改生产语义行为。
> 上位计划：[`semantic-query-ontology-migration-plan.md`](semantic-query-ontology-migration-plan.md)。

## 1. 本阶段要回答什么

阶段 0 不是让弱 Agent 设计一套它喜欢的本体，也不是让它提前创建 Java 类。它只负责把下一阶段无法从当前规划仓库得知的事实查清楚：

1. 四个固定问题在真实货架中分别命中哪些分类节点、逻辑实体和指标。
2. 每个问题的正确业务语义、查询模式、范围、指标口径和预期终点是什么。
3. 哪些问题能取得真实数据库数值，哪些只能取得指标目录或受控失败。
4. 现有 `locateNode` 如何复用 `treeModelView()`，如何过滤逻辑实体，是否有缓存或索引。
5. 真实货架中文/英文 aliases 字段的实际字段名、非空比例和当前匹配行为。
6. Phase A YAML、Phase B Metric Family、RealModel 和真实查数代码分别位于哪里。
7. 后续新增语义代码应进入哪些现有 Controller、Service、DTO、loader、resolver 和测试位置。

本阶段的结果必须做到：下一阶段即使换一个零上下文弱 Agent，也能依靠交付物找到真实文件、复现实验并知道哪些值仍未确认。

---

## 2. 已知事实：直接验证，不要重新猜测

以下是项目负责人提供的当前事实。弱 Agent 应通过真实接口或代码补充证据；若观察结果不一致，应记录冲突并请求确认，不能静默覆盖：

1. 首批问题只有 §3 的四个，旧的八问集合废止。
2. 真实货架有中文和英文业务 aliases 字段，但绝大部分为空。
3. 现有 `locateNode` 已在 databp 内部使用 `treeModelView()` 的逻辑拉取真实树，过滤逻辑实体并返回具体分类节点。
4. category-only 目录第一轮应优先照搬、复用或抽取 `locateNode` 已验证的遍历和过滤逻辑，不另造树获取链路。
5. `locateNode` 是否已经实现缓存、缓存在哪里、何时刷新，目前未知，必须查代码。
6. “最近一个月的推广成功率是多少”能够取得最终数据库数据。
7. 广告点击能够取得最终数据库数据；其他与“点击”相关的候选可能无法取得数据。
8. “`ad` 的内存使用率是多少”预期返回广告最小、最大内存使用率两种数据。
9. 小艺有黄金指标，但没有最终数据库数据。
10. 货架节点和逻辑数据实体可以按测试需要调整，但每项调整必须单独登记，不能与生产原状混写。

---

## 3. 固定四问

弱 Agent 必须使用原句，不得为方便匹配而改写：

```text
Q1：最近一个月的推广成功率是多少
Q2：点击的一般时延是多少
Q3：ad的内存使用率是多少
Q4：给我小艺的所有黄金指标
```

四问覆盖的重点不同：

| 问题 | 必须调查的重点 | 当前已知终点 |
|---|---|---|
| Q1 | `推广` 的 alias 来源、成功率指标、滚动一个月、真实 metric ID 和真实数值 | T4 真实查数 |
| Q2 | 所有“点击”候选、正确范围、“一般时延”的规范口径、可查与不可查实体 | 广告点击可 T4；其他候选按事实处理 |
| Q3 | `ad` 的中英文/alias 命中、内存使用率 family、min/max 两个指标和两个结果 | 两种真实数据 |
| Q4 | 小艺范围、全部逻辑实体、黄金过滤字段、完整指标清单、无数值边界 | 指标列表；不查假数据 |

“当前已知终点”不是允许弱 Agent 跳过调查的答案。必须给出真实调用或代码证据。

---

## 4. 不允许做什么

1. 不新增或实现 `resolveSemanticQuery`。
2. 不创建生产 TBox、Mapping、Policy 或 Capability YAML。
3. 不重构 `locateNode`、`treeModelView()`、`resolveMetric` 或查数接口。
4. 不因为没有找到缓存就顺手实现缓存。
5. 不因为其他“点击”候选没有数据就静默删除，只保留广告点击。
6. 不把“一般时延”自行等同于 avg、P50 或其他口径；必须找真实命名、规则或让负责人确认。
7. 不把 Q3 的最小、最大内存使用率合并、平均或静默选择一种。
8. 不为 Q4 伪造小艺数值；它的正确终点是所有黄金指标目录。
9. 不编造 Java 包名、文件路径、货架 ID、逻辑实体 UUID、metric ID、接口字段或缓存策略。
10. 不把测试期间新增/修改的节点和实体写成生产原始事实。
11. 不在交付物中记录鉴权 token、Cookie、SQL 凭据或完整敏感响应；证据只保留必要字段并脱敏。

---

## 5. 调查顺序

### 5.1 建立代码与资源地图

先在真实 Java 仓库定位并阅读，不修改：

1. `locateNode` Controller、Service、DTO、Swagger/schema。
2. `treeModelView()` 定义及其节点结构。
3. `locateNode` 的递归遍历、分类/逻辑实体过滤、name/alias 匹配和排序代码。
4. 与上述逻辑相关的缓存、索引、定时刷新、失效或启动初始化代码。
5. Phase A YAML 的 resources 根路径、loader、entry 和测试。
6. Phase B `metric-families.yaml`、loader、matcher、resolver 和测试。
7. RealModel 的内部 service/repository 和 published 指标过滤逻辑。
8. `getNextLevelNode`、指标目录接口和 `queryIndicatorDimensionData` 的调用位置。
9. 现有 Controller、Service、DTO、配置和测试包的组织规则。

把结果同步写入 `docs/semantic-query-java-file-map.md`，格式见 §8.3。

### 5.2 核实 `locateNode` 与真实树行为

必须回答：

1. `locateNode` 是否每次调用 `treeModelView()`，还是读取缓存。
2. 如果有缓存：缓存类、键、构建时机、刷新/失效条件和多实例行为是什么。
3. 如何区分分类节点与逻辑实体；真实字段和值是什么。
4. 返回结果为什么不含逻辑实体；过滤发生在哪一段代码。
5. 实际匹配哪些字段：ID、中文名、英文名、中文 alias、英文 alias 或 Phase A YAML alias。
6. 中文和英文货架 alias 的真实字段名与数据类型是什么。
7. 四问涉及节点的 alias 字段哪些非空、哪些为空。
8. `depth`、path 和 parent 字段分别如何产生，哪些可以用于范围判断。

复用结论只能写成以下三种之一：

```text
REUSE_AS_IS       # 现有逻辑可直接由后续 resolver 调用
EXTRACT_SHARED    # 逻辑正确，但需抽成现有模块中的共享方法/组件
BLOCKED           # 真实实现无法复用，并附证据；不能直接另写一套
```

### 5.3 为每一问执行分层调查

每一问按相同顺序调查：

1. 记录结构化槽位，不改写原话。
2. 调用当前 `locateNode`，保存全部必要候选，不只保存最终选中的一个。
3. 记录每个候选的匹配字段、matched value、真实 ID、名称和路径。
4. 说明为何选择、保留歧义或拒绝某个候选。
5. 对合法范围调用 `getNextLevelNode`，记录 published 逻辑实体总数和必要标识。
6. 按当前 Skill/接口规则解析指标或列出指标目录。
7. 记录直接指标、歧义、公式、未找到和错误，不提前停止扫描。
8. 仅对预期需要真实数值且真实 metric ID 可查的结果调用查数接口。
9. 记录达到 T1/T2/T3/T4 的哪一级及阻塞原因。
10. 把证据摘要写入 YAML，把过程、判断和冲突写入 Markdown 报告。

### 5.4 Q1 专项检查

必须确认：

1. `推广` 命中广告的依据来自真实货架 alias、Phase A YAML alias，还是二者都有。
2. 命中的准确分类节点和范围。
3. `成功率` 对应的 Metric Family、真实指标和逻辑实体。
4. “最近一个月”由云端 Agent 解释时使用滚动月还是其他规则；本阶段只记录现行规则和实际起止时间，不把时间解析下沉 Java。
5. metric ID 能否成功调用真实数据库查数接口。
6. 返回是单值还是时间序列，以及实际时区。

### 5.5 Q2 专项检查

必须确认：

1. `locateNode("点击")` 的全部分类候选，不得只记录广告点击。
2. 哪个候选是广告点击，其匹配依据和真实路径是什么。
3. 其他候选分别有哪些逻辑实体、相关指标，以及为何不能查数。
4. “一般时延”在现有业务与真实指标中准确对应什么 family/variant；若没有权威依据，标记 `TBD` 并请求负责人决定。
5. 当多个“点击”节点都词法匹配但只有广告点击可查数时，正确语义策略是什么：追问、根据稳定概念映射选择，还是其他规则。不能把“有数据”本身当作语义相关性的证据。
6. 广告点击的最终 metric ID 和真实查数结果。
7. 原问题没有时间表达，而查数接口需要起止时间时，当前正确行为是追问、采用产品默认时间还是已有其他规则；没有已确认规则时标记 `TBD`。

### 5.6 Q3 专项检查

必须确认：

1. `ad` 由中文名、英文名、真实货架 alias 还是 Phase A YAML alias 命中广告。
2. 大小写归一化行为。
3. “内存使用率”命中哪个 Metric Family。
4. 为什么该表达应同时返回 min/max 两个 variant；将依据记录为业务合同，而不是 matcher 偶然返回两个候选。
5. 最小和最大内存使用率分别对应的逻辑实体、metric ID、指标名称和真实数值。
6. 当前 `resolveMetric` 是否会把两个结果标为 `AMBIGUOUS`；如果会，只记录现状和后续合同差距，不在阶段 0 改代码。
7. 原问题没有时间表达时，两个真实数据查询应使用什么时间范围；没有已确认规则时标记 `TBD`，不能私设默认值。

### 5.7 Q4 专项检查

必须确认：

1. `小艺` 命中的准确范围和全部候选。
2. 节点下所有 published 逻辑实体数量。
3. “黄金指标”实际对应哪个字段和值，大小写和可能变体是什么。
4. 用哪个真实接口取得“所有指标”；是 RealModel 已部署指标目录、定义指标还是其他接口。
5. 输出的黄金指标总数、每个指标所属逻辑实体和必要字段。
6. 为什么这些指标不能取得真实数据库数值；记录真实空结果或能力限制。
7. Q4 的 `query_mode` 应是指标目录/list/definition 中的哪一个正式枚举，若当前没有枚举则标记 `TBD`。

### 5.8 测试环境变更登记

如果为了四问修改货架节点或逻辑实体，必须对每项变更记录：

```text
change_id
environment
before
after
reason
affected_questions
created_at
owner
rollback_method
rollback_status
```

没有发生变更时也要在报告中明确写“未修改货架或逻辑实体”，不能省略本节。

---

## 6. 必须交付的文件

阶段 0 完成时必须提交三个文件：

```text
docs/semantic-query-stage-0/
├── semantic-query-facts.yaml
└── investigation-report.md

docs/semantic-query-java-file-map.md
```

说明：

1. `semantic-query-facts.yaml` 是机器可读的调查事实和四问合同，不是生产本体资源，不放进 Java resources。
2. `investigation-report.md` 是给人和下一位 Agent 阅读的调查文章，必须包含证据、判断、冲突和未决项。
3. `semantic-query-java-file-map.md` 是持续维护的真实 Java 文件地图，后续每个阶段都必须更新。
4. 如果某个值未知，YAML 使用 `null` 并在 `open_questions` 登记；Markdown 写 `TBD`、原因、负责人和最晚确认阶段。
5. 不允许用看似合理的示例值替换未知生产值。

---

## 7. `semantic-query-facts.yaml` 预期格式

弱 Agent 应复制以下骨架，替换调查所得的真实值。`<...>` 仅代表说明文字，最终文件中未知值必须写 `null`，不能保留伪值。

```yaml
schema_version: 1
investigated_at: null
investigator: null
java_commit: null
environment: null

known_conditions:
  shelf_has_alias_fields: true
  shelf_alias_coverage: MOSTLY_EMPTY
  locate_node_uses_tree_model_view_in_process: true
  locate_node_filters_logic_entities: true
  locate_node_cache_status: null

locate_node_implementation:
  controller_file: null
  service_file: null
  dto_file: null
  swagger_file: null
  tree_model_view_file: null
  category_discriminator:
    field: null
    category_value: null
    logic_entity_value: null
  matched_fields:
    - field: null
      source: null       # SHELF | PHASE_A_YAML
      normalization: null
  aliases:
    chinese_field: null
    english_field: null
    value_type: null
    observed_non_empty_examples: []
    observed_empty_examples: []
  cache:
    status: null         # PRESENT | ABSENT | UNKNOWN
    implementation_file: null
    build_trigger: null
    refresh_policy: null
    evidence: null
  reuse_decision: null   # REUSE_AS_IS | EXTRACT_SHARED | BLOCKED
  reuse_reason: null

semantic_contracts:
  - id: Q1
    question: 最近一个月的推广成功率是多少
    slots:
      business_phrase: 推广
      metric_phrase: 成功率
      filter_phrases: []
      time_expression: 最近一个月
      query_mode: null
    expected_semantics:
      business_concept_id: null
      runtime_asset_ids: []
      metric_concept_id: null
      metric_variant_ids: []
      filters: []
      scope_policy: null
      expected_status: null
    evidence:
      locate_node_candidates: []
      selected_category_ids: []
      logic_entities: []
      resolved_metrics: []
      query_results: []
    validation:
      highest_level: T4
      real_data_expected: true
      result: null        # PASS | FAIL | BLOCKED
      blockers: []

  - id: Q2
    question: 点击的一般时延是多少
    slots:
      business_phrase: 点击
      metric_phrase: 一般时延
      filter_phrases: []
      time_expression: null
      query_mode: null
    expected_semantics:
      business_concept_id: null
      runtime_asset_ids: []
      metric_concept_id: null
      metric_variant_ids: []
      filters: []
      scope_policy: null
      ambiguity_policy: null
      expected_status: null
    evidence:
      locate_node_candidates: []
      advertising_click_candidate_id: null
      other_click_candidate_ids: []
      logic_entities: []
      resolved_metrics: []
      query_results: []
    validation:
      highest_level: null
      advertising_click_real_data_expected: true
      other_click_real_data_expected: false
      result: null
      blockers: []

  - id: Q3
    question: ad的内存使用率是多少
    slots:
      business_phrase: ad
      metric_phrase: 内存使用率
      filter_phrases: []
      time_expression: null
      query_mode: null
    expected_semantics:
      business_concept_id: null
      runtime_asset_ids: []
      metric_concept_id: null
      metric_variant_ids: []
      expected_variant_roles:
        - MIN
        - MAX
      filters: []
      scope_policy: null
      expected_status: null
    evidence:
      locate_node_candidates: []
      selected_category_ids: []
      logic_entities: []
      resolved_metrics: []
      query_results: []
    validation:
      highest_level: T4
      expected_real_result_count: 2
      real_data_expected: true
      result: null
      blockers: []

  - id: Q4
    question: 给我小艺的所有黄金指标
    slots:
      business_phrase: 小艺
      metric_phrase: null
      filter_phrases:
        - 黄金指标
      time_expression: null
      query_mode: null
    expected_semantics:
      business_concept_id: null
      runtime_asset_ids: []
      metric_concept_id: null
      metric_variant_ids: []
      filters: []
      scope_policy: null
      expected_status: null
    evidence:
      locate_node_candidates: []
      selected_category_ids: []
      logic_entities: []
      metric_catalog_source: null
      gold_metrics: []
      data_query_attempt: null
      data_query_result: null
    validation:
      highest_level: T3
      metric_catalog_expected: true
      real_data_expected: false
      result: null
      blockers: []

test_environment_changes: []

open_questions:
  - id: null
    question: null
    reason: null
    owner: null
    required_by_phase: null
    status: OPEN
```

数组元素的详细字段由真实响应决定，但必须遵守以下最小证据合同：

- `locate_node_candidates`：ID、中文名、英文名、路径、命中字段、命中值、alias 来源。
- `logic_entities`：真实 ID、名称、`parentOperObjId`、published/draft 来源。
- `resolved_metrics`：真实 metric ID、中文名、英文名、family、variant、所属实体、解析状态。
- `query_results`：metric ID、请求时间范围、时区、结果是否为空、结果形态；不要复制不必要的大响应。
- 所有敏感值必须脱敏；真实业务 ID 若项目允许登记则保留，否则记录稳定哈希和安全取证位置。

---

## 8. `investigation-report.md` 预期结构

报告不能只是把 YAML 改成表格。它必须解释调查过程、为什么得出结论以及仍有哪些风险。

```markdown
# 阶段 0 调查报告

## 1. 执行摘要
- 调查环境、Java commit、时间。
- 四问达到的最高测试等级。
- 阶段 1 是否可以开始：GO / NO-GO。
- 阻塞项摘要。

## 2. 调查范围与方法
- 阅读了哪些真实代码。
- 调用了哪些接口。
- 哪些响应经过脱敏。
- 是否修改测试货架或逻辑实体。

## 3. locateNode / treeModelView 事实
### 3.1 调用链
### 3.2 分类与逻辑实体过滤
### 3.3 名称与 aliases 字段
### 3.4 缓存、索引与刷新
### 3.5 后续复用决定

## 4. 四问语义合同
### 4.1 Q1：最近一个月的推广成功率是多少
### 4.2 Q2：点击的一般时延是多少
### 4.3 Q3：ad的内存使用率是多少
### 4.4 Q4：给我小艺的所有黄金指标

每问均包含：槽位、全部候选、正确概念、范围、指标/过滤、计划终点、T1-T4、证据和未决项。

## 5. 真实数据能力矩阵
- 哪些节点/实体有指标。
- 哪些 metric ID 可查数。
- 哪些只能列目录。
- 空数据与接口错误如何区分。

## 6. 测试环境变更
- 每项 before/after、原因、影响和回滚状态。
- 未变更时明确写“无”。

## 7. Java 文件与资源发现
- 链接到 ../semantic-query-java-file-map.md。
- 说明后续代码应进入哪些现有分层，不在此处杜撰新目录。

## 8. 与当前规划的差距
- 当前 Phase A/B 能做什么。
- 四问暴露了哪些合同缺口。
- 哪些缺口属于阶段 1/2/3，阶段 0 不实现。

## 9. 未决事项与负责人
- TBD、证据缺口、负责人、最晚确认阶段。

## 10. 阶段 0 结论
- GO / NO-GO。
- 进入阶段 1 前必须满足的条件。
```

每个 Q 小节至少提供一张表：

| 项目 | 结论 | 证据 | 状态 |
|---|---|---|---|
| 业务对象 | 真实值或 TBD | 文件/接口摘要 | CONFIRMED/TBD |
| 查询范围 | 真实值或 TBD | 候选及选择依据 | CONFIRMED/TBD |
| 指标语义 | 真实值或 TBD | Metric Family/真实指标 | CONFIRMED/TBD |
| 最终能力 | T1/T2/T3/T4 | 真实调用摘要 | PASS/FAIL/BLOCKED |

---

## 9. `semantic-query-java-file-map.md` 预期格式

```markdown
# Semantic Query Java 文件地图

> Java 仓库：<真实仓库>
> 当前基线 commit：<真实 commit>
> 最后核对时间：<时间>

## 1. 现有相关文件

| 逻辑组件 | 模块 | 完整相对路径 | 类/资源 | 职责 | 调用方 | 依赖 | 测试路径 | 状态 |
|---|---|---|---|---|---|---|---|---|
| locateNode Controller | TBD | TBD | TBD | 对外节点定位入口 | TBD | TBD | TBD | EXISTING |
| locateNode Service | TBD | TBD | TBD | 真实树节点搜索 | TBD | treeModelView | TBD | EXISTING |
| treeModelView | TBD | TBD | TBD | 返回真实树 | TBD | TBD | TBD | EXISTING |
| Phase A loader | TBD | TBD | TBD | 读取节点 aliases | TBD | TBD | TBD | EXISTING |
| Phase B resolver | TBD | TBD | TBD | 指标语义解析 | TBD | RealModel | TBD | EXISTING |

## 2. 后续计划文件

| 逻辑组件 | 预期现有模块/分层 | 最终路径 | 职责 | 复用对象 | 测试路径 | 首次阶段 | 状态 |
|---|---|---|---|---|---|---|---|
| BusinessConceptLoader | 调查后填写 | TBD | 加载业务概念 | TBD | TBD | 1 | PLANNED |
| RuntimeShelfAssetResolver | 调查后填写 | TBD | 复用真实树解析动态节点 | locateNode/treeModelView | TBD | 2 | PLANNED |
| SemanticPlanBuilder | 调查后填写 | TBD | 构建强类型计划 | TBD | TBD | 3 | PLANNED |

## 3. Resources 与加载关系

| YAML | Java resources 完整路径 | Loader | Validator | 使用方 | 状态 |
|---|---|---|---|---|---|
| business-concepts.yaml | TBD | TBD | TBD | TBD | PLANNED |

## 4. 对外接口与 Swagger

| 接口 | Controller | DTO | Swagger/schema | 鉴权 | 状态 |
|---|---|---|---|---|---|
| locateNode | TBD | TBD | TBD | TBD | EXISTING |
| resolveSemanticQuery | TBD | TBD | TBD | TBD | PLANNED |

## 5. 路径变更历史

| 日期 | 组件 | 原路径 | 新路径 | 原因 | commit |
|---|---|---|---|---|---|
```

阶段 0 只填写已经确认的现有路径和合理的“预期现有模块/分层”；尚未创建的类不能伪造最终路径。

---

## 10. 证据要求

每个关键结论至少引用一种证据：

1. Java 文件相对路径 + 类/方法名 + 行号或 commit。
2. 脱敏后的真实接口请求与必要响应字段。
3. 真实货架路径和节点 ID。
4. RealModel 中的真实指标名称、ID 和所属逻辑实体。
5. 查数接口的时间范围、时区、结果是否为空。

报告中使用如下格式：

```text
Evidence E-Q2-03
Source: <Java相对路径>#<方法名> / <接口名>
Commit/Environment: <真实值>
Observation: <只写支持结论的必要事实>
Redaction: <脱敏说明或 NONE>
Supports: <该证据支持的合同字段>
```

同一个证据可以支持多个字段，但不能只写“已验证”而不给来源。

---

## 11. 阶段 0 完成门禁

以下全部满足才可以把阶段 0 标为完成：

1. 三个必交付文件存在且相互链接。
2. 四个问题均填写 YAML 合同和 Markdown 小节。
3. Q1 有真实 T4 查数证据。
4. Q2 记录全部“点击”候选，确认广告点击的能力，并明确其他候选的处理策略或保留 `TBD`。
5. Q3 记录 min/max 两个独立真实指标和结果，或明确真实阻塞证据。
6. Q4 列出所有黄金指标，并明确没有真实数值，不使用假数据。
7. 真实货架中文/英文 alias 字段名、类型和四问相关值已记录。
8. `locateNode -> treeModelView()` 调用、逻辑实体过滤和返回结构已有代码证据。
9. 缓存机制明确为 `PRESENT` 或 `ABSENT`；无法确认时阶段 0 为 `NO-GO`，不能写 `UNKNOWN` 后直接进入阶段 2。
10. 所有真实 Java 文件进入文件地图，所有未来文件保留 `TBD` 而非虚构路径。
11. 测试环境变更已回滚或有负责人、期限和风险说明。
12. 所有未决项都有 owner 和最晚确认阶段。

---

## 12. 弱 Agent 最终回复格式

弱 Agent 完成提交后，最终回复必须简洁列出：

```text
Summary
- 三个交付文件及路径
- 四问各自达到的 T1/T2/T3/T4
- locateNode 复用决定
- 缓存调查结论
- 测试环境是否发生变更及回滚状态

Open Questions
- 所有未决项及负责人

Validation
- 实际执行的检查命令
- 真实接口验证摘要（脱敏）
- 对应 commit
```

阶段 0 不得在最终回复中声称已实现语义查询接口或已完成本体迁移。
