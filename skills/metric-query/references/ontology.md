# 本体锚定与指标消歧（Agent 规程）

本文件是 `metric-query` Skill 的本体侧操作细则。方案背景见 `docs/metric-ontology-enhancement.md`。  
运行时清单：`ontology/metric-shelf/concepts.yaml`（优先）。形式化 TBox：`ontology/metric-shelf/schema.ttl`。

## 总原则

1. 本体是**语义地图**：查概念、别名、意图桶、货架绑定；**不要**假设本体里有全树或时序值。
2. 有绑定时优先用 ID；无 ID 时用 `locate_keywords`；都没有则回退纯 `locateNode` 路径。
3. **API 现场结果覆盖陈旧映射**。映射对不上时标注 `stale` 线索，继续用 API 数据，不编造。
4. **禁止**把当前对话里的评测期望答案写回 `concepts.yaml`（除非用户明确要求进入治理录入流程）。

## Stage 1.5 · 本体锚定算法

输入：Stage 1 抽出的 `target_concepts[]`、`metric_phrase`（用户对指标的说法）、`filters`。

1. **读清单**：加载 `concepts.yaml` 的 `concepts` 与 `metric_intents`。
2. **概念命中**：对每个 `target_concept`，在 `labels` / `utterances` 上做大小写不敏感匹配（精确 > 包含 > 被包含）。记录命中字段。
3. **扩展**：命中后并入 `synonyms` 一跳；必要时沿 `broader` / `narrower` 各扩一层（默认各最多 +3 个概念，防爆）。
4. **意图命中**：用 `metric_phrase` 匹配 `metric_intents.utterances`，得到 `intent_ids[]`。可多标签。
5. **汇总绑定**（去重）：
   - `category_bindings`（`status!=stale`）
   - `logic_entity_bindings`
   - `metric_bindings`（若有 `intent_ids`，提高带交集 intent 的绑定权重）
   - `locate_keywords` 并集
6. **输出锚定包**（后续阶段只读这份）：

```yaml
ontology_grounding:
  matched_concepts: []      # id + 命中 utterance
  matched_intents: []       # id + 命中 utterance
  category_ids: []          # shelf 点分 ID
  logic_entities: []        # {id, parent_oper_obj_id, name_cn, name_en}
  metric_candidates: []     # {name_cn, name_en, logic_entity_id, intent_ids, hints, score}
  locate_keywords: []
  explain: []               # 人可读：为何命中
```

7. 若 `concepts` 为空或全无命中：`ontology_grounding.empty = true`，不阻塞主流程。

## Stage 2 如何用锚定包

- `category_ids` 非空 → **可跳过或少调** `locateNode`，直接进入 Stage 3（仍建议对不确定 ID 用 `locateNode`/`getBaseInfo` 校验存在性）。
- 仅有 `locate_keywords` → 对这些词调 `locateNode`，再与语义增强词合并。
- `empty` → 完全走原 Stage 1 增强词。

## Stage 4 如何用锚定包

- 有 `logic_entities`：在 `getNextLevelNode` 结果里**优先保留** UUID 命中或名称高度相似者。
- 无实体绑定：用概念标签 / hints 与实体 `nameCn`/`nameEn` 做相关性过滤（原逻辑），可把本体 `explain` 附在排序键里。

## Stage 5.7 · 指标语义对齐

在 Stage 5（及 5.5）之后执行：

1. 候选指标 = defineInfo 返回的 metrics（已按 level/type 筛过的）。
2. 打分信号（可加和，需在回答中能复述）：
   - 与 `metric_candidates` 的 `metric_name_cn/en` 精确/包含匹配
   - 与 `matched_intents` 的 hints / 用户 `metric_phrase` 在 `nameCn`/`nameEn`/`description` 中的共现
   - 所属实体是否落在锚定的 `logic_entities` 中
3. **排序**取 Top-K（默认 K=5）。
4. **决策**：
   - 唯一高分且显著领先 → 作为主答案，其余可作「相关指标」附录。
   - 多个接近高分 → **消歧列表**：每条给出路径、实体、指标名、命中依据；意图 C（要数值）时先确认再取数。
   - 全低分 → 坦诚说明未对齐，展示最相关若干，建议换说法或补业务域信息。

## Stage 7 · RealModel 取数（能力已具备接口，执行通道按环境接入）

当意图需要数值/图，且已选定唯一（或用户确认的）逻辑实体 + 指标：

1. 调 `getLogicEntityRealModel(logicEntityId)`，从返回中定位该指标对应的**已部署 SQL**。
2. 在只读、限流的数据通道执行 SQL（具体连接不在本体里；本体只保留到实体/指标的语义绑定）。
3. 按 `output-format.md` 图表规范绘图；信息头必须含指标正式名、实体、时间范围、筛选条件。
4. SQL 缺失或执行失败：返回定义信息 + 明确错误原因，不编造数值。

## 查阅 vs 推理

| 模式 | 用于 | Phase |
|---|---|---|
| 查阅 YAML | 别名、ID 映射、意图桶、hints | A（当前） |
| 推理（可选） | `broaderThan` 闭包、意图多重归类等价类 | C |

当前默认**只查阅**。不要为了「用本体」而强行上推理机。
