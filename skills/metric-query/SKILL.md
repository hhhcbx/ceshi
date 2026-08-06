---
name: metric-query
description: 基于本体拓扑查询真实指标。适用于用户已经提供 operation_object 叶子节点 ID，并希望查询该节点的指标目录、指标数值、趋势，或显式查询其拓扑/上下游关系的场景。使用 queryOntologyTopology 发现真实指标，以 queryIndicatorDimensionData 查数；当前不负责把业务口语解析成叶子节点 ID。
---

# 本体拓扑指标查询

## 1. 当前能力边界

本 Skill 只实现“已知叶子节点 ID 后的链路”：

```text
用户问题 + operation_object 叶子节点 ID
  -> 抽取 structuredIntent
  -> queryOntologyTopology 获取真实指标候选
  -> 在候选集合内匹配指标
  -> 必要时澄清
  -> queryIndicatorDimensionData 查询真实数据
  -> 返回指标身份、查询范围、实际时间和结果
```

必须遵守：

1. 当前叶子节点 ID 必须由用户直接提供；不得根据业务名称猜测或拼接 ID。
2. `start_node_type` 固定为 `operation_object`。
3. 普通指标查询默认 `max_depth=1`，只使用起始节点直接关联的指标。
4. 只有用户明确要求拓扑、上下游、引用或关联节点时，才使用用户指定的 `max_depth=2` 或 `3`。
5. 不因深度 1 没有指标而静默扩大查询深度。
6. 指标只能从 `queryOntologyTopology` 的真实返回中选择；不得编造指标 ID。
7. `queryKnowledge` 与本流程无关，不得调用。
8. `getOntologyClassList` 不是叶子节点目录，也不能定位业务对象；普通指标查询不得把它作为强制第一步。
9. `queryOntologyInstance` 尚在完善中，当前主链路不依赖它。接口合同稳定后再用于补充单位、口径、级别、维度等指标元数据。
10. 工具事实见 [references/tools.md](references/tools.md)，结果呈现见 [references/output-format.md](references/output-format.md)。

## 2. 抽取 structuredIntent

从用户问题与会话上下文抽取：

```yaml
original_query: 用户原始问题
operation_object_id: 用户明确提供的叶子节点 ID；没有则为 null
metric_phrase: 用户的指标原话；拓扑查询时可为空
time_range:
  original: 用户原始时间表达；目录或拓扑查询时可为空
  start_time: 解析后的明确开始时间
  end_time: 解析后的明确结束时间
  timezone: 实际使用的时区
query_mode: value | trend | indicator_catalog | topology
max_depth: 1 | 2 | 3
```

规则：

- 不把业务名称放进 `operation_object_id`。
- 不擅自改写 `metric_phrase`，例如不得把“成功率”改成“成功次数”。
- “最近一个月”表示截至当前时刻的滚动一个月；“上个月”表示上一个自然月。
- `value`、`trend` 和 `indicator_catalog` 默认 `max_depth=1`。
- `topology` 的深度由用户指定；缺少时追问，不能自行取 2 或 3。

## 3. 前置校验

### 3.1 缺少叶子节点 ID

若 `operation_object_id` 为空：

1. 停止工具调用。
2. 告知用户当前需要 `operation_object` 叶子节点 ID。
3. 可以复述已识别的业务表达和指标表达，但不得推荐一个猜测的 ID。
4. 不得调用 `getOntologyClassList` 试图查找实例；它只返回本体类元数据。

推荐答复：

```text
我已识别到要查询“<指标表达>”，但当前本体拓扑查询必须从一个确定的
operation_object 叶子节点开始。请提供该节点 ID；我不会根据“<业务表达>”自行拼接或猜测 ID。
```

### 3.2 ID 已提供

用户明确提供 ID 时原样传递，不进行格式补全。接口若返回节点不存在或参数错误，如实反馈，不尝试相似 ID。

## 4. 普通指标查询

对 `value`、`trend`、`indicator_catalog` 调用：

```json
{
  "start_node_type": "operation_object",
  "start_node_id": "<用户提供的叶子节点ID>",
  "end_node_type": "indicator",
  "max_depth": 1
}
```

处理返回图：

