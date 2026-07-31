# locateNode 别名语义层 MVP 代码侧实施方案

## 1. 文档定位

本文写给 **Java 代码侧弱 Agent / 工程实现者**，用于指导在 databp Java 工程中改造 `locateNode` 代码和 resources YAML。

角色边界：

1. **Java 侧弱 Agent**：在 IDEA 中辅助编码，能访问内部 Java 工程、`resources/DataModel`、已有 controller/service 代码和内部依赖。
2. **云端 Agent**：databp 部署到云上并刷新 MCP/Swagger 后，调用 `locateNode`、`getNextLevelNode`、`getLogicEntityRealModel` 等接口完成问数编排。
3. **本文只管 Java 侧 locateNode 改造**。
4. **云端 Agent 的问数规程属于 `docs/agent-realmodel-query-rules.md`**，不要写进本文。

## 2. 这一步的本体到底是什么

本阶段不要把“本体”做复杂。

结合用户给的两篇本体文章，这里只取一个最小可落地思想：**本体不是另一个数据库，而是 Agent 和企业系统之间的一层业务语义映射。**

在我们的 locateNode MVP 里，这层语义映射非常薄：

```text
用户说法 / 口语 / 英文 / 缩写
  ↓ aliases
货架节点 base.yaml 中已有的节点
  ↓ id
真实 databp 分类节点 ID
```

所以，本阶段本体的主要价值就是：

```text
给每个货架节点补 aliases，提高 locateNode 的匹配准确性和召回率。
```

不做推理机，不做规则引擎，不做复杂 TBox/ABox，不做 schema 查询引擎。

### 2.1 为什么不额外设计 concept_id

不新增 `concept_id`。

原因：

1. 当前 `resources/DataModel` 的每个节点本身就是一个业务概念。
2. 节点已有 `id`、`name_cn`、`name_en`，足以表达“这个概念是什么”。
3. 额外维护 `concept_id` 会引入第二套命名体系，增加同步成本。
4. MVP 阶段没有跨节点规则推理、概念继承、复杂关系传递，因此不需要独立概念 ID。

结论：

```text
节点本身就是本体概念。
节点 id 就是稳定标识。
aliases 是这一步唯一必须新增的本体字段。
```

### 2.2 为什么不额外维护 path 字段

不新增 `path` / `pathCn` 字段。

原因：

1. 真实货架分类 ID 已经用 `.` 分隔层级，例如：

```text
business_and_platform.ADV.AdvertiserRebate.pps_click
```

2. `parent_category_id` 已经记录父节点关系。
3. 中文路径可以由云端 Agent 展示时根据已有接口结果或节点名辅助说明，不是 locateNode MVP 必须维护的资源字段。
4. 额外维护 path 容易和真实货架不同步。

结论：

```text
locateNode 返回 id、nameCn、nameEn、parentCategoryId 即可支撑后续调用和基本消歧。
如确实需要展示路径，可以后续由调用侧或现有树数据生成，不在 MVP 手工维护。
```

## 3. 当前已有资源：resources/DataModel

Java 项目 resources 中已有简要节点数据，路径类似：

```text
resources/DataModel/
  <node-folder>/
    base.yaml
    <child-node-folder>/
      base.yaml
```

规则：

1. 每个节点一个文件夹。
2. 每个节点目录有一个 `base.yaml`。
3. 有子节点时继续嵌套子文件夹。
4. `base.yaml` 通常已有：
   - `id`
   - `parent_category_id`
   - `name_cn`
   - `name_en`
   - `description`
5. 不同节点还可能有：
   - `version`
   - `owner`
   - `offering`
   - 其他字段

已知限制：

1. 这份资源可能落后于真实货架。
2. 例如「广告点击」真实 ID 是：

```text
business_and_platform.ADV.AdvertiserRebate.pps_click
```

但当前 resources 可能只记录到：

```text
business_and_platform.ADV.AdvertiserRebate
```

3. 这不是说叶子节点不该记录，只是信息没更新。
4. MVP 阶段先跑通流程，缺失节点后续慢慢同步。

## 4. 资源修改策略：复制一份，再只加 aliases

不要直接大规模修改原始 `resources/DataModel`。

建议：

