# 工具接口参考

货架数据模型（databp）相关 MCP 工具的入参、出参与使用要点。

## locateNode

**作用**：按关键词在整棵模型树中查找名字匹配的节点（服务端搜索，返回量小）。

| 项 | 说明 |
|---|---|
| 入参 | `keyword`（string，必填）：要定位的概念词，如 `小艺` |
| 出参 | `data`: 数组，每项含 `id` / `nameCn` / `nameEn` / `depth` / `path` |

要点：

- 名字**包含**关键词即返回，因此会同时返回祖先与后代节点（如「小艺」会命中 `业务&平台 > 小艺` 和 `... > 小艺_修图`）。
- `path` 是从根到该节点的完整路径（`业务&平台 > 小艺 > AI Vision`），可直接用于呈现。
- ⚠️ `depth` 字段目前不可靠，**禁止依赖**；层级关系一律用点分 ID 前缀判断。
- 匹配范围覆盖中文名、英文名、中英别名，大小写不敏感。

## getModelTree

**作用**：返回前两层分类骨架（id / nameCn / nameEn）。

| 项 | 说明 |
|---|---|
| 入参 | 无 |
| 出参 | `data`: 树形数组，节点含 `id` / `nameCn` / `nameEn` / `childNodeList`（仅前两层） |

要点：

- 仅在「用户没给明确概念、需要浏览有哪些顶层分类」时使用；日常定位一律优先 `locateNode`。
- 返回已被 schema 投影裁剪，不含实体细节。

## getNextLevelNode

**作用**：返回指定分类节点下的**全部逻辑实体**。

| 项 | 说明 |
|---|---|
| 入参 | `id`（string，必填）：分类 ID，如 `business_and_platform.CEL`；`type`（string，必填）：固定传 `CATEGORY` |
| 出参 | `data.draftData` / `data.publishedData`: 逻辑实体数组，每项含 `id`（UUID）/ `nameCn` / `nameEn` / `parentOperObjId` |

要点：

- **递归返回**：包含该分类**所有后代分类**下的逻辑实体。对祖先调用一次即覆盖全部后代，因此严禁对祖先和后代重复调用（会拿到重复数据且量爆炸）。
- 以 `publishedData` 为准；`draftData` 是草稿。
- **必须保留每个实体的 `parentOperObjId`**，它是 `getLogicEntityDefineInfo` 的必填入参。
- 数据量与该分类下实体总数成正比，越高层的分类返回越多——只对 Stage 3 剪枝后的目标节点调用。

## getLogicEntityDefineInfo

**作用**：返回逻辑实体的定义信息（指标、字段、基本信息）。

| 项 | 说明 |
|---|---|
| 入参 | `id`（string，必填）：逻辑实体 UUID，来自 `getNextLevelNode` 的 `id`；`parentOperObjId`（string，必填）：来自 `getNextLevelNode` 的 `parentOperObjId`；`reference`（boolean，选填，默认 false） |
| 出参 | `data.draftData` / `data.publishedData`，每个含 `metrics`（指标列表）/ `fields`（字段列表）/ `universal`（基本信息） |

要点：

- **指标在 `publishedData.metrics`**；`draftData` 通常为空。
- 每条指标关注的字段：`measureType` / `nameCn` / `nameEn` / `description` / `type`（BASIC/DERIVED/COMPOSITE）/ `level`（GOLD/HEALTH/NORMAL）/ `tag`。呈现规范见 output-format.md。
- 两个必填入参**必须**取自 `getNextLevelNode` 的返回，不要自行构造。
- 字段信息（`fields`）仅在用户明确要字段时才使用，避免无谓的大输出。

## getBaseInfo

**作用**：返回指定分类的基本信息（描述、负责人、版本、父分类等）。

| 项 | 说明 |
|---|---|
| 入参 | `id`（string，必填）：分类 ID；`dataModelType`（string，必填）：固定传 `CATEGORY` |
| 出参 | `data.draftData` / `data.publishedData`: 分类详情 |

要点：

- 辅助工具，不在主链路中；仅当需要分类的描述/负责人等元信息时使用。

## getLogicEntityRealModel

**作用**：返回逻辑实体的已部署指标目录，用于用户明确要求浏览指标或排查。

| 项 | 说明 |
|---|---|
| 入参 | `id`（string，必填）：逻辑实体 UUID |
| 出参 | 逻辑实体及其已部署指标；Agent 可见字段以 Swagger 投影为准 |

要点：

- 标准数值问数使用 `resolveMetric`，不要由 Agent 拉取 RealModel 后自行实现 Phase B。
- 原始响应很大；仅在指标目录浏览或排查时调用，并遵守 Swagger 控量。

## resolveMetric

**作用**：Java Phase B。对一个逻辑实体解析用户指标短语，并返回真实指标候选。

| 项 | 说明 |
|---|---|
| 入参 | `logicEntityId`：来自 `getNextLevelNode` 的逻辑实体 ID；`metricPhrase`：用户指标原话 |
| 出参 | `status`，以及按状态出现的 `selectedMetric` / `candidates` / `formula` / `message` |

状态：

- `RESOLVED`：唯一直接指标，使用 `selectedMetric.id`。
- `AMBIGUOUS`：多个候选，必须追问。
- `FORMULA_CANDIDATE`：只有公式候选，未经确认和安全执行计划不得自行计算。
- `NOT_FOUND`：该实体没有目标指标。

要点：

- `resolveMetric` 内部读取 Java Metric Family 和真实 RealModel；Agent 不上传 RealModel。
- `getNextLevelNode` 返回的实体名称不能用于判断指标内容。对锁定 Phase A 节点下的每个去重实体都调用一次。
- 不因前几个 `NOT_FOUND` 或第一个 `RESOLVED` 提前结束；扫描全部实体后统一决策。
- 单实体失败不阻塞其他实体；记录失败摘要后继续。

## queryIndicatorDimensionData

**作用**：按真实指标 ID 和起止时间查询指标数据。

| 项 | 说明 |
|---|---|
| 入参 | 指标 `id`、查询开始时间、查询结束时间；参数名称和时间格式以已安装工具为准 |
| 出参 | 该指标在时间范围内的真实数据，可能是单值、时间序列或空结果 |

要点：

- `id` 必须来自 `resolveMetric.selectedMetric.id`，不是分类 ID 或逻辑实体 ID。
- 开始和结束时间都必须明确，并在最终回答中回显实际范围和时区。
- 不改变接口返回的聚合含义，不自行编造总值、平均值或趋势。
- 返回为空时如实报告空结果，不使用本地假数据补齐。

## 典型调用链

```text
locateNode(业务对象)                              # Phase A，只定位一次
  └─> [锁定分类节点]
        └─> getNextLevelNode(分类id, CATEGORY)            # 取全部逻辑实体并按id去重
              └─> resolveMetric(每个实体id, 指标原话)     # Phase B，全部实体各调用一次
                    └─> [扫描完成后汇总候选]
                          └─> queryIndicatorDimensionData(选中指标id, 开始时间, 结束时间)
```