1. 遍历 `leftnode`、`rightnode` 和 `edge`。
2. 只把 `tags` 表明为 `indicator` 的节点收入指标候选集。
3. 按指标 ID 去重；同一指标通过多条边出现时保留全部证据路径，不重复查数。
4. 保存指标 ID、名称、服务 ID、与起始节点相连的 edge 类型及可还原的路径。
5. 不把 `operation_object` 节点当成指标。
6. 深度 1 返回空时如实报告，不自动改成深度 2 或 3。

## 5. 在真实候选内匹配指标

### 5.1 指标目录

`query_mode=indicator_catalog` 时返回深度 1 的全部指标候选，不需要凭关键词删减。按指标 ID 去重，并说明这些是该叶子节点直接关联的指标。

### 5.2 唯一匹配

如果一个候选与 `metric_phrase` 的名称和口径唯一匹配，选择其真实指标 ID。

### 5.3 多个候选

以下情况必须列出最少必要候选并追问：

- 平均、最小、最大、P95、P99 等 variant 不明确；
- 成功率、成功次数、请求次数等口径容易混淆；
- 多个候选名称相近但缺少足够元数据；
- 用户表达只能匹配到一组指标，不能唯一确定。

不得根据返回顺序、是否有数据或名称长度静默选择。

### 5.4 没有匹配

如果真实候选中不存在目标指标：

- 报告在该叶子节点的直接指标集合中未找到；
- 可展示少量真实候选帮助用户修正指标说法；
- 不替换叶子节点；
- 不扩大拓扑深度；
- 不创造公式或近似指标。

## 6. 查询真实数据

仅 `value` 和 `trend` 模式执行：

1. 唯一指标尚未确定时不得查数。
2. 把时间原话解析为工具要求的明确开始、结束时间和时区。
3. 调用 `queryIndicatorDimensionData(metricId, startTime, endTime)`；参数名和格式以已安装工具为准。
4. 传指标 ID，不传叶子节点 ID。
5. 返回空时报告该时间范围无数据，不补零、不换指标。
6. 不改变接口返回的聚合含义；没有明确规则时不自行求和、平均或计算成功率。
7. 多指标只有在用户明确要求全部 variant 时分别查数并分别展示，不擅自合并。

## 7. 拓扑、上下游与关联查询

仅当用户明确询问拓扑、上下游、引用或关联节点时使用 `query_mode=topology`。

1. 要求用户给出 `operation_object_id`。
2. 要求用户指定 `max_depth=1..3`；缺少时追问。
3. 按用户意图设置 `end_node_type`；不能确认时先追问。
4. 返回节点和边的真实方向、类型与路径，不把“图上可达”解释成“指标口径等价”。
5. 深度含义：
   - `1`：起始节点的直接关系和直接指标；
   - `2`：包括起始节点引用的其他叶子节点及其指标；
   - `3`：还可能包括其他引用了中间节点的叶子节点及其指标。
6. 只有深度 1 的直接指标可默认用于普通指标问数。深度 2、3 的指标属于扩展拓扑结果，除非用户明确指定，不能冒充起始节点的直接指标。

## 8. 输出要求

每次成功结果至少包含：

- 起始 `operation_object` ID；
- 实际使用的 `max_depth`；
- 命中的真实指标 ID 和名称，或指标目录；
- 对应的边/路径证据；
- 数值查询的实际起止时间和时区；
- 数据接口返回的真实结果或明确空结果。

澄清和失败结果至少包含：

- 已确定的槽位；
- 缺少或歧义的槽位；
- 为什么不能继续；
- 用户下一步需要提供什么。

## 9. 禁止事项

1. 不根据“小艺输入法服务”“广告推广”等名称猜测叶子节点 ID。
2. 不把“广告推广”静默扩大成“广告”。
3. 不调用旧链路的 `locateNode`、`getNextLevelNode` 或 `resolveMetric`。
4. 不遍历逻辑数据实体；当前本体拓扑已经提供聚合后的指标节点。
5. 不调用 `queryKnowledge`。
6. 不把 `getOntologyClassList` 当作实例搜索。
7. 不因没有结果而扩大 `max_depth`。
8. 不在真实拓扑候选之外编造指标。
9. 不把图上的关联关系解释成数值可聚合或指标可替代。
10. 不在无明确规则时合并多个指标的数值。
