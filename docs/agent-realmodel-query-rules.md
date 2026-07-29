# 云端 Agent 本体增强问数规程

## 1. 文档定位

本文讲清楚 **云端 Agent 的执行逻辑和系统边界**，供方案评审、Skill 编写和云端 Agent 运行时参考。

本文不指导 Java 代码实现。Java 侧的 Phase A 实现见 `docs/locatenode-ontology-mvp.md`，
Phase B 实现见 `docs/metric-family-ontology-mvp.md`。

当前目标是完成一条真实数据闭环：

```text
用户问题
  -> Phase A：定位业务节点
  -> 获取逻辑实体
  -> Phase B：解析指标口径并取得真实指标 ID
  -> 按指标 ID 和时间范围查询真实数据
  -> 展示结果
```

## 2. 系统分工

### 2.1 Java 本体语义层维护什么

Java 侧是本体资产和本体执行逻辑的唯一来源，维护：

1. 节点 `base.yaml`，包括 `id/name_cn/name_en/aliases` 等节点属性。
2. `metric-families.yaml`，包括指标族 aliases、变体、直接指标匹配规则和公式关系。
3. 本体 YAML 的加载、校验、版本和运行时索引。
4. Phase A 的节点匹配逻辑。
5. Phase B 的指标族识别、真实指标匹配和候选消歧逻辑。
6. 后续新增的关系、规则、过滤概念和查询映射等本体资产。

### 2.2 云端 Agent 维护什么

云端 Agent 维护：

1. 识别用户是在查定义、查数值、查趋势、做比较，还是浏览结构。
2. 从问题中抽取业务对象、指标短语、时间范围和筛选条件。
3. 按本文规定的顺序调用接口。
4. 根据接口返回的 `RESOLVED/AMBIGUOUS/NOT_FOUND` 等状态继续执行或追问。
5. 将相对时间转换成现有查数接口要求的明确起止时间。
6. 调用真实数据查询接口。
7. 展示命中对象、指标口径、实际时间范围和真实结果。

### 2.3 云端 Agent 不维护什么

云端 Agent 和 Skill 不应复制或硬编码：

1. 节点 aliases。
2. Metric Family aliases、公式和变体。
3. Java resources 中的业务规则和关系。
4. 真实分类 ID、逻辑实体 ID 或指标 ID。
5. RealModel 内部结构和 SQL。

Skill 可以说明接口调用方式和状态处理，但不能成为第二份业务本体。否则 Java YAML 与 Skill 规则会发生漂移。

## 3. 当前接口与语义阶段

| 能力 | 接口 | 当前职责 |
|---|---|---|
| Phase A | `locateNode(keyword)` | 使用 Java 节点本体把业务说法解析为分类候选 |
| 获取逻辑实体 | `getNextLevelNode(categoryId, CATEGORY)` | 返回分类及其后代下的真实逻辑实体 |
| Phase B | `resolveMetric(logicEntityId, metricPhrase)` | 使用 Java Metric Family 和真实 RealModel 解析目标指标 |
| 查询数据 | `queryIndicatorDimensionData(metricId, startTime, endTime)` | 按真实指标 ID 和明确时间范围查数 |
| 指标目录/排查 | `getLogicEntityRealModel(logicEntityId)` | 浏览或排查已部署指标；不是标准问数链路中的匹配执行者 |

`resolveMetric` 是 Phase B 需要新增的对外语义接口。接口内部自行读取该逻辑实体的真实 RealModel，
云端 Agent 不需要先取得巨大的 RealModel，再把它传回 Phase B。

## 4. 标准问数流程

### 4.1 槽位抽取

云端 Agent 先抽取：

```yaml
business_object: 用户描述的业务对象
metric_phrase: 用户描述的指标口径
filters: 可选筛选条件
time_range: 用户原始时间表达
query_mode: value | trend | comparison | definition
```

示例问题：

```text
最近一个月推广业务的成功占比是多少？
```

抽取结果：

```yaml
business_object: 推广业务
metric_phrase: 成功占比
filters: []
time_range: 最近一个月
query_mode: value
```

