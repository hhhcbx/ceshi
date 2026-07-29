---
name: metric-query
description: 智能问数——通过节点 aliases 定位货架分类，从 RealModel 精简指标目录中按 Metric Family 选择真实指标 ID，再按起止时间查询并展示真实指标数据。适用于“最近一个月推广业务的成功占比是多少”“广告平均时延趋势”等问题，也支持指标定义和结构浏览。
---

# 智能问数：本体增强的真实指标查询

## 何时触发

用户要查询业务对象相关的指标定义、指标值、趋势、对比、字段或货架结构时使用。例如：

- “最近一个月推广业务的成功占比是多少？”
- “最近 7 天广告平均延迟趋势”
- “广告有哪些指标？”
- “有哪些业务分类？”

## 心智模型

1. **分类节点**使用点分 ID，是导航骨架；点分前缀表示祖先关系。
2. **逻辑实体**使用 UUID，指标挂在逻辑实体上。
3. **Phase A 节点本体**：`locateNode` 用节点 `aliases` 把“推广业务”等用户说法映射到广告分类。
4. **Phase B Metric Family**：把“成功占比”“平均延迟”等说法映射到 RealModel 的真实指标。
5. **RealModel** 是已部署指标目录；指标 `id` 是真实查数入口。
6. **queryIndicatorDimensionData** 按指标 ID、开始时间和结束时间返回真实数据。

工具契约见 [references/tools.md](references/tools.md)，呈现规范见
[references/output-format.md](references/output-format.md)。

## Stage 0：意图与槽位

抽取：

```yaml
business_object: 用于定位分类的短语
metric_phrase: 指标短语
time_range: 用户原话及明确起止时间
query_mode: definition | value | trend | comparison | structure | fields
filters: 可选的等级、类型或维度条件
```

路由：

| 意图 | 后续流程 |
|---|---|
| 指标值/趋势/对比 | Stage 1 至 Stage 7 全流程 |
| 指标目录/定义 | Stage 1 至 Stage 5，展示 RealModel 精简指标目录 |
| 字段查询 | 使用 `getLogicEntityDefineInfo` 的 fields；不要把定义指标用于生产查数 |
| 结构浏览 | `getModelTree` / `locateNode`，不下钻查数 |

## Stage 1：Phase A 节点定位

1. 将抽取出的 `business_object` **原样优先**传给 `locateNode`。例如“推广业务”直接调用
   `locateNode("推广业务")`，用于验证服务端 alias，不要先由 Agent 改写成“广告”。
2. 只保留点分 ID 的分类节点。
3. 广义查询做最小覆盖根剪枝：若 B 以 `A + "."` 开头，保留 A、删除 B。
4. 具体查询选名称/别名最贴合的节点，不额外加入祖先。
5. 多个候选无法唯一确定时追问。
6. 仅在 alias 未命中时，才使用 Agent 中英同义改写兜底，并明确说明发生了兜底。

`getNextLevelNode` 会递归覆盖后代，因此每个剪枝后的节点只调用一次。

## Stage 2：获取逻辑实体

1. 调 `getNextLevelNode(categoryId, "CATEGORY")`。
2. 使用 `publishedData` 中的真实实体 `id`、`nameCn/nameEn`、`parentOperObjId`。
3. 按用户对象与实体名称相关性收敛。广告演示应找到“广告测试实体”。
4. 多个实体都可能包含目标指标时，逐个获取精简 RealModel；多个高置信结果必须追问。
5. 实体过多时先排序/截断或请用户确认，禁止不加控制地批量调用。

## Stage 3：获取已部署指标

对候选实体调用：

```text
getLogicEntityRealModel(logicEntityId)
```

只读取 Agent 可见的精简字段：指标 `id`、`nameCn`、`nameEn`、`description`、`unit`、
`type`、`level`（后五项按实际存在使用）。

规则：

1. 生产查数只使用 RealModel 指标。
2. `getLogicEntityDefineInfo` 仅用于字段查询、测试或排查，不作为生产指标来源。
3. RealModel 指标 ID 必须原样保存，禁止拼接。
4. 若工具仍返回巨型对象，停止继续批量调用并报告 Swagger 投影未生效。

## Stage 4：Phase B Metric Family 匹配

