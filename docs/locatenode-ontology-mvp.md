# locateNode 本体定位 MVP 代码侧实施方案

## 1. 文档定位

本文不是给云端问数 Agent 的 Skill 规则，而是写给 **Java 代码侧弱 Agent / 工程实现者** 的实施文档。

这里的角色边界必须明确：

1. **Java 侧弱 Agent**：在 IDEA 中辅助修改 databp Java 代码、resources YAML、单测和本地验证。它处在内部开发环境里，能访问 Java 工程、内部依赖、已有 `resources/DataModel` 目录和相关服务代码。
2. **云端 Agent**：databp 部署到云上并刷新 MCP/Swagger 后，另一个 Agent 调用 `locateNode`、`getNextLevelNode`、`getLogicEntityRealModel` 等接口完成问数编排。
3. **本文只管 Java 侧**：目标是改造 `locateNode` 的代码和 resources 中的本体 YAML，让 `locateNode` 融入本体语义层。
4. **云端 Agent 的调用规程另写**：`docs/agent-realmodel-query-rules.md` 才是给云端 Agent Skill/规则看的文档，两者不能混在一起。

因此，本文后续所有“Agent”如无特别说明，均指 **代码侧弱 Agent**。

## 2. 背景与目标

当前智能问数链路中，云端 Agent 已经可以调用 databp 暴露出的货架接口，但用户表达与货架节点名称之间仍存在语义鸿沟。例如：

- 用户说 `ads` / `ad` / `推广`，货架中可能叫「广告」。
- 用户说「广告点击」，真实节点 ID 可能是 `business_and_platform.ADV.AdvertiserRebate.pps_click`。
- 同一路径中可能出现多个同名或近似节点，例如上层「广告」与子层「广告」。
- resources 中已有节点快照，但它可能落后于真实货架，不应把它当成绝对真相。

本阶段不新增多个 databp 对外接口，也不把 `locateNode` 改成一站式问数接口，而是在 **Java 侧改造既有 `locateNode`**：

```text
locateNode(keyword)
  ↓
先查 resources 中的本体语义层 / 节点概念配置
  ↓
返回候选货架分类节点 ID、路径、命中原因、置信度
  ↓
未命中时走旧版树搜索兜底
```

MVP 目标：

1. 让 `locateNode` 能识别口语化、英文、缩写和业务别名。
2. 基于 resources 中已有 DataModel 节点快照，快速生成/维护第一版节点本体数据。
3. 允许本体数据与真实货架存在短期不一致，先跑通流程，后续再同步补齐。
4. 保持 `locateNode` 职责单一：只做节点定位，不查逻辑实体、不查 RealModel、不执行 SQL。
5. 返回结构要对云端 Agent 友好：必须包含后续调用 `getNextLevelNode` 需要的真实分类 ID，以及用于消歧的路径和命中原因。

## 3. 输入现状：resources/DataModel 已有节点数据

现在 Java 项目的 resources 中已经有一份简要本体/节点数据，路径形态类似：

```text
resources/DataModel/
  <node-folder>/
    base.yaml
    <child-node-folder>/
      base.yaml
      <grandchild-node-folder>/
        base.yaml
```

每个节点一个文件夹：

1. 节点自身信息放在该目录的 `base.yaml`。
2. 如果它有子节点，就继续在该目录下嵌套子文件夹。
3. 每个 `base.yaml` 通常包含：
   - `id`
   - `parent_category_id`
   - `name_cn`
   - `name_en`
   - `description`
4. 根据节点不同，`base.yaml` 还可能包含：
   - `version`
   - `owner`
   - `offering`
   - 其他已有字段

重要限制：

1. `resources/DataModel` 是别人已有的节点快照，可能不完全等于当前真实货架。
2. 例如「广告点击」真实 ID 是：

```text
business_and_platform.ADV.AdvertiserRebate.pps_click
```

但当前 resources 可能只记录到：

```text
business_and_platform.ADV.AdvertiserRebate
```

