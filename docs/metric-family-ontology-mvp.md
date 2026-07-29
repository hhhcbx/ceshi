# Metric Family 本体 Layer 2：真实数据展示流程实施方案

## 1. 文档定位

本文写给 **databp Java 代码侧弱 Agent / 工程实现者**。目标是在不新增、
不修改后端接口的前提下，把已经可访问的真实数据库数据串成一个可演示闭环：

```text
用户问题
  -> Phase A：aliases-only locateNode 定位广告节点
  -> 找到“广告测试实体”
  -> getLogicEntityRealModel 返回精简后的真实指标目录
  -> Phase B：Metric Family 识别成功率口径并选中真实指标 ID
  -> queryIndicatorDimensionData(id, startTime, endTime)
  -> 云端 Agent 展示真实结果
```

本文负责代码侧资源、Swagger 2.0 投影和联调验收；云端 Agent 的调用顺序见
`docs/agent-realmodel-query-rules.md` 和 `skills/metric-query/SKILL.md`。

## 2. 已确认现状与约束

1. 广告节点下已有真实逻辑数据实体，名称为“广告测试实体”。
2. 该实体有六个真实指标：广告接口成功率、广告接口最小内存使用率、广告接口平均时延、
   广告接口成功次数、广告接口最大内存使用率、广告接口请求次数。
3. `getLogicEntityRealModel` 已能访问数据库，但原始返回量很大。
4. `queryIndicatorDimensionData` 已能查数；选中指标后，只需提供指标 `id`、查询开始时间和结束时间。
5. 可以修改用于安装工具的 Swagger 2.0 YAML，包括 Agent 可见的响应 schema 和字段说明；不能修改接口实现、
   URL、参数或实际响应。
6. 不再创建本地假指标数据。测试必须使用上述真实逻辑实体、真实指标 ID 和真实查询结果。

## 3. Phase A 与 Phase B 的职责

### 3.1 Phase A：节点本体

每个节点目录中的 `base.yaml` 是一个节点本体文件。`id`、`parent_category_id`、
`name_cn`、`name_en`、`description` 和 `aliases` 都是这个节点的属性。

Phase A 只解决：

```text
用户对业务对象的说法 -> 真实货架分类节点
```

广告节点的最小示例仍为：

```yaml
id: business_and_platform.ADV
parent_category_id: business_and_platform
name_cn: 广告
name_en: Advertising
description: 广告业务大类。
aliases:
  - 广告
  - ads
  - ad
  - 推广
  - 广告业务
```

因此演示问题可以故意使用货架名称之外的说法，例如：

```text
最近一个月推广业务的接口成功率是多少？
```

`推广业务` 通过 `aliases` 命中广告节点，能够直接展示 Phase A 的收益。不要让云端 Agent
自行把“推广业务”猜成“广告”来掩盖 `locateNode` 是否生效。

### 3.2 Phase B：指标族本体

Metric Family 不写入广告节点的 `base.yaml`。它是跨业务节点复用的指标口径，继续独立存放：

```text
resources/ontology/metric-shelf/metric-families.yaml
```

Phase B 解决：

```text
用户指标短语 -> 指标族/变体 -> RealModel 中的真实指标 ID
```

Phase B 不保存指标值，也不复制数据库中的指标目录。RealModel 是真实指标目录，
`metric-families.yaml` 只保存稳定的语义规则。

## 4. Metric Family 最小配置

第一版只配置本次真实数据可以验收的三个指标族：

