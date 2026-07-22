# metric-shelf 本体维护说明

本目录是智能问数的**业务语义层**：承载概念、别名、意图类型，以及到货架 ID 的映射。  
**不是**货架数据的副本。树、指标定义、数值仍以 databp API / 数据库为准。

## 文件

| 文件 | 角色 |
|---|---|
| `schema.ttl` | 正式 TBox（类、属性、注解定义） |
| `concepts.yaml` | 运行时清单：Agent / Skill 优先读这个做查阅 |
| `README.md` | 本说明 |

## 何时改 TTL vs YAML

- 改**模型结构**（新类、新关系、新注解）→ 改 `schema.ttl`，同步更新本 README 与 Skill 引用。
- 改**业务映射内容**（新概念、新别名、新 ID 绑定）→ 只改 `concepts.yaml`。
- Phase C 若启用推理机，再从 YAML 生成/同步 ABox 个体；当前 Phase A **不要求**推理机。

## 录入一条映射的最小字段

```yaml
- id: concept.example_domain   # 稳定 ID，勿随意改
  labels: ["示例域"]           # 正式名
  utterances: ["示例说法"]     # 用户可能怎么说
  synonyms: []                 # 同义概念 id
  broader: []                  # 上位概念 id
  locate_keywords: []          # 尚无 ID 时给 locateNode 的词
  category_bindings: []        # shelf 点分 ID + 可选 path 标签
  logic_entity_bindings: []    # UUID + parent_oper_obj_id + 名称
  metric_bindings: []          # 指标中英名 + 所属实体 + intent + hints
```

## 硬性规则

1. **禁止**把离线评测问句及其「标准答案路径」写进本目录（会破坏盲测意义）。
2. 写入的 `shelf_*` ID 必须能在云上 API 验证；验证失败标 `status: stale`，不要删除历史以便审计。
3. `disambiguation_hints` 写**口径特征**（字段语义、计算含义类别），不要写死某次评测的期望选项。
4. 新增系统/新货架域时：先加概念与绑定，不改 Skill 主流程。

## Agent 查阅优先级

1. `utterances` / `labels` 字面或包含匹配  
2. `synonyms` 一跳  
3. `broader` / `narrower` 扩展（注意控量）  
4. 得到的 `category_bindings` / `logic_entity_bindings` / `metric_bindings`  
5. 仍空 → 返回空锚定，Skill 回退纯 locateNode 路径
