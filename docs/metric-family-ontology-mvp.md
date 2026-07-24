# Metric Family 本体 Layer 2 MVP 构建方案

## 1. 文档定位

本文写给 **Java 代码侧弱 Agent / 工程实现者**，用于指导在 databp Java 工程中构建 Layer 2：指标口径本体 / Metric Family 本体。

它和 `docs/locatenode-ontology-mvp.md` 的关系是：

1. `locatenode-ontology-mvp.md` 负责 Layer 1：节点别名语义层，用 `base.yaml` 里的 `aliases` 把用户业务词映射到货架分类节点 ID。
2. 本文负责 Layer 2：指标族和指标口径语义层，把用户说的“成功率、时延、内存使用率”等指标短语映射到一套可复用的指标匹配与口径规则。
3. 本阶段暂不解决真实查数和 SQL 执行，只做本地可测的指标匹配、口径识别、公式候选和消歧输出。

## 2. 先回答核心问题：Metric Family 应该写在哪里

不要把 Metric Family 直接写进每个节点的 `base.yaml` 后面。

### 2.1 每个 base.yaml 是什么

可以达成这个共识：

```text
resources/DataModel 中每个节点目录下的 base.yaml
≈ 货架树上一个节点对应的节点本体文件
```

在这个节点本体里：

1. `id` 是节点稳定标识。
2. `parent_category_id` 是节点之间的父子关系属性。
3. `name_cn` / `name_en` 是节点名称属性。
4. `description` 是节点描述属性。
5. `aliases` 是节点别名属性，用于 Layer 1 的 locateNode 匹配。

所以，`aliases/id/name` 都可以理解成“这个节点本体的属性”。

### 2.2 Metric Family 为什么不放进每个节点 base.yaml

Metric Family 不是某个单一货架节点的属性，而是一类跨节点复用的指标口径概念。

例如“成功率”：

1. 广告节点可能有成功率。
2. 小艺节点可能有成功率。
3. 搜索节点可能有成功率。
4. 支付节点可能有成功率。
5. 成功率的通用口径通常都是 `成功次数 / 请求次数` 或优先匹配直接 `成功率` 指标。

如果把这套规则写进每个节点的 `base.yaml`，会出现问题：

1. 同一套成功率规则被复制很多份。
2. 规则改动时要改很多节点，容易不一致。
3. 节点本体和指标族本体混在一起，职责不清。
4. 后续扩展时会越来越像手工知识库，而不是语义层。

因此 Layer 2 应该新增独立 YAML，例如：

```text
resources/ontology/metric-shelf/metric-families.yaml
```

### 2.3 节点 base.yaml 与 Metric Family 的关系

节点 `base.yaml` 只回答：

```text
用户说的业务对象是什么节点？
```

`metric-families.yaml` 回答：

```text
用户说的指标口径是什么意思？
在候选指标列表里应该怎么匹配？
直接指标、公式指标、相似但不等价指标如何区分？
```

两者组合：

```text
用户问题：最近一个月广告成功率是多少？

Layer 1：广告 -> business_and_platform.ADV... -> 找到广告相关逻辑实体
Layer 2：成功率 -> success_rate metric family -> 在实体指标中匹配直接指标或公式候选
```

## 3. Layer 2 的 MVP 目标

本阶段目标不是查真实数，而是构建一个本地可测的指标口径识别器。

输入：

```text
metric_phrase: 用户问题中的指标短语，例如“广告成功率”
metrics: 某个逻辑实体下的候选指标列表
```

输出：

```text
1. 命中的 metric family，例如 success_rate。
2. 直接指标候选，例如“广告接口成功率”。
3. 公式候选，例如“广告接口成功次数 / 广告接口请求次数”。
4. 相关但不等价的候选，例如“曝光率、点击率”等。
5. 是否需要追问或确认。
```

本阶段不做：

1. 不查 RealModel 真实 SQL。
2. 不执行 SQL。
3. 不返回真实指标值。
4. 不把所有业务指标逐条写进本体。
5. 不只服务广告，要设计成所有节点/业务都可复用。

## 4. metric-families.yaml 建议结构

建议新增：

```text
resources/ontology/metric-shelf/metric-families.yaml
```

第一版结构：