```yaml
version: 1

metric_families:
  - id: success_rate
    name_cn: 成功率
    aliases: [成功率, 成功占比, 接口成功率, success_rate, success rate]
    direct_metric:
      name_contains: [成功率, success_rate]
    formula:
      expression: numerator / denominator
      numerator:
        name_contains: [成功次数, 成功量, success_count]
      denominator:
        name_contains: [请求次数, 请求量, request_count]
    decision_policy:
      if_one_direct: use_direct
      if_multiple_direct: ask_user
      if_no_direct_but_formula_complete: use_formula_after_confirmation
      if_no_match: report_not_found

  - id: latency
    name_cn: 时延
    aliases: [时延, 延迟, 耗时, latency, rt]
    variants:
      - id: avg_latency
        aliases: [平均时延, 平均延迟, average latency, avg_latency]
        name_contains: [平均时延, 平均延迟, avg_latency]

  - id: memory_usage_rate
    name_cn: 内存使用率
    aliases: [内存使用率, 内存占用率, memory usage, memory_usage]
    variants:
      - id: min_memory_usage_rate
        aliases: [最小内存使用率, 最低内存使用率, min memory usage]
        name_contains: [最小内存使用率, 最低内存使用率, min_memory]
      - id: max_memory_usage_rate
        aliases: [最大内存使用率, 最高内存使用率, max memory usage]
        name_contains: [最大内存使用率, 最高内存使用率, max_memory]
```

关键规则：

1. `success_rate` 是通用指标族，不命名为 `advertising_success_rate`。
2. 真实指标 ID 不写入配置；不同环境的 ID 由 RealModel 动态返回。
3. 用户问“成功占比”时，先通过 family alias 识别 `success_rate`，再从六个真实指标中选中
   “广告接口成功率”。这体现 Phase B，而不是只靠名称完全相等。
4. 已有直接成功率指标时，查询它的 ID，不要同时查询成功次数和请求次数后自行重算。
5. 成功次数/请求次数只作为口径解释和直接指标缺失时的公式候选。
6. 平均、最小、最大是不能丢失的变体约束；不能把平均时延匹配成任意时延，
   也不能把最小内存使用率匹配成最大内存使用率。

## 5. 对 `getLogicEntityRealModel` 做 Swagger 投影

### 5.1 为什么改 Swagger，而不是改接口

后端 RealModel 返回保持不变。Swagger 2.0 文件只向云端 Agent 暴露完成匹配所需的字段，
避免大对象全部进入上下文。这个动作是 **工具契约投影**，不是更改业务接口或数据库。

### 5.2 Agent 最少需要看到什么

对 RealModel 的响应定义，只保留：

| 字段 | 是否必需 | 用途 |
|---|---|---|
| 逻辑实体 `id` | 建议 | 追踪本次匹配来自哪个实体 |
| 逻辑实体 `nameCn` / `nameEn` | 建议 | 确认“广告测试实体”并用于展示 |
| 指标 `id` | 必需 | 传给 `queryIndicatorDimensionData` |
| 指标 `nameCn` | 必需 | 中文匹配和展示 |
| 指标 `nameEn` | 建议 | 英文/编码名匹配 |
| 指标 `description` | 建议 | 同名指标消歧和口径解释 |
| 指标 `unit` | 建议 | 结果展示和公式安全判断 |
| 指标 `type` / `level` | 可选 | 用户明确按类型或等级筛选时使用 |

不要向 Agent 暴露与本次决策无关的大块建模信息、内部关系对象、编辑态元数据或重复结构。
尤其不要因为原始对象里存在 SQL 等实现细节，就要求 Agent 解析或改写 SQL；当前查数入口是
`queryIndicatorDimensionData`。

### 5.3 Swagger 2.0 schema 示例

下面只给出响应定义的目标形状。弱 Agent 必须先查看现有 Swagger 中 RealModel 的实际字段路径，
将 `properties` 对齐到真实 JSON；不得为了符合示例而修改接口。

