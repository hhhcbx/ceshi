# Phase B：Metric Family Java 侧实施方案

## 1. 文档定位

本文只指导 **Java 代码侧弱 Agent / 工程实现者** 实现 Phase B。

Phase B 的目标是：

```text
logicEntityId + 用户指标短语
  -> 读取 Java resources 中的 Metric Family
  -> 获取该逻辑实体的真实 RealModel 指标
  -> 匹配直接指标、公式候选或歧义候选
  -> 通过 resolveMetric 接口返回真实指标 ID 和依据
```

本文不描述云端 Agent 如何编排接口、解析时间或展示结果；这些内容统一见
`docs/agent-realmodel-query-rules.md`。

## 2. 实现边界

### 2.1 本阶段要做

1. 在 Java resources 中新增 `metric-families.yaml`。
2. 按现有 YAML loader/entry 模式加载 Metric Family。
3. 建立可查询的 Metric Family 内存索引。
4. 实现 Metric Family 识别和真实指标匹配。
5. 新增 `resolveMetric` 对外接口。
6. `resolveMetric` 内部通过既有 service/repository 获取逻辑实体的真实 RealModel。
7. 返回唯一指标、歧义候选、公式候选或未找到状态。
8. 使用“广告测试实体”的六个真实指标完成集成验收。

### 2.2 本阶段不做

1. 不修改 `getNextLevelNode`、`getLogicEntityRealModel` 或 `queryIndicatorDimensionData` 的现有逻辑。
2. 不把 Metric Family 塞进节点 `base.yaml`。
3. 不把真实指标 ID 写进 YAML。
4. 不执行指标数据查询。
5. 不解析用户时间范围。
6. 不生成图表或最终自然语言回答。
7. 不实现后续关系、规则、查询映射等阶段。
8. 不设计统一语义接口的升级方案。

## 3. 资源位置和数据归属

所有本体资源继续统一放在 Java 工程。节点本体和指标族本体同属一个本体资源域，但作用域不同：

```text
resources/ontology/metric-shelf/
├── DataModel/
│   └── .../base.yaml
└── metric-families.yaml
```

节点 `base.yaml` 描述单个货架节点；`metric-families.yaml` 描述跨节点复用的指标口径。
二者不应合并为同一个文件，也不应把 Metric Family 复制到每个业务节点。

真实指标目录和真实指标 ID 仍来自 RealModel。YAML 只保存稳定的语义知识，不能成为数据库指标快照。

## 4. Metric Family YAML

第一版只实现当前真实数据可验证的三个 family：

```yaml
version: 1

metric_families:
  - id: success_rate
    name_cn: 成功率
    name_en: Success Rate
    aliases:
      - 成功率
      - 成功占比
      - 成功概率
      - 接口成功率
      - success rate
      - success_rate
    direct_metric:
      name_contains:
        - 成功率
        - success_rate
    formula:
      expression: numerator / denominator
      numerator:
        name_contains:
          - 成功次数
          - 成功量
          - success_count
      denominator:
        name_contains:
          - 请求次数
          - 请求量
          - request_count
    policy:
      one_direct: RESOLVED
      multiple_direct: AMBIGUOUS
      formula_only: FORMULA_CANDIDATE
      no_candidate: NOT_FOUND

  - id: latency
    name_cn: 时延
    name_en: Latency
    aliases:
      - 时延
      - 延迟
      - 耗时
      - latency
      - rt
    variants:
      - id: avg_latency
        aliases:
          - 平均时延
          - 平均延迟
          - average latency
          - avg_latency
        name_contains:
          - 平均时延
          - 平均延迟
          - avg_latency

  - id: memory_usage_rate
    name_cn: 内存使用率
    name_en: Memory Usage Rate
    aliases:
      - 内存使用率
      - 内存占用率
      - memory usage
      - memory_usage
    variants:
      - id: min_memory_usage_rate
        aliases:
          - 最小内存使用率
          - 最低内存占用率
          - min memory usage
        name_contains:
          - 最小内存使用率
          - 最低内存使用率
          - min_memory
      - id: max_memory_usage_rate
        aliases:
          - 最大内存使用率
          - 最高内存占用率
          - max memory usage
        name_contains:
          - 最大内存使用率
          - 最高内存使用率
          - max_memory
```

约束：

1. family ID 是稳定语义标识，不是指标 ID。
2. aliases 用于识别用户指标短语。
3. `name_contains` 用于匹配 RealModel 的 `nameCn/nameEn`。
4. 平均、最小、最大等 variant 约束不能在归一化时丢失。
5. YAML 不保存业务节点 ID、逻辑实体 ID、指标 ID 或指标值。
6. `success_rate` 必须可复用于广告、支付、搜索等不同业务实体。

## 5. Java 结构

遵循 Phase A 已有的 loader/entry 风格扩展，不要求为了名称统一而重构 Phase A。

建议最小结构：

