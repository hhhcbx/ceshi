# Metric Ontology 讨论结论与复盘

## 1. 本文目的

本文记录本轮关于 PR9、PR10、metric-query skill、本体层、locateNode、gateway、databp 和 RealModel 查询链路的讨论结论。

目的有两个：

1. 让其他 Agent 快速理解当前思路，避免重新争论 gateway、接口新增、本体粒度等问题。
2. 给项目维护者一个简要复盘，避免后续遗忘关键决策和约束。

## 2. 真实工作模式

当前仓库只是中转站，不是真正执行代码和测试的主环境。真实代码最终会写入另一个受限环境，其中有一个能力较弱的 Agent，且外部强 Agent 无法直接操作或测试。

因此，当前协作模式是：

```text
强 Agent 负责：理解、规划、写方案、写文档、写代码草稿、排错建议。
用户负责：把文档下载给弱 Agent，或把弱 Agent 的反馈贴回仓库。
弱 Agent 负责：在真实环境中实际改代码、部署、测试。
```

当前仓库中有很多与本项目无关的文件。与本项目直接相关的是：

1. PR8 的 metric-query skill。
2. PR9 的 locateNode 交接思路。
3. PR10 的本体语义层构想。
4. `skills/metric-query` 目录。

PR 是否已合并不是关键，仓库主要作为方案和交接材料的暂存地。

## 3. 环境与接口约束

### 3.1 Agent 能直接调用 databp 接口

Agent 当前可以直接调用 databp 中已有的接口，包括：

1. `getModelTree`
2. `getNextLevelNode`
3. `getLogicEntityDefineInfo`
4. `getLogicEntityRealModel`
5. 已新增的 `locateNode`

### 3.2 新增 databp 对外接口很麻烦

在 databp 中新增一个可被 Agent 调用的接口涉及权限、鉴权、Swagger/MCP 契约、云上部署等问题，成本高、风险大。

`locateNode` 是已经被打通的新增接口，因此后续如需改造，应优先集中在 `locateNode` 上，而不是继续新增多个 databp 对外接口。

### 3.3 gateway 暂不参与真实查询链路

gateway 中新增接口虽然方便，但 gateway 环境无法访问 databp 真实货架数据。因此，gateway 不能作为真实数据查询的中转。

结论：

```text
需要真实货架数据的链路不走 gateway。
gateway 暂时不用管。
```

## 4. locateNode 的新定位

`locateNode` 最初用于解决：

```text
用户只有节点名称或业务词，但 getNextLevelNode 需要分类节点 ID。
```

旧问题：

1. `getModelTree` 返回全量树，数据太大，几乎不可用。
2. `getNextLevelNode` 需要分类节点 ID。
3. 用户说 `ads`、`ad`、`推广` 时，原始节点名搜索可能找不到中文节点「广告」。
4. 货架路径中可能存在多个同名节点，例如两个都叫「广告」的节点。

新结论：

```text
locateNode 应改造成轻量本体定位接口。
```

它应该：

1. 读取 databp resources 中的 `nodeConcepts.yaml`。
2. 优先用本体配置匹配业务节点、别名和真实 categoryId。
3. 本体未命中时，再走旧树搜索兜底。
4. 返回分类节点 ID、路径、命中概念、置信度和原因。

它不应该：

1. 不做完整问数理解。
2. 不处理任意长对话。
3. 不调用 `getNextLevelNode`。
4. 不调用 `getLogicEntityRealModel`。
5. 不执行 SQL。
6. 不返回真实指标值。

## 5. 本体层的边界

本体层不应该事无巨细维护所有具体业务指标。否则会变成难以维护的手工知识库或知识图谱。

更合适的边界是：

```text
本体 = 稳定业务概念 + 货架节点绑定 + 通用指标族 + 通用过滤概念 + 少量业务特例。
```

第一阶段只强制落地：

```text
nodeConcepts：业务/货架节点概念。
```

例如：

```text
广告
广告点击
小艺
翻译
支付
搜索
```

这些用于解决：

```text
用户词 / 英文别名 / 口语表达 -> 真实货架 categoryId
```

## 6. 具体指标不应全部写进本体

以下指标不应全部逐条写入本体：

```text
广告点击率
广告曝光率
广告时延
广告内存使用率
广告成功率
广告请求次数
广告失败次数
```

更合理的方式是分层：

### 6.1 指标族 Metric Family

维护通用指标族，例如：

```text
成功率
曝光率
点击率
时延
内存使用率
CPU 使用率
请求次数
失败次数
错误率
```

