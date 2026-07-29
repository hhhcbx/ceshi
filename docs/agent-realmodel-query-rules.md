# 云端 Agent：RealModel 指标问数规程

## 1. 目标与边界

本文指导云端 Agent 使用现有工具完成真实问数。后端接口不可修改；
`getLogicEntityRealModel` 的 Swagger 响应已被投影为精简指标目录，
`queryIndicatorDimensionData` 负责按指标 ID 和时间范围查数。

两个语义层分工如下：

1. Phase A（节点 aliases）：把用户业务说法映射到货架分类节点。
2. Phase B（Metric Family）：把用户指标说法映射到 RealModel 中的真实指标。

Agent 不执行 SQL，不从 `getLogicEntityDefineInfo` 获取生产指标，不自行构造节点、实体或指标 ID。

## 2. 完整调用链

```text
用户问题
  -> 抽取 business_object / metric_phrase / time_range
  -> locateNode(business_object)
  -> getNextLevelNode(categoryId, CATEGORY)
  -> 选择逻辑实体
  -> getLogicEntityRealModel(logicEntityId)
  -> 按 Metric Family 匹配真实 metric.id
  -> 将时间表达转换成明确 startTime/endTime
  -> queryIndicatorDimensionData(metric.id, startTime, endTime)
  -> 展示真实返回
```

不要跳过 RealModel 直接猜指标 ID，也不要把逻辑实体 ID 传给查数接口。

## 3. 槽位抽取

```yaml
business_object: 用于 locateNode 的业务对象短语
metric_phrase: 用户要查询的指标短语
time_range: 用户时间表达及转换后的明确起止时间
query_mode: value | trend | comparison
filters: 可选的指标元数据或维度过滤条件
```

示例：

```text
最近一个月推广业务的成功占比是多少？
```

```yaml
business_object: 推广业务
metric_phrase: 成功占比
time_range:
  text: 最近一个月
  startTime: 按当前日期和接口格式计算
  endTime: 按当前日期和接口格式计算
query_mode: value
```

必须把 `business_object` 原样优先传给 `locateNode`，让 Phase A aliases 发挥作用；
只有未命中时才做 Agent 语义改写兜底，并在回答中说明。

## 4. Phase A：定位节点和实体

1. 调用 `locateNode(business_object)`。
2. 多个分类候选时，按用户粒度和点分 ID 做最小覆盖根/最贴合节点选择。
3. 无法唯一确定时追问，不要静默猜。
4. 对最终分类调用一次 `getNextLevelNode(id, "CATEGORY")`。
5. 本次广告演示选择“广告测试实体”；必须使用接口返回的真实实体 ID。
6. 多个实体都可能包含目标指标时，可按实体名收敛后逐个取 RealModel；仍有多个高置信结果时追问。

## 5. Phase B：匹配真实指标

### 5.1 通用顺序

1. 用 Metric Family aliases 识别指标族和变体。
2. 在 RealModel `metrics` 中先匹配 `nameCn`，再匹配 `nameEn`，必要时用 `description` 消歧。
3. 保留平均/最小/最大、P95/P99、次数/比率等限定词，不能在归一化时删除。
4. 一个高置信直接指标：使用其真实 `id`。
5. 多个高置信指标：向用户列出名称和实体并追问。
6. 没有符合变体的指标：报告未找到，不能用近似但不同口径代替。

### 5.2 成功率

`成功率`、`成功占比`、`接口成功率`、`success_rate` 属于 `success_rate` family：

1. 优先直接指标，名称含“成功率”或 `success_rate`。
2. 成功次数和请求次数是公式候选，不是直接成功率。
3. 直接指标存在时，直接查询它；不要重复查两个次数指标后重算。
4. 只有公式候选时，说明“成功率 = 成功次数 / 请求次数”并先请求确认；当前查数接口每次按单一指标 ID 查询，
   如需组合两次返回，还必须确认时间粒度和对齐方式，不能直接把两个总值随意相除。

