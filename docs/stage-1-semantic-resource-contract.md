# 阶段 1：最小语义资源合同与只读校验

> 执行者：能够访问真实 databp Java 工程和阶段 0 全部交付物的弱 Agent。
> 本阶段性质：建立最小资源合同、loader/validator 和离线合同测试；不实现 `resolveSemanticQuery`，不改变现有问数主链路。
> 上位计划：[`semantic-query-ontology-migration-plan.md`](semantic-query-ontology-migration-plan.md)。
> 阶段 0 指南：[`stage-0-semantic-query-investigation.md`](stage-0-semantic-query-investigation.md)。

## 1. 现在能否开始阶段 1

### 1.1 判断

**可以开始阶段 1 的文档定稿和资源设计，但当前不能直接宣称阶段 0 已完整验收，也不能立即开始生产编码。**

原因：项目负责人已经回答阶段 0 报告中的 OQ-001 至 OQ-005，语义决策足以确定阶段 1 的职责边界；但已提供的调查报告仍显示：

1. Q1 只到 T2，尚未附最终真实查数证据。
2. Q2 只到 T1，“一般时延”虽然已有处理决策，但尚未验证现有接口能返回 family 下全部 variants。
3. Q3 只到 T2，尚未验证 min/max 两个真实指标和两个数据结果。
4. Q4 到 T3，但报告正文仍写“黄金指标字段待确认”，需要按 `level=gold` 修订并补真实指标目录证据。
5. 阶段 0 要求的 `semantic-query-facts.yaml` 和 `semantic-query-java-file-map.md` 未随本次输入提供内容，无法核对真实完整路径和机器合同。

因此采用两道门：

```text
DESIGN_READY         # 本文可以定稿，弱 Agent 可准备 YAML 草案和测试样例
IMPLEMENTATION_READY # 补齐 §2 准入物后，才允许在真实 Java 工程新增 loader/validator
```

当前状态：`DESIGN_READY`，尚未达到 `IMPLEMENTATION_READY`。

### 1.2 为什么不强行等待所有 T4 才设计资源

阶段 1 只负责表达已确认语义和校验资源，不查询数据库。Q1/Q3 的 T4 证据不会改变“推广属于广告”“成功率是 family”“内存使用率包含 min/max”这些资源形态，
所以可以先写合同；但真实 ID、文件路径和测试期望必须来自阶段 0 交付物，不能凭调查报告摘要补造。

---

## 2. 开始生产实施前必须补齐的准入物

弱 Agent 开始改真实 Java 工程前必须提交或更新：

```text
docs/semantic-query-stage-0/semantic-query-facts.yaml
docs/semantic-query-stage-0/investigation-report.md
docs/semantic-query-java-file-map.md
```

具体要求：

1. `investigation-report.md` 将 OQ-001 至 OQ-005 标为 `RESOLVED`，写入 §3 的负责人决定。
2. `semantic-query-facts.yaml` 同步写入四问合同，不只在 Markdown 中口头关闭。
3. Q1 至少补齐真实指标解析证据；若环境允许，补 T4 查数证据。未达到 T4 时必须写明阻塞，不得标 PASS。
4. Q2 记录全部“点击”候选，并验证“有数据”不参与 Java 候选排序。
5. Q3 验证当前 `resolveMetric` 对无 variant 输入的实际行为，以及分别请求 min/max variant 能否取得两个真实 metric ID；有条件时补两个真实数据结果。
6. Q4 用真实指标数据证明 `level` 字段及 `gold` 实际大小写，列出全部黄金指标必要字段；明确不查数。
7. `semantic-query-java-file-map.md` 给出真实 Java 仓库根、module、完整相对路径和基线 commit。
8. 若测试环境仍为 `localhost:8083`，记录它对应的代码 commit、配置 profile 和数据环境；不能只写端口。

任何一项缺失时，阶段 1 YAML 中相应生产值必须保持 `null`/`TBD`，loader 开发不得用示例值代替。

---

## 3. 已关闭开放问题的正式决策

### 3.1 OQ-001：“一般时延”

决定：

1. 不给 `latency` 或任何 variant 增加“一般时延” alias。
2. 如果云端 Agent 从原话识别出基础词“时延”，但没有明确 avg/min/max/P95/P99 等 variant，则保留 `latency` family 层级。
3. Java 只提供该 family 已声明的全部 variants 和必要解释，不替用户选择。
4. 云端 Agent / Skill 展示 variants 并追问用户想要哪一种准确口径。
5. 在用户确认前不调用真实指标查数。

