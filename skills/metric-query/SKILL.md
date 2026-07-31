---
name: metric-query
description: 本体增强的真实指标问数。用于查询某个业务节点下的指标数值、趋势、比较或指标目录，例如“最近一个月的推广成功概率是啥”“广告平均时延趋势”“小艺有哪些指标”。先用 locateNode 的节点 aliases 锁定 Phase A 节点，再对该节点返回的全部逻辑实体逐一调用 Java Phase B 的 resolveMetric，最后按真实指标 ID 和时间范围查询数据。也用于结构浏览和字段查询。
---

# 本体增强的真实指标问数

## 核心边界

- Java 是本体知识的唯一来源：节点 aliases 和 Metric Family 均由 Java YAML 维护。
- 本 Skill 只负责编排、状态处理、时间解析和展示；不要在 Skill 中重建 aliases 或 Metric Family。
- Phase A 一旦确定节点，本轮指标搜索范围即被锁定。只有用户明确更换业务对象或确认 Phase A 选错时，才可再次调用 `locateNode`。
- 逻辑实体名称不能反映其指标内容。不得按实体名称猜测或只抽查一两个实体。
- 工具契约见 [references/tools.md](references/tools.md)，输出规范见 [references/output-format.md](references/output-format.md)。

## 1. 抽取槽位

从用户问题抽取：

```yaml
business_object: 用于 Phase A 的业务对象原话
metric_phrase: 用于 Phase B 的指标原话
time_range: 用户原始时间表达
query_mode: value | trend | comparison | definition | structure | fields
filters: 可选筛选条件
```

不要擅自改写 `business_object` 或 `metric_phrase`。例如：

```text
最近一个月的推广成功概率是啥？
```

抽取为：

```yaml
business_object: 推广
metric_phrase: 成功概率
time_range: 最近一个月
query_mode: value
```

## 2. Phase A：锁定节点

1. 调用 `locateNode(business_object)`，例如 `locateNode("推广")`。
2. 只保留点分 ID 的分类节点。
3. 广义查询做最小覆盖根剪枝：若一个候选是另一个候选的后代，只保留能够覆盖目标范围的祖先。
4. 具体查询选择最贴合的具体节点，不扩大到父级。
5. 多个节点无法可靠区分时先向用户确认。
6. 保存确定的 `categoryId` 和路径，标记 `phase_a_locked=true`。
7. `locateNode` 未命中或用户确认节点错误时可以追问；禁止自行造同义词循环调用 `locateNode`。

## 3. 获取节点下全部逻辑实体

1. 对锁定节点只调用一次 `getNextLevelNode(categoryId, "CATEGORY")`。
2. 使用 `publishedData`，按逻辑实体 `id` 去重。
3. 保留每个实体的真实 `id` 和名称；不要按名称相关性过滤。
4. 即使实体名称与指标完全无关，也必须进入 Phase B 扫描。
5. 列表为空时报告该 Phase A 节点下没有逻辑实体，停止流程；不要重新定位其他节点。

## 4. Phase B：穷举当前节点内的全部实体

对去重后的**每一个逻辑实体**恰好调用一次：

```text
resolveMetric(logicEntityId, metric_phrase)
```

执行要求：

1. 可并行调用时并行；否则分批顺序调用，直至全部实体完成。
2. 不因前几个实体返回 `NOT_FOUND` 而停止。
3. 不因已经找到一个 `RESOLVED` 而停止，因为同一指标可能存在于多个逻辑实体。
4. 不直接调用 `getLogicEntityRealModel` 自行匹配；Phase B 匹配由 Java `resolveMetric` 完成。
5. 记录每个实体的 `RESOLVED`、`AMBIGUOUS`、`FORMULA_CANDIDATE`、`NOT_FOUND` 或错误状态。
6. 单个实体调用失败时记录错误并继续其他实体；全部扫描后再汇总。
7. 实体量较大时使用固定大小批次控制并发和上下文，但不得只扫描前 N 个实体。只保留匹配结果和失败摘要，不复述所有 `NOT_FOUND`。

## 5. 汇总 Phase B 结果

完成全部实体扫描后再决策。

### 没有任何候选

若全部为 `NOT_FOUND`：