```text
原始快照：resources/DataModel
运行时副本：resources/ontology/metric-shelf/DataModel
```

实施策略：

1. 复制现有 `resources/DataModel` 到本体运行时目录。
2. 在副本的 `base.yaml` 中保留所有原字段。
3. 只新增一个字段：`aliases`。
4. 如副本缺少 MVP 必需叶子节点，先手工补少量关键节点。
5. 后续再慢慢同步完整节点树。

为什么只加 `aliases`：

1. 用户这一步要解决的是“用户怎么说”和“货架节点叫什么”不一致。
2. aliases 足以表达同义词、英文、缩写、口语说法。
3. 其他复杂字段会让第一版实现和维护变重，但收益不明显。

## 5. base.yaml 最小格式

### 5.1 已有节点只补 aliases

广告大类示例：

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

说明：

1. `aliases` 直接放在 `base.yaml` 顶层即可。
2. 不新增 `ontology.concept_id`。
3. 不新增 `ontology.tags`。
4. 不新增 `ontology.match_reason`。
5. 不新增 `path`。

### 5.2 缺失叶子节点可先补 base.yaml

广告点击示例：

```yaml
id: business_and_platform.ADV.AdvertiserRebate.pps_click
parent_category_id: business_and_platform.ADV.AdvertiserRebate
name_cn: 广告点击
name_en: pps_click
description: 广告点击节点，MVP 阶段根据真实货架 ID 手工补齐。
aliases:
  - 广告点击
  - 点击广告
  - 广告 click
  - ad click
  - ads click
  - pps click
  - pps_click
```

注意：

1. 真实 `id` 必须写完整。
2. 不要根据中文名、目录名或父节点动态拼真实 ID。
3. 如果真实货架已确认有叶子节点，但 resources 副本缺失，可以先手工补齐。
4. 如果不确定真实 ID，不要编造，先只给已有节点补 aliases。

## 6. locateNode 代码改造边界

新版 `locateNode` 只做节点定位：

1. 接收短 keyword，例如「广告」「ads」「广告点击」「pps click」。
2. 加载 DataModel 副本中的所有 `base.yaml`。
3. 用 `id/name_cn/name_en/aliases` 匹配 keyword。
4. 返回匹配到的分类节点候选。
5. 未命中时走旧版树搜索兜底。

不做：

1. 不解析完整问数意图。
2. 不调用 `getNextLevelNode`。
3. 不调用 `getLogicEntityRealModel`。
4. 不调用 `getLogicEntityDefineInfo`。
5. 不查指标。
6. 不拼 SQL。
7. 不执行 SQL。
8. 不做推理机或规则判断。

## 7. DataModel loader 最小实现

### 7.1 加载方式

MVP loader 做简单递归扫描即可：

```text
resources/ontology/metric-shelf/DataModel
  ↓
递归找到所有 base.yaml
  ↓
解析 id / parent_category_id / name_cn / name_en / aliases
  ↓
缓存为内存列表
```

不需要：

1. 不需要图数据库。
2. 不需要 OWL 文件。
3. 不需要推理机。
4. 不需要单独索引服务。
5. 不需要概念 ID 映射表。

### 7.2 Java 结构建议

```java
class LocateNodeEntry {
    String id;
    String parentCategoryId;
    String nameCn;
    String nameEn;
    List<String> aliases;
}
```

如果已有 DTO/VO 可以复用，就复用已有结构，不必为了本体新增复杂对象模型。

### 7.3 容错规则

1. 缺少 `id` 的 `base.yaml` 跳过并打 warning。
2. 缺少 `aliases` 的节点仍然可用 `id/name_cn/name_en` 匹配。
3. 单个 YAML 解析失败，不要拖垮整个服务。
4. 启动日志打印加载节点数、带 aliases 节点数、坏 YAML 数。

## 8. 匹配规则

### 8.1 归一化

匹配前做最小归一化：

1. trim。
2. 英文转小写。
3. 多空格合并。
4. `_`、`-`、`.` 可以当弱分隔符处理，方便 `pps_click` 和 `pps click` 互相命中。

### 8.2 匹配字段

只匹配这些字段：

1. `id`
2. `name_cn`
3. `name_en`
4. `aliases`

