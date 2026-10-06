# 从 YAML 映射到可推理本体：演进方案（规划文档）

> 作者角色：规划 / 引导 Agent（本仓库中转站文档）。  
> 读者：人、Java 弱 Agent、云端 Agent Skill 维护者。  
> 前提：Phase A（`locateNode` + aliases）与 Phase B（`resolveMetric` + Metric Family）已打通真实问数闭环。

## 0. 一句话结论

当前 Phase A/B 的价值是**词表映射**；本体真正该守住的优势是：

```text
稳定意图（TBox）  ≠  可变货架部署（ABox / 运行时目录）
用「覆盖根 + 公理 + 轻量推理」把二者绑在一起，而不是把整棵货架树手抄进 YAML。
```

先不要上完整 OWL 工具链（Protégé + HermiT/Pellet + 全量公理工程）。先落地一套**语义等价的分层运行时**；字段与推理结果将来可导出 OWL，但产品路径不依赖它。

---

## 1. 问题诊断：为什么现在「不像本体」

| 现状 | 实际在做什么 | 缺的本体能力 |
|---|---|---|
| 每个节点 `base.yaml` + `aliases` | 词表 / 同义词表 | 没有「概念 vs 部署节点」的分层 |
| `metric-families.yaml` | 指标口径词典 + 字符串匹配策略 | 口径之间的互斥、从属、可推导关系未形式化 |
| `locateNode` / `resolveMetric` | 查表 + contains | 几乎没有 subsumption / 一致性 / 覆盖推理 |
| 货架变更靠人改 YAML | 把 ABox 当配置手维 | 高频漂移，维护成本随树深爆炸 |

Phase A/B 作为 MVP 是对的；下一步不是「把 YAML 写成 OWL 文件」，而是**把稳定知识与可变实例拆开，并引入最小必要推理**。

---

## 2. 目标架构：四层 + 一个轻量推理机

```text
┌─────────────────────────────────────────────────────────┐
│  TBox（术语层，人工/弱 Agent 维护，低频）                  │
│  业务概念、指标族、过滤概念、互斥/覆盖/公式公理             │
├─────────────────────────────────────────────────────────┤
│  Binding（概念→货架覆盖根，半自动，中频）                   │
│  Advertising.covering = business_and_platform.ADV         │
├─────────────────────────────────────────────────────────┤
│  ABox（货架实例层，从 databp 自动同步，高频）              │
│  分类节点个体、父子、nameCn/nameEn/nameAlias、是否仍存在    │
├─────────────────────────────────────────────────────────┤
│  RealModel ABox（查数时按需拉取，不进长期本体库）           │
│  逻辑实体下的已部署指标个体                                │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              Lightweight Reasoner（Java 进程内）
              · 覆盖根上卷 / 剪枝
              · 互斥与禁止替代
              · Binding 一致性
              · （可选）公式候选归类
```

### 2.1 TBox 里放什么（只放稳定意图）

允许进 TBox 的，必须同时满足：

1. **意图稳定**：半年内名字/口径不应随货架改版而变（如「广告业务」「成功率」）。
2. **可被多节点复用**或作为高层覆盖根。
3. **需要人工语义判断**（同义词、互斥、公式），机器无法从货架结构可靠推出。

禁止进 TBox 的：

1. 每一个中低层货架文件夹的镜像副本。
2. 真实逻辑实体 UUID、真实 metricId、指标数值。
3. 会随运营改名/搬家的叶子分类（除非它本身就是稳定产品概念且 ID 已确认长期不变）。

### 2.2 ABox 里放什么（从货架自动来）

每个分类节点同步为一个个体，建议字段：

```text
shelf_node_id          # 点分 ID，主键
parent_id
name_cn / name_en
labels[]               # 来自货架 nameAlias* + name*
is_category            # true
last_seen_at
status                 # ACTIVE | MISSING
```

逻辑实体**不必**全量进本体库：它们由 `getNextLevelNode(covering_root)` 在问数时按需取得（与现有 Skill 一致）。若未来要做跨实体关系推理，再增量物化。

### 2.3 Binding 里放什么

```text
concept_id → covering_shelf_ids[]   # 1..N 个「不允许随便动」的高层覆盖根
priority / match_policy             # 广义查询用覆盖根；具体查询可落到更深 ABox 节点
```

**覆盖根定理（本方案的关键公理，对应你的突破点）：**

```text
若 Parent 是 Child 的祖先（点分 ID 前缀，或 ABox parent 链），
则 getNextLevelNode(Parent) 的逻辑实体集合 ⊇ getNextLevelNode(Child)。
因此：概念绑定到稳定 Parent 后，子树在货架上的增删改名搬家，
只要不脱离该 Parent，就不需要改 TBox / Binding。
```

