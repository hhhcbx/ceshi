# 运维对象 name 模糊匹配分阶段改造指导

> 更新日期：2026-08-12

> 适用现状：ontology `queryNode` 已支持 `operation_object.instance_name` 精确查询；`pps_click` 能返回两个真实候选并标记 `AMBIGUOUS`，`event` 能返回唯一候选并标记 `RESOLVED`；Gateway 已能通过机机接口消费两种状态。
>
> 当前限制：可修改 ontology、Gateway 和 Skill 代码，但不能修改 Nebula 数据、图实例或本体；命令行 Maven 无私库权限，构建由人工通过 IDE Maven 插件完成，验证以 PowerShell/HTTP 和运行日志为主。

## 1. 改造目标与边界

模糊匹配的目标不是让任意输入都得到一个节点，而是在精确名称未命中时，扩大真实候选召回，同时保留可解释证据和拒识能力：

```text
精确查询
├─ 唯一：RESOLVED，停止
├─ 多个：AMBIGUOUS，停止并澄清
└─ 零个：才允许进入较弱的模糊层
          ├─ 唯一可靠候选：RESOLVED 或待确认
          ├─ 多个：AMBIGUOUS
          └─ 零个/证据太弱：NOT_FOUND
```

必须保持：

- `queryNode` 只返回数据库中的真实节点；
- 精确层已有结果时不再扩大搜索；
- 多候选不按数据库顺序静默选择；
- `pps_click` 的两个精确候选不能因模糊能力上线而被压成一个；
- Gateway 负责编排状态，ontology 负责真实节点召回；
- 本阶段物理 Tag 仍为 `operation_object`，不猜测 `slb/service/pod` 到图存储的映射；
- 不修改原 ID 查询和拓扑遍历算法。

## 2. 为什么不是简单把 `==` 改成 `CONTAINS`

当前精确语句类似：

```ngql
LOOKUP ON operation_object
WHERE operation_object.instance_name == "pps_click"
YIELD vertex AS vid
| LIMIT 2
```

直接改成 `CONTAINS` 会产生三个问题：

1. 精确名称也可能返回大量包含候选，降低已有正确率；
2. 无法说明候选来自精确、前缀还是任意包含；
3. `LIMIT 2` 只取得数据库执行顺序中的两条，不能形成可靠排序。

因此，模糊能力必须是多阶段控制流，而不是一个更宽的谓词：

```text
输入规范化
→ EXACT
→ PREFIX（仅 EXACT=0）
→ CONTAINS（仅 PREFIX=0，且满足安全条件）
→ 小候选集重排
→ 状态决策
```

Nebula 中底层字符串召回仍可能使用 `STARTS WITH`、`CONTAINS`。优化点在调用条件、候选上限、证据、排序和拒识，不是伪造一种不存在的查询语法。

## 3. 先调整内部模型

在新增模糊层前，为候选增加匹配证据。示例 Java 模型：

```java
public enum MatchLevel {
    EXACT,
    NORMALIZED_EXACT,
    PREFIX,
    CONTAINS
}

public class NodeCandidate {
    private String vid;
    private String instanceId;
    private String instanceName;
    private String serviceId;
    private String offering;
    private List<String> tags;
    private MatchLevel matchLevel;
    private String matchedExpression;
    private Integer score;
}
```

`score` 是可选的应用层排序分，不是数据库真实性或业务置信度。`matchLevel` 和 `matchedExpression` 应向 Gateway 保留，以便 Agent 解释为何需要确认。

建议内部状态继续使用：

```text
NOT_FOUND
RESOLVED
AMBIGUOUS
```

如果产品不允许模糊层单候选自动锁定，可增加：

```text
CANDIDATE
```

或让单个弱候选仍作为 `AMBIGUOUS`/待确认返回。是否自动锁定应通过真实测试集决定，不能仅因候选数为一就默认高置信。

## 4. 阶段 0：冻结精确查询基线

在改代码前保存以下人工测试结果：

| 输入 | 当前预期 |
|---|---|
| `pps_click` | `AMBIGUOUS`，两个 offering 不同的真实候选 |
| `event` | `RESOLVED`，唯一真实候选 |
| 明确不存在的长名称 | `NOT_FOUND` |

为每次解析记录结构化日志：

```text
nameResolution name={} stage={} rows={} status={} elapsedMs={}
```

