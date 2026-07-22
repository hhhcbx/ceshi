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

**作用**：返回逻辑实体的实时模型。

| 项 | 说明 |
|---|---|
| 入参 | `id`（string，必填）：逻辑实体 UUID |
| 出参 | 当前恒为空对象 |

要点：

- **暂不可用**（后端返回空），不要调用。保留在此仅作登记。

## 典型调用链

```text
locateNode(关键词)                    # 定位候选分类节点
  └─> [Stage 3 剪枝：最小覆盖根 / 最贴合节点]
        └─> getNextLevelNode(分类id, CATEGORY)          # 取逻辑实体（递归覆盖后代）
              └─> getLogicEntityDefineInfo(实体id, parentOperObjId)   # 取指标定义
```
