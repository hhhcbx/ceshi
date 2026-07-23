# locateNode 本体定位 MVP 方案

## 1. 背景与目标

当前智能问数链路里，Agent 已经可以直接调用 databp 中的货架接口获取真实数据，但新增一个可被 Agent 调用的 databp 接口成本很高，涉及权限、Swagger/MCP 暴露、云上部署与鉴权等问题。相比之下，`locateNode` 已经被打通，并且它本来就是为了解决「用户词语无法直接得到货架节点 ID」的问题。

因此，本阶段不再新增多个 databp 对外接口，也不让 gateway 参与真实数据链路，而是将 `locateNode` 改造成一个轻量的本体定位入口：

```text
用户/Agent 提供业务定位短语
  ↓
locateNode 读取 nodeConcepts.yaml
  ↓
返回候选货架分类节点 ID、路径、命中原因
  ↓
Agent 继续调用 getNextLevelNode 和 getLogicEntityRealModel
```

MVP 目标：

1. 解决 `ads`、`ad`、`推广` 等用户表达无法命中中文货架节点的问题。
2. 解决同名节点歧义，例如路径中存在两个都叫「广告」的节点。
3. 让 Agent 尽快拿到真实货架分类 ID，而不是在整棵树或大结果里猜。
4. 保持 `locateNode` 职责单一：只做节点定位，不查逻辑实体、不查 RealModel、不执行 SQL。

## 2. 为什么暂不使用 gateway

gateway 中新增 MCP 接口虽然方便，但当前环境中 gateway 无法访问 databp 真实货架数据。因此，gateway 不能作为真实问数链路的一部分：

```text
gateway 调 databp 接口
  ↓
由于环境隔离，无法返回真实数据
```

所以本阶段不在 gateway 中实现本体定位或语义查询。所有需要真实货架数据的步骤都应该发生在 Agent 直接调用 databp 已暴露接口的链路中。

## 3. 为什么不新增多个 databp 接口

新增可被 Agent 调用的 databp 接口成本高，且云上权限、Swagger、鉴权 tag、MCP 契约刷新都可能出问题。为了降低风险，本阶段只改造已经打通的 `locateNode`。

不做：

- 不新增 `resolveMetricQuery`。
- 不新增 `semanticMetricQuery`。
- 不新增 `queryMetricValue`。
- 不让 `locateNode` 变成一站式问数接口。

只做：

- `locateNode(keyword)` 先查本体配置，再兜底旧搜索。
- 返回更可靠的货架分类节点候选。

## 4. 新版 locateNode 的职责边界

### 4.1 应该做什么

新版 `locateNode` 负责：

1. 接收用于定位货架节点的短语，例如「广告」「ads」「广告点击」。
2. 从 `nodeConcepts.yaml` 中匹配业务概念、别名、货架分类绑定。
3. 返回候选分类节点的真实 `categoryId`、中文路径、节点名、置信度和原因。
4. 如果本体未命中，再走旧版树搜索逻辑兜底。

### 4.2 不应该做什么

新版 `locateNode` 不负责：

1. 不解析任意长对话。
2. 不完整理解用户所有问数意图。
3. 不调用 `getNextLevelNode`。
4. 不调用 `getLogicEntityRealModel`。
5. 不调用 `getLogicEntityDefineInfo`。
6. 不查 SQL。
7. 不返回真实指标值。

## 5. Agent 调用 locateNode 前应先抽取定位短语

不要把用户的长篇输入原封不动交给 `locateNode`。Agent 应先做轻量槽位抽取。

示例：

```text
用户问题：最近一个月的指标等级是黄金的广告成功率是多少？
```

Agent 应抽取：

```yaml
business_object: 广告
metric_phrase: 广告成功率
filters:
  - level = GOLD
time_range: 最近一个月
```

然后调用：

```text
locateNode("广告")
```

必要时可以传更短的组合短语：

```text
locateNode("广告 广告成功率")
```

但不推荐依赖：

```text
locateNode("最近一个月的指标等级是黄金的广告成功率是多少")
```

## 6. nodeConcepts.yaml 设计

建议放在 databp 微服务 resources 目录中，例如：

```text
src/main/resources/ontology/metric-shelf/nodeConcepts.yaml
```

第一阶段只维护货架节点概念，不穷举所有具体业务指标。

示例：