阶段 1 的资源必须支持 `family -> variants[]` 枚举；阶段 1 不实现追问代码。

### 3.2 OQ-002：“黄金指标”

决定：

1. 黄金指标指逻辑实体指标数据中 `level=gold` 的指标。
2. 第一阶段由云端 Agent / Skill 对真实指标目录执行该过滤。
3. Java 阶段 1 不新增 `FilterConcept`、`filter-concepts.yaml` 或过滤执行器。
4. 弱 Agent 必须用真实数据确认字段名是 `level`，并记录实际值是 `gold`、`GOLD` 或其他大小写；Skill 应按现有规范做大小写不敏感比较。
5. Q4 返回全部符合条件的指标，不因无数值而减少指标目录。

### 3.3 OQ-003：时间解析

决定：

1. “最近一个月”和无时间表达时的交互继续由云端 Agent / Skill 处理。
2. Java 阶段 1 不新增时间概念 YAML、时间解析器或默认时间窗口。
3. Agent 最终调用查数工具时仍必须提供明确起止时间和时区。
4. 无时间表达且现有 Skill 没有默认规则时，由 Agent 追问，不允许 Java 私设默认范围。

### 3.4 OQ-004：min/max 返回

决定：

1. 用户只说“内存使用率”且没有指定 variant 时，当前把 family 下全部 variants 返回给云端 Agent。
2. 对 Q3，已知验收期望是 min/max 两种指标全部返回。
3. Java 不静默选择 min 或 max，不合并数值，也不把两个结果当成只能选一项的普通错误歧义。
4. 云端 Agent 当前全部展示；如果以后需要追问，由 Skill 调整，不改变 family 资源。

### 3.5 OQ-005：多个节点候选

决定：

1. `locateNode` 的多个候选当前全部返回。
2. Java 不根据候选有没有指标或数据决定哪个“更相关”。
3. 云端 Agent / Skill 结合路径和用户上下文展示或追问。
4. 用户确认前不扩大范围、不上卷，也不只扫描有数据的广告候选。

---

## 4. 阶段 1 的目标与边界

### 4.1 本阶段目标

1. 用最小 YAML 表达四问所需的稳定业务概念、指标 family/variants 和 Concept 到真实货架资产的 mapping。
2. 复用真实 Java 工程现有 loader 所在分层，建立只读加载和静态校验。
3. 生成确定的内存索引供后续阶段使用，但不接入现有生产查询链路。
4. 用离线合同测试证明四问的稳定语义可以表达。
5. 更新 Java 文件地图，使下一阶段能找到每个资源、loader、validator 和测试。

### 4.2 Java 本阶段要做

1. 在真实 resources 根下创建 §5 的最小目录。
2. 加载并校验 `business-concepts.yaml`、`metric-concepts.yaml`、`mappings.yaml`。
3. 如真实 loader 架构需要，自描述 schema 可单独放入 `model.yaml`；否则不创建空壳文件。
4. 构建只读索引：label/alias 到 concept、concept 到 entry、concept 到 mapping、family 到 variants。
5. 启动或测试时验证 ID、alias、引用和 mapping 冲突。
6. 只写单元/离线合同测试，不修改 `locateNode` 和 `resolveMetric` 运行顺序。

### 4.3 Java 本阶段不做

1. 不实现 `resolveSemanticQuery` Controller/Service。
2. 不实现运行时 Shelf Catalog；这是阶段 2。
3. 不接入或重构 `treeModelView()`、`locateNode` 和现有五分钟缓存。
4. 不新增时间解析。
5. 不实现 `level=gold` 过滤。
6. 不实现云端追问、多候选选择或 variant 选择。
7. 不查询 RealModel 或真实指标数据。
8. 不创建 `capabilities.yaml`、`policies.yaml`、`filter-concepts.yaml` 以凑齐目录。
9. 不删除或迁移旧 Phase A/Phase B 资源。

### 4.4 Skill 本阶段要做

Skill 变更可以与 Java 资源合同并行，但必须保持现有接口：

1. 记录 Q2 规则：family 命中而 variant 未明确时展示全部 variants 并追问，不制造“一般时延” alias。
2. 记录 Q4 规则：遍历锁定范围内全部逻辑实体的指标目录，按 `level=gold` 大小写不敏感过滤并全部返回。
3. 记录时间规则：时间表达由 Agent 解析；缺少时间且要查数时按已有产品规则处理，没有规则则追问。
4. 记录 Q3 规则：无 variant 的内存使用率返回 family 下全部 variants；当前 min/max 全部展示。
5. 记录多节点候选规则：全部保留并向用户澄清，不用“是否有数据”排序。

