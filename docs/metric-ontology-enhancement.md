# 指标增强方案：本体语义层接入智能问数

> 目标：让不熟悉货架数据模型命名体系的用户，用口语化问题也能定位到正确的分类节点 → 逻辑实体 → 指标，并为后续「取数画图」铺路。  
> 原则：**本体是地图，不是仓库**——业务语义与映射放本体；树数据、指标定义、时序数值仍走 databp / 数据库。

## 1. 问题拆解

当前主链路依赖 `locateNode(keyword)` 的**名字包含匹配**。由此产生三层缺口：

| 缺口 | 现象 | 根因 |
|---|---|---|
| G1 节点定位 | 用户说的词不在分类节点名里 → `locateNode` 空 | 口语概念 ≠ 货架分类命名 |
| G2 实体选择 | 命中分类后，其下逻辑实体很多，不知哪个承载目标指标 | 实体名与用户说法可能完全不同 |
| G3 指标对齐 | 同一口语意图可能对应多个指标（不同实体、不同口径/SQL） | 指标正式名/描述与口语不对齐；需要语义消歧而非字符串相等 |

现有 Stage 1「同义词扩展」只能覆盖浅层别名，**无法表达「概念→节点/实体/指标」的结构化映射，也无法解释多候选冲突**。

## 2. 方法论对齐（本体 + Agent）

参考「本体遇上 Agent」上下篇的核心结论，落到本项目：

1. **本体 = 语义层（TBox + 精选映射），不是第二份货架库（ABox 不全量灌树）**。
2. **Agent 架构不变**：仍是意图路由 + MCP 工具调用；变化是在必要时查阅/推理本体，补 LLM 不擅长的业务语义。
3. **推理机按需**：别名查找、ID 映射用**查阅**；跨层归属、意图多重归类、消歧规则用**推理/声明式分类**。
4. **工具变薄、语义变厚**：不给每种口语查询新写一个 tool；用「一个本体查询入口 + 既有 databp 工具」。
5. **从小闭环起步**：先打通「口语 → 候选绑定 → 既有 API 验证 → 可解释结果」，再扩展取数画图与全量治理。

## 3. 本体在本项目中的定位

```text
用户口语问题
    │
    ▼
metric-query Skill（意图 / 抽取）
    │
    ├─► 本体语义层（本仓库 ontology/metric-shelf）
    │     · 业务概念 / 口语别名 / 上下位
    │     · 概念 → 分类节点 / 逻辑实体 / 指标 的映射
    │     · 指标意图类型与消歧线索（声明式，非硬编码业务样例）
    │
    └─► databp MCP（事实层）
          · locateNode / getNextLevelNode / getLogicEntityDefineInfo
          · getLogicEntityRealModel（已部署指标 SQL）→ 后续执行取数 → 画图
```

| 放进本体 | 不放进本体 |
|---|---|
| 业务概念、别名、同义/上下位 | 模型树全量节点 |
| 概念到货架 ID 的映射注解 | 指标时序数值 |
| 指标意图类型、消歧规则（TBox） | SQL 执行结果、图表二进制 |
| 「如何从业务语言走到 API」的查询契约 | 取代 locateNode 的服务端搜索 |

## 4. 本体模型（TBox 积木）

完整 schema 见 `ontology/metric-shelf/schema.ttl`；运行时可读清单见 `concepts.yaml`。

### 4.1 核心类

| 类 | 含义 |
|---|---|
| `BusinessConcept` | 用户业务语言中的概念（可口语、可正式） |
| `CategoryBinding` | 绑定到货架**分类节点**（点分 ID） |
| `LogicEntityBinding` | 绑定到货架**逻辑实体**（UUID） |
| `MetricBinding` | 绑定到具体**指标**（通常挂在某逻辑实体下） |
| `MetricIntent` | 指标意图类型（如成功率类、占比类、次数类……），用于口语→口径粗分桶 |
| `Utterance` | 一条用户可能说法（字面别名） |

### 4.2 关键关系

| 属性 | 语义 | 传递？ |
|---|---|---|
| `hasUtterance` | 概念/意图拥有口语说法 | 否 |
| `synonymOf` | 同义（对称） | 否 |
| `broaderThan` / `narrowerThan` | 上下位 | **是**（传递） |
| `mapsToCategory` | 概念 → 分类绑定 | 否 |
| `mapsToLogicEntity` | 概念 → 逻辑实体绑定 | 否 |
| `mapsToMetric` | 概念/意图 → 指标绑定 | 否 |
| `belongsToEntity` | 指标绑定 → 所属逻辑实体 | 否 |
| `underCategory` | 实体绑定 → 所属分类 | 否 |
| `hasIntent` | 指标绑定 → 意图类型 | 否 |
| `disambiguationHint` | 消歧线索（描述关键词、SQL 语义特征、字段口径提示） | 否 |

### 4.3 注解映射（Schema Mapping 思路）

与文章中 `mapsToTable` / `mapsToColumn` 同构，这里映射到货架 API 契约：