```text
load/
├── OntologyLoader                 # 已有；是否扩展它由现有职责决定
├── LocateNodeEntry                # 已有 Phase A entry
├── MetricFamilyEntry              # 新增 family entry
├── MetricVariantEntry             # 新增 variant entry
└── MetricFormulaEntry             # 新增 formula entry

resolve/
├── MetricFamilyMatcher            # 用户短语 -> family/variant
├── RealMetricMatcher              # family/variant -> RealModel 指标候选
└── MetricResolver                 # 编排 Phase B 并生成返回结果
```

如果现有 `OntologyLoader` 已负责扫描和加载全部本体资源，就在其中增加 Metric Family 加载；
如果它明确只负责 DataModel 节点，则新增 `MetricFamilyLoader`，再由同一 Spring 配置统一初始化。
不要只为追求某个架构名称而重命名稳定的 Phase A 类。

## 6. 加载与校验

启动时加载 `metric-families.yaml`，构建只读索引：

```text
normalized alias -> family + optional variant
family id -> MetricFamilyEntry
```

必须校验：

1. `version` 存在且受支持。
2. family `id/name_cn/aliases` 不为空。
3. family ID 唯一。
4. 同一 family 内 variant ID 唯一。
5. 归一化后的 alias 冲突可被检测并给出明确启动错误或告警。
6. formula 同时声明 numerator 和 denominator。
7. policy 只能使用代码支持的枚举值。
8. YAML 解析失败时给出文件位置和字段路径，不能静默忽略整个配置。

是否因单条错误阻止启动，应沿用当前本体资源的容错策略；但重复 ID、无法解析的 policy 等会导致错误匹配，
建议在生产配置中作为启动失败处理。

## 7. 输入模型

`resolveMetric` 第一版请求：

```json
{
  "logicEntityId": "<真实逻辑实体ID>",
  "metricPhrase": "成功占比"
}
```

校验：

1. `logicEntityId` 必填且非空。
2. `metricPhrase` 必填，trim 后非空。
3. 不接收完整 RealModel 对象。
4. 不接收客户端指定的 Metric Family ID 作为最终结论。
5. 不允许调用方传入或覆盖真实指标 ID。

## 8. Phase B 内部流程

### 8.1 获取真实指标

`MetricResolver` 根据 `logicEntityId` 调用已有内部 service/repository 获取 RealModel，不应通过 HTTP 再调用本服务自己的对外接口。

从 RealModel 中只提取匹配所需字段：

```text
id
nameCn
nameEn
可选 description/unit/type/level
```

只使用已部署/已发布指标。具体字段路径必须以当前真实 RealModel DTO 为准，不得根据文档示例编造。

### 8.2 归一化

对 `metricPhrase`、family aliases 和指标名称使用一致的轻量归一化：

1. trim。
2. 英文转小写。
3. 连续空白折叠。
4. `_`、`-` 和空格可作为弱分隔符统一处理。
5. 不删除 `avg/min/max/p95/p99`、平均、最小、最大、次数、比率等口径词。
6. 不对中文做不受控的分词扩展。

### 8.3 识别 family 和 variant

优先级：

1. metric phrase 与 family/variant alias 归一化后完全相等。
2. metric phrase 包含完整 variant alias。
3. metric phrase 包含完整 family alias。
4. 多个 family 得分相同且无法通过 variant 区分时返回 `AMBIGUOUS`。

例如：

```text
成功占比 -> success_rate
平均延迟 -> latency.avg_latency
最低内存占用率 -> memory_usage_rate.min_memory_usage_rate
最高内存使用率 -> memory_usage_rate.max_memory_usage_rate
```

### 8.4 匹配直接指标

使用命中 family/variant 的 `name_contains` 匹配 RealModel `nameCn/nameEn`。

规则：

1. variant 已命中时，候选必须满足 variant 约束。
2. 中文名完整匹配优先于包含匹配。
3. 英文名完整匹配次之。
4. description 只用于同名候选消歧，不能单独产生高置信直接指标。
5. 一个直接候选返回 `RESOLVED`。
6. 多个高置信候选返回 `AMBIGUOUS`，不能按列表第一项静默选择。

### 8.5 生成公式候选

只有 family 声明 formula 时执行：

1. 分别匹配 numerator 和 denominator。
2. 两侧都只有一个可靠候选时生成 `FORMULA_CANDIDATE`。
3. 任一侧缺失时返回 `NOT_FOUND`，并说明缺少哪一侧。
4. 任一侧有多个候选时返回 `AMBIGUOUS`。
5. 直接指标存在时优先返回直接指标；公式可作为解释信息附带，但不覆盖直接指标。
6. Phase B 只返回公式计划，不调用数据接口，不在服务端计算结果。

## 9. 返回模型

建议统一响应骨架：

```json
{
  "status": "RESOLVED | AMBIGUOUS | FORMULA_CANDIDATE | NOT_FOUND | INVALID_REQUEST | ERROR",
  "family": {},
  "variant": {},
  "selectedMetric": {},
  "candidates": [],
  "formula": {},
  "matchType": "DIRECT_METRIC | FORMULA | NONE",
  "matchedAlias": "",
  "requiresConfirmation": false,
  "message": ""
}
```

### `RESOLVED`

