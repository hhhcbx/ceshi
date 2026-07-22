---
name: metric-query
description: 智能问数——在货架数据模型中按用户描述定位分类节点、获取逻辑实体并查询指标定义；借助本体语义层做口语概念锚定与指标消歧；支持按级别/类型筛选，并在需要时经 getLogicEntityRealModel 取已部署 SQL 查数画图。当用户想查询某个业务/分类/对象相关的指标、字段、逻辑实体或指标数值时使用。
---

# 智能问数：货架数据模型指标查询

## 何时触发

当用户想「查某个业务/分类相关的指标、字段、逻辑实体」，或用**口语化指标说法**提问（不一定等于货架节点名/指标正式名），例如：

- 「帮我找小艺的指标」
- 「给我所有小艺的黄金指标」
- 「小艺_翻译有哪些指标」
- 「数据库相关的实体和指标有哪些」
- 「某某业务的成功率大概看哪个指标？」（口语意图，需本体锚定 + 消歧）

## 数据模型心智模型（必须先理解）

- 树分两类节点：
  - **分类节点（骨架，导航用）**：ID 是**点分字符串**，如 `business_and_platform.CEL`（小艺）、`business_and_platform.CEL.AIVision`（AI Vision）。
  - **逻辑实体/运维对象（数据，目标）**：ID 是 **UUID**，如 `0b6b22bf-...`。
- **点分 ID 天然编码了层级**：`A` 是 `B` 的祖先 ⟺ `B` 以 `A + "."` 开头。
  例：`business_and_platform.CEL` 是 `business_and_platform.CEL.AIVision` 的祖先。这是**去重和选节点的核心依据**。
- 指标（metrics）挂在**逻辑实体**上，要经「分类 → 逻辑实体 → 指标定义」三跳拿到。
- **已确认**：`getNextLevelNode(分类)` 返回该分类**及其全部后代分类**下的所有逻辑实体（递归）。因此对祖先节点调用一次即可覆盖所有后代，绝不能对祖先与后代重复调用。
- **本体语义层**（`ontology/metric-shelf`）解决「口语 ≠ 货架命名」：它是地图不是仓库，不替代 databp。详见 [references/ontology.md](references/ontology.md) 与 `docs/metric-ontology-enhancement.md`。

工具入参、出参细节见 [references/tools.md](references/tools.md)。  
输出格式与图表规范见 [references/output-format.md](references/output-format.md)。  
本体锚定规程见 [references/ontology.md](references/ontology.md)。

## 核心工作流

### Stage 0 · 意图分类

先判断用户问题属于哪类，再路由：

| 意图 | 特征 | 路由 |
|---|---|---|
| A. 指标定义查询 | 「找 X 的指标」「X 有哪些指标」 | Stage 1 → 6（含 1.5 / 5.7） |
| B. 指标筛选查询 | 「X 的黄金指标」「X 的复合指标」——带级别/类型等限定词 | 同 A，Stage 5.5 必须执行筛选 |
| C. 指标数值/趋势查询 | 「近一个月 X 的 … 趋势 / 有多少」——要**数值**或**图** | 先走定义对齐（含 1.5 / 5.7）；选定指标后走 Stage 7：`getLogicEntityRealModel` → 执行 SQL → 按 output-format 绘图。多候选时先消歧再取数 |
| D. 结构浏览 | 「有哪些分类」「模型树长什么样」 | 用 `getModelTree` / `locateNode` 返回结构，不下钻实体 |
| E. 字段查询 | 「X 有哪些字段」 | 同 A，Stage 5 提取 `fields` |
| F. 口语指标定位 | 用户用业务口语描述指标，但未必说得出节点/实体/正式指标名 | **必须**走 Stage 1.5；Stage 5.7 消歧；其余同 A 或 C |
| G. 与数据模型无关 | 闲聊、其他任务 | 不使用本 skill |

多意图组合（如「黄金指标的趋势」）按 B + C 叠加；口语 + 要数值按 F + C 叠加。

### Stage 1 · 概念抽取 + 语义增强

