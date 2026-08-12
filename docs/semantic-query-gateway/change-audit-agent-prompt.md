# 三项目未纳入 Git 的改动盘点提示词

> 用途：直接复制给能够访问实际 Java 工作区的实施 Agent。目标不是评审设计，而是在没有可靠 Git 变更记录时，尽可能完整地恢复本次功能改动清单，为后续人工合并提供依据。

```text
你现在执行“未纳入 Git 的改动审计”，不要继续实现功能，也不要运行 Maven。

## 背景和目标

本次功能横跨以下三个项目：

1. WiseEyeAIOpsTopologyGatewayService
2. WiseEyeAIOpsTopologyService
3. um-master

已验证的外部行为是：

- ontology 的 queryNode 接受 className=operation_object、name；
- 精确名称 pps_click 返回 AMBIGUOUS 和两个真实候选；
- 精确名称 event 返回 RESOLVED 和唯一候选；
- Gateway 的 ontology/instance 已能通过机机调用消费上述结果；
- Gateway 返回的候选字段包括 vid、instanceId、instanceName、serviceId、offering、tags；
- 当前工作区改动没有被可靠地纳入 Git 管理，后续合并不能漏文件。

你的唯一目标是：找出这三个项目中为该功能新增或修改的所有文件、代码位置、接口合同、依赖关系和部署顺序，形成一份可供人工合并逐项核对的 Markdown 文档。

## 重要限制

- 不要运行 mvn、gradle 或任何依赖下载命令；命令行 Maven 无私库权限。
- 不要新增、删除或修改业务代码。
- 不要要求我提供 Git diff；Git 状态不可靠，只能作为辅助证据。
- 不要声称要逐行阅读三个项目的全部代码，也不要因代码量大而停止。
- 使用“入口驱动 + 符号搜索 + 调用链追踪 + 交叉引用”的方法收敛范围。
- 可以使用 rg、find、git status、git log、git diff、文件时间等只读命令；禁止 rg -R/grep -R 和 ls -R。
- 即使 git status 显示干净，也不能据此断言没有改动。
- 不要把 target、logs、IDE 元数据、生成物列为源代码改动，除非它们承载必须合并的手写配置。

## 一、先建立功能符号清单

在三个项目分别搜索以下精确符号和字符串，并记录所有命中文件：

queryNode
NodeQueryService
NodeQueryInterface
NodeQueryRequest
NodeQueryResult
NodeCandidate
QueryResult
RESOLVED
AMBIGUOUS
NOT_FOUND
QUERY_NODE_PROVIDER_V1
QUERY_NODE_CONSUMER_V1
QUERY_NODE_RESPONSE_V1
queryInstanceByName
route=BY_NAME
operation_object
start_node_name
instanceName
instanceId
offering

建议使用类似命令，但按实际目录调整：

rg -n --hidden --glob '!target/**' --glob '!logs/**' --glob '!.idea/**' \
  'queryNode|NodeQueryService|NodeQueryInterface|NodeQueryResult|NodeCandidate|RESOLVED|AMBIGUOUS|NOT_FOUND|queryInstanceByName|QUERY_NODE_' <项目目录>

把首次命中的文件形成“候选改动文件集合”，不要只看文件名中含 NodeQuery 的文件。

## 二、从两个 HTTP 入口反向追踪

### ontology provider 入口

从实际成功路径开始：

POST /topo/v1/externalController/queryNode

沿调用链追踪并记录：

Controller/producer interface
→ 请求 DTO
→ NodeQueryService
→ NebulaQueryExecutor
→ LOOKUP 返回 VID
→ FETCH 获取属性
→ NodeCandidate/QueryResult
→ 外层响应包装

必须找出：

- 新增的方法声明是否同时存在于共享接口和实现类；
- provider 暴露 ServiceComb operation 所需的接口、注解或契约文件；
- 精确 LOOKUP/FETCH 语句所在位置；
- NOT_FOUND/RESOLVED/AMBIGUOUS 的定义和分支；
- vid 与 instanceId 分开的模型位置；
- topology 字段是否仍被 queryNode 填充。

### Gateway 入口

从实际成功路径开始：

POST /topology-gateway/v1/knowledge/ontology/instance

沿调用链追踪并记录：

Controller
→ 请求 DTO 的 class_name/name/instance_id
→ OntologyQueryService
→ SchemaInstanceService 的 BY_ID/BY_NAME 路由
→ queryNode consumer/client
→ 共享接口/响应泛型
→ AMBIGUOUS/RESOLVED/NOT_FOUND 映射
→ Gateway 响应模型

必须找出：

- name 字段在哪些 DTO/接口间传递；
- BY_NAME 在哪里提前返回，是否绕过旧 InstanceInvokerRegistry；
- CSE 目标 service/path 在哪里定义；
- code=0 的成功判断在哪里修复；
- consumer 的 data 泛型和候选 DTO；
- RESOLVED 是否已进入旧 ID 后续链路，还是当前只返回 candidate；
- 临时诊断日志是否仍存在。

## 三、专项审计 um-master

um-master 很可能承载共享机机接口和 DTO。不要扫描后就只写“有/无改动”，必须回答：

- provider 和 consumer 是否依赖同一个 queryNode 接口声明；
- 新增的方法签名、HTTP method、path；
- 请求与响应类型；
- 新增/修改的 DTO 字段及 JSON 命名；
- 泛型从 List<NodeInfo> 到 NodeQueryResult 等变化；
- 哪些模块必须先通过 IDE Maven 插件 install，另外两个项目才能编译；
- 是否存在只修改了一端、另一端使用了本地复制 DTO 的情况。

## 四、用多种证据判定“可能改过”

对候选文件逐个使用以下证据，不要求每种证据都存在：

1. Git 工作树和暂存区差异；
2. 与当前分支 HEAD 的差异；
3. 文件创建/修改时间与本次开发窗口；
4. 新功能专属符号；
5. 同一接口在 provider、consumer、shared API 的闭包关系；
6. 注释、临时日志、TODO 和未使用类型；
7. 调用者和被调用者是否同时有对应变化。

若有可访问的干净基线目录、旧压缩包或旧分支，优先逐文件比较。若没有基线，必须把结论标成：

- CONFIRMED：有 diff/基线或明显新增文件证据；
- HIGH_CONFIDENCE：无基线，但包含本次独有符号且位于完整调用链；
- POSSIBLE：可能受影响，需要人工复核；
- GENERATED/IRRELEVANT：生成物或无关文件，不纳入合并。

不得把 HIGH_CONFIDENCE 写成百分之百确认。

## 五、检查容易遗漏的外围文件

必须专项搜索并说明是否变化：

- controller/producer interface；
- consumer/client interface；
- request/response DTO；
- JSON/Swagger/OpenAPI/ServiceComb 契约；
- constants 和 URL/path；
- registry/adapter/invoker；
- exception/status enum；
- Spring/ServiceComb 配置；
- module pom 依赖或共享接口版本；
- 测试或 PowerShell/curl 验证脚本；
- 临时日志标记。

## 六、输出文档结构

将结果写入一个新的 Markdown 文档，不覆盖业务代码。文档必须包含：

### 1. 审计范围与限制

写清三个项目根目录、审计时间、没有可靠 Git 基线的限制，以及采用的调查方法。

### 2. 端到端调用链

用文本图列出当前实际调用链和每一步所在项目/文件/方法。

### 3. 确认/高置信改动文件总表

表格字段必须是：

| 项目 | 文件相对路径 | 状态 | 新增/修改 | 相关符号/行号 | 改动目的 | 合并依赖 | 证据 |

每个文件一行，不能只列目录。

### 4. 每个文件的改动明细

对每个 CONFIRMED/HIGH_CONFIDENCE 文件列出：

- 类/接口/方法；
- 修改前职责（能从基线确认时）；
- 当前职责；
- 新增或变化的字段/方法/分支；
- 与其他项目文件的依赖；
- 合并时若遗漏会造成的具体症状。

### 5. POSSIBLE 文件

单列可能受影响但证据不足的文件，并写明人工复核方法。

### 6. 机机接口合同

完整记录 queryNode 的请求、NOT_FOUND、RESOLVED、AMBIGUOUS 响应及字段命名；记录 provider path 和 Gateway consumer target。

### 7. 合并顺序

按依赖给出人工合并顺序，例如：

um-master 共享接口/DTO
→ WiseEyeAIOpsTopologyService provider
→ WiseEyeAIOpsTopologyGatewayService consumer/路由

只有代码事实支持时才采用该顺序。

### 8. IDE Maven 构建与重启清单

不要写命令行 mvn。写明哪些 module 需要在 IDE Maven 插件中 install/compile，以及应重启哪些服务。

### 9. 人工验收命令

给出 PowerShell Invoke-RestMethod 或 curl.exe 命令，覆盖：

- provider 直接查询 pps_click → AMBIGUOUS；
- provider 查询 event → RESOLVED；
- Gateway 查询 pps_click → AMBIGUOUS；
- Gateway 查询 event → RESOLVED；
- NOT_FOUND；
- 原 ID 路径（仅当当前合同支持）。

### 10. 合并核对清单

每项使用 Markdown checkbox，确保共享接口、provider、consumer、DTO、路由、状态映射、异常、临时日志清理和人工测试都不会遗漏。

## 七、完整性复核

初稿完成后不要立即结束。执行一次反向复核：

- 从每个新增 DTO 查找所有引用；
- 从 queryNode path 查找 provider 和 consumer 两端；
- 从三个 status 查找所有 switch/if；
- 从 name 字段查找请求入口到 provider 的每次转换；
- 从 vid/instanceId 查找是否被混用；
- 从新增文件反查 pom/module 是否需要依赖变化。

把复核中新发现的文件补进总表。

## 八、最终回复

只报告：

1. 文档路径；
2. CONFIRMED、HIGH_CONFIDENCE、POSSIBLE 文件数量；
3. 三项目各自的文件清单；
4. 仍无法确认的风险；
5. 推荐合并顺序；
6. 不要声称已运行 Maven 或单元测试。
```