```json
{
  "status": "RESOLVED",
  "family": {"id": "success_rate", "nameCn": "成功率"},
  "selectedMetric": {
    "id": "<真实指标ID>",
    "nameCn": "广告接口成功率",
    "nameEn": "<真实英文名>",
    "unit": "<真实单位>"
  },
  "matchType": "DIRECT_METRIC",
  "matchedAlias": "成功占比",
  "requiresConfirmation": false
}
```

### `AMBIGUOUS`

返回最少但足以消歧的候选字段：

```json
{
  "status": "AMBIGUOUS",
  "candidates": [
    {"id": "...", "nameCn": "...", "nameEn": "...", "reason": "..."}
  ],
  "requiresConfirmation": true,
  "message": "找到多个同等可信的指标候选"
}
```

### `FORMULA_CANDIDATE`

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

不得返回完整 RealModel、SQL、内部对象图或本体配置全文。

## 10. 接口实现

新增一个薄 Controller，例如：

```java
@PostMapping("/ontology/resolveMetric")
public ResolveMetricResponse resolveMetric(@RequestBody ResolveMetricRequest request) {
    return metricResolver.resolve(request);
}
```

Controller 只负责：

1. 请求反序列化和基础校验。
2. 调用 `MetricResolver`。
3. 映射业务状态和 HTTP 状态。
4. 记录必要的 trace 信息。

所有匹配逻辑放在 resolver/matcher 中，禁止堆进 Controller。

建议状态映射：

| 业务状态 | HTTP 建议 |
|---|---|
| `RESOLVED` | 200 |
| `AMBIGUOUS` | 200 |
| `FORMULA_CANDIDATE` | 200 |
| `NOT_FOUND` | 200 |
| `INVALID_REQUEST` | 400 |
| 逻辑实体不存在 | 404 |
| RealModel 或内部依赖失败 | 5xx，沿用项目异常规范 |

歧义和未找到是正常业务结果，不应滥用异常。

## 11. 缓存和刷新

1. Metric Family YAML 可在应用启动时加载到内存。
2. 第一版可以随应用发布刷新，不强制支持热更新。
3. 如果已有 OntologyLoader 刷新机制，应复用同一机制。
4. 配置刷新必须原子替换索引，不能让请求看到半加载状态。
5. RealModel 指标是动态数据，不写入长期本体缓存。
6. 如对 RealModel 做短时缓存，必须沿用现有服务的缓存和失效规则，不在 Phase B 私自新增不一致缓存。

## 12. 测试

### 12.1 YAML 加载测试

1. 三个 family 均可加载。
2. aliases 索引正确。
3. 重复 family ID 被拒绝。
4. alias 冲突可检测。
5. 非法 policy 和不完整 formula 可检测。

### 12.2 Matcher 单元测试

RealModel service 使用 mock，返回与真实“广告测试实体”字段结构一致的六个指标；不要新增生产用假数据 YAML。

| 输入 | 期望 |
|---|---|
| `成功占比` / `成功概率` | `success_rate`，选择广告接口成功率 |
| `接口成功率` | `success_rate`，选择广告接口成功率 |
| `平均延迟` | `latency.avg_latency`，选择广告接口平均时延 |
| `最低内存占用率` | 选择广告接口最小内存使用率 |
| `最高内存使用率` | 选择广告接口最大内存使用率 |
| `P95 时延` | `NOT_FOUND`，不能选择平均时延 |
| `成功次数` | 不能误选广告接口成功率 |
| `请求次数` | 不能误选广告接口成功次数 |

还要覆盖：

1. 多个直接成功率返回 `AMBIGUOUS`。
2. 无直接成功率但分子分母齐全返回 `FORMULA_CANDIDATE`。
3. 公式缺分子或分母返回 `NOT_FOUND`。
4. RealModel 为空返回明确结果。
5. 指标缺少 ID 时不能返回 `RESOLVED`。
6. RealModel 内部调用失败按项目规范返回错误。

### 12.3 真实集成验收

使用真实广告逻辑实体：

1. `resolveMetric(广告测试实体ID, "成功占比")` 返回 `RESOLVED`。
2. `selectedMetric.nameCn` 为“广告接口成功率”。
3. `selectedMetric.id` 是 RealModel 中的真实指标 ID。
4. 返回中不包含完整 RealModel 和无关大字段。
5. 该 ID 可原样用于现有查数接口。
6. 时延和内存三个变体均命中正确真实指标。
7. P95 负向用例不发生错误替代。

## 13. 完成定义

满足以下条件才算 Phase B 完成：

1. Metric Family YAML 位于 Java resources，并可随应用稳定加载。
2. `resolveMetric` 能被外部云端 Agent 调用。
3. 接口内部使用真实逻辑实体 RealModel，不要求调用方上传 RealModel。
4. “成功占比”能解析到“广告接口成功率”的真实 ID。
5. 直接指标、公式候选、歧义和未找到四类结果边界明确。
6. 平均/最小/最大等 variant 不会被错误替换。
7. 生产响应不暴露完整 RealModel、SQL 或内部配置。
8. 单元测试和真实广告集成验收通过。