```yaml
definitions:
  AgentVisibleRealModel:
    type: object
    description: 逻辑实体及其已部署指标的精简视图；用于选择查询指标 ID。
    properties:
      id:
        type: string
        description: 逻辑实体 ID。
      nameCn:
        type: string
        description: 逻辑实体中文名。
      nameEn:
        type: string
        description: 逻辑实体英文名。
      metrics:
        type: array
        description: 已部署且可用于真实查数的指标目录。
        items:
          $ref: '#/definitions/AgentVisibleMetric'

  AgentVisibleMetric:
    type: object
    required: [id, nameCn]
    properties:
      id:
        type: string
        description: 指标真实 ID；原样传给 queryIndicatorDimensionData.id，禁止自行构造。
      nameCn:
        type: string
        description: 指标中文名，用于 Metric Family 匹配。
      nameEn:
        type: string
        description: 指标英文名或编码名。
      description:
        type: string
        description: 指标口径描述；仅用于候选消歧和结果解释。
      unit:
        type: string
        description: 指标单位。
      type:
        type: string
        description: 指标类型；仅在真实响应存在时暴露。
      level:
        type: string
        description: 指标等级；仅在真实响应存在时暴露。
```

如果生成工具的平台支持响应字段白名单或 schema 投影，应使用白名单。如果平台只是把 schema
作为提示而仍把完整 HTTP body 交给 Agent，则单改 schema 不能真正减小返回体；必须在安装后实测工具输出，
确认未声明的大字段确实没有进入 Agent 上下文。

## 6. `queryIndicatorDimensionData` 的 Swagger 契约

不修改接口，只把三个必要参数及语义写清楚：

```yaml
parameters:
  - name: id
    in: query
    required: true
    type: string
    description: 从 getLogicEntityRealModel.metrics[*].id 原样取得的指标 ID，禁止传逻辑实体 ID。
  - name: startTime
    in: query
    required: true
    type: string
    description: 查询开始时间；格式必须与现有接口要求一致。
  - name: endTime
    in: query
    required: true
    type: string
    description: 查询结束时间；格式必须与现有接口要求一致，且不得早于 startTime。
```

参数名、`in` 位置和时间格式必须以现有接口为准。若真实名字不是 `startTime/endTime`，
只修改文档中的描述，不得把后端参数改成示例名称。

## 7. 完整展示场景

### 7.1 主场景：同时展示 Phase A、Phase B 和真实查数

推荐演示问题：

```text
最近一个月推广业务的成功占比是多少？
```

展示价值：

1. `推广业务` 不是节点标准名，通过 Phase A 的广告 aliases 命中。
2. `成功占比` 不是指标标准名，通过 Phase B 的 `success_rate.aliases` 命中。
3. RealModel 六个指标中，Phase B 选择直接指标“广告接口成功率”，而不是平均时延、内存使用率、
   成功次数或请求次数。
4. Agent 取该指标真实 `id`，调用 `queryIndicatorDimensionData` 返回最近一个月真实数据。

执行轨迹：

```text
1. 解析：business_object=推广业务，metric_phrase=成功占比，time_range=最近一个月。
2. locateNode("推广业务") -> 广告分类节点。
3. getNextLevelNode(categoryId, "CATEGORY") -> 广告测试实体。
4. getLogicEntityRealModel(广告测试实体真实 ID) -> 六个精简指标。
5. success_rate family 命中“成功占比”。
6. direct_metric 选中“广告接口成功率”，保存其真实 metric.id。
7. 将“最近一个月”转换成明确的 [startTime, endTime]，并在结果中回显。
8. queryIndicatorDimensionData(metric.id, startTime, endTime)。
9. 按接口真实返回展示数值或时间序列，不编造聚合。
```

### 7.2 Phase B 变体验收

使用同一真实实体追加三条查询，无需假数据：

| 用户说法 | 期望选择 |
|---|---|
| `最近一个月广告平均延迟怎么样？` | 广告接口平均时延 |
| `最近一个月广告最低内存占用率是多少？` | 广告接口最小内存使用率 |
| `最近一个月广告最高内存使用率是多少？` | 广告接口最大内存使用率 |

这三条用于证明 family/variant 可以处理近义表达，同时保留平均、最小、最大约束。

### 7.3 负向验收