```yaml
version: 1

nodeConcepts:
  - conceptId: advertising
    nameCn: 广告
    nameEn: Advertising
    aliases:
      - 广告
      - ads
      - ad
      - 推广
      - 广告业务
    categoryBindings:
      - categoryId: business_and_platform.ADV
        pathCn: 业务平台 > 广告
        nodeNameCn: 广告
        confidence: HIGH
        reason: 业务平台下广告大类节点。

  - conceptId: advertiser_rebate_ad
    nameCn: 广告
    nameEn: Advertiser Rebate Advertising
    parentConceptId: advertising
    aliases:
      - 广告返利
      - 广告投放
      - 广告
    categoryBindings:
      - categoryId: business_and_platform.ADV.AdvertiserRebate
        pathCn: 业务平台 > 广告 > 广告
        nodeNameCn: 广告
        confidence: MEDIUM
        reason: ADV 下同名广告子节点，需要结合更具体语境判断。

  - conceptId: advertising_click
    nameCn: 广告点击
    nameEn: Advertising Click
    parentConceptId: advertiser_rebate_ad
    aliases:
      - 广告点击
      - 点击广告
      - ad click
      - ads click
      - pps click
    categoryBindings:
      - categoryId: business_and_platform.ADV.AdvertiserRebate.pps_click
        pathCn: 业务平台 > 广告 > 广告 > 广告点击
        nodeNameCn: 广告点击
        confidence: HIGH
        reason: 广告点击真实货架分类节点。
```

注意：不要依赖 `parentConceptId` 动态拼真实货架 ID。真实 ID 应直接写完整 `categoryId`，因为中文路径和点分 ID 片段不一定一一对应。

## 7. locateNode 返回结构建议

旧字段可以被替换或扩展，不需要兼容旧逻辑，但返回中必须包含 Agent 后续调用需要的节点 ID。

建议结构：

```json
{
  "data": [
    {
      "id": "business_and_platform.ADV.AdvertiserRebate.pps_click",
      "nameCn": "广告点击",
      "nameEn": "Advertising Click",
      "path": "业务平台 > 广告 > 广告 > 广告点击",
      "matchType": "ONTOLOGY_ALIAS",
      "matchedConceptId": "advertising_click",
      "matchedAlias": "ads click",
      "confidence": "HIGH",
      "reason": "keyword 命中 nodeConcepts.yaml 中 advertising_click 的别名 ads click。"
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
| `matchType` | `ONTOLOGY_ALIAS` / `ONTOLOGY_NAME` / `RAW_TREE_SEARCH` |
| `matchedConceptId` | 命中的本体概念 ID |
| `matchedAlias` | 命中的别名 |
| `confidence` | `HIGH` / `MEDIUM` / `LOW` |
| `reason` | 给 Agent 和人看的命中原因 |

## 8. 匹配优先级

建议匹配顺序：

1. `keyword` 与 `categoryId` 精确匹配。
2. `keyword` 与 `nodeConcepts.nameCn/nameEn` 精确匹配。
3. `keyword` 与 `nodeConcepts.aliases` 精确匹配。
4. `keyword` 包含 alias，或 alias 包含 `keyword`。
5. 未命中本体时，走旧版树搜索逻辑。

排序建议：

1. 精确匹配优先于包含匹配。
2. `confidence=HIGH` 优先于 `MEDIUM/LOW`。
3. 更具体的节点可以排在更前，但不要静默丢弃同名父节点。
4. 如果多个候选同为高置信，交给 Agent 追问或结合指标短语选择。

## 9. 本地测试 checklist

最小测试用例：

| 输入 | 期望 |
|---|---|
| `广告` | 返回 `business_and_platform.ADV` 以及相关同名广告节点 |
| `ads` | 返回广告相关节点，不应为空 |
| `ad click` | 返回 `business_and_platform.ADV.AdvertiserRebate.pps_click` |
| `广告点击` | 返回广告点击节点 |
| `pps click` | 返回广告点击节点 |
| 不存在的词 | 走旧树搜索；仍无结果则返回空数组 |

## 10. 弱 agent 实施步骤

1. 在 databp resources 下新增 `ontology/metric-shelf/nodeConcepts.yaml`。
2. 新增 YAML loader，启动时读取并缓存。
3. 修改 `locateNode`，先查 nodeConcepts。
4. 本体命中时返回结构化候选。
5. 本体未命中时保留旧树搜索兜底。
6. 本地测试 `广告`、`ads`、`广告点击`、`ad click`。
7. 云上部署前确认 `@ApiOperation.tags`、JAX-RS 注解、返回类型仍与已有可用接口一致。

## 11. 常见错误

1. 不要把完整问数系统塞进 `locateNode`。
2. 不要在 `locateNode` 内调用 RealModel。
3. 不要通过 gateway 转发 databp 真实数据。
4. 不要用中文路径自动拼真实 categoryId。
5. 不要把所有具体指标都写进 nodeConcepts。
6. 不要让 Agent 在本体命中前先自由发散大量同义词。