阶段 0 的验收是所有现有结果不变。后续每完成一阶段都重复三条基线测试。

## 5. 阶段 1：确定性输入规范化

只做不改变业务含义的转换：

```java
static String normalizeName(String input) {
    if (input == null) {
        return null;
    }
    return Normalizer.normalize(input.trim(), Normalizer.Form.NFKC)
            .replaceAll("\\s+", " ");
}
```

可依据真实命名规则再决定是否统一英文大小写。不要立即把 `-`、`_`、空格互换，因为它们可能在真实 name 中有不同含义。

执行顺序：

```text
原始值精确查询
→ 若 0 条且 normalized != original，再做规范化精确查询
```

不要通过 `toLower(instance_name)` 做无索引全量计算，除非已确认 Nebula 版本、索引和性能允许。更安全的是先规范化用户输入，并以数据库实际大小写合同查询。

阶段 1 测试：

- `" event "` 能否按已决定的空白规则命中 `event`；
- 全角字符按 NFKC 后是否符合预期；
- `pps_click` 仍为两个精确候选；
- 空白或空字符串在查询前报参数错误。

## 6. 阶段 2：前缀召回

只有精确层返回零行时，才执行前缀层。逻辑 nGQL：

```ngql
LOOKUP ON operation_object
WHERE operation_object.instance_name STARTS WITH "pps"
YIELD vertex AS vid
| LIMIT <candidateLimit>
```

具体语法必须以当前 Nebula 版本实际可执行结果为准。如果 `LOOKUP + STARTS WITH` 因索引合同失败，应暴露真实错误，并停止该阶段；不要改成全图 FETCH。

建议候选上限先使用小值，例如 10，而不是 2：

- 精确层 `LIMIT 2` 足以判断是否重复；
- 模糊层需要一个有限候选集进行稳定重排；
- 上限最终由数据规模和性能测试决定。

候选经 FETCH 后标记：

```text
matchLevel=PREFIX
matchedExpression=<规范化输入>
```

前缀层状态建议：

- 0 条：允许进入包含层；
- 1 条：早期版本返回待确认候选，不自动查拓扑；
- 多条：`AMBIGUOUS`，按稳定规则排序并返回有限候选。

示例测试：

```text
输入 pps
EXACT=0
PREFIX 应至少召回 pps_click 的两个真实节点
最终 AMBIGUOUS
```

这条测试能确认前缀层不会错误选择其中一个 offering。

## 7. 阶段 3：受限包含召回

只有以下条件同时满足才执行 `CONTAINS`：

- 精确和前缀都为零；
- 规范化关键词达到最小长度；
- 不是纯标点、纯空白或过于通用的词；
- 有固定候选上限和查询超时保护。

逻辑 nGQL：

```ngql
LOOKUP ON operation_object
WHERE operation_object.instance_name CONTAINS "click"
YIELD vertex AS vid
| LIMIT <candidateLimit>
```

`CONTAINS` 是弱召回证据。即使只返回一个候选，第一版也建议让 Agent/用户确认，不直接进入拓扑查询。

建议配置而非散落常量：

```java
public final class NameQueryPolicy {
    static final int PREFIX_LIMIT = 10;
    static final int CONTAINS_LIMIT = 10;
    static final int MIN_CONTAINS_LENGTH = 3;
}
```

中文最小长度与英文不同，不能简单统一用字符数 3。可先对当前英文/标识符测试数据开放包含层，中文规则在获得真实样例后再定义。

阶段 3 测试：

- `click` 能召回两个 `pps_click` 候选以及数据库中的其他真实包含候选；
- 太短的 `p` 不执行包含查询；
- 不存在的长词返回 `NOT_FOUND`；
- 特殊字符不会改变 nGQL 结构。

## 8. 阶段 4：小候选集稳定排序

排序只能作用于 ontology 已真实召回并 FETCH 成功的有限候选，不得生成新节点。

推荐优先级：

```text
EXACT
> NORMALIZED_EXACT
> PREFIX
> CONTAINS
```

同一层可使用确定性特征：

```java
int score(NodeCandidate candidate, String query) {
    String name = normalizeName(candidate.getInstanceName());
    if (name.equals(query)) {
        return 1000;
    }
    if (name.startsWith(query)) {
        return 700 - Math.min(100, name.length() - query.length());
    }
    if (name.contains(query)) {
        return 400 - Math.min(100, name.length() - query.length());
    }
    return 0;
}
```