不要匹配 `description`，避免描述文本带来噪声。

### 8.3 匹配优先级

建议顺序：

1. `keyword == id`
2. `keyword == name_cn/name_en`
3. `keyword == aliases[*]`
4. `aliases[*]` 与 `keyword` 做包含匹配
5. `name_cn/name_en` 与 `keyword` 做包含匹配
6. 本体副本未命中时，走旧树搜索

### 8.4 排序规则

1. 精确匹配优先于包含匹配。
2. alias 命中优先于 name 包含命中。
3. 更长的 `id` 可排在更前，因为通常表示更具体节点。
4. 不要静默丢弃同名节点。
5. 多个候选都合理时全部返回，交给云端 Agent 结合问题继续判断或追问。

## 9. locateNode 返回结构

尽量沿用旧结构，少扩字段。

建议最小返回：

```json
{
  "data": [
    {
      "id": "business_and_platform.ADV.AdvertiserRebate.pps_click",
      "nameCn": "广告点击",
      "nameEn": "pps_click",
      "parentCategoryId": "business_and_platform.ADV.AdvertiserRebate",
      "matchType": "ALIAS",
      "matchedValue": "ad click"
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `id` | 真实货架分类 ID，后续传给 `getNextLevelNode` |
| `nameCn` | 节点中文名 |
| `nameEn` | 节点英文名 |
| `parentCategoryId` | 父分类 ID，用于基本消歧 |
| `matchType` | `ID` / `NAME` / `ALIAS` / `RAW_TREE_SEARCH` |
| `matchedValue` | 命中的原始值 |

不建议新增：

1. `matchedConceptId`：节点 id 已经是概念稳定标识。
2. `path`：id 已有层级分隔，path 容易重复维护。
3. `confidence`：MVP 先由匹配顺序排序，不引入人工置信度。
4. `reason`：`matchType + matchedValue` 已能解释第一版命中原因。

如果旧接口已有 `path/depth` 等字段，可以保留兼容，但新逻辑不依赖它们。

## 10. 本地测试 checklist

最小测试用例：

| 输入 | 期望 |
|---|---|
| `广告` | 返回 `business_and_platform.ADV` 以及相关同名节点 |
| `ads` | 通过 aliases 返回广告相关节点 |
| `ad` | 通过 aliases 返回广告相关节点，允许多个候选 |
| `广告点击` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `ad click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `pps click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `pps_click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| 不存在的词 | 走旧树搜索；仍无结果则返回空数组 |

还要验证：

1. 没有 aliases 的节点仍可通过 `id/name_cn/name_en` 命中。
2. 同名节点都返回。
3. 单个坏 YAML 不影响服务启动。
4. 英文大小写不敏感。
5. `_` 和空格变体能互相命中。

## 11. 弱 Agent 实施步骤

1. 确认 Java 工程中的原始 `resources/DataModel`。
2. 复制到本体运行时目录，例如 `resources/ontology/metric-shelf/DataModel`。
3. 在副本中给关键节点补 `aliases`。
4. 如关键叶子节点缺失，确认真实 ID 后，在副本中手工补 `base.yaml`。
5. 新增或修改 loader，递归读取所有 `base.yaml`。
6. 修改 `locateNode`：先按 `id/name_cn/name_en/aliases` 匹配副本数据。
7. 未命中时调用旧树搜索兜底。
8. 返回旧结构 + 少量匹配解释字段：`parentCategoryId/matchType/matchedValue`。
9. 跑本地 checklist。
10. 云上部署前确认接口注解、鉴权 tag、返回类型仍与已打通版本一致，并刷新 MCP/Swagger。

## 12. 常见错误

1. 把本体做成另一套数据库。
2. 为第一版引入 `concept_id`、`confidence`、`tags`、`reason` 等额外维护字段。
3. 手工维护中文 path，导致它和真实货架或 id 层级不同步。
4. 把云端 Agent 的问数编排规则写进本文。
5. 在 `locateNode` 里查实体、查 RealModel 或执行 SQL。
6. 删除旧树搜索兜底。
7. 把 `description` 也纳入高优匹配，导致误召回。
8. 直接大改原始 `resources/DataModel`，没有保留可回退副本。