阶段 1 文档可以规定这些 Skill 行为；是否在同一提交修改 `SKILL.md` 由项目负责人安排。Java loader 完成不依赖 Skill 已发布。

---

## 5. 预期 resources 目录

真实前缀必须从 `semantic-query-java-file-map.md` 读取：

```text
<java-resources-root>/ontology/semantic-query/
├── business-concepts.yaml
├── metric-concepts.yaml
└── mappings.yaml
```

只有当真实 loader 需要集中声明 schema version 时才增加：

```text
└── model.yaml
```

不要在本阶段创建：

```text
filter-concepts.yaml
capabilities.yaml
policies.yaml
axioms.yaml
shelf-nodes.json
```

---

## 6. `business-concepts.yaml` 合同

### 6.1 作用

只保存稳定业务概念和稳定词法标注，不镜像完整货架，不保存逻辑实体 UUID、真实 metric ID 或查询数值。

四问第一批至少需要调查是否建立：

```text
advertising
celia
```

“点击”是否应成为稳定业务概念不能由本阶段自行决定。阶段 0 只证明它命中两个真实节点；若没有独立、稳定、可复用的业务定义，
它应继续由运行时节点发现和云端澄清处理，不要为了 Q2 强建 `click` concept。

### 6.2 预期 YAML

```yaml
schema_version: 1
concepts:
  - id: <稳定 concept id>
    type: BusinessConcept
    canonical_name: <规范业务名称>
    aliases:
      - value: <稳定业务说法>
        language: <zh-CN | en-US | 真实项目枚举>
        source: <PHASE_A_YAML | SHELF | BUSINESS_CONFIRMED>
    definition: <经确认的业务定义；未知则 null>
    owner: <真实 owner；未知则 null>
    status: ACTIVE
```

要求：

1. `推广`、`ad` 的来源必须按阶段 0 证据填写，不能统一声称来自真实货架。
2. 真实货架非空 alias 可以作为来源，但不能把空字段写入 aliases。
3. 同一个归一化 alias 指向多个 concept 时加载失败或输出明确冲突，不能按文件顺序取第一个。
4. `一般时延` 不属于 business concepts。
5. `黄金指标` 不属于本阶段 business concepts。

---

## 7. `metric-concepts.yaml` 合同

### 7.1 作用

表达稳定 Metric Family、variants 和不可替代关系。第一版可以从现有 `metric-families.yaml` 读取或迁移，但不能形成两个会漂移的生产真相源。

弱 Agent 必须先选择一种方式并记录理由：

```text
REFERENCE_EXISTING  # 新资源引用/适配现有 metric-families.yaml，不复制内容
MIGRATE_ONCE        # 一次迁移后由新文件成为唯一真相源，旧 loader 兼容读取
EXTEND_EXISTING     # 不创建新 metric-concepts.yaml，直接扩展现有文件 schema
```

阶段 1 默认优先 `REFERENCE_EXISTING` 或 `EXTEND_EXISTING`，除非真实 loader 结构证明不可行。

### 7.2 预期 YAML

若最终需要独立文件，格式应至少支持：

```yaml
schema_version: 1
metric_concepts:
  - id: success_rate
    type: MetricFamily
    canonical_name: 成功率
    aliases: []
    variants: []

  - id: latency
    type: MetricFamily
    canonical_name: 时延
    aliases: []
    unspecified_variant_policy: RETURN_ALL_VARIANTS
    variants:
      - id: <从现有真实配置填写>
        canonical_name: <从现有真实配置填写>
        aliases: []

  - id: memory_usage_rate
    type: MetricFamily
    canonical_name: 内存使用率
    aliases: []
    unspecified_variant_policy: RETURN_ALL_VARIANTS
    variants:
      - id: min_memory_usage_rate
        role: MIN
        canonical_name: <从现有真实配置填写>
        aliases: []
      - id: max_memory_usage_rate
        role: MAX
        canonical_name: <从现有真实配置填写>
        aliases: []
```

要求：

1. `一般时延` 不加入 aliases。
2. `unspecified_variant_policy` 表达返回候选集合，不表达 Java 自动追问。
3. min/max 是两个独立 variant，不互相替代。
4. 真实 aliases、variant ID 和匹配规则从现有 `metric-families.yaml` 读取，不以本文示意覆盖真实配置。
5. 若采用 `REFERENCE_EXISTING`，上述新字段应放在兼容的扩展/适配层，而不是复制全部 family。

---

## 8. `mappings.yaml` 合同

### 8.1 作用

