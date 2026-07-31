# 指标本体讨论结论

## 1. 文档目的

本文只保留目前仍然有效的背景、约束和设计结论，作为后续 Java 弱 Agent、云端 Agent 和方案评审的共同上下文。

详细实施文档：

1. `docs/locatenode-ontology-mvp.md`：Java 侧 Phase A。
2. `docs/metric-family-ontology-mvp.md`：Java 侧 Phase B。
3. `docs/agent-realmodel-query-rules.md`：云端 Agent 调用规程。
4. `skills/metric-query/SKILL.md`：现有 Skill；后续按稳定接口规程演进。

## 2. 项目目标

本体不是数据库，也不替代真实数据接口。它是云端 Agent 和企业系统之间的业务语义层，负责告诉系统：

1. 用户说的业务对象对应哪个货架节点。
2. 用户说的指标口径对应哪个已部署指标。
3. 不同指标、过滤条件、关系和规则之间是什么语义。
4. 应如何把业务语言转成可执行、可解释的查询计划。

长期希望通过本体统一业务口径、减少 Agent 猜测、提高匹配准确度和结果可解释性。实施策略不是先建设完整 OWL 工程，
而是从可验证的小闭环开始：

```text
一组轻量 YAML/资源配置
  + Java 运行时加载和解析层
  + 少量稳定语义接口
  + 云端 Agent 编排
  + 现有真实数据接口
```

## 3. 两类 Agent 的边界

### 3.1 Java 代码侧弱 Agent

“弱 Agent”是在 IDEA 中辅助开发的内部 Agent。它可以访问 Java 工程和内部 resources，负责：

1. 修改 Java 代码和 YAML。
2. 建立 loader、entry、matcher、resolver 等运行时能力。
3. 暴露云端可调用的语义接口。
4. 编写单元测试和真实接口集成测试。

Java 实施文档只写代码侧职责，不重复云端 Agent 的完整编排逻辑。

### 3.2 云端 Agent

云端 Agent 在服务部署后通过接口完成问数，负责：

1. 意图和槽位抽取。
2. 按顺序调用节点、实体、语义解析和查数接口。
3. 根据歧义状态追问用户。
4. 解析时间范围。
5. 展示真实结果和解释依据。

云端 Agent 不直接读取 Java YAML，不在 Skill 中复制本体规则，也不构造真实 ID。

## 4. 本体资产的存放原则

所有本体 YAML 统一放在 Java 侧，作为业务语义的唯一来源。统一存放不代表所有概念写进同一个文件：

```text
resources/ontology/metric-shelf/
├── DataModel/
│   └── 每个节点目录/base.yaml
├── metric-families.yaml
├── filter-concepts.yaml          # 后续
├── relations.yaml                # 后续
├── query-mappings.yaml           # 后续
└── rules/                        # 后续
```

按语义作用域拆分的原因：

1. `base.yaml` 描述单个货架节点。
2. Metric Family 是成功率、时延、内存使用率等跨节点口径。
3. 过滤概念、关系、规则和查询映射也可能跨多个节点复用。
4. 避免在每个节点重复维护相同规则。
5. 所有文件仍由同一 Java 工程、同一发布流程和同一运行时管理。

## 5. 当前 DataModel 现状

Java 项目已有 `resources/DataModel`：

1. 每个节点一个目录。
2. 子节点继续嵌套目录。
3. 每个节点对应一个 `base.yaml`。
4. 常见字段包括 `id`、`parent_category_id`、`name_cn`、`name_en`、`description`。
5. 部分节点还有 `version`、`owner`、`offering` 等字段。

resources 快照可能落后于真实货架。例如广告点击真实 ID 为：

```text
business_and_platform.ADV.AdvertiserRebate.pps_click
```

但旧资源可能只记录到父节点。MVP 不因此阻塞：先复制现有 DataModel 到本体资源目录，在副本上补 aliases 和已确认节点；
真实 ID 不确定时禁止编造，后续逐步同步。

## 6. Phase A：aliases-only locateNode

### 6.1 目标

```text
用户业务对象说法 -> 真实货架分类节点
```

当前本体收益集中在 `aliases`：列出同义词、英文、缩写和口语表达，提高节点定位准确率。

节点已有 `id/name_cn/name_en`，因此 Phase A 不额外维护 `concept_id`。点分 ID 已编码层级，
因此不手工维护另一份 `path`。