这些用于指导 Agent 在 RealModel 已部署指标中匹配候选。

### 6.2 过滤概念 Filter Concept

维护通用筛选条件，例如：

```text
黄金 -> level=GOLD
健康 -> level=HEALTH
普通 -> level=NORMAL
端侧打点 -> collectSide/sourceType/tags 中的端侧相关值
```

这些是过滤规则，不是具体业务指标本体。

### 6.3 少量业务特例 Metric Exception

只有高频、高风险、特别容易歧义的指标才写特例。

例如「广告成功率」可以作为代表性特例，因为它可能对应：

1. 直接指标：广告成功率。
2. 公式候选：广告接口成功次数 / 广告接口请求次数。
3. 相关但不同：广告曝光率。

但这不是所有具体指标的维护模式。

## 7. Agent 和 locateNode 的分工

### 7.1 Agent 负责槽位抽取

Agent 应先从用户问题中抽取：

```yaml
business_object: 用于定位货架节点的业务对象
metric_phrase: 用户想查的指标短语
filters: 指标或数据筛选条件
time_range: 时间范围
query_mode: definition | value | trend | comparison
```

例如：

```text
最近一个月的指标等级是黄金的广告成功率是多少？
```

抽取：

```yaml
business_object: 广告
metric_phrase: 广告成功率
filters:
  - level = GOLD
time_range: 最近一个月
query_mode: value
```

### 7.2 locateNode 负责节点定位

Agent 调用：

```text
locateNode("广告")
```

不要默认把长篇用户输入原样丢给 `locateNode`。

### 7.3 Agent 负责后续编排

拿到分类节点 ID 后，Agent 继续：

```text
getNextLevelNode(categoryId, CATEGORY)
  ↓
getLogicEntityRealModel(logicEntityId)
  ↓
匹配已部署指标
  ↓
应用过滤和时间条件
  ↓
必要时消歧
```

## 8. RealModel 是生产查数依据

关键纠正：

```text
getLogicEntityDefineInfo 返回未部署指标，数据库中找不到。
getLogicEntityRealModel 返回已部署指标，是生产查数依据。
```

因此，生产链路应直接使用：

```text
getNextLevelNode
  ↓
getLogicEntityRealModel
```

`getLogicEntityDefineInfo` 只用于测试、对照、排查，不用于生产查数。

## 9. 广告成功率场景复盘

货架链路：

```text
业务平台 > 广告 > 广告 > 广告点击
```

真实分类 ID 示例：

```text
business_and_platform.ADV.AdvertiserRebate.pps_click
```

该节点下有逻辑实体「广告测试」。RealModel 中可能有：

1. 广告成功率
2. 广告接口成功次数
3. 广告接口请求次数
4. 广告曝光率

用户问：

```text
最近一个月的广告成功率是多少？
```

推荐流程：

```text
1. Agent 抽取 business_object=广告，metric_phrase=广告成功率，time_range=最近一个月。
2. Agent 调 locateNode("广告")。
3. locateNode 基于 nodeConcepts.yaml 返回广告相关分类节点。
4. Agent 选择或追问确认广告点击节点。
5. Agent 调 getNextLevelNode。
6. Agent 对逻辑实体调用 getLogicEntityRealModel。
7. Agent 优先匹配 RealModel 中的直接指标「广告成功率」。
8. 如果没有直接指标，再考虑「广告接口成功次数 / 广告接口请求次数」公式候选。
9. 「广告曝光率」只是相关但不同，不能默认作为成功率。
10. Agent 应用最近一个月时间条件。
11. 查询并返回结果。
```

## 10. 已确认的设计决策

1. gateway 暂时不用管。
2. 不新增多个 databp 对外接口。
3. 改造已打通的 `locateNode`。
4. 不给 `locateNode` 增加 mode，默认就是新逻辑。
5. `locateNode` 不做一站式问数。
6. Agent 调用 `locateNode` 前应尽量先抽取短定位词。
7. 本体第一阶段只强制维护节点概念和真实 categoryId 映射。
8. 不穷举所有具体指标。
9. 指标匹配以 RealModel 已部署指标为准。
10. `getLogicEntityDefineInfo` 只测试，不作为生产查数依据。
11. 本体找不到时，Agent 语义增强只能作为兜底，不是主流程。
12. 多个高置信候选时必须追问。

## 11. 后续文档

本次沉淀出两份执行文档：