只保存稳定业务概念到当前真实货架分类资产的映射。它不保存运行时搜索候选，不把所有 L2.3/L2.4 抄入 YAML。

### 8.2 预期 YAML

```yaml
schema_version: 1
mappings:
  - concept_id: <business concept id>
    targets:
      - source: databp
        asset_type: ShelfCategory
        asset_id: <阶段 0 真实 ID>
        scope_policy: EXACT_SUBTREE
    owner: <真实 owner；未知则 null>
    status: ACTIVE
```

要求：

1. advertising 和 celia 的 `asset_id` 必须来自阶段 0 事实文件。
2. Q2 的两个“点击”候选不得为了让测试通过全部写成 advertising 的固定映射。
3. mapping target 必须能在阶段 0 真实树证据中找到。
4. 不做 covering root 上卷；`EXACT_SUBTREE` 只描述概念自己映射的范围。
5. mapping 中不写逻辑实体 UUID、metric ID、时间范围或 `level=gold`。

---

## 9. Loader 与 Validator 合同

### 9.1 文件位置

不得新建脱离真实工程分层的 `semantic-query-code/` 总目录。弱 Agent 应通过 `semantic-query-java-file-map.md` 找到现有 loader/config/test 包，
把新增类放到对应职责位置，并在同一提交更新文件地图。

### 9.2 必须校验

1. `schema_version` 存在且受支持。
2. concept/family/mapping ID 非空且唯一。
3. canonical name 非空。
4. alias 值非空，归一化冲突可检测。
5. alias source/language 使用受支持枚举；真实项目没有语言枚举时先保留字符串校验，不编造 Java enum。
6. variant ID 在 family 内唯一。
7. `RETURN_ALL_VARIANTS` 只允许用于确实存在 variants 的 family。
8. mapping 引用的 concept 存在。
9. mapping asset ID 非空；阶段 1 只做静态校验，是否实时存在留到阶段 2。
10. `scope_policy` 只接受代码支持值，第一版至少需要 `EXACT_SUBTREE`。
11. 单个错误不能被静默忽略；失败策略沿用现有 loader 规范并在报告中说明。
12. 三份资源应一次性构建不可变快照；是否支持热刷新本阶段不决定。

### 9.3 最小内存索引

```text
normalized label/alias -> business concept candidates
business concept id -> business concept
metric family id -> family + variants
metric label/alias -> family/variant candidates
business concept id -> mappings
```

索引只供测试和后续阶段复用，本阶段不接入 `locateNode` 或 `resolveMetric`。

---

## 10. 阶段 1 测试合同

### 10.1 YAML/loader 测试

至少覆盖：

1. 三份资源可加载。
2. 重复 concept/family/variant ID 被拒绝。
3. 空 alias 被拒绝或明确过滤，行为与现有 loader 规范一致。
4. 归一化 alias 冲突被报告。
5. mapping 引用不存在 concept 被拒绝。
6. 非法 `scope_policy` 被拒绝。
7. 没有 variants 的 family 使用 `RETURN_ALL_VARIANTS` 被拒绝。
8. 单文件解析失败不会留下半更新内存索引。

### 10.2 四问离线合同测试

本阶段不调用数据库。输入为阶段 0 的四问事实，期望为稳定资源解释：

| 问题 | 阶段 1 只验证什么 | 不在 Java 阶段 1 验证什么 |
|---|---|---|
| Q1 | `推广` 可关联 advertising；success_rate family 存在；mapping 指向真实广告资产 | 最近一个月解析、真实查数 |
| Q2 | latency family 可枚举全部真实 variants；`一般时延` 未被新增为 alias | 节点候选选择、追问和查数 |
| Q3 | `ad` 可关联 advertising；memory family 无 variant 时返回 min/max 元数据 | Agent 展示、时间和真实查数 |
| Q4 | celia mapping 存在 | `level=gold` 过滤和指标目录输出 |

注意：Q2 的“点击”是运行时节点候选问题，阶段 1 不应为了让离线测试全绿而硬编码选择广告点击。

### 10.3 兼容回归

1. 现有 `locateNode("推广")` 行为不变。
2. 现有 `locateNode("ad")` 行为不变。
3. 现有 `resolveMetric` 行为不变，除非采用经批准的 `EXTEND_EXISTING` 兼容 schema；即便扩展也不能改变现网响应。
4. 原 Phase A/Phase B loader 测试继续通过。

---

## 11. 必须交付的文件

真实 Java 工程中的文件名和路径以文件地图为准；阶段 1 至少交付：