### 2.4 「推理机」在本项目里具体算什么

不做通用 OWL DL 推理。第一版只实现下列**可测、可日志**的规则引擎（名称可叫 `OntologyReasoner`）：

| 推理任务 | 输入 | 输出 | 替代人工 YAML 的点 |
|---|---|---|---|
| 词项归类 | keyword | 命中的 TBox 概念（或 ABox 节点） | 中低层节点不再手写 aliases |
| 覆盖上卷 | 命中节点 id | 最近的 stable covering root | 子节点搬家后仍落到同一概念 |
| 最小覆盖根剪枝 | 多个候选 id | 互不祖先的最小集合 | 与现有 Skill 剪枝一致，上移到 Java |
| Binding 一致性 | covering id | OK / BROKEN + 告警 | 根被删才惊动人 |
| 口径互斥 | family/variant | 禁止互相替代的集合 | Phase B 政策形式化 |
| （可选）公式归类 | family + RealModel | FORMULA_CANDIDATE | 已有，保持 |

完整 OWL 工程若日后扩展，是把上述 TBox 导出为 `owl:Class` / `rdfs:subClassOf` / `owl:disjointWith`，ABox 导出为 named individuals；推理任务映射到分类与一致性检查。**产品不阻塞在这一步。**

---

## 3. 资源落地形态（给弱 Agent 的目录合同）

替换「整树 DataModel 副本手维」为：

```text
resources/ontology/metric-shelf/
├── tbox/
│   ├── concepts.yaml          # 业务概念 + aliases + covering 绑定
│   ├── metric-families.yaml   # 现有 Phase B，可原样迁入
│   ├── axioms.yaml            # 互斥、覆盖稳定声明、（后续）关系
│   └── filters.yaml           # 后续：黄金/健康等
├── abox/
│   └── shelf-nodes.json       # 同步产物（也可 DB 表）；禁止手改
└── sync/
    └── README.md              # 同步任务说明
```

### 3.1 `concepts.yaml` 最小示例

```yaml
version: 1
concepts:
  - id: Advertising
    name_cn: 广告
    name_en: Advertising
    aliases: [广告, 推广, 推广业务, ads, ad]
    stable: true
    covering_shelf_ids:
      - business_and_platform.ADV
    notes: "高层覆盖根；子树变更不改本条"

  - id: Celia
    name_cn: 小艺
    name_en: Celia
    aliases: [小艺, Celia, CEL]
    stable: true
    covering_shelf_ids:
      - business_and_platform.CEL
```

### 3.2 `axioms.yaml` 最小示例

```yaml
version: 1
axioms:
  - type: covering_includes_descendants
    description: "对任意 covering 根 R，查询实体范围用 getNextLevelNode(R) 一次即可"

  - type: stable_covering_root
    concept_id: Advertising
    shelf_id: business_and_platform.ADV

  - type: disjoint_metric_families
    members: [success_rate, success_count, request_count]

  - type: disjoint_variants
    family: latency
    members: [avg_latency, p95_latency, p99_latency]

  - type: disjoint_variants
    family: memory_usage_rate
    members: [min_memory_usage_rate, max_memory_usage_rate]
```

说明：`success_count` / `request_count` 若尚未建成独立 family，可先作为「禁止与 success_rate 互换」的符号，在 matcher 里显式拒绝。

### 3.3 ABox 同步算法（必须进程内，遵守云上铁律）

与 `locateNode` 相同约束：在 **databp 内**调用 `treeModelView()`，禁止 gateway HTTP 拉树。

```text
syncShelfABox():
  tree = treeModelView()
  seen = {}
  for each category node in tree (DFS):
    upsert ABox(node.id, parent, names, aliases_from_shelf)
    seen.add(node.id)
  for each abox id not in seen:
    mark MISSING
  for each Binding.covering_shelf_id:
    if MISSING or not in tree: emit ALERT "TBox binding broken"
  atomically swap ABox index
```

触发：应用启动全量 + 定时（如 5–15 min）+ 可选管理接口 `POST /ontology/syncShelf`。

货架侧已有的 `nameAliasCn/nameAliasEn` 进入 ABox `labels`，**中低层同义词优先靠货架维护**，不再抄进 Java `base.yaml`。

---

## 4. 改造后的 Phase A 运行时（具体算法）

`locateNode(keyword)` 重写为三通道，仍对外保持小结果集：