1. `docs/locatenode-ontology-mvp.md`：指导弱 Agent 改造 `locateNode` 和 `nodeConcepts.yaml`。
2. `docs/agent-realmodel-query-rules.md`：指导 Agent 如何基于 `getNextLevelNode` 和 `getLogicEntityRealModel` 做生产问数。

本文作为讨论总结和复盘入口，供后续 Agent 快速理解背景。

---

## 12. 2026-07-24 对齐：locateNode 本体文档改为代码侧弱 Agent 实施说明

本轮用户明确纠正了文档对象和系统边界：

1. Java 侧确实需要修改 `locateNode` 代码和 resources 里的 YAML，使 `locateNode` 融入本体语义层。
2. “弱 Agent”指的是在 IDEA 中辅助编码的内部弱 Agent，它有权限访问 Java 工程、内部代码和 resources，因此 `docs/locatenode-ontology-mvp.md` 应该演化成写给代码侧弱 Agent / 工程实现者看的实施文档。
3. “Agent 侧”指的是 databp 部署到云上后，由另一个云端 Agent 调用接口执行问数逻辑。因此 `docs/agent-realmodel-query-rules.md` 才应该演化成给云端 Agent Skill 提供指导的文档。
4. 之前把“弱 Agent 辅助编码文档”说成可选新增文档，或者把 Java 侧实现与云端 Agent 调用规程写在一起，是错误的逻辑；两份文档必须分工明确。
5. 用户发现 Java 项目里已经有简要本体/节点数据，位于 `resources/DataModel` 路径下。
6. `resources/DataModel` 的组织方式是每个节点一个文件夹；如果节点有子节点，就继续嵌套子文件夹；每个节点目录下有一个 `base.yaml`。
7. `base.yaml` 中已有字段包括 `id`、`parent_category_id`、`name_cn`、`name_en`、`description`，不同节点还可能有 `version`、`owner`、`offering` 等字段。
8. 这份 resources 节点信息可能与现有真实货架不完全一致。例如「广告点击」真实 ID 是 `business_and_platform.ADV.AdvertiserRebate.pps_click`，但 resources 可能只记录到 `business_and_platform.ADV.AdvertiserRebate`。
9. 这不代表叶子节点不应该记录，只是当前 resources 信息没有完全更新。MVP 阶段不要因此阻塞，应先跑通流程，节点信息后续再慢慢同步。
10. 用户建议最好复制一份现有 `resources/DataModel`，然后在副本基础上修改，而不是直接改原始数据。
11. 从本轮开始，每轮对话都要把记录追加到 `docs/metric-ontology-discussion-summary.md` 后面。要求是追加即可，不压缩内容，不修改原始内容。

基于以上对齐，本轮将 `docs/locatenode-ontology-mvp.md` 改写为代码侧实施方案，重点包括：

1. 明确文档对象是 Java 代码侧弱 Agent，不是云端问数 Agent。
2. 明确云端 Agent 的 RealModel 查询和问数编排规则属于 `docs/agent-realmodel-query-rules.md`。
3. 引入已有 `resources/DataModel` 作为输入现状。
4. 建议复制一份 DataModel 到本体运行时目录，例如 `resources/ontology/metric-shelf/DataModel`。
5. 建议在副本 `base.yaml` 中保留原字段，并新增 `ontology` 字段块保存 `concept_id`、`aliases`、`confidence`、`tags`、`match_reason`。
6. 明确广告点击缺失叶子节点可以在副本中先手工补齐，真实 ID 写完整：`business_and_platform.ADV.AdvertiserRebate.pps_click`。
7. 明确 `locateNode` 只做节点定位：加载本体 DataModel、匹配 keyword、返回候选节点、未命中时走旧树搜索兜底；不查实体、不查 RealModel、不执行 SQL。
8. 增加 DataModel loader、匹配规则、返回结构、本地测试 checklist、云上部署前检查和常见错误。

---

## 13. 2026-07-24 再对齐：locateNode MVP 本体层先简化为 aliases

本轮用户继续纠偏，认为上一版 `locatenode-ontology-mvp.md` 仍然过度复杂。新的关键理解如下：