广告示例：

```yaml
id: business_and_platform.ADV
name_cn: 广告
name_en: Advertising
aliases:
  - 广告
  - ads
  - ad
  - 推广
  - 推广业务
```

### 6.2 Java 实现现状和边界

Phase A 已有 `load` 包、`OntologyLoader` 和用于读取 `base.yaml` 的 `LocateNodeEntry`。
这套 loader + entry + 内存查询结构已经承担节点本体加载职责，不要求为了抽象概念而重命名。

`locateNode`：

1. 读取节点本体副本。
2. 匹配 `id/name_cn/name_en/aliases`。
3. 返回分类候选和匹配依据。
4. 未命中时保留旧树搜索兜底。
5. 不获取逻辑实体，不读取 RealModel，不查数。

## 7. Phase B：Metric Family

### 7.1 目标

```text
logicEntityId + 用户指标短语
  -> Metric Family
  -> 真实 RealModel 指标
  -> 真实 metricId / 歧义 / 公式候选 / 未找到
```

Metric Family 统一放在 Java `metric-families.yaml`，不放进各节点 `base.yaml`，也不复制到云端 Skill。

第一版覆盖当前真实数据可验证的：

1. `success_rate`。
2. `latency.avg_latency`。
3. `memory_usage_rate.min/max`。

### 7.2 Java 运行方式

Phase B 沿用 Phase A 的实现思路：

1. entry 表达 YAML 结构。
2. loader 在启动时加载并校验资源。
3. matcher 识别 family/variant 并匹配真实指标。
4. resolver 编排 RealModel 获取和匹配结果。
5. Controller 只提供薄接口层。

可扩展现有 `OntologyLoader`，也可在其职责仅限节点时新增 `MetricFamilyLoader`。名字不是关键；关键是配置只有一份、
加载逻辑清楚、索引只读、错误可见。暂不为了统一抽象回头重构稳定的 Phase A。

### 7.3 `resolveMetric` 接口

因为云端 Agent 无法直接访问 Java 内部 matcher，Phase B 必须暴露对外接口：

```text
resolveMetric(logicEntityId, metricPhrase)
```

接口内部：

1. 根据 `logicEntityId` 使用已有内部 service/repository 获取真实 RealModel。
2. 根据 `metricPhrase` 命中 Metric Family。
3. 在已部署指标中选择直接候选或公式候选。
4. 返回真实指标 ID 和匹配依据。

云端 Agent 不先下载巨大 RealModel 再传回 `resolveMetric`。`getLogicEntityRealModel` 保留给指标目录浏览和排查。

## 8. 当前真实数据和展示场景

广告节点下已有逻辑数据实体“广告测试实体”，包含：

1. 广告接口成功率。
2. 广告接口最小内存使用率。
3. 广告接口平均时延。
4. 广告接口成功次数。
5. 广告接口最大内存使用率。
6. 广告接口请求次数。

真实查数接口为：

```text
queryIndicatorDimensionData(metricId, startTime, endTime)
```

主演示问题：

```text
最近一个月推广业务的成功占比是多少？
```

它同时验证：

1. Phase A：`推广业务` 通过广告节点 alias 命中。
2. 实体获取：找到“广告测试实体”。
3. Phase B：`成功占比` 命中 `success_rate`。
4. 指标匹配：选择直接指标“广告接口成功率”，而不是成功次数或请求次数。
5. 真实查数：使用 `resolveMetric` 返回的真实指标 ID 和明确起止时间查询。

不再维护生产用本地假指标 YAML。单元测试可以 mock RealModel service，结构应与真实返回一致；最终必须通过真实广告实体集成验收。

## 9. 云端标准调用链

```text
用户问题
  -> Agent 抽取 businessObject / metricPhrase / timeRange
  -> locateNode(businessObject)                    # Phase A
  -> getNextLevelNode(categoryId, CATEGORY)        # 获取真实逻辑实体
  -> resolveMetric(logicEntityId, metricPhrase)    # Phase B
  -> 必要时根据候选追问
  -> queryIndicatorDimensionData(metricId, startTime, endTime)
  -> 展示真实结果和依据
```

云端 Agent 维护调用编排、追问、时间和展示；Java 维护 aliases、Metric Family、真实匹配和后续本体规则。

