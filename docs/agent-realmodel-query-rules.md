# Agent 基于 RealModel 的指标问数规程

## 1. 目标

本文规定 Agent 在拿到货架分类节点后，如何使用 databp 已有接口查询真实已部署指标，并完成指标匹配、筛选、消歧和查数。

核心原则：

1. 生产查数以 `getLogicEntityRealModel` 返回的已部署指标为准。
2. `getLogicEntityDefineInfo` 只用于测试、对照或排查，不作为生产查数依据。
3. 本体层主要解决业务对象到货架分类节点的定位问题。
4. 指标匹配、过滤条件、时间条件由 Agent 基于 RealModel 结果处理。
5. 多个高置信候选时必须追问，不要静默猜。

## 2. 总体链路

```text
用户问题
  ↓
Agent 抽取槽位
  ↓
locateNode(业务/对象定位短语)
  ↓
getNextLevelNode(categoryId, CATEGORY)
  ↓
getLogicEntityRealModel(logicEntityId)
  ↓
在已部署指标中匹配 metric_phrase
  ↓
应用 filters/time_range
  ↓
必要时消歧
  ↓
查 SQL / 返回结果
```

## 3. 槽位抽取

Agent 先从用户问题抽取以下槽位：

```yaml
business_object: 用于定位货架节点的业务对象
metric_phrase: 用户想查的指标短语
filters: 指标或数据筛选条件
time_range: 时间范围
query_mode: definition | value | trend | comparison
```

示例：

```text
用户问题：最近一个月的指标等级是黄金的广告成功率是多少？
```

抽取：

```yaml
business_object: 广告
metric_phrase: 广告成功率
filters:
  - field: level
    operator: =
    value: GOLD
time_range:
  text: 最近一个月
  type: ROLLING_LAST_MONTH
query_mode: value
```

## 4. 节点定位

Agent 使用 `business_object` 调用 `locateNode`：

```text
locateNode("广告")
```

如果返回多个候选：

1. 优先选择与用户业务对象最具体、最贴合的节点。
2. 如果用户指标短语能帮助判断，可以结合指标短语选择，例如「广告成功率」可能比广告大类更接近广告点击链路。
3. 如果仍有多个高置信候选，必须追问用户。

不要把长篇用户输入原样传给 `locateNode`，除非槽位抽取失败。

## 5. 获取逻辑实体

对选中的分类节点调用：

```text
getNextLevelNode(categoryId, CATEGORY)
```

注意：

1. `getNextLevelNode` 会返回该分类及后代分类下的逻辑实体。
2. 如果节点过高，返回实体可能很多，Agent 应优先筛选与业务对象相关的逻辑实体。
3. 后续调用 RealModel 时使用逻辑实体的真实 `id`。

## 6. 获取已部署指标

对候选逻辑实体调用：

```text
getLogicEntityRealModel(logicEntityId)
```

只使用 RealModel 中已部署的指标和 SQL 做生产查询。

`getLogicEntityDefineInfo` 的定位：

```text
仅用于测试、对照、排查未部署指标，不用于生产查数。
```

## 7. 指标匹配规则

### 7.1 基础优先级

给定用户指标短语 `metric_phrase`，在 RealModel 指标列表中按以下顺序匹配：

1. `nameCn` 完全等于 `metric_phrase`。
2. `nameEn` 完全等于英文或编码化后的 `metric_phrase`。
3. `nameCn` 包含完整 `metric_phrase`。
4. `metric_phrase` 包含 RealModel 指标中文名。
5. 按指标族规则匹配。

### 7.2 成功率规则

用户说「成功率」时：

1. 优先找直接指标：名称包含「成功率」或 `success_rate`。
2. 如果没有直接成功率，查找公式候选：
   - 分子：名称包含「成功次数」「成功量」「success_count」。
   - 分母：名称包含「请求次数」「请求量」「request_count」。
3. 「曝光率」「点击率」虽然也是 rate，但不能默认等同成功率。
4. 如果只有公式候选，默认追问用户是否按该口径计算，除非业务规则明确允许自动计算。

### 7.3 曝光率规则

用户说「曝光率」时：

1. 优先找名称包含「曝光率」或 `exposure_rate` 的指标。
2. 不要自动替换为成功率、点击率。
3. 如只有曝光次数和总请求次数，应说明这是推导口径并请求确认。

### 7.4 点击率规则

用户说「点击率」时：