不要在调用 Phase A 前擅自把“推广业务”改写成“广告”，否则无法验证 Java 节点 aliases 是否生效。

### 4.2 Phase A：定位分类节点

调用：

```text
locateNode("推广业务")
```

处理规则：

1. 只把点分 ID 的分类节点用于后续导航。
2. 广义查询保留能够覆盖目标范围的最小根节点，避免同时查询祖先和后代。
3. 具体查询选择最贴合的具体节点，不额外扩大到父级。
4. 多个候选无法可靠选择时向用户确认。
5. 未命中时可以建议用户换一种说法；不要自行编造分类 ID。

### 4.3 获取逻辑实体

对确定的分类调用一次：

```text
getNextLevelNode(categoryId, "CATEGORY")
```

`getNextLevelNode` 会递归返回该分类及后代分类中的逻辑实体，因此不能再对其后代重复调用。

处理规则：

1. 使用接口返回的真实逻辑实体 ID。
2. 按实体名称和用户目标收敛候选。
3. 当前广告展示场景应找到“广告测试实体”。
4. 多个实体同样相关时，列出候选并让用户确认；不要批量调用所有实体。

### 4.4 Phase B：解析指标

对选中的逻辑实体调用：

```text
resolveMetric(logicEntityId, "成功占比")
```

云端 Agent 不自行实现 Metric Family 匹配，只处理接口状态。

#### 唯一解析成功

```json
{
  "status": "RESOLVED",
  "family": {
    "id": "success_rate",
    "nameCn": "成功率"
  },
  "selectedMetric": {
    "id": "<真实指标ID>",
    "nameCn": "广告接口成功率",
    "nameEn": "<真实英文名>"
  },
  "matchType": "DIRECT_METRIC",
  "matchedAlias": "成功占比",
  "requiresConfirmation": false
}
```

Agent 保存 `selectedMetric.id`，进入查数。

#### 多个高置信候选

```json
{
  "status": "AMBIGUOUS",
  "candidates": [
    {"id": "...", "nameCn": "...", "reason": "..."},
    {"id": "...", "nameCn": "...", "reason": "..."}
  ],
  "requiresConfirmation": true
}
```

Agent 按接口顺序列出候选并追问，不能静默选择。

#### 只有公式候选

```json
{
  "status": "FORMULA_CANDIDATE",
  "family": {"id": "success_rate", "nameCn": "成功率"},
  "formula": {
    "expression": "numerator / denominator",
    "numerator": {"id": "...", "nameCn": "广告接口成功次数"},
    "denominator": {"id": "...", "nameCn": "广告接口请求次数"}
  },
  "requiresConfirmation": true
}
```

Agent 先说明推导口径并取得用户确认。公式执行还必须保证分子、分母的数据时间粒度和维度能够对齐；
在 Java 接口未返回可安全执行的公式计划前，Agent 不得自行查询两个不明口径的结果后直接相除。

#### 未找到

```json
{
  "status": "NOT_FOUND",
  "message": "未在该逻辑实体的已部署指标中找到 P95 时延"
}
```

Agent 如实说明，不得用平均时延等近似指标替代。

### 4.5 解析时间范围

Phase B 成功后，Agent 把用户时间转换成 `queryIndicatorDimensionData` 的真实参数格式。

规则：

1. “最近一个月”是截止当前时刻的滚动一个月。
2. “上个月”是上一个自然月，与“最近一个月”不同。
3. 必须使用工具实际要求的格式和时区。
4. 用户没有提供时间且接口要求必填时，应先追问或明确提出默认范围，不能静默假设。
5. 最终回答必须回显实际起止时间和时区。

### 4.6 查询真实数据

调用：

```text
queryIndicatorDimensionData(
  selectedMetric.id,
  startTime,
  endTime
)
```

注意：