- 报告在已锁定节点及其全部逻辑实体中未找到该指标。
- 给出已扫描实体数量和 Phase A 路径。
- 停止，不得更换关键词再次调用 `locateNode`。
- 只有用户明确更换业务对象或要求重新定位时，才开始新的 Phase A。

### 一个直接指标

若全节点只有一个 `RESOLVED`：使用其 `selectedMetric.id` 查数。

### 多个直接指标

若多个实体返回 `RESOLVED`：

- 保留所有候选；同一指标可能分布在不同实体中。
- 不根据实体名称或返回顺序静默选一个。
- 若用户问题本身要求覆盖整个节点，则分别查询并按实体展示，禁止在没有聚合规则时合并数值。
- 若用户只想要单一口径但候选意义不明，列出实体与指标名称并追问。

### 歧义或公式候选

- 任一 `AMBIGUOUS`：展示最少必要候选并追问。
- 只有 `FORMULA_CANDIDATE`：说明公式和组成指标；未取得用户确认且接口未提供安全执行计划时不要自行计算。
- 同时有直接指标和公式候选：优先直接指标；公式仅作为口径解释，不重复计算。

## 6. 解析时间并查数

仅 `value/trend/comparison` 执行：

1. 把时间原话转换成工具要求的明确 `startTime/endTime`。
2. “最近一个月”表示截至当前时刻的滚动一个月；“上个月”表示上一个自然月。
3. 使用已安装工具的实际格式和时区，并在最终回答中回显。
4. 对每个最终选中的直接指标调用：

```text
queryIndicatorDimensionData(selectedMetric.id, startTime, endTime)
```

5. 传指标 ID，不传分类 ID 或逻辑实体 ID。
6. 返回空就报告空，不补零、不换指标、不使用假数据。
7. 多实体结果分别展示；没有明确聚合规则时不得求和、平均或计算总体成功率。

## 7. 完整示例

用户：

```text
最近一个月的推广成功概率是啥？
```

执行：

1. 抽取 `business_object=推广`、`metric_phrase=成功概率`、`time_range=最近一个月`、`query_mode=value`。
2. 调 `locateNode("推广")`。Java Phase A 读取节点 `base.yaml` 的 aliases，将“推广”映射到广告分类。
3. 锁定广告 `categoryId`；后续即使未命中指标，也不得自由改词重新定位节点。
4. 调一次 `getNextLevelNode(categoryId, "CATEGORY")`，取得该节点及后代中的全部逻辑实体。
5. 不看实体名称猜指标；对每个去重后的实体调用 `resolveMetric(entity.id, "成功概率")`。
6. Java Phase B 读取 `metric-families.yaml`，把“成功概率”识别为 `success_rate`，并在各实体真实 RealModel 中匹配指标。
7. 扫描全部实体后汇总。若“广告测试实体”返回“广告接口成功率”的真实 ID，且没有其他直接候选，选中该 ID。
8. 将“最近一个月”转换为明确起止时间。
9. 调 `queryIndicatorDimensionData(metricId, startTime, endTime)`。
10. 展示命中节点、逻辑实体、指标名称、语义口径、实际时间范围和真实返回。

## 8. 定义、结构和字段查询

- 结构浏览：使用 `getModelTree` / `locateNode`，不执行实体穷举和查数。
- 逻辑实体指标目录：用户明确要求目录时可调用 `getLogicEntityRealModel`；不要用它在 Skill 中重写 Phase B。
- 字段查询：使用 `getLogicEntityDefineInfo` 的 `fields`；其未部署指标不能用于生产查数。

## 9. 禁止事项

1. Phase A 锁定后，不因 Phase B 未命中而自由造词再次调用 `locateNode`。
2. 不按逻辑实体名称过滤 Phase B 扫描范围。
3. 不只尝试一两个实体，也不找到第一个结果就提前结束。
4. 不在 Skill 中硬编码节点 aliases、Metric Family 或真实 ID。
5. 不自行扫描 RealModel、执行 SQL 或拼接 ID。
6. 不把成功概率、成功次数、请求次数当成同一个指标。
7. 不把平均、最小、最大、P95/P99 等口径互相替代。
8. 不在多个候选间静默选择，不在没有聚合规则时合并跨实体数据。