1. 从用户问题中抽取：
   - **目标概念**（业务对象/域）与**粒度**（广义覆盖 vs 具体对象）
   - **指标说法** `metric_phrase`（用户怎么称呼想看的指标；可为空）
   - **筛选条件**（级别、类型等），留给 Stage 5.5；映射见 output-format.md
2. **浅层语义增强**：为概念生成同义/近义候选词（中英）。这是本体未命中时的兜底，不能替代 Stage 1.5。
3. 得到关键词候选 + `metric_phrase`，进入 Stage 1.5。

### Stage 1.5 · 本体锚定（口语 → 货架绑定）

**严格按 [references/ontology.md](references/ontology.md) 执行。** 摘要：

1. 查阅 `ontology/metric-shelf/concepts.yaml`（`concepts` + `metric_intents`）。
2. 用目标概念匹配 `labels` / `utterances`，并做 synonym / 有限上下位扩展。
3. 用 `metric_phrase` 匹配意图桶，得到 `intent_ids`。
4. 汇总 `category_ids`、`logic_entities`、`metric_candidates`、`locate_keywords` 与 `explain`。
5. 无命中则标记 `ontology_grounding.empty=true`，不报错，继续 Stage 2。

> 纪律：不要把用户本轮的「标准答案路径」写进本体文件，除非用户明确要求做映射治理录入。

### Stage 2 · 定位候选节点

- 若锚定包有可靠 `category_ids`：优先使用（可做存在性校验），再视需要用 `locate_keywords` 补召回。
- 否则：对关键词候选（含本体 `locate_keywords` + Stage 1 增强词）调用 `locateNode(keyword)`，合并候选集。
- **只保留分类节点（点分 ID）** 用于后续导航；UUID 实体节点先忽略（Stage 4 覆盖）。
- 若用户没给明确概念、需要先了解顶层分类，才用 `getModelTree()` 兜底。

### Stage 3 · 节点筛选与去重（最关键，防重复/防爆量）

先按**用户粒度**决定策略：

- **广义查询（要覆盖整个概念）**：做「**最小覆盖根**」剪枝——
  - 在候选分类 ID 集合中，**若某节点的 ID 是另一节点 ID 的后代（前缀关系），删掉后代，只留祖先**。
  - 依据：`getNextLevelNode` 是递归的，查祖先已完全覆盖后代，再查后代必然产生重复数据。
  - 例：候选 `...CEL`、`...CEL.AIVision`、`...CEL.AIVision.celia_photo_editing` → 只保留 `...CEL`（小艺）。

- **具体查询（只要某个具体对象）**：
  - 选**名字与用户短语最贴合**的那个节点（优先精确/最长匹配），**只用它**，不要把它的父级祖先加进来。
  - 例：用户要「小艺_翻译」→ 选 `...CEL.AIVision.celia_translation` 这一个，忽略 `...CEL`。

- **多关键词去重**：多个关键词若命中重叠节点，先合并再按上面规则剪枝，确保**每个最终节点只查一次**。

剪枝后得到一个**去重的目标分类节点列表**。

### Stage 4 · 取逻辑实体

- 对每个目标分类节点调 `getNextLevelNode(id, type="CATEGORY")`。
- 汇总 `publishedData` 里的逻辑实体，保留每个实体的 `id` + `parentOperObjId` + 名称。
- **优先对齐**本体锚定的 `logic_entities`（UUID 或名称）。
- 其余按实体名与用户概念 / 本体 hints 的相关性过滤。
- **量控**：实体很多（如 >20）时按相关性排序，优先最相关若干；必要时先给用户确认。

### Stage 5 · 取指标定义

- 对筛选后的每个逻辑实体调 `getLogicEntityDefineInfo(id, parentOperObjId)`。
- 从 `publishedData.metrics` 提取指标；意图为字段查询（E）时提取 `publishedData.fields`。

### Stage 5.5 · 条件筛选（意图 B 必须执行）

