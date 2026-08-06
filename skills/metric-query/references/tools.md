# Gateway 本体指标工具参考

本文只记录新环境中可用的工具事实。旧 databp 的 `locateNode`、`getModelTree`、`getNextLevelNode` 和 `resolveMetric` 不属于当前链路。

## 1. getOntologyClassList

**作用**：返回本体类定义、各类查询参数及关系类型元数据。

当前固定类包括 `Service`、`MicroService`、`AnomalyDetectionTask` 和 `LogSpace`；当前关系元数据包括 `associated_with`、`belongs_to`、`contains`、`part_of`。

边界：

- 不返回本体实例目录；
- 不返回所有 `operation_object` 叶子节点；
- 不能把业务名称解析为叶子节点 ID；
- 普通指标问数不必每次先调用；
- 可用于用户主动查询本体元数据或排查能力契约。

## 2. queryOntologyTopology

**作用**：从已知节点出发查询本体图。

当前必要入参：

| 参数 | 说明 |
|---|---|
| `start_node_type` | 当前仅支持 `operation_object` |
| `start_node_id` | 用户提供的叶子节点 ID |
| `end_node_type` | 目标节点类型；普通指标查询使用 `indicator` |
| `max_depth` | 1-3 |

返回图由 `leftnode`、`rightnode` 和 `edge` 构成。节点目前至少包含名称、ID、服务 ID 和 tags；edge 的 type 可能包括 `related_to`、`belongs_to`、`has_member`、`contains`、`part_of`。

深度语义：

- `max_depth=1`：起始叶子节点的直接指标和直接关系；普通指标查询固定使用该深度。
- `max_depth=2`：还可能返回起始节点引用的其他叶子节点及该节点指标。
- `max_depth=3`：还可能返回其他引用中间节点的叶子节点及其指标。

注意：图上可达不代表指标口径等价，也不代表数值可以聚合。不得因深度 1 无结果而自动扩大深度。

## 3. queryOntologyInstance

**状态**：由其他维护者完善中。

目标能力是输入指标 ID，返回指标相关信息。当前主链路不依赖该接口。后续至少需要和维护者确认是否返回：

- 中文名、英文名和描述；
- 单位与度量类型；
- 指标类型和级别；
- 聚合口径和 variant；
- 支持的维度；
- 数据可查询状态；
- 所属服务及必要来源信息。

接口未形成稳定合同时，不得假设这些字段已经存在。

## 4. queryIndicatorDimensionData

**作用**：按真实指标 ID 与时间段查询指标仓库数据。

要点：

- 指标 ID 必须来自 `queryOntologyTopology` 的真实指标节点；
- 开始和结束时间必须明确；
- 参数名称、时间格式和响应结构以已安装工具为准；
- 返回空时如实报告；
- 不改变接口已有的聚合语义；
- 不用假数据补齐。

## 5. 当前标准调用链

```text
用户直接提供 operation_object 叶子节点 ID
  -> queryOntologyTopology(operation_object, id, indicator, max_depth=1)
  -> Skill 从真实图结果提取并匹配指标
  -> queryIndicatorDimensionData(metricId, startTime, endTime)
```

拓扑查询：

```text
用户提供 operation_object ID 和 max_depth
  -> queryOntologyTopology(..., max_depth=1..3)
  -> Skill 按原始节点、边和路径解释结果
```