稳定 tie-breaker 可用：

```text
score 降序
→ instanceName 升序
→ vid 升序
```

不得把以下信息作为未经用户授权的自动选择规则：

- UUID 或业务路径形式；
- `serviceId` 是否为空；
- `offering` 看起来更熟悉；
- 是否关联指标；
- 是否有数据。

`offering`、`serviceId` 只在用户或 Skill 明确提供限定时用于过滤，否则只作为澄清证据。

## 9. 阶段 5：显式上下文过滤

精确或模糊召回多个同名/近似节点时，允许 Gateway 将用户已明确提供的限定传给 ontology，优先考虑当前节点已有真实属性：

```text
offering
serviceId
```

逻辑：

```text
name 分层召回
→ FETCH 真实属性
→ 仅按请求中明确给出的 offering/serviceId 过滤
→ 0：限定不匹配
→ 1：RESOLVED
→ 多个：AMBIGUOUS
```

示例：

```json
{
  "className": "operation_object",
  "name": "pps_click",
  "offering": "com.huawei.wiseeye"
}
```

应从两个精确同名候选中得到 wiseeye 对应节点。Gateway 和 Skill 不得凭当前会话以外的常识补充 offering。

## 10. 阶段 6：Gateway 状态编排

Gateway 调用策略：

```text
用户明确提供 instance_id
→ 保留原 ID 链路，不调用 name resolver

用户提供 name
→ 调 queryNode
   ├─ RESOLVED 且匹配策略允许自动锁定
   │   → 使用 candidate.vid 或现有链路要求的 ID
   │   → 复用原后续逻辑
   ├─ AMBIGUOUS/待确认
   │   → 返回最少必要候选
   │   → 不查拓扑
   └─ NOT_FOUND
       → 如实报告
```

候选展示优先使用：

```text
instanceName + offering + serviceId + matchLevel
```

`vid` 和 `instanceId` 可保留在机器响应中，但不必全部展示给最终用户。

## 11. 阶段 7：Skill 接入

等 ontology 和 Gateway 的人工接口测试稳定后再更新 Skill。Skill 负责：

- 判断是否是运维指标/拓扑请求；
- 抽取主体 name，不把完整问题传给 queryNode；
- 保留用户原始名称；
- 识别显式 offering/service 限定；
- `AMBIGUOUS` 时基于真实候选发起一次最小澄清；
- `NOT_FOUND` 时不创造别名或 ID；
- 只有 `RESOLVED` 才进入既有指标发现链路。

示例：

```text
用户：查询 wiseeye 的 pps_click 最近三天成功率

Skill：
name=pps_click
offering=com.huawei.wiseeye
metric=成功率
time=最近三天
```

如果 offering 过滤唯一，减少一次澄清；如果用户只说 `pps_click`，应展示两个 offering 让用户选择。

## 12. nGQL 构造安全

Tag 不能来自任意用户输入。当前只允许代码白名单中的 `operation_object`。

name 必须复用项目现有 nGQL 字符串转义/参数化能力。不得直接使用：

```java
String.format("... CONTAINS \"%s\"", userInput)
```

除非 `userInput` 已经经过项目统一的 nGQL 字面量编码器。至少正确处理：

```text
反斜杠
双引号
换行/控制字符
```

精确、前缀和包含三层必须共用同一个安全编码方法，不能只修其中一层。

## 13. 实施代码骨架

以下是控制流示例，不规定真实类名：

```java
public NodeQueryResult resolve(String rawName, NodeQueryFilter filter) {
    String normalized = normalizer.normalize(rawName);

    List<NodeCandidate> exact = queryAndFetch(
            MatchLevel.EXACT, normalized, EXACT_LIMIT);
    if (!exact.isEmpty()) {
        return decide(applyExplicitFilters(exact, filter), MatchLevel.EXACT);
    }

    List<NodeCandidate> prefix = queryAndFetch(
            MatchLevel.PREFIX, normalized, PREFIX_LIMIT);
    if (!prefix.isEmpty()) {
        return decideWeak(applyExplicitFilters(prefix, filter), MatchLevel.PREFIX);
    }

    if (!policy.allowContains(normalized)) {
        return NodeQueryResult.notFound();
    }

    List<NodeCandidate> contains = queryAndFetch(
            MatchLevel.CONTAINS, normalized, CONTAINS_LIMIT);
    return decideWeak(
            applyExplicitFilters(contains, filter), MatchLevel.CONTAINS);
}
```