```yaml
version: 1

metric_families:
  - id: success_rate
    name_cn: 成功率
    name_en: Success Rate
    aliases:
      - 成功率
      - 成功占比
      - 接口成功率
      - success rate
      - success_rate
    direct_metric:
      name_contains:
        - 成功率
        - success_rate
      prefer: true
    formula:
      expression: numerator / denominator
      numerator:
        aliases:
          - 成功次数
          - 成功量
          - 成功请求数
          - success count
          - success_count
        name_contains:
          - 成功次数
          - 成功量
          - success_count
      denominator:
        aliases:
          - 请求次数
          - 请求量
          - 总请求数
          - request count
          - request_count
        name_contains:
          - 请求次数
          - 请求量
          - request_count
      require_confirmation: false
    not_equivalent_to:
      - exposure_rate
      - click_rate
    decision_policy:
      if_direct_metric_exists: use_direct_metric
      if_only_formula_exists: use_formula_with_explanation
      if_multiple_direct_metrics: ask_user_to_disambiguate
      if_no_direct_or_formula: report_not_found

  - id: latency
    name_cn: 时延
    name_en: Latency
    aliases:
      - 时延
      - 延迟
      - 耗时
      - latency
      - rt
    direct_metric:
      name_contains:
        - 时延
        - 延迟
        - 耗时
        - latency
        - rt
      prefer: true
    variants:
      - id: avg_latency
        aliases:
          - 平均时延
          - 平均延迟
          - avg latency
          - average latency
        name_contains:
          - 平均时延
          - 平均延迟
          - avg_latency
      - id: min_latency
        aliases:
          - 最小时延
          - 最小延迟
          - min latency
        name_contains:
          - 最小时延
          - 最小延迟
          - min_latency
      - id: p95_latency
        aliases:
          - p95 时延
          - p95 延迟
          - p95 latency
        name_contains:
          - p95
          - P95

  - id: memory_usage
    name_cn: 内存使用率
    name_en: Memory Usage
    aliases:
      - 内存使用率
      - 内存占用
      - 内存
      - memory usage
      - memory
      - mem
    direct_metric:
      name_contains:
        - 内存使用率
        - 内存占用
        - memory_usage
        - memory
        - mem
      prefer: true
    variants:
      - id: min_memory_usage
        aliases:
          - 最小内存使用率
          - 最小内存占用
          - min memory usage
        name_contains:
          - 最小内存
          - min_memory
      - id: max_memory_usage
        aliases:
          - 最大内存使用率
          - 最大内存占用
          - max memory usage
        name_contains:
          - 最大内存
          - max_memory
```

说明：

1. `metric_families[*].id` 是指标族 ID，不是货架节点 ID。
2. 指标族 ID 只在 `metric-families.yaml` 内使用，不写回节点 `base.yaml`。
3. `aliases` 用于把用户说法映射到指标族。
4. `direct_metric.name_contains` 用于在候选指标列表中查直接指标。
5. `formula` 用于定义无法或不优先使用直接指标时的公式候选。
6. `not_equivalent_to` 用于说明相关但不能互相替代的指标族。
7. `decision_policy` 用于让弱 Agent/云端 Agent 知道遇到候选时怎么处理。

## 5. 本地测试指标数据

本阶段可以先用本地假数据测试，不依赖真实 RealModel。

建议测试数据文件：

```text
resources/ontology/metric-shelf/test-data/advertising-metrics.yaml
```

示例：

```yaml
logic_entity:
  id: mock-advertising-interface-entity
  name_cn: 广告接口测试实体
  category_id: business_and_platform.ADV.AdvertiserRebate.pps_click

metrics:
  - id: ad_interface_success_rate
    name_cn: 广告接口成功率
    name_en: ad_interface_success_rate
    level: GOLD
    type: DERIVED
    data_source: SERVER
    unit: ratio

  - id: ad_interface_min_memory_usage
    name_cn: 广告接口最小内存使用率
    name_en: ad_interface_min_memory_usage
    level: HEALTH
    type: BASIC
    data_source: SERVER
    unit: percent

  - id: ad_interface_avg_latency
    name_cn: 广告接口平均时延
    name_en: ad_interface_avg_latency
    level: GOLD
    type: BASIC
    data_source: SERVER
    unit: ms

  - id: ad_interface_success_count
    name_cn: 广告接口成功次数
    name_en: ad_interface_success_count
    level: NORMAL
    type: BASIC
    data_source: SERVER
    unit: count

  - id: ad_interface_max_memory_usage
    name_cn: 广告接口最大内存使用率
    name_en: ad_interface_max_memory_usage
    level: HEALTH
    type: BASIC
    data_source: SERVER
    unit: percent

  - id: ad_interface_request_count
    name_cn: 广告接口请求次数
    name_en: ad_interface_request_count
    level: NORMAL
    type: BASIC
    data_source: SERVER
    unit: count
```