```text
<java-resources-root>/ontology/semantic-query/
├── business-concepts.yaml
├── metric-concepts.yaml      # 仅在未采用 REFERENCE_EXISTING/EXTEND_EXISTING 时
└── mappings.yaml

<existing-loader-package>/...Loader.java
<existing-loader-package>/...Validator.java   # 可合并在 loader，按现有风格
<existing-test-package>/...LoaderTest.java
<existing-test-package>/...ContractTest.java

docs/semantic-query-stage-1/implementation-report.md
docs/semantic-query-java-file-map.md
```

不得照抄上面的 `...` 创建真实文件；弱 Agent 必须替换为项目现有命名和真实路径。

---

## 12. `implementation-report.md` 预期结构

```markdown
# 阶段 1 实施报告

## 1. 执行摘要
- 基线 commit、实施 commit、环境。
- IMPLEMENTATION_READY 证据。
- 阶段 1 PASS / PARTIAL / FAIL。

## 2. 阶段 0 准入复核
- 三个阶段 0 文件位置。
- Q1-Q4 最新等级。
- OQ-001 至 OQ-005 的关闭记录。

## 3. 资源设计
### 3.1 Business Concepts
### 3.2 Metric Families / Variants
### 3.3 Mappings
### 3.4 明确未创建的资源及原因

## 4. Loader / Validator
- 真实类路径、职责、初始化方式、失败策略。
- 内存索引结构。
- 是否复用现有 loader。

## 5. 四问离线合同结果
### 5.1 Q1
### 5.2 Q2
### 5.3 Q3
### 5.4 Q4

## 6. 兼容回归
- Phase A/B 现有测试和接口行为。

## 7. Skill 合同
- 本阶段已修改或待修改的 Skill 规则。
- Java 明确未承担的职责。

## 8. 文件地图变更
- 链接到 ../semantic-query-java-file-map.md。

## 9. 未决事项
- 负责人、证据、最晚阶段。

## 10. 阶段 1 结论
- 是否允许进入阶段 2。
```

---

## 13. 未决事项

以下仍不能从当前输入确定，弱 Agent 不得编造：

| 未决项 | 负责人 | 最晚确认点 |
|---|---|---|
| 三个阶段 0 交付文件的真实内容和 commit | 阶段 0 弱 Agent | 实施编码前 |
| 完整 Java 包路径和 module | 阶段 0 弱 Agent | 实施编码前 |
| Q1/Q3 真实指标与查数证据 | Java 弱 Agent | 阶段 1 验收前 |
| “一般时延”识别为 latency family 的云端抽取方式 | Skill 维护者 | Skill 改造前 |
| `level` 实际大小写和值域 | Java 弱 Agent | Skill 改造前 |
| Q4 指标目录使用 RealModel 还是定义接口 | Java 弱 Agent / 项目负责人 | Skill 改造前 |
| metric concepts 是引用、迁移还是扩展现有文件 | Java 弱 Agent | YAML 开工前 |
| loader 启动失败还是降级 | Java 弱 Agent，遵循现有规范 | loader 开工前 |
| 是否创建独立 `model.yaml` | Java 弱 Agent | schema 定稿时 |

---

## 14. 阶段 1 完成门禁

以下全部通过才可进入阶段 2：

1. 达到 `IMPLEMENTATION_READY`，阶段 0 三个交付物已核对。
2. OQ-001 至 OQ-005 在 facts 和 report 中关闭。
3. 三类资源存在，或 metric concepts 采用有文档和测试的复用方案。
4. loader/validator 和不可变索引测试通过。
5. 四问离线合同测试通过，且没有为了 Q2 硬编码广告点击。
6. `一般时延` 未加入 metric aliases。
7. `level=gold`、时间、variant 追问和多节点澄清没有被错误下沉到 Java。
8. min/max 保持两个独立 variants。
9. 现有 Phase A/B 测试和接口行为未回归。
10. Java 文件地图与实施报告已更新。
11. 所有未知生产值仍是 `null`/`TBD`，没有示例值混入生产资源。

---

## 15. 弱 Agent 最终回复格式

```text
Readiness
- DESIGN_READY / IMPLEMENTATION_READY
- 阶段 0 缺失项（如有）

Summary
- 新增/复用的语义资源
- Loader/Validator/索引
- 四问合同结果
- Skill 与 Java 职责边界

Files
- Java 文件地图链接
- 实施报告链接
- 所有实际代码/资源/测试路径

Validation
- 精确测试命令与结果
- 兼容回归结果
- commit

Open Questions
- 仍未关闭的事项、负责人和最晚阶段
```

不得在只达到 `DESIGN_READY` 时声称阶段 1 已经实施完成。