3. 这不是说叶子节点不该记录，只是资源数据还没完全更新。
4. MVP 阶段不要因为数据不全而阻塞实现；先复制一份，在副本上补充/修正关键节点，跑通流程。
5. 后续再建立同步机制或人工维护流程，使 resources 本体数据逐步贴近真实货架。

## 4. 资源目录改造策略

### 4.1 不直接大改原始 DataModel

不要直接在原始 `resources/DataModel` 上做不可逆大规模改写。建议复制一份作为 `locateNode` 本体运行时数据源，例如：

```text
src/main/resources/ontology/metric-shelf/DataModel/
```

或按 Java 项目实际 resources 根目录放置：

```text
resources/ontology/metric-shelf/DataModel/
```

复制策略：

1. 第一版从已有 `resources/DataModel` 整体复制。
2. 在副本中补充本轮 MVP 必需的缺失节点和别名信息。
3. 原始 `resources/DataModel` 保留为上游快照，不作为本次改造的直接编辑目标。
4. 如果 Java 工程已有更合适的配置目录规范，优先遵循工程现有约定，但必须保证和原始 DataModel 分离。

### 4.2 在副本 base.yaml 上扩展本体字段

现有 `base.yaml` 字段继续保留，不破坏原字段。新增字段建议放在 `ontology` 或 `semantic` 命名空间下，避免污染原始字段语义。

示例：

```yaml
id: business_and_platform.ADV.AdvertiserRebate.pps_click
parent_category_id: business_and_platform.ADV.AdvertiserRebate
name_cn: 广告点击
name_en: Advertising Click
description: 广告点击相关分类节点。

ontology:
  concept_id: advertising_click
  aliases:
    - 广告点击
    - 点击广告
    - ad click
    - ads click
    - pps click
  confidence: HIGH
  tags:
    - advertising
    - click
  match_reason: 广告点击真实货架分类节点。
```

字段说明：

| 字段 | 说明 |
|---|---|
| `ontology.concept_id` | 稳定概念 ID，便于命中结果解释和后续维护 |
| `ontology.aliases` | 用户可能输入的口语、英文、缩写、业务别名 |
| `ontology.confidence` | 该节点作为语义命中的默认置信度：`HIGH` / `MEDIUM` / `LOW` |
| `ontology.tags` | 粗粒度语义标签，可用于排序和后续扩展 |
| `ontology.match_reason` | 给云端 Agent 和人看的命中解释 |

### 4.3 缺失叶子节点先手工补齐关键样例

如果副本中缺少 MVP 关键叶子节点，允许先新增目录和 `base.yaml`。

广告点击示例：

```text
ontology/metric-shelf/DataModel/business_and_platform/ADV/AdvertiserRebate/pps_click/base.yaml
```

`base.yaml`：

```yaml
id: business_and_platform.ADV.AdvertiserRebate.pps_click
parent_category_id: business_and_platform.ADV.AdvertiserRebate
name_cn: 广告点击
name_en: pps_click
description: 广告点击节点，MVP 阶段根据真实货架 ID 手工补齐。

ontology:
  concept_id: advertising_click
  aliases:
    - 广告点击
    - 点击广告
    - 广告 click
    - ad click
    - ads click
    - pps click
  confidence: HIGH
  tags:
    - advertising
    - click
  match_reason: 手工补齐的广告点击真实货架分类节点。
```

注意：

1. 真实 `id` 必须写完整，不要根据目录名或中文路径动态拼。
2. `parent_category_id` 尽量使用真实父分类 ID；如果上游快照暂时缺失父节点，也要在注释或说明中标出待同步。
3. MVP 可以先补少量关键节点，不要求一次性修完整棵树。

## 5. locateNode 代码改造边界

### 5.1 应该做什么

新版 `locateNode` 负责：