```text
Channel 1 — TBox 概念匹配（aliases / name，精确优先于包含）
  hit concept C
    → 取 covering_shelf_ids，校验 ABox ACTIVE
    → 返回候选：{ id: coveringId, matchType: CONCEPT_ALIAS, conceptId: C, ... }

Channel 2 — ABox 现场标签匹配（货架同步的 name/alias）
  hit node N
    → reasoner.rollupToStableCovering(N) 得到 R（若存在）
    → 广义意图：返回 R（并带 matchedNodeId=N 作解释）
    → 具体意图（keyword 与 N 名称高度贴合）：可返回 N，但 Skill 仍可用祖先覆盖策略
    → matchType: SHELF_LABEL

Channel 3 — 旧树搜索兜底（兼容现网）
  matchType: RAW_TREE_SEARCH
```

### 4.1 `rollupToStableCovering(N)`

```text
cur = N
while cur != null:
  if exists Binding(concept.stable=true, covering=cur): return cur
  if cur marked stable_covering_root in axioms: return cur
  cur = parent(cur)   # 点分 ID 去最后一段，或 ABox parent_id
return N   # 无稳定根则返回自身，并打低置信标记
```

### 4.2 与现有 Skill 的对齐

云端 Skill 已规定：Phase A 锁定后对该节点 `getNextLevelNode` 一次并穷举实体。  
本方案要求 Java 在广义业务说法上**尽量返回稳定覆盖根**，这样：

1. 子节点在货架上改名/搬家 → 只要仍在根下，**不必改 YAML，也不必改 Skill**。
2. `getNextLevel(父) ⊇ getNextLevel(子)` 被显式当成公理使用，而不是偶然实现细节。

Skill 侧仅需补充一句规程（后续改 `SKILL.md` / `agent-realmodel-query-rules.md`）：

```text
若 locateNode 返回 conceptId + covering 根，优先锁定 covering 根；
matchedNodeId 只作解释，不作为缩小扫描范围的依据（除非用户确认只要该子树）。
```

---

## 5. Phase B 如何「更像本体」（在已完成基础上加公理，不大拆）

保持 `resolveMetric(logicEntityId, metricPhrase)` 对外不变。内部增强：

1. Metric Family 继续作为 TBox 类；variant 作为子类或带属性的特化。
2. `disjoint_*` 公理进入 matcher：命中 success_rate 后，禁止再把同名附近的「成功次数」当成功率和稀。
3. 公式视为 **defined construction**（有条件的推导类）：仅当直接个体不存在、分子分母个体可唯一归类时，生成 `FORMULA_CANDIDATE`。
4. RealModel 指标 = 临时 ABox 个体；`name_contains` 是 **lexical realization 规则**，不是 TBox 定义本身——长期可把「中文名模式」收成 annotation，但匹配仍在 Java。

这是「完整 OWL」里 Class Assertion + DisjointClasses + 定义类的工程替代物。

---

## 6. 场景验证：货架可改 vs Phase A YAML 手维

### 6.1 场景陈述（来自需求）

1. 货架节点可在云端被改（增删改名、调整父子）。
2. Phase A YAML 若镜像整树，将被迫频繁维护。
3. 突破点：部分**高层节点不允许动**；`getNextLevel(父)` 信息覆盖 `getNextLevel(子)`。

### 6.2 本方案如何消解

| 货架变化 | 旧方案（整树 YAML） | 新方案（TBox 覆盖根 + ABox 同步） |
|---|---|---|
| 在 `ADV` 下新增子分类 | 可能要补 `base.yaml` + aliases | ABox 自动出现；问「推广」仍命中 Advertising→ADV；`getNextLevel(ADV)` 已含新实体 |
| 子分类改名 | 手改 YAML name/aliases | ABox 标签更新；TBox aliases 不动 |
| 子分类在 `ADV` 内搬家 | 手改 parent / path | ABox parent 更新；covering 仍是 ADV；上卷推理结果不变 |
| 子分类删掉 | 手删 YAML，易漏 | ABox MARK MISSING；不影响 Advertising 绑定 |
| 运营在货架上给节点加别名 | Java 侧不知情 | 同步进 ABox labels，Channel 2 直接可用 |
| 高层 `ADV` 本身被删/改 ID（罕见） | 静默错命中或空 | Binding 一致性 ALERT；人改 `covering_shelf_ids` 一行 |
| 新口语「推广业务」货架没有 | 必须写 YAML | **仍然**写在 TBox `Advertising.aliases`——这是唯一应人工维护的词表 |

### 6.3 维护责任切分（验收标准）

```text
人工 / 弱 Agent 只维护：
  · 稳定概念的 aliases
  · covering_shelf_ids
  · Metric Family 与互斥/公式公理

自动系统维护：
  · 整棵分类 ABox
  · Binding 健康检查

云端 Agent：
  · 不维护任何上述配置
  · 只消费 locateNode / resolveMetric 的状态与解释字段
```