1. `id` 是 `resolveMetric.selectedMetric.id`，不是分类 ID 或逻辑实体 ID。
2. 不自行构造或缓存跨环境复用的指标 ID。
3. 接口返回单值就展示单值，返回时间序列就展示趋势。
4. 返回空时说明该时间范围内无数据，不能补零或使用假数据。
5. 不改变接口返回的聚合语义。

## 5. 广告真实数据展示

当前真实数据：

```text
广告节点
  -> 广告测试实体
     -> 广告接口成功率
     -> 广告接口最小内存使用率
     -> 广告接口平均时延
     -> 广告接口成功次数
     -> 广告接口最大内存使用率
     -> 广告接口请求次数
```

主演示问题：

```text
最近一个月推广业务的成功占比是多少？
```

预期调用轨迹：

```text
1. locateNode("推广业务")
   -> Phase A 通过广告节点 alias 命中分类。
2. getNextLevelNode(categoryId, "CATEGORY")
   -> 找到“广告测试实体”。
3. resolveMetric(logicEntityId, "成功占比")
   -> Phase B 命中 success_rate。
   -> 从真实 RealModel 中选择“广告接口成功率”。
   -> 返回真实 metricId。
4. queryIndicatorDimensionData(metricId, startTime, endTime)
   -> 返回最近一个月的真实数据。
5. Agent 展示指标、口径、实际时间范围和结果。
```

推荐最终回答结构：

```text
命中对象：广告 > 广告测试实体
指标：广告接口成功率
语义口径：“成功占比”通过 success_rate 指标族解析
查询范围：<startTime> 至 <endTime>（<timezone>）
结果：<真实接口返回摘要>
口径说明：使用已部署的直接成功率指标，未用成功次数/请求次数重新计算。
```

## 6. 定义查询和排查流程

当用户只是问“广告测试实体有哪些指标”时，可以调用 `getLogicEntityRealModel` 获取精简指标目录，
不需要调用 `resolveMetric` 和查数接口。

`getLogicEntityRealModel` 还可用于：

1. 排查为什么 `resolveMetric` 未命中。
2. 展示已部署指标目录。
3. 对照某个指标的名称、描述、单位、类型或等级。

由于 RealModel 原始数据量大，Swagger 应只向 Agent 暴露排查所需字段。Swagger 投影只负责控量，
不承担 Phase B；真正的 Phase B 在 Java `resolveMetric` 内执行。

## 7. 后续本体能力如何接入

后续关系、规则、过滤概念和查询映射等本体能力仍由 Java YAML 和 Java 运行时维护。
云端 Agent 不读取这些 YAML，而是调用 Java 暴露的语义接口取得解析结果或执行计划。

为了避免每增加一种 YAML 就增加一个接口，后续可以新增一个组合式语义解析接口，例如：

```text
resolveSemanticQuery(structuredIntent)
```

它可以返回节点、实体、指标、过滤条件、关系、规则依据和查询计划。当前 `resolveMetric` 保持职责单一，
先完成 Phase B；是否升级或被组合接口复用，由后续阶段的真实需求决定。

接口划分原则：

1. 不按每个 YAML 文件暴露一个接口。
2. 不要求 Agent 自己串联 Java 本体内部的每个小模块。
3. 语义解析与真实数据执行保持分离。
4. 内部模块可以很多，对外接口按稳定业务职责收敛。
5. 若某类能力输入输出、性能或安全边界明显不同，可以放心拆成独立接口，不为追求数量少而制造万能接口。

## 8. 云端 Agent 禁止事项

1. 不在 Skill 中复制 Java aliases、Metric Family、公式或业务规则。
2. 不用自由联想替代 `locateNode` 或 `resolveMetric`。
3. 不自行扫描 RealModel 并实现另一套 Phase B。
4. 不自行构造分类、实体或指标 ID。
5. 不执行、改写或拼接 SQL。
6. 不把成功率、成功次数和请求次数视为同一个指标。
7. 不把平均、最小、最大、P95/P99 等口径互相替代。
8. 不在多个高置信候选中静默选择。
9. 不使用 `getLogicEntityDefineInfo` 中未部署的定义指标做生产查数。
10. 不使用本地假数据替代真实接口结果。