注意：

1. 这些属性是 MVP 测试用，可以合理编造。
2. 后续接真实 RealModel 时，把字段适配到真实返回结构。
3. 本地测试重点不是数值，而是“用户短语 -> 指标族 -> 直接指标/公式候选”的匹配结果是否合理。

## 6. 以“最近一个月广告成功率是多少？”为例

用户问题：

```text
最近一个月广告成功率是多少？
```

### 6.1 Layer 1 已完成的部分

Layer 1 负责定位业务节点：

```text
广告 -> aliases -> business_and_platform.ADV / 广告相关节点
```

然后通过既有链路拿到某个广告逻辑实体下的候选指标列表。现阶段本地测试可以直接用 `advertising-metrics.yaml` 模拟。

### 6.2 Layer 2 要完成的部分

从用户问题抽取：

```yaml
business_object: 广告
metric_phrase: 广告成功率
time_range: 最近一个月
```

Metric Family 匹配：

```text
metric_phrase=广告成功率
  ↓
包含“成功率”
  ↓
命中 metric family: success_rate
```

在测试指标中匹配直接指标：

```text
广告接口成功率
```

同时也能识别公式候选：

```text
广告接口成功次数 / 广告接口请求次数
```

如果同时存在直接指标和公式候选，建议决策：

```text
优先使用直接指标“广告接口成功率”。
同时在调试输出中说明：也找到了可解释公式候选“广告接口成功次数 / 广告接口请求次数”。
```

如果未来某个实体没有“广告接口成功率”，但有成功次数和请求次数，则按 `decision_policy.if_only_formula_exists`：

```text
使用公式候选，并说明成功率按 成功次数 / 请求次数 计算。
```

这里用户已经明确：成功率 = 成功次数 / 请求次数。因此测试期可以不强制追问，但输出必须说明口径。

## 7. 弱 Agent 需要实现的本地 matcher

建议新增一个本地服务/工具类，例如：

```java
class MetricFamilyMatcher {
    MetricFamilyMatchResult match(String metricPhrase, List<MetricDefinition> metrics);
}
```

输入：

```java
String metricPhrase = "广告成功率";
List<MetricDefinition> metrics = loadTestMetrics();
```

输出建议：

```json
{
  "matchedFamilyId": "success_rate",
  "matchedFamilyNameCn": "成功率",
  "directMetrics": [
    {
      "id": "ad_interface_success_rate",
      "nameCn": "广告接口成功率",
      "nameEn": "ad_interface_success_rate",
      "level": "GOLD",
      "type": "DERIVED",
      "dataSource": "SERVER"
    }
  ],
  "formulaCandidates": [
    {
      "expression": "numerator / denominator",
      "numerator": {
        "id": "ad_interface_success_count",
        "nameCn": "广告接口成功次数"
      },
      "denominator": {
        "id": "ad_interface_request_count",
        "nameCn": "广告接口请求次数"
      }
    }
  ],
  "decision": "USE_DIRECT_METRIC",
  "explanation": "命中指标族 success_rate；找到直接指标“广告接口成功率”，同时找到公式候选“广告接口成功次数 / 广告接口请求次数”。"
}
```

## 8. 匹配流程

### 8.1 先匹配指标族

用 `metric_phrase` 匹配 `metric-families.yaml`：

1. `metric_phrase` 精确等于某个 family alias。
2. `metric_phrase` 包含某个 family alias。
3. 某个 family alias 包含 `metric_phrase`。
4. 英文大小写不敏感。
5. `_`、`-`、空格做弱分隔符归一化。

例如：

```text
广告成功率 -> 命中 success_rate，因为包含“成功率”。
接口平均时延 -> 命中 latency 的 avg_latency variant。
最大内存 -> 命中 memory_usage 的 max_memory_usage variant。
```

### 8.2 再匹配直接指标

在候选指标列表中，用 family 的 `direct_metric.name_contains` 或 variant 的 `name_contains` 查找直接指标。

例如 success_rate：

```text
广告接口成功率 name_cn 包含 成功率 -> direct metric
```

### 8.3 再匹配公式候选

如果 family 有 `formula`：

1. 用 numerator aliases/name_contains 找分子指标。
2. 用 denominator aliases/name_contains 找分母指标。
3. 分子和分母都存在时，生成 formula candidate。
4. 如果直接指标不存在，但公式候选完整，根据 policy 决定是否可用。