### 通用规则

1. 先用 family aliases 识别指标族，再在本实体指标中找直接指标。
2. `nameCn` 优先，`nameEn` 次之，`description` 只用于消歧。
3. 保留平均/最小/最大、P95/P99、次数/比率等限定词。
4. 唯一高置信候选可选用；多个候选必须追问；没有对应变体则报告未找到。

### MVP families

| 用户说法 | family/variant | RealModel 匹配 |
|---|---|---|
| 成功率、成功占比、接口成功率 | `success_rate` | 名称含成功率 / `success_rate` |
| 平均时延、平均延迟 | `latency.avg_latency` | 名称含平均时延/平均延迟 |
| 最小内存使用率、最低内存占用率 | `memory_usage_rate.min` | 名称含最小/最低 + 内存 + 使用率 |
| 最大内存使用率、最高内存占用率 | `memory_usage_rate.max` | 名称含最大/最高 + 内存 + 使用率 |

成功率特别规则：

1. 直接“成功率”存在时，使用其 ID。
2. “成功次数 / 请求次数”只是公式候选；直接指标存在时不要重算。
3. 只有公式候选时先确认口径，还要确认两次查询结果的时间粒度可以对齐。
4. 成功次数、请求次数、成功率不是同一个指标。

负向规则：

- P95/P99 不能用平均时延代替。
- 最小值不能用最大值代替。
- 使用率不能用使用量代替。
- 点击率、曝光率不能用成功率代替。

## Stage 5：指标元数据筛选

用户明确要求等级或类型时，才应用 `level/type` 过滤；语义映射见
[references/output-format.md](references/output-format.md)。字段不存在时说明无法可靠过滤，不要猜。

过滤必须发生在候选指标匹配期间，不能先选一个指标再假装它符合条件。

## Stage 6：时间解析与真实查数

仅 `value/trend/comparison` 意图执行：

1. 把用户时间表达转换成明确起止时间。
2. “最近一个月”是截止当前时刻的滚动一个月；“上个月”是上一个自然月。
3. 按工具实际格式和时区构造参数，并保存用于最终回显。
4. 调用：

```text
queryIndicatorDimensionData(metric.id, startTime, endTime)
```

5. 这里的 `id` 是 RealModel 的指标 ID，不是分类 ID 或逻辑实体 ID。
6. 用户没给时间而接口要求必填时先追问。
7. 工具返回空就报告空，不补零、不换近似指标、不使用假数据。

## Stage 7：呈现

严格遵循 [references/output-format.md](references/output-format.md)。至少包含：

- 命中分类路径和逻辑实体。
- 用户说法命中的 Metric Family 及真实指标名称。
- 实际查询起止时间和时区。
- `queryIndicatorDimensionData` 的真实返回摘要。
- 必要口径说明；例如直接成功率存在，因此未用成功次数/请求次数重算。

单值直接展示；时间序列优先折线图；接口返回的聚合语义不得擅自改变。

## 完整演示：Phase A + Phase B + 真实数据

用户：

```text
最近一个月推广业务的成功占比是多少？
```

执行：

1. 抽取 `business_object=推广业务`、`metric_phrase=成功占比`、`time=最近一个月`。
2. `locateNode("推广业务")`，由 Phase A alias 命中广告节点。
3. `getNextLevelNode`，找到“广告测试实体”。
4. `getLogicEntityRealModel`，获得六个真实指标的精简目录。
5. Phase B 把“成功占比”识别为 `success_rate`。
6. 唯一选中“广告接口成功率”，使用其真实 `id`；不选成功次数或请求次数。
7. 转换最近一个月为明确起止时间。
8. `queryIndicatorDimensionData(id, startTime, endTime)`。
9. 展示真实结果、实际时间和口径说明。

## 禁止事项

1. 不让 Agent 自由联想替代 Phase A 或 Phase B；自由语义增强仅作显式兜底。
2. 不执行 SQL，不从 RealModel 猜 SQL。
3. 不自行构造节点、实体或指标 ID。
4. 不用本地假数据补充真实数据库。
5. 不在多个高置信候选中静默选择。
6. 不对祖先和后代分类重复调用 `getNextLevelNode`。
7. 不把相似但不同的指标口径互相替代。