查询构造示例：

```java
private String condition(MatchLevel level, String encodedName) {
    return switch (level) {
        case EXACT, NORMALIZED_EXACT ->
                "operation_object.instance_name == \"" + encodedName + "\"";
        case PREFIX ->
                "operation_object.instance_name STARTS WITH \"" + encodedName + "\"";
        case CONTAINS ->
                "operation_object.instance_name CONTAINS \"" + encodedName + "\"";
    };
}
```

此示例仅展示分支，不授权手写不安全转义；实际代码必须复用已有编码器。

查询与 FETCH 应继续分离：

```text
LOOKUP 返回 VID
→ FETCH PROP ON * 获取真实属性
→ 构造 NodeCandidate
```

## 14. 人工测试矩阵

由于当前无法由实施 Agent 运行 Maven/单元测试，每阶段由人工使用 IDE Maven 插件构建、彻底重启相关服务，再执行 PowerShell HTTP 测试。

建议维护固定测试表：

| 类别 | 输入 | 期望层级 | 期望状态 | 关键断言 |
|---|---|---|---|---|
| 精确唯一 | `event` | EXACT | RESOLVED | 唯一 wiseeye 节点 |
| 精确重复 | `pps_click` | EXACT | AMBIGUOUS | 两个 offering 均保留 |
| 前缀 | `pps` | PREFIX | AMBIGUOUS | 不选择任一 pps_click |
| 包含 | `click` | CONTAINS | 待确认/AMBIGUOUS | 只返回真实有限候选 |
| 未命中 | 长随机串 | 全部 | NOT_FOUND | 不编造候选 |
| 过短 | `p` | 拒绝 CONTAINS | NOT_FOUND/参数提示 | 不做宽扫描 |
| 特殊字符 | `a"\\%_` | 任意 | 安全失败或真实结果 | 不破坏 nGQL |
| 显式过滤 | `pps_click` + wiseeye offering | EXACT | RESOLVED | 选中真实 wiseeye 节点 |

每次记录：

```text
构建模块和 IDE Maven 生命周期
重启的服务
请求体
HTTP 响应
EXACT/PREFIX/CONTAINS 各层耗时和候选数
是否进入拓扑链路
```

## 15. 分阶段提交与回退

不要一次实现所有阶段。推荐每阶段单独保存可合并变更：

1. 候选证据与日志，不改变查询行为；
2. 规范化精确；
3. PREFIX；
4. 受限 CONTAINS；
5. 稳定排序；
6. offering/serviceId 显式过滤；
7. Gateway 与 Skill 策略更新。

任一阶段异常时应能关闭该层并回退到已验证的精确查询。可为 PREFIX/CONTAINS 设置配置开关；是否采用项目配置系统由实施仓规范决定。

## 16. 性能与质量验收

至少比较：

- 精确查询 P50/P95；
- 各模糊层 P50/P95；
- 每层数据库返回数和 FETCH 数；
- Top-K 真实节点召回率；
- 精确结果被模糊层改变的次数，必须为 0；
- 自动误选率，早期阶段目标为 0；
- 平均候选数；
- Gateway 到 Agent 的澄清轮次。

在不能修改索引的条件下，不能预先宣称 `CONTAINS` 会提升数据库速度。当前可验证的贡献是：精确查询短路、类型/Tag 约束、候选上限和减少 Agent 无效交互。若 PREFIX/CONTAINS 在真实环境不可接受，应停止上线该层，而不是改为无界全图扫描。

## 17. 当前阶段的下一条实施指令

首次改造只执行阶段 1 和阶段 2：

```text
保留精确查询
→ 增加确定性规范化
→ 精确为零时增加 PREFIX
→ PREFIX 候选一律不自动进入拓扑
→ 返回 matchLevel 和真实候选
```

暂不实现 CONTAINS、编辑距离、offering 自动过滤和 Skill 变更。先用 `event`、`pps_click`、`pps` 三个样例证明精确基线不退化且前缀层能受控召回。