| 注解 | 用途 |
|---|---|
| `shelfCategoryId` | 点分分类 ID，可直接喂给 `getNextLevelNode` |
| `shelfLogicEntityId` | 逻辑实体 UUID |
| `parentOperObjId` | 调 `getLogicEntityDefineInfo` 所需 |
| `metricNameEn` / `metricNameCn` | 与 defineInfo 返回对齐，用于 Stage 5 精确过滤 |
| `locateKeywords` | 当尚无可靠 ID 时，推荐给 `locateNode` 的关键词集合 |

**Agent 只说业务概念；具体 ID/列名/关键词由本体注解翻译。** ID 变更时改本体，不改 Skill 主流程代码。

### 4.4 消歧：声明式归类，而非散落 if/else

当一个口语问题命中多个 `MetricBinding` 时，不在 Skill 里写死业务分支，而在本体声明：

- 每个 `MetricBinding` 挂 `hasIntent` + `disambiguationHint`
- 可选定义等价类（如「成功率类意图」）供推理机或规则引擎做多标签归类
- Agent 输出候选时**必须带回判定依据**（命中了哪条 utterance / hint / 映射路径）

多重候选是默认情况：本体不要求互斥；Skill 负责排序与向用户呈现。

## 5. 融入现有 Skill 的工作流

在 `skills/metric-query` 中插入/强化阶段（详见 SKILL.md 与 `references/ontology.md`）：

```text
Stage 0  意图分类（扩展：口语指标定位 / 数值取数）
Stage 1  概念抽取（目标对象 + 指标意图 + 筛选条件）
Stage 1.5  本体锚定（NEW）
           · 用口语查 utterance / synonym / broader-narrower
           · 得到 Category/Entity/Metric 候选绑定 + locateKeywords
           · 记录可解释路径
Stage 2  定位节点
           · 优先用本体给出的 shelfCategoryId
           · 否则用 locateKeywords / 语义增强词调 locateNode
Stage 3  剪枝去重（不变）
Stage 4  取逻辑实体
           · 若有 LogicEntityBinding，优先对齐 UUID / 名称
           · 否则按名称+本体 hint 相关性过滤
Stage 5  取指标定义
Stage 5.5  条件筛选（level/type 等，不变）
Stage 5.7  指标语义对齐与消歧（NEW）
           · 用 MetricIntent + description/hint 对口语意图打分
           · 多候选：排序 + 解释；高歧义时反问用户
Stage 6  呈现
Stage 7  取数画图（启用路径）
           · getLogicEntityRealModel → 解析已部署 SQL
           · 执行查询（独立数据通道，后续接入）→ 按 output-format 绘图
```

### 失败回退

| 情况 | 行为 |
|---|---|
| 本体无命中 | 回退现有 Stage 1 同义词 + locateNode；结果注明「未经本体锚定」 |
| 有概念无 ID | 用 `locateKeywords` 走 locateNode，命中后再用 Stage 4/5.7 收敛 |
| 多候选接近 | 列出 Top-K，附映射路径与 hint，请用户确认后再取数 |
| 本体映射与 API 不一致 | **以 API 现场返回为准**，标记映射失效，不编造 |

## 6. 落地阶段（小闭环 → 扩展）

### Phase A — 语义查阅闭环（本 PR 交付）

- TBox schema + YAML 运行时清单模板
- Skill 接入 Stage 1.5 / 5.7 的操作规程
- 修正 `getLogicEntityRealModel` 能力描述
- **不**把评测用口语样例写入本体或 Skill（避免污染测试）

### Phase B — 映射治理

- 由业务/数仓同学按 `concepts.yaml` 规范录入高价值概念与绑定
- 建立「映射失效」反馈：Agent 发现 ID 404 / 名称对不上时回写待审项

### Phase C — 可选推理增强

- 对 `broaderThan` 闭包、MetricIntent 多重归类引入 owlready2 / 图推理（或轻量规则引擎）
- 仅在查阅不够时启用；日常别名查找仍走快路径

### Phase D — 数值与绘图

- 固定：`getLogicEntityRealModel` 返回已部署指标 SQL
- 增加受控 SQL 执行通道（权限、限流、只读）
- Skill Stage 7 按 `output-format.md` 生成可下载图

## 7. 非目标与风险

- **非目标**：用本体替换 databp；把全树灌进 OWL；让 LLM 自由改写 SQL。
- **风险**：映射质量决定上限；无治理会变成第二套脏数据。缓解：小范围高价值概念、API 校验、失效标记。
- **测试纪律**：方案/Skill/本体种子中**禁止写入具体评测问句与其标准答案路径**；评测集外置，仅用于离线评估。

## 8. 仓库产物索引

| 路径 | 内容 |
|---|---|
| `docs/metric-ontology-enhancement.md` | 本方案 |
| `ontology/metric-shelf/schema.ttl` | OWL/Turtle TBox |
| `ontology/metric-shelf/concepts.yaml` | Agent 可直接查阅的映射清单（模板，无评测样例） |
| `ontology/metric-shelf/README.md` | 维护规范 |
| `skills/metric-query/SKILL.md` | 工作流（含 1.5 / 5.7 / Stage 7 启用说明） |
| `skills/metric-query/references/ontology.md` | Agent 侧本体使用细则 |
| `skills/metric-query/references/tools.md` | 工具契约（含 RealModel 更新） |
