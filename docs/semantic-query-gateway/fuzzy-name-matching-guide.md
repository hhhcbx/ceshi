# 运维对象名称解析：Skill 优先、代码兜底的最小改造方案

> 更新日期：2026-08-13
>
> 当前基线：ontology `queryNode` 已能按 `className + instance_name` 精确查询；`event` 返回唯一节点，`pps_click` 返回两个真实同名节点；Gateway 已能消费 `RESOLVED`、`AMBIGUOUS` 和 `NOT_FOUND`。
>
> 约束：现有精确查询代码即将合并，不做大规模重构；不能修改本体、Nebula 数据和实例；可修改 Skill，并允许少量 Java 加固。

## 1. 重新定义问题

当前真正困难的不是字符串模糊匹配，而是：

```text
用户业务口语                  数据库真实 instance_name
“广告点击”          ->        pps_click
“资源变更事件”      ->        event
```

`STARTS WITH`、`CONTAINS`、编辑距离只能处理同一字符串空间内的差异，例如：

```text
pps       -> pps_click
click     -> pps_click
pps-click -> pps_click（仅当符号等价规则成立）
```

它们不能从字符串本身推导：

```text
广告点击 -> pps_click
资源变更事件 -> event
```

中文业务表达到英文内部标识的转换需要语义知识。当前数据库没有中文名、alias 或 Concept→Asset 映射，又不能修改本体，因此 Java 侧堆叠多层字符串算法不能解决核心问题。

本阶段应采用：

```text
云 Agent / Skill 负责语义理解和查询词生成
ontology Java 负责用候选词精确查询真实节点
Gateway 负责状态编排和候选澄清
```

这里必须区分“生成查询候选”和“确认企业事实”：云 Agent 可以根据用户表达生成少量可能的英文标识，但只有 `queryNode` 返回的真实节点才可被接受；Agent 的生成结果不能直接当作真实 ID 或企业映射。

## 2. 本阶段最小架构

```text
用户问题
  -> Skill 判断是否为运维对象查询
  -> 抽取用户对象原话
  -> 生成有序、有限的 name 候选
  -> 按顺序调用 queryNode 精确匹配
       -> RESOLVED：停止，进入既有后续链路
       -> AMBIGUOUS：停止，展示真实候选并澄清
       -> NOT_FOUND：尝试下一个候选
  -> 所有候选未命中：如实报告，要求用户提供更准确名称
```

优先级：

```text
用户显式给出的英文 name
> 会话中已经由真实接口确认的 name
> Skill 对中文口语生成的少量候选
```

不需要在 Java 中实现完整的 EXACT→PREFIX→CONTAINS→编辑距离流水线。Java 继续承担确定性、可审计的精确验证器角色。

## 3. Skill 如何生成 name 候选

### 3.1 输出结构

建议 Skill 内部状态：

```yaml
object_expression: 广告点击
ontology_type: operation_object
name_candidates:
  - value: ad_click
    source: semantic_generation
    rank: 1
  - value: advertisement_click
    source: semantic_generation
    rank: 2
max_attempts: 3
```

这些只是待验证候选，不是事实。

### 3.2 生成规则

1. 用户明确输入符合内部 name 形态的字符串时，原样候选排第一：

   ```text
   用户：“查 pps_click”
   候选：[pps_click]
   ```

2. 中文业务表达允许云 Agent 生成少量英文 `snake_case` 候选：

   ```text
   “广告点击” -> [ad_click?, advertisement_click?]
   ```

   `pps` 是企业内部缩写，若用户上下文和可用工具均未提供“广告业务使用 pps”这一知识，Agent 不应凭空生成 `pps_click`。因此仅靠 Skill 候选生成时，“广告点击”很可能无法命中真实 name；这是能力边界，不应通过提示词伪装成可稳定解决。

3. 候选数量必须有限，建议最多 3 个，禁止让 Agent 枚举几十种翻译轰炸接口。

4. 候选必须保持原语义，禁止扩大或替换业务概念：

   ```text
   “广告推广”不能退化成“广告”
   “成功率”不能改成“成功次数”
   ```

5. 不生成 VID 或 `instance_id`，只生成可能的 `instance_name`。

6. 候选去重后依次查询；同一候选在一次请求中只调用一次。

### 3.3 两个示例的真实含义

#### 广告点击

```text
用户表达：广告点击
可能候选：ad_click、advertisement_click
```

在没有受治理 alias、会话已确认映射或其他权威上下文时，Skill 通常无法推出内部缩写 `pps_click`。若上述自然翻译候选均为 `NOT_FOUND`，必须如实报告未定位到真实对象，并请求准确 name 或更多限定。

只有当用户明确提供 `pps_click`，或会话/权威工具已经确认“广告点击对应 pps_click”时，才能查询该候选。若它返回两个节点，结果是 `AMBIGUOUS`，Skill 必须立即停止并澄清。

Skill 应用真实 `offering` 生成澄清：