1. 当前这一步的本体作用不应该被拔高；在 locateNode MVP 中，本体最直接、最有效的用途就是 `aliases` 这一个字段。
2. 通过把用户可能说的同义词、英文、缩写、口语表达列举到节点 `base.yaml` 的 `aliases` 中，提高节点匹配的准确性和召回率。这本质上是一个简单、低技术含量但有效的语义映射方法。
3. 不需要额外维护 `concept_id`。用户指出，节点本身的名字就是一个本体概念；节点已有 `id`、`name_cn`、`name_en`，额外引入 `concept_id` 会变成第二套命名体系，增加维护成本。
4. 不需要手工维护 `path`。用户指出，`id` 中已经用分隔符明确表达了层级关系；再维护 path 容易重复且不同步。
5. 用户粘贴了两篇“本体 + Agent”的文章，要求理解其中思路，但不要联网查原文或图片。
6. 从文章中吸收的核心思想是：本体不是另一个数据库，而是 Agent 和企业系统之间的业务语义层；不一定每次都用推理机，轻量查阅也是本体的一种用法。
7. 对当前 locateNode MVP 来说，这个轻量查阅层就是：用户说法 / 口语 / 英文 / 缩写 → aliases → 货架节点 base.yaml → 真实 databp 分类 ID。
8. 因此本轮将 `docs/locatenode-ontology-mvp.md` 再次简化：去掉 `ontology.concept_id`、`ontology.tags`、`ontology.confidence`、`ontology.match_reason`、手工 `path` 等设计；只保留顶层 `aliases` 作为必须新增字段。
9. 返回结构也随之简化：尽量沿用旧结构，只建议增加 `parentCategoryId`、`matchType`、`matchedValue` 这类轻量字段，不再新增 `matchedConceptId`、`confidence`、`reason`。
10. 匹配规则也简化为只匹配 `id/name_cn/name_en/aliases`，不再匹配 `description`，避免描述文本带来噪声。
11. 仍然保留前一轮已经确认的边界：本文是给 Java 代码侧弱 Agent 的实施文档；云端 Agent 的问数编排规程仍归 `docs/agent-realmodel-query-rules.md`；`locateNode` 不查实体、不查 RealModel、不执行 SQL；旧树搜索兜底不能删除。

---

## 14. 2026-07-24 对齐：Layer 2 Metric Family 应独立于节点 base.yaml

本轮用户提出了 Layer 2 的关键建模问题：如果每个 `base.yaml` 都是货架树上一个节点对应的本体，那么 `aliases`、`id`、`name` 等都可以理解为该节点本体的属性；接下来要添加指标口径本体 / Metric Family 本体时，是否也应该像 Layer 1 一样写在每个节点的 `base.yaml` 后面。

本轮达成的设计判断：

1. 每个节点目录下的 `base.yaml` 可以理解为一个“节点本体文件”，对应货架树上的一个节点。
2. `id` 是节点稳定标识，`parent_category_id` 是父子关系属性，`name_cn/name_en` 是名称属性，`description` 是描述属性，`aliases` 是 Layer 1 节点别名属性。
3. Metric Family 不应写进每个节点的 `base.yaml`。原因是成功率、时延、内存使用率等指标族是跨业务节点复用的指标口径概念，不属于单个广告节点、小艺节点或支付节点。
4. 如果把 Metric Family 写进每个节点 `base.yaml`，会导致同一套成功率规则在多个节点中重复维护，后续规则变更时容易不一致，也会混淆“节点本体”和“指标族本体”。
5. Layer 2 应新增独立 YAML，例如 `resources/ontology/metric-shelf/metric-families.yaml`，集中维护成功率、时延、内存使用率等通用指标族。
6. 节点 `base.yaml` 继续回答“用户说的业务对象是什么节点”；`metric-families.yaml` 回答“用户说的指标口径是什么意思，在候选指标列表中如何匹配直接指标、公式候选和相关但不等价候选”。
7. 广告只是 Layer 2 的测试样例，不是规则边界。`success_rate` 应写成通用指标族，可复用于广告、小艺、搜索、支付、翻译等业务节点。
8. 本阶段暂不解决真实查数和 SQL 执行，只做本地可测的指标匹配、口径识别、公式候选和消歧输出。
9. 测试数据可先合理编造，包括广告接口成功率、广告接口最小内存使用率、广告接口平均时延、广告接口成功次数、广告接口最大内存使用率、广告接口请求次数等。
10. 对问题“最近一个月广告成功率是多少？”，Layer 1 负责定位广告节点，Layer 2 负责识别 `success_rate` 指标族，并在候选指标中优先找到直接指标“广告接口成功率”，同时识别公式候选“广告接口成功次数 / 广告接口请求次数”。用户已明确成功率=成功次数/请求次数，因此测试期可使用公式口径但必须解释。
11. 本轮新增 `docs/metric-family-ontology-mvp.md`，作为像 `locatenode-ontology-mvp.md` 一样面向弱 Agent 的 Layer 2 构建指导文档。