### 8.4 最后给出决策

建议第一版决策规则：

1. 有且只有一个直接指标：`USE_DIRECT_METRIC`。
2. 有多个直接指标：`ASK_USER_TO_DISAMBIGUATE`。
3. 没有直接指标，但有完整公式候选：`USE_FORMULA_WITH_EXPLANATION`。
4. 既没有直接指标，也没有完整公式候选：`NO_MATCH`。
5. 直接指标和公式候选都存在：`USE_DIRECT_METRIC`，但解释中列出公式候选。

## 9. 如何保证不是只能处理“广告”

Layer 2 的关键是：**Metric Family 与业务节点解耦。**

`success_rate` 不写成“广告成功率本体”，而写成“成功率指标族”。这样它可以处理：

```text
广告成功率
小艺接口成功率
搜索成功率
支付成功率
翻译成功率
```

处理方式相同：

```text
<业务对象> + <指标族词>
  ↓
Layer 1 定位业务对象节点
Layer 2 识别指标族
在该业务对象对应的候选指标列表中找直接指标或公式候选
```

也就是说，广告只是测试样例，不是规则边界。

后续扩展其他本体/节点时，通常只需要：

1. 在对应节点 `base.yaml` 里补业务对象 aliases。
2. 复用已有 `metric-families.yaml` 中的成功率、时延、内存等指标族。
3. 如果出现全新的指标族，再往 `metric-families.yaml` 增加一个 family。
4. 如果某个业务节点有特殊口径，再单独加 exception，不要污染通用 family。

## 10. 弱 Agent 实施步骤

1. 新增 `resources/ontology/metric-shelf/metric-families.yaml`。
2. 先写入 `success_rate`、`latency`、`memory_usage` 三个指标族。
3. 新增本地测试数据 `resources/ontology/metric-shelf/test-data/advertising-metrics.yaml`。
4. 实现 `MetricFamilyLoader`，读取 `metric-families.yaml`。
5. 实现 `MetricFamilyMatcher`，输入 `metric_phrase + metrics`，输出匹配结果。
6. 写单测：`广告成功率` 应命中 `success_rate`。
7. 单测断言直接指标为 `广告接口成功率`。
8. 单测断言公式候选为 `广告接口成功次数 / 广告接口请求次数`。
9. 单测断言 `广告接口平均时延` 能命中 `latency`。
10. 单测断言 `广告接口最大内存使用率` 和 `广告接口最小内存使用率` 能命中 `memory_usage` 的不同 variant。
11. 暂不接真实 SQL，暂不返回真实数值。

## 11. 本地测试 checklist

| 测试输入 | 期望 |
|---|---|
| `广告成功率` | 命中 `success_rate` |
| `广告接口成功率` | 直接指标候选为 `广告接口成功率` |
| `广告成功率` + 测试指标列表 | 同时识别公式候选：成功次数 / 请求次数 |
| `广告接口平均时延` | 命中 `latency`，variant 可识别为 avg latency |
| `广告接口最小内存使用率` | 命中 `memory_usage`，variant 可识别为 min memory usage |
| `广告接口最大内存使用率` | 命中 `memory_usage`，variant 可识别为 max memory usage |
| `广告曝光率` | 如果未配置 exposure_rate，返回 `NO_MATCH` 或提示未配置，不要误判成成功率 |
| `success rate` | 英文 alias 命中 `success_rate` |

## 12. 常见错误

1. 把 `metric-families.yaml` 写进每个节点 `base.yaml`，导致规则复制和概念混淆。
2. 把“广告成功率”写死成唯一规则，导致不能复用到小艺、搜索、支付等其他节点。
3. 看到“rate”就把曝光率、点击率、成功率互相替代。
4. 只有成功次数没有请求次数时仍然生成完整成功率公式。
5. 为了本地测试去伪造真实 SQL 或真实数值。
6. 把 Metric Family 当成真实指标清单，逐条维护所有指标。
7. 忽略直接指标优先级，在已有“广告接口成功率”时仍强行用公式计算。

## 13. 后续扩展方向

Layer 2 跑通后，再考虑：

1. 增加 `filter-concepts.yaml`：黄金、健康、普通、端侧、基础、衍生、复合等。
2. 增加 `metric-exceptions/`：只放高频、高风险、强歧义业务特例。
3. 接真实 RealModel：把本地测试 metrics 替换成 `getLogicEntityRealModel` 返回的已部署指标。
4. 接真实查数：等 SQL 执行链路明确后，再处理时间范围和结果计算。