1. 问“广告成功次数”时选择广告接口成功次数，不能选择成功率。
2. 问“广告请求次数”时选择广告接口请求次数，不能选择成功次数。
3. 问“广告 P95 时延”时，现有六个指标没有 P95，必须报告未找到，不能用平均时延代替。
4. RealModel 出现多个高置信成功率时必须让用户消歧，不能静默选一个。

## 8. 弱 Agent 实施步骤

1. 保留并验证广告节点 `base.yaml` 的 `aliases`，至少覆盖 `推广`、`推广业务`、`ads`。
2. 确认 locateNode 实际读取的是本体 DataModel 副本，并保留旧树搜索兜底。
3. 新增或更新 `metric-families.yaml`，按第 4 节配置三个通用 family；不要写真实指标 ID。
4. 删除此前计划的 `test-data/advertising-metrics.yaml` 及其 loader/fixture；不要再用假指标验收。
5. 在 Java 工程中使用 `getLogicEntityRealModel` 的真实响应做 matcher 测试输入，至少验证六个指标均可见。
6. 调整 Swagger 2.0 YAML 中 `getLogicEntityRealModel` 的响应 schema，只暴露第 5.2 节字段。
7. 补充 `queryIndicatorDimensionData` 三个参数的来源、时间格式和禁止事项说明。
8. 重新安装/刷新基于 Swagger 生成的工具。
9. 先在 Swagger/MCP 工具层调用 RealModel，确认返回已被裁剪且指标 `id/nameCn` 没有丢失。
10. 按第 7 节执行主场景、变体场景和负向场景。

## 9. 必须写的测试

### 9.1 代码侧测试

1. `locateNode("推广业务")` 命中广告节点，并能追溯到 alias。
2. `成功占比` 命中 `success_rate`。
3. 六个真实指标同时作为候选时，只产生一个直接成功率候选。
4. 成功次数和请求次数能组成公式候选，但直接成功率存在时决策仍为 `USE_DIRECT_METRIC`。
5. `平均延迟`、`最低内存占用率`、`最高内存使用率` 分别命中正确变体。
6. `P95 时延` 返回 `NO_MATCH`。
7. 空 RealModel、缺少指标 ID、多个直接候选都有明确失败或消歧结果，不抛出无法理解的空指针异常。

### 9.2 接口联调验收

1. RealModel 工具输出只含允许字段，没有大块无关对象。
2. “广告测试实体”的六个指标均有真实 `id` 和 `nameCn`。
3. 选中的指标 ID 可原样调用 `queryIndicatorDimensionData`。
4. 起止时间在请求和最终回答中一致。
5. 返回结果来自接口；若为空，应展示空结果和实际查询范围，不能伪造数值。

## 10. 跨业务扩展原则

本方案不是“广告专用逻辑”：

1. 新业务对象只需在其节点 `base.yaml` 增加 aliases，Phase A 主流程不变。
2. 支付成功率、搜索成功率、小艺接口成功率继续复用 `success_rate`，无需复制 family。
3. 新增 P95 时延等已知变体时扩展 `latency.variants`；不要硬编码到广告分支。
4. 只有出现新的稳定指标口径时才新增 family。
5. 实际指标 ID 永远从对应逻辑实体的 RealModel 动态获取，不能写入本体配置。
6. 所有业务最终都复用同一条查询链：节点定位、实体获取、指标匹配、按 ID 和时间查数。

## 11. 完成定义

只有同时满足以下条件，才能宣布展示流程完成：

1. Phase A 能用 `推广业务` 定位广告，不依赖 Agent 自己改写关键词。
2. Phase B 能用 `成功占比` 选中“广告接口成功率”的真实 ID。
3. RealModel 的 Agent 可见输出已显著裁剪，但没有丢失匹配和查数所需字段。
4. `queryIndicatorDimensionData` 使用真实指标 ID 和明确起止时间返回真实结果或真实空结果。
5. 云端 Agent 的最终回答包含命中对象、指标口径、查询时间范围和接口返回值。
6. 主场景、变体场景、负向场景均通过。
