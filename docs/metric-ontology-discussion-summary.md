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