1. 优先找名称包含「点击率」或 `click_rate` / `ctr` 的指标。
2. 如只有点击次数和曝光次数，可作为公式候选。
3. 不要自动替换为广告成功率。

### 7.5 时延规则

用户说「时延」「延迟」「latency」「rt」时：

1. 优先找名称包含「时延」「延迟」「耗时」「latency」「rt」的指标。
2. 如果用户指定 P95/P99/平均值，必须匹配对应分位或聚合口径。
3. P95、P99、平均时延不能互相默认替换。

### 7.6 内存使用率规则

用户说「内存使用率」「内存占用」「memory usage」时：

1. 优先找名称包含「内存」「memory」「mem」的指标。
2. 如果同时存在使用量和使用率，按用户短语区分：
   - 使用率：ratio/rate/percent。
   - 使用量：bytes/MB/GB/count。

## 8. 过滤条件规则

### 8.1 指标等级

| 用户说法 | 过滤条件 |
|---|---|
| 黄金、黄金指标、gold | `level = GOLD` |
| 健康、健康指标、health | `level = HEALTH` |
| 普通、普通指标、normal | `level = NORMAL` |

如果 RealModel 指标中没有 `level` 字段，Agent 应说明无法可靠按等级过滤。

### 8.2 指标类型

| 用户说法 | 过滤条件 |
|---|---|
| 基础指标、原子指标、basic | `type = BASIC` |
| 衍生指标、派生指标、derived | `type = DERIVED` |
| 复合指标、组合指标、composite | `type = COMPOSITE` |

如果 RealModel 中没有 `type` 字段，Agent 应说明无法可靠按类型过滤。

### 8.3 端侧打点

用户说「端侧」「端侧打点」「客户端打点」「client side」时，尝试在 RealModel 指标元数据中查找：

```text
collectSide
sourceType
dataSource
tags
nameCn/nameEn
```

候选值包括：

```text
CLIENT
client
端侧
客户端
device_side
```

如果 RealModel 没有可判断字段，不要猜，应明确说明无法可靠筛选端侧打点口径。

## 9. 时间条件规则

常见时间表达式：

| 用户说法 | 解释 |
|---|---|
| 最近一个月、近一个月、过去一个月 | 滚动最近 1 个月 |
| 最近 7 天、近 7 天 | 滚动最近 7 天 |
| 昨天 | 前一自然日 |
| 上个月 | 上一个自然月 |

回答或查询时必须写清楚实际时间范围。

如果无法确认 SQL 的时间字段，不要强行注入时间条件，应返回：

```text
找到了指标 SQL，但无法确认时间字段，不能安全筛选时间范围。
```

## 10. 消歧规则

必须追问的情况：

1. 多个逻辑实体都包含同名或高相似指标。
2. 多个指标都与用户短语高置信匹配。
3. 只有公式候选但没有直接指标，且业务未允许自动计算。
4. 用户限定条件无法映射到 RealModel 元数据。
5. 用户同时提出多个目标但没有说明聚合或对比方式。

追问格式建议：

```text
我找到了多个可能的「广告成功率」口径：
1. 广告成功率：已部署直接指标，位于广告测试实体。
2. 广告接口成功次数 / 广告接口请求次数：可推导成功率。
3. 广告曝光率：相关但含义不同，不能默认作为成功率。

请确认要查询哪一个口径？
```

## 11. 广告成功率完整示例

用户问题：

```text
最近一个月的指标等级是黄金的广告成功率是多少？
```

执行：

```text
1. 抽取 business_object=广告，metric_phrase=广告成功率，filter=level=GOLD，time=最近一个月。
2. 调 locateNode("广告")。
3. 选择广告点击分类 business_and_platform.ADV.AdvertiserRebate.pps_click，必要时追问。
4. 调 getNextLevelNode。
5. 找到逻辑实体「广告测试」。
6. 调 getLogicEntityRealModel。
7. 在已部署指标中找 nameCn=广告成功率。
8. 应用 level=GOLD 过滤。
9. 应用最近一个月时间范围。
10. 如果 SQL 时间字段可确认，执行只读查询。
11. 返回数值、时间范围、指标口径和必要解释。
```

## 12. 不要做的事

1. 不要把 `getLogicEntityDefineInfo` 的未部署指标当成生产查数依据。
2. 不要把曝光率默认当成成功率。
3. 不要把点击率默认当成成功率。
4. 不要在无法确认时间字段时硬改 SQL。
5. 不要在多个高置信候选中静默选一个。
6. 不要把所有具体业务指标都写进本体配置。