1. 接收短定位词，例如「广告」「ads」「广告点击」「pps click」。
2. 加载 resources 中的本体 DataModel 副本。
3. 将目录树中的每个 `base.yaml` 解析成可搜索节点。
4. 用 `id/name_cn/name_en/description/ontology.aliases/ontology.tags` 等字段匹配 keyword。
5. 返回候选分类节点的真实 `id`、中英文名、中文路径、命中类型、命中字段、置信度和原因。
6. 本体副本未命中时，保留旧版树搜索作为兜底。

### 5.2 不应该做什么

新版 `locateNode` 不负责：

1. 不解析完整多轮对话。
2. 不判断用户最终是查定义、查数值、查趋势还是对比。
3. 不调用 `getNextLevelNode`。
4. 不调用 `getLogicEntityRealModel`。
5. 不调用 `getLogicEntityDefineInfo`。
6. 不拼 SQL、不执行 SQL。
7. 不返回指标真实值。
8. 不把所有具体指标都写入节点本体。

### 5.3 旧搜索兜底不能删除

本体数据可能不全，所以旧版树搜索必须保留作为兜底：

```text
1. ontology DataModel 命中 → 返回本体候选，并可合并旧搜索补充候选。
2. ontology DataModel 未命中 → 执行旧 locateNode 树搜索逻辑。
3. 两边都未命中 → 返回空 data，不要编造节点。
```

## 6. DataModel loader 设计

### 6.1 启动加载 + 内存缓存

建议新增一个 loader/service，在服务启动或首次调用时读取本体 DataModel 副本：

```text
resources/ontology/metric-shelf/DataModel
  ↓
递归扫描所有 base.yaml
  ↓
解析为 OntologyNode 列表
  ↓
构建 searchable index
```

MVP 可以先做简单内存缓存，不需要引入外部数据库或图数据库。

### 6.2 OntologyNode 建议结构

Java 侧可定义类似结构：

```java
class OntologyNode {
    String id;
    String parentCategoryId;
    String nameCn;
    String nameEn;
    String description;
    String pathCn;
    String conceptId;
    List<String> aliases;
    String confidence;
    List<String> tags;
    String matchReason;
}
```

`pathCn` 可以在加载时通过父子关系或目录遍历顺序计算：

```text
业务平台 > 广告 > 广告 > 广告点击
```

如果无法可靠计算中文路径，也可以先返回当前节点名和 ID，但应尽量补齐路径，方便云端 Agent 消歧。

### 6.3 YAML 解析容错

弱 Agent 实现时要注意：

1. 单个 `base.yaml` 解析失败，不要导致整个服务不可用；至少要记录日志并跳过坏文件。
2. 缺少 `ontology` 字段的节点仍可被索引，只是只能用 `id/name_cn/name_en/description` 匹配。
3. 缺少 `name_en`、`description`、`owner` 等非关键字段时不要失败。
4. 缺少 `id` 的节点不能作为有效候选，应记录 warning 后跳过。
5. 启动日志中打印加载节点数、带 aliases 节点数、跳过节点数。

## 7. 匹配规则

### 7.1 归一化

匹配前对 keyword 和候选字段做统一归一化：

1. trim 前后空白。
2. 英文统一小写。
3. 多个空白合并为一个空格。
4. 中文保留原文。
5. 可选：把 `_`、`-`、`.` 视为弱分隔符，用于英文编码匹配。

### 7.2 匹配字段

按以下字段建立候选：

1. `id`
2. `name_cn`
3. `name_en`
4. `ontology.aliases`
5. `ontology.tags`
6. `description`，低优先级，仅做兜底

### 7.3 匹配优先级

建议顺序：

1. `keyword` 与 `id` 精确匹配。
2. `keyword` 与 `name_cn/name_en` 精确匹配。
3. `keyword` 与 `ontology.aliases` 精确匹配。
4. `keyword` 与 `ontology.tags` 精确匹配。
5. `keyword` 包含 alias，或 alias 包含 `keyword`。
6. `keyword` 与 `name_cn/name_en` 包含匹配。
7. `description` 包含匹配。
8. 本体 DataModel 未命中时，走旧版树搜索。