### 5.3 时延与内存

1. “平均延迟”可匹配“平均时延”，但不能匹配 P95/P99 时延。
2. “最低内存占用率”可匹配“最小内存使用率”。
3. “最高内存使用率”可匹配“最大内存使用率”。
4. 最小值和最大值不能互相替代；使用率和使用量不能互相替代。

## 6. RealModel 控量规则

Swagger 投影后的 RealModel 应只提供实体标识和指标的：`id`、`nameCn`、`nameEn`、
`description`、`unit`、`type`、`level`（后四项按真实存在情况返回）。

Agent 规则：

1. 只读取匹配所需字段，不复述整个指标目录。
2. 指标 `id` 必须来自本次 RealModel 返回。
3. 字段缺失时不猜。例如没有 `level` 就不能可靠执行“黄金指标”过滤。
4. 如果工具仍返回巨型对象，停止继续批量调用并报告 Swagger 投影未生效，避免上下文爆量。

## 7. 时间范围与查数

1. 将相对时间转换为明确 `startTime` 和 `endTime`。
2. “最近一个月”默认解释为截止当前时刻的滚动一个月；“上个月”是上一个自然月，二者不同。
3. 使用工具实际要求的时间格式和时区，不可凭示例猜格式。
4. 调用 `queryIndicatorDimensionData(id, startTime, endTime)`，其中 `id` 是指标 ID。
5. 最终回答必须回显实际起止时间和时区。
6. 不改变接口返回的聚合语义：接口返回时间序列就展示趋势；只返回单值就展示单值；返回空就如实说明无数据。
7. 用户没有给时间范围且查数接口要求必填时，先追问，不能默选一个范围而不说明。

## 8. 完整演示

用户：

```text
最近一个月推广业务的成功占比是多少？
```

执行：

```text
1. 抽取 business_object=推广业务、metric_phrase=成功占比、time_range=最近一个月。
2. locateNode("推广业务")，通过 Phase A alias 命中广告节点。
3. getNextLevelNode，找到“广告测试实体”。
4. getLogicEntityRealModel，读取六个真实指标的精简目录。
5. Phase B 将“成功占比”识别为 success_rate。
6. 从六个指标中唯一选中“广告接口成功率”，保存其真实 id。
7. 计算并记录明确 startTime/endTime。
8. queryIndicatorDimensionData(指标 id, startTime, endTime)。
9. 返回真实值/序列、实际时间范围、指标名称和口径说明。
```

推荐回答结构：

```text
命中对象：广告 > 广告测试实体
指标：广告接口成功率（用户说法“成功占比”按 success_rate 口径匹配）
查询范围：<startTime> 至 <endTime>（<timezone>）
结果：<queryIndicatorDimensionData 的真实返回摘要>
口径说明：优先使用已部署的直接成功率指标；未用成功次数/请求次数重新计算。
```

## 9. 必须消歧或失败的情况

1. 多个分类节点或逻辑实体同样匹配。
2. RealModel 中存在多个同口径直接指标。
3. 只有公式候选，而用户尚未确认计算口径。
4. 用户问 P95 时延，但只有平均时延。
5. 指标缺少真实 ID。
6. 相对时间无法按接口要求转成确定值。
7. RealModel 投影未生效导致返回不可控。
8. 查数接口返回空或报错。

上述情况不得编造结果。可以追问的先追问；接口错误应简要报告已完成到哪一步。

## 10. 禁止事项

1. 不使用 `getLogicEntityDefineInfo` 代替 RealModel 做生产查数。
2. 不执行、改写或拼接 SQL。
3. 不自行构造任何 ID。
4. 不把成功次数、请求次数、成功率当成同一指标。
5. 不把平均、最小、最大或分位数互相替换。
6. 不让 Agent 的自由联想替代 Phase A/Phase B；语义增强只能是明确标注的兜底。
7. 不为了给出答案而伪造本地测试数据或数值。