**验收用例（建议弱 Agent 写成集成测）：**

1. TBox 仅含 Advertising→`business_and_platform.ADV` + aliases「推广」。  
2. 在测试树中于 ADV 下插入新子节点「广告新实验」，不改 YAML。  
3. `locateNode("推广")` 仍返回 ADV（CONCEPT_ALIAS）。  
4. `getNextLevelNode(ADV)` 含新实验下实体；对实体 `resolveMetric(...,"成功概率")` 行为与改树前一致。  
5. 将某子节点改名后，`locateNode(新名)` 走 SHELF_LABEL 并上卷到 ADV。  
6. 删除 ADV 后同步，出现 binding BROKEN 告警；`locateNode("推广")` 不得假装成功指向旧 ID。

若 1–6 通过，即证明：**完整 OWL 不是前提；覆盖公理 + ABox 同步已经解决你提的手维痛点。**

---

## 7. 和实施顺序（谁干什么）

### Phase C1 — 文档与契约（本仓库 / 规划 Agent）

1. 本文落地评审。  
2. 评审通过后改 `metric-ontology-discussion-summary.md` 增加「TBox/ABox 分层」结论指针。  
3. 再改 Skill / `agent-realmodel-query-rules.md`：锁定 covering 根的规程（C3 联调时再提交）。

### Phase C2 — Java 弱 Agent

1. 新增 `tbox/concepts.yaml` + `axioms.yaml`；把现有广告/小艺等高层 aliases **迁出**散落的整树副本。  
2. 实现 `ShelfABoxSync` + 内存索引。  
3. 重写 `locateNode` 三通道 + `rollupToStableCovering`。  
4. Binding 健康检查与启动/同步日志。  
5. 按 §6.3 写测试；遵守 `locatenode-handover.md` 云上铁律。  
6. **不要**删旧树兜底，直到云上回归通过。

### Phase C3 — 云端 Skill

1. 消费可选返回字段 `conceptId` / `matchType` / `matchedNodeId`。  
2. 广义查询锁定 covering 根；仅当用户确认子树时才缩小。  
3. 仍禁止在 Skill 复制 aliases。

### Phase C4 — 可选 OWL 导出（真要「标准完整 OWL」时）

1. 用同一 TBox 生成 OWL：Concept→Class，covering→annotation，disjoint→`owl:disjointWith`。  
2. ABox 快照可导出 RDF 供 Protégé 目视检查。  
3. 线上推理仍用 Java 轻量引擎（延迟、依赖、云上约束更可控）。  
4. 仅当出现跨大量公理的一致性需求时，再评估嵌入 OWL API reasoner。

---

## 8. 明确不做什么（防范围膨胀）

1. 不把货架整树重新手抄回 `DataModel/**/base.yaml`。  
2. 不上图数据库 / 独立本体服务（除非 databp 进程内方案被证伪）。  
3. 不让云端 Agent 读 YAML 或跑推理。  
4. 不用推理机「猜」被删的 covering 根。  
5. 不在第一版引入完整 SWRL/SPARQL 查询栈。  
6. 逻辑实体全量物化进 ABox 不做（成本高，现网 `getNextLevelNode` 已覆盖问数需要）。

---

## 9. 与「完整 OWL 工程」的对照表

| OWL 工程概念 | 本方案落地物 | 何时需要真 OWL |
|---|---|---|
| TBox | `concepts.yaml` + `metric-families.yaml` + `axioms.yaml` | 需要跨团队用 Protégé 评审公理时 |
| ABox | `shelf-nodes` 同步索引 + 按需 RealModel | 需要对外联邦知识图谱时 |
| Reasoner | `OntologyReasoner` 规则集 | 公理数量与交互复杂到自研引擎错误率不可控时 |
| Annotation / label | aliases + 货架 nameAlias | 已够用 |
| Ontology governance | 同步告警 + version 字段 + 发布流程 | 多环境多版本并行时加强 |

---

## 10. 决策请求（给人）

请确认以下默认决策，弱 Agent 才可开工：

1. **停维整树节点 YAML**，改为「少量稳定概念 + covering 绑定」，是否同意？  
2. ABox 同步间隔与是否暴露 `syncShelf` 管理接口？  
3. `locateNode` 对外是否新增 `conceptId/matchType/matchedNodeId`（建议加，旧字段保留）？  
4. Phase B 是否本轮只加 disjoint 公理、不动接口签名？（建议是）

确认前，弱 Agent 不应大规模删现有 `ontology/metric-shelf/DataModel` 副本。