### 7.4 排序规则

排序建议：

1. 精确匹配优先于包含匹配。
2. `ontology.confidence=HIGH` 优先于 `MEDIUM/LOW`。
3. 更具体的节点可以排在更前，但不要静默丢弃同名父节点。
4. `id` 更长通常代表更深层节点，可作为“更具体”的弱信号。
5. 如果多个候选同为高置信，全部返回，交给云端 Agent 结合用户问题或追问消歧。

## 8. locateNode 返回结构建议

旧字段可以扩展，但返回中必须包含云端 Agent 后续调用需要的分类 ID。

建议结构：

```json
{
  "data": [
    {
      "id": "business_and_platform.ADV.AdvertiserRebate.pps_click",
      "nameCn": "广告点击",
      "nameEn": "pps_click",
      "path": "业务平台 > 广告 > 广告 > 广告点击",
      "matchType": "ONTOLOGY_ALIAS_EXACT",
      "matchedField": "ontology.aliases",
      "matchedValue": "ads click",
      "matchedConceptId": "advertising_click",
      "confidence": "HIGH",
      "reason": "keyword 命中广告点击节点 ontology.aliases 中的 ads click。"
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `id` | 真实货架分类 ID，后续传给 `getNextLevelNode` |
| `nameCn` | 节点中文名 |
| `nameEn` | 节点英文名，可为空 |
| `path` | 中文路径，用于展示和消歧 |
| `matchType` | 如 `ONTOLOGY_ALIAS_EXACT`、`ONTOLOGY_NAME_CONTAINS`、`RAW_TREE_SEARCH` |
| `matchedField` | 命中的字段，如 `ontology.aliases`、`name_cn`、`id` |
| `matchedValue` | 命中的具体值 |
| `matchedConceptId` | 命中的本体概念 ID，可为空 |
| `confidence` | `HIGH` / `MEDIUM` / `LOW` |
| `reason` | 给云端 Agent 和人看的命中原因 |

兼容注意：

1. 如果旧版 `locateNode` 已经返回 `depth`，可以保留，但不要让云端 Agent 依赖它。
2. 层级判断应以点分 ID 前缀为准，不以 `depth` 为准。
3. 如果后端接口契约暂时不方便扩展太多字段，至少要保留 `id/nameCn/nameEn/path`，并尽量加上 `matchType/reason`。

## 9. 广告点击 MVP 数据样例

第一阶段建议至少补齐广告相关样例，用来验证英文缩写和缺失叶子节点的流程。

### 9.1 广告大类

```yaml
id: business_and_platform.ADV
parent_category_id: business_and_platform
name_cn: 广告
name_en: Advertising
description: 广告业务大类。

ontology:
  concept_id: advertising
  aliases:
    - 广告
    - ads
    - ad
    - 推广
    - 广告业务
  confidence: HIGH
  tags:
    - advertising
  match_reason: 业务平台下广告大类节点。
```

### 9.2 广告返利/广告子节点

```yaml
id: business_and_platform.ADV.AdvertiserRebate
parent_category_id: business_and_platform.ADV
name_cn: 广告
name_en: AdvertiserRebate
description: 广告返利相关子节点。当前 resources 可能只记录到这一层。

ontology:
  concept_id: advertiser_rebate_ad
  aliases:
    - 广告返利
    - 广告投放
    - advertiser rebate
    - rebate ad
  confidence: MEDIUM
  tags:
    - advertising
    - rebate
  match_reason: ADV 下广告返利相关同名广告节点，需要结合更具体语境判断。
```

### 9.3 广告点击叶子节点

```yaml
id: business_and_platform.ADV.AdvertiserRebate.pps_click
parent_category_id: business_and_platform.ADV.AdvertiserRebate
name_cn: 广告点击
name_en: pps_click
description: 广告点击节点，MVP 阶段根据真实货架 ID 手工补齐。