## 10. 接口策略

新增接口有成本，但本体 Java 运行时必须有接口才能被云端 Agent 使用。

当前采用清晰的小闭环：

1. 保留已有 `locateNode` 承担 Phase A。
2. 新增职责单一的 `resolveMetric` 承担 Phase B。
3. 复用已有 `getNextLevelNode` 和 `queryIndicatorDimensionData`。
4. 标准问数链路不要求 Agent 拉取完整 RealModel。

后续本体能力增加时，不按每个 YAML 文件机械新增接口。优先考虑一个组合式语义解析接口返回节点、指标、过滤、关系、
规则依据和查询计划；如果某类能力输入输出、性能或安全边界明显不同，可以独立拆分。

核心原则：内部可以有多个 loader/resolver，对外接口按稳定业务职责收敛；不能为了接口数量少制造不可测试的万能接口。

## 11. 后续本体方向

后续希望逐步增加：

1. 过滤概念：黄金、健康、基础、复合、端侧等自然语言到规范条件的映射。
2. 关系语义：声明哪些节点、实体或指标之间存在依赖、归属和可传递关系。
3. 业务规则：将稳定口径和判断条件从 Agent 提示词收敛到 Java 本体资源。
4. 查询映射：把业务概念映射到真实数据实体、字段、维度和查询能力。
5. 语义查询计划：将多个本体模块组合成可执行、可解释的计划。
6. 本体治理：版本、校验、冲突检测、刷新、审计和解释。

这些能力仍遵循：YAML 在 Java 侧、Java 运行时执行、接口向云端暴露、云端 Agent 负责编排和交互。
具体阶段的字段和接口等有真实需求后再设计，当前不阻塞 Phase B。

## 12. 关键禁止事项

1. 不把本体当数据库或真实指标快照。
2. 不在多个节点 `base.yaml` 重复 Metric Family。
3. 不在 Java YAML 和云端 Skill 各维护一份业务规则。
4. 不写死真实指标 ID。
5. 不把 `getLogicEntityDefineInfo` 的未部署指标用于生产查数。
6. 不让云端 Agent 构造 ID、执行 SQL 或自行实现另一套指标 matcher。
7. 不把成功率、成功次数、请求次数混为同一指标。
8. 不把平均、最小、最大、P95/P99 等不同口径互相替代。
9. 不在歧义时静默猜测。
10. 不使用假数据掩盖真实接口空结果或错误。

## 13. 2026-07-31：Skill 的节点内全实体扫描策略

当前 `getNextLevelNode` 返回的逻辑实体数量较多，实体名称又不能反映内部指标，因此云端 Agent 不能依靠实体名称筛选，
也不能只尝试一两个实体。暂定策略如下：

1. Phase A 通过 `locateNode` 确定分类节点后立即锁定搜索范围。
2. 对锁定节点调用一次 `getNextLevelNode`，按逻辑实体 ID 去重。
3. 对该节点下每一个去重逻辑实体恰好调用一次 `resolveMetric(logicEntityId, metricPhrase)`。
4. 可以并行或分批调用以控制并发和上下文，但不能只处理前 N 个实体。
5. 前几个实体 `NOT_FOUND` 时继续；找到第一个 `RESOLVED` 后也继续，因为同一指标可能分布在多个逻辑实体。
6. 完成全部实体扫描后统一处理直接指标、歧义候选、公式候选和失败摘要。
7. 全部未命中时，在已锁定 Phase A 节点内结束，不允许 Agent 自由造词再次调用 `locateNode`。
8. 只有用户明确更换业务对象或确认 Phase A 节点错误时，才开始新的 Phase A。
9. 多个实体命中时保留所有结果；没有明确聚合规则时分别展示或追问，不能静默选择或自行合并。
10. 主验收问题调整为“最近一个月的推广成功概率是啥？”。`推广` 由 Phase A 节点 aliases 解析，`成功概率` 由 Java Phase B 的 `success_rate` alias 解析。

该策略是当前只提供实体级 `resolveMetric` 时的 Skill 侧临时方案。后续若实体数量和调用成本成为瓶颈，
可考虑由 Java 新增节点级语义解析能力，在服务端完成节点内实体遍历、跨实体候选汇总和必要的跨实体公式组合；本轮不实现该能力。