```text
找到两个名为 pps_click 的运维对象：
1. com.huawei.paid_presentation_service
2. com.huawei.wiseeye
请确认要查询哪一个。
```

#### 资源变更事件

```text
用户表达：资源变更事件
可能候选：resource_change_event、event
```

如果第一个候选 `NOT_FOUND`，允许查询第二个；`event` 返回 `RESOLVED` 后停止，并把真实 candidate 交给后续链路。

这个例子也说明纯 Java 字符串匹配无能为力：中文原文与 `event` 没有可利用的字符重叠。

## 4. Skill 的状态机

伪代码：

```text
for candidate in name_candidates[0:max_attempts]:
    result = queryNode(className, candidate)

    if result.status == RESOLVED:
        use result.candidate
        stop

    if result.status == AMBIGUOUS:
        ask user to choose among result.candidates
        stop

    if result.status == NOT_FOUND:
        continue

    otherwise:
        report tool/contract error
        stop

if all candidates are NOT_FOUND:
    report that no real object was found
```

关键规则：

- `AMBIGUOUS` 不是失败，也不能继续换候选；
- 接口异常不是 `NOT_FOUND`，不得尝试下一个候选掩盖错误；
- 第一个 `RESOLVED` 不一定可以在所有场景自动采用：若它来自弱语义生成且与用户原话差异很大，可先向用户确认；
- 如果候选来自用户显式英文 name 或会话中已由接口确认的 name，可以直接采用；
- 不把未命中的生成候选沉淀为公共 alias。

## 5. 对现有 Java 代码的判断

现有 `queryNodes` 主链路已经完成本阶段需要的核心能力：

```text
className + name 精确 LOOKUP
→ 得到最多 10 个 VID
→ FETCH 真实属性
→ 0/1/多候选状态
```

不建议在合并前改造成复杂模糊检索。只建议做以下小范围加固。

### 5.1 className 必须使用白名单

当前代码把 `className` 直接插入 nGQL 标识符：

```java
"LOOKUP ON %s WHERE %s.instance_name ..."
```

字符串值可以转义，但 Tag 标识符不能仅靠 `escapeString`。应使用已有 schema 白名单，或当前阶段只允许：

```java
private static final Set<String> QUERYABLE_TAGS = Set.of("operation_object");
```

非法 className 直接报参数错误。

### 5.2 name 做 trim，但不要擅自改写

建议：

```java
String queryName = name.trim();
if (queryName.isEmpty()) {
    throw new ServiceInsightException("name is required");
}
```

本阶段不要在 Java 中：

- 中文翻英文；
- 驼峰转下划线；
- `-` 与 `_` 自动互换；
- 大小写强制转换；
- 去掉业务词。

这些转换可能改变真实标识，且没有数据合同支持。

### 5.3 不要用 VID 回填 instanceId

当前代码：

```java
.instanceId(instanceId != null ? instanceId : vid)
```

会混淆：

```text
vid = operation_object:...
instanceId = props.instance_id
```

建议 `instance_id` 缺失时保留 null 或抛合同错误，不要把 VID 填入 `instanceId`。后续需要 VID 时使用 `candidate.getVid()`。

### 5.4 精确结果上限语义

`QUERY_LIMIT=10` 表示最多返回 10 个候选，不代表数据库总共有 10 个。Gateway 响应中的 `total` 应明确是“本次候选数”，或者不要声称是完整总数。

对于同名数量可能超过 10 的情况，可额外返回 `truncated/hasMore`；若合并前不方便改合同，至少在代码和接口说明中记录限制。

### 5.5 避免为每个候选单独 FETCH（可选）

当前循环中每个 VID 执行一次 FETCH：

```text
1 次 LOOKUP + N 次 FETCH
```

在候选最多 10 条时功能正确，但可以做一个不改变合同的小优化：把 VID 合并成一次批量 `FETCH PROP ON *`，将数据库往返从 N+1 降为 2。

示意代码：

```java
String vidList = vids.stream()
        .map(this::escapeVid)
        .map(v -> "\"" + v + "\"")
        .collect(Collectors.joining(", "));

String fetchNgql = "FETCH PROP ON * " + vidList + " YIELD vertex AS v";
Map<String, GraphNode> nodeMap = nebulaQueryExecutor.queryVertices(fetchNgql);
```

这是可选性能优化。若现有执行器对批量 FETCH 的返回键或语法没有成熟用例，合并前不要冒险修改。

### 5.6 queryNode 不宜附带 topology（合并后整理）

当前：

```java
queryNodeWithTopology
buildNodeQueryResponse
queryNodeAsList
```

把“名称解析”和“拓扑查询”混在一起。Gateway 已有知道 ID 后的后续链路，长期建议 `queryNode` 只返回 candidate/candidates；只有 `RESOLVED` 后由 Gateway 复用原拓扑流程。

但这不是本次提高中文口语命中率的必要改动。如果即将合并，应作为后续清理项，不阻塞当前代码。

## 6. 少量代码优化后的示例