ontology:
  concept_id: advertising_click
  aliases:
    - 广告点击
    - 点击广告
    - ad click
    - ads click
    - pps click
    - pps_click
  confidence: HIGH
  tags:
    - advertising
    - click
  match_reason: 广告点击真实货架分类节点。
```

## 10. 弱 Agent 实施步骤

1. 在 Java 项目中确认原始节点快照目录：`resources/DataModel`。
2. 复制一份到本体运行时目录，例如 `resources/ontology/metric-shelf/DataModel`。
3. 不直接大规模改写原始 `resources/DataModel`。
4. 在副本 `base.yaml` 中保留原字段，并新增 `ontology` 字段块。
5. 手工补齐 MVP 关键缺失节点，例如 `business_and_platform.ADV.AdvertiserRebate.pps_click`。
6. 新增 DataModel loader，递归扫描所有 `base.yaml`。
7. 将每个 `base.yaml` 解析为 `OntologyNode`，并构建内存索引。
8. 修改 `locateNode`：先查本体索引，再走旧树搜索兜底。
9. 本体命中时返回结构化候选，至少包含 `id/nameCn/nameEn/path/matchType/reason`。
10. 本体未命中时保留旧搜索输出，必要时标记 `matchType=RAW_TREE_SEARCH`。
11. 加日志：加载节点数、alias 节点数、命中方式、兜底次数、跳过坏 YAML 次数。
12. 本地测试通过后，再按既有 databp 云上流程部署并刷新 MCP/Swagger 契约。

## 11. 本地测试 checklist

最小测试用例：

| 输入 | 期望 |
|---|---|
| `广告` | 返回 `business_and_platform.ADV` 以及相关同名广告节点 |
| `ads` | 返回广告相关节点，不应为空 |
| `ad` | 返回广告相关节点，不应为空，但可能有多个候选 |
| `广告点击` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `ad click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `pps click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `business_and_platform.ADV.AdvertiserRebate.pps_click` | 精确返回该节点 |
| 不存在的词 | 走旧树搜索；仍无结果则返回空数组 |

还应验证：

1. 删除或损坏一个非关键 `base.yaml`，服务不应整体启动失败。
2. 某节点没有 `ontology` 字段时，仍可通过 `id/name_cn/name_en` 命中。
3. 同名节点都返回，不要因为去重只留下一个。
4. 返回顺序符合精确匹配、置信度、具体程度优先规则。

## 12. 云上部署前检查

虽然本文主要给代码侧弱 Agent，但 Java 改造最终要给云端 Agent 调用，所以部署前必须确认：

1. `locateNode` 仍在 databp 服务内，不通过 gateway 转发真实数据。
2. Controller、注解体系、鉴权 tag、返回类型仍与已验证可用的 databp 接口保持一致。
3. 不混用 Spring `@GetMapping` / `@RequestParam` 和既有 JAX-RS 风格。
4. 修改 resources 后，部署包确实包含新的本体 DataModel 副本。
5. 云上部署后刷新 Swagger/MCP 契约。
6. 用中文和英文 keyword 都做 smoke test，例如 `广告`、`ads`、`广告点击`、`ad click`。

## 13. 常见错误

1. 把给云端 Agent 的问数编排规则写进本文，导致 Java 侧弱 Agent 实施目标发散。
2. 把 `locateNode` 改成一站式问数接口，在里面查实体、查 RealModel、执行 SQL。
3. 直接大规模修改原始 `resources/DataModel`，没有保留上游快照。
4. 假设 resources 节点一定等于真实货架，遇到缺失叶子节点就停止推进。
5. 根据中文路径或目录名动态拼真实 `categoryId`。
6. 删除旧版树搜索兜底，导致本体数据不全时召回下降。
7. 静默丢弃同名候选节点，让云端 Agent 失去消歧机会。
8. 让云端 Agent 依赖 `depth` 判断层级，而不是使用点分 ID 前缀。