- 若 Stage 1 抽取到了筛选条件（如「黄金指标」），在**汇总后的指标列表**上执行过滤，再进入 5.7 / 呈现。
- 条件词到字段值的映射见 output-format.md。匹配时**大小写不敏感**。
- 若筛选后结果为空：报告总数与条件，并列出实际 level/type 分布。
- 映射表未覆盖的说法：按最接近规范值猜测并**在回答中说明**。

### Stage 5.7 · 指标语义对齐与消歧（口语指标必须执行）

当存在 `metric_phrase` 或意图 F/C，或本体给出了 `metric_candidates` / `matched_intents`：

1. 按 ontology.md 的打分信号排序（名称对齐、意图 hints、描述共现、实体是否锚定）。
2. 唯一领先 → 主答案 + 可选相关附录。
3. 多个接近 → **消歧列表**（路径、实体、指标、依据）；意图 C 必须先确认再 Stage 7。
4. 全低分 → 说明未可靠对齐，给出最相关候选与换词建议。

可解释性要求：每条入选/落选理由能追溯到 utterance、intent、hint 或名称匹配，**禁止**无依据的武断选择。

### Stage 6 · 汇总与呈现

**严格遵循 [references/output-format.md](references/output-format.md)。** 核心要求：

- 指标默认字段：`measureType`、`nameCn`、`nameEn`、`description`、`type`、`level`、`tag`；全空列省略。
- Markdown 表格，按「分类路径 → 逻辑实体」分组。
- 信息头：命中路径、实体名、指标总数、筛选条件；若经过本体锚定，增加一行**锚定摘要**（命中概念/意图，或注明未经本体锚定）。
- 消歧场景用 output-format 的「多候选消歧」模板。
- 结果为空：如实说明，并建议换词（可触发增强或请用户补充业务域）。

### Stage 7 · 取指标数值与画图

前置：已通过 Stage 5.7 得到**唯一**目标指标（或用户从消歧列表中确认）。

1. `getLogicEntityRealModel(逻辑实体 id)` → 找到该指标**已部署 SQL**。
2. 在环境提供的只读数据通道执行 SQL（含时间范围等用户条件，若 SQL/通道支持参数则注入；不支持则说明限制）。
3. 按 output-format.md 图表规范生成可下载图；失败则表格兜底，并报告错误。
4. 无 SQL / 执行失败：返回定义信息 + 原因，**不编造数值**。

## 通用规则

- **层级判断只用点分 ID 前缀**，不用 `locateNode` 的 `depth`（该字段目前不可靠）。
- **每个目标节点只调一次 `getNextLevelNode`**，靠 Stage 3 剪枝保证。
- **`getLogicEntityDefineInfo` 的两个入参都来自 `getNextLevelNode` 返回**，不要自己拼。
- **控量优先**：任何一步预感数据量大时先收敛再深入。
- **本体优先于瞎猜，API 优先于陈旧映射**。
- 找不到就如实说 + 建议换词，不要编造节点、ID、指标或数值。
- **评测纪律**：不得把评测用例的标准答案路径写入 Skill、方案或 `concepts.yaml`。

## 完整示例（「给我所有小艺的黄金指标」）

1. **Stage 0**：意图 = B，筛选条件 =「黄金」。
2. **Stage 1**：概念=「小艺」，粒度=广义；增强候选=[小艺, Celia]；`metric_phrase` 空；条件映射：黄金 → `level=GOLD`。
3. **Stage 1.5**：查阅本体；若无「小艺」映射则 `empty=true`，继续用增强词。
4. **Stage 2**：`locateNode("小艺")` → `...CEL`（小艺）、`...CEL.AIVision` 等。
5. **Stage 3**：最小覆盖根 → 只留 `business_and_platform.CEL`。
6. **Stage 4**：`getNextLevelNode("business_and_platform.CEL", "CATEGORY")` → 逻辑实体集。
7. **Stage 5**：逐个 `getLogicEntityDefineInfo` → `metrics`。
8. **Stage 5.5**：过滤 `level == GOLD`。
9. **Stage 5.7**：无 `metric_phrase`，跳过或仅作轻量排序。
10. **Stage 6**：按 output-format 分组出表，并注明筛选条件。