下面只展示加固方向，不要求照搬类名：

```java
private static final Set<String> QUERYABLE_TAGS = Set.of("operation_object");
private static final int QUERY_LIMIT = 10;

public QueryResult queryNodes(String className, String name) {
    if (!QUERYABLE_TAGS.contains(className)) {
        throw new ServiceInsightException("unsupported className: " + className);
    }

    String queryName = name == null ? null : name.trim();
    if (Strings.isNullOrEmpty(queryName)) {
        throw new ServiceInsightException("name is required");
    }

    String encodedName = escapeString(queryName);
    String lookupNgql = String.format(Locale.ROOT,
            "LOOKUP ON %s WHERE %s.instance_name == \"%s\" "
                    + "YIELD id(vertex) AS vid | LIMIT %d",
            className, className, encodedName, QUERY_LIMIT);

    // 保持现有 LOOKUP → FETCH → 状态判断逻辑。
}
```

这个代码不会提升“广告点击 → pps_click”的语义召回率；它只是让真实节点验证更安全稳定。语义命中率主要由 Skill 的候选生成和状态控制提升。

## 7. 推荐的近期实施顺序

### 第一步：合并现有精确查询

保留已经人工验证的基线：

```text
event -> RESOLVED
pps_click -> AMBIGUOUS
不存在 name -> NOT_FOUND
```

只在风险可控时加入 className 白名单、trim 和 instanceId/VID 分离修复。

### 第二步：修改 Skill，而不是先扩展 Nebula 模糊查询

加入：

- 对象原话抽取；
- 最多 3 个 snake_case name 候选；
- 候选来源和顺序；
- NOT_FOUND 才尝试下一个；
- AMBIGUOUS 立即澄清；
- RESOLVED 才进入后续链路。

### 第三步：用小测试集评估

至少包含：

| 用户表达 | 期望真实 name | 预期行为 |
|---|---|---|
| `pps_click` | `pps_click` | 精确调用，返回 AMBIGUOUS |
| 广告点击（无映射知识） | 未知 | 自然翻译候选未命中后停止，不声称能推出 `pps_click` |
| 广告点击（上下文已确认 `pps_click`） | `pps_click` | 精确调用并返回 AMBIGUOUS |
| `event` | `event` | 精确 RESOLVED |
| 资源变更事件 | `event` | Skill 候选依次验证，最终 RESOLVED 或确认 |
| 无关问题 | 无 | 不调用 queryNode |
| 不存在的业务对象 | 无 | 有限候选均 NOT_FOUND 后停止 |

重点统计：

- 用户口语最终命中真实 name 的比例；
- 每个请求的 queryNode 调用次数；
- 错误自动选择次数；
- AMBIGUOUS 后继续搜索的次数，必须为 0；
- 无关问题误调用率。

### 第四步：只有数据证明需要时，再加 Java 前缀搜索

如果真实失败样例主要是：

```text
用户已经给出英文片段，但不是完整 name
```

例如 `pps`、`click`，才有理由在 Java 增加 `STARTS WITH` 或 `CONTAINS`。

如果失败样例主要是：

```text
中文业务语言与英文 name 无字符关系
```

继续增加 Java 字符串模糊层没有价值，应优先建设 alias/资产目录或继续优化 Skill 候选生成。

## 8. Skill 指令示例

可将以下核心规则加入下一版 Skill：

```text
当用户没有提供内部 operation_object name，但提供了中文业务对象表达时：

1. 保留用户对象原话。
2. 生成最多 3 个可能的英文 snake_case instance_name 候选；候选只是查询假设，不是企业事实。
3. 按候选顺序调用 queryNode 做精确验证。
4. queryNode 返回 RESOLVED：停止尝试其他候选，使用真实 candidate。
5. queryNode 返回 AMBIGUOUS：停止尝试其他候选，展示 instanceName、offering、serviceId，要求用户确认。
6. queryNode 返回 NOT_FOUND：才允许尝试下一个候选。
7. 工具异常、合同错误：立即停止，不得视为 NOT_FOUND。
8. 所有候选均未命中：说明未找到真实对象，要求用户提供准确英文 name 或更多业务限定。
9. 不生成或猜测 VID、instanceId；不把未命中候选写成 alias；不把中文概念静默扩大。
10. 与指标、时间、维度的解析并行进行，但只有对象 RESOLVED 后才进入拓扑和指标查询。
```

## 9. 长期正确方案

Skill 生成只能提高机会，不能提供稳定的企业语义映射。长期按可靠性排序：

```text
受治理的中文名/alias → instance_name 映射
> 权威资产目录的名称与描述检索
> 本体 Concept→Asset 显式关系
> Skill 生成少量候选 + 真实接口验证
> 单纯字符串 PREFIX/CONTAINS
```

当权限允许时，应把：

```text
广告点击 -> pps_click
资源变更事件 -> event
```

维护在权威元数据或资产目录，而不是长期依赖提示词或 Java 硬编码。
