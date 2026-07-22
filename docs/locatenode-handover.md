# locateNode 接口交接文档

> 写给零上下文接手的 agent/工程师。看完本文你应该明白：这个接口为什么存在、它解决什么问题、开发过程中踩了哪些坑及根因、现在云上环境的硬性约束是什么。**在这套系统里写新接口之前，务必先读「云上环境铁律」一节，否则大概率重蹈「本地能跑、云上不行」的覆辙。**

## 1. 背景：我们在做什么

用户的最终目标是做一个**智能问数 agent**：用户用自然语言问「帮我找小艺的指标」，agent 通过一串 MCP 工具调用，从**货架数据模型**（华为 AIOps 体系，databp 微服务）中定位目标、取出指标定义，未来还要接指标数值和画图。

数据模型是一棵树：

- **分类节点**（导航骨架）：ID 是点分字符串，如 `business_and_platform.CEL`（小艺）、`business_and_platform.CEL.AIVision`。
- **逻辑实体/运维对象**（挂数据的叶子）：ID 是 UUID。指标（metrics）挂在逻辑实体上。

主链路：`定位分类节点(拿 id)` → `getNextLevelNode(id)` 取逻辑实体 → `getLogicEntityDefineInfo(实体id, parentOperObjId)` 取指标定义。

agent 侧的完整工作流见仓库里的 `skills/metric-query/SKILL.md`。

## 2. 为什么需要 locateNode

「定位分类节点」这一步最初依赖后端现成接口 `getModelTree`（databp 服务，`GET .../databp/v1/model/getModelTree`，无参数），它**一次性返回整棵树：全部分类 + 全部逻辑实体**。问题：

1. **数据量爆炸**：实体数量远大于分类数（一个分类下动辄 70+ 实体）。整树 JSON 直接进 LLM 上下文，触发上下文压缩，多调几次 agent 直接崩（`Agent execute failed: Stream processing failed`）。
2. **无法在中间层过滤**：
   - MCP 网关的 swagger response schema **只能做字段投影和深度截断，不能按字段值删节点**（没法表达「丢掉 UUID 实体、只留分类」）。
   - 前端页面是刷新时一次拉整树、纯前端展开，**后端没有「只取分类」「按父节点懒加载」的接口**，`getModelTree` 也无任何入参。
   - databp 的既有 get 系列接口**不允许修改**。
3. **让 LLM 自己在树里找节点不可靠**且费上下文。

结论：**在数据所在地（databp 服务内部）做服务端搜索**——新增 `locateNode(keyword)`，进程内拿全树、递归匹配、只返回命中节点的小结果。全量数据永远不出 databp，LLM 只看到几条匹配项。

## 3. 当前实现（已在云上跑通）

### 3.1 Controller（databp 服务，与 getModelTree 同一个 controller 类）

```java
@ApiOperation(value = "按关键词定位模型树节点",
              notes = "根据关键词在模型树中查找匹配的节点",
              tags = Constants.AUTH_WITH_PORTAL)   // 关键！必须与 getModelTree 一致
@GET
@Path("/locateNode")
public WiseEyeResponse locateNode(                  // 关键！裸 WiseEyeResponse，不带泛型
        @QueryParam("keyword") String keyword) {    // 关键！jakarta.ws.rs.QueryParam
    return WiseEyeResponse.createSuccess(dataModelService.locateNode(keyword));
}
```

### 3.2 Service（与 treeModelView 同一个 service 类，进程内调用）

```java
public List<NodeMatchDto> locateNode(String keyword) {
    String trimmed = keyword.trim();
    if (trimmed.isEmpty()) {
        return new ArrayList<>();
    }
    List<DataModelTreeNode> tree = treeModelView();   // 进程内直调，不走任何 HTTP
    List<NodeMatchDto> matches = new ArrayList<>();
    for (DataModelTreeNode root : tree) {
        search(root, trimmed.toLowerCase(), new ArrayList<>(), matches);
    }
    return matches;
}
// search(): 递归遍历，nameCn/nameEn/nameAliasCn/nameAliasEn 大小写不敏感 contains 匹配，
// 命中则记录 id/nameCn/nameEn/depth/path（path 为「根 > ... > 节点」的中文路径）
```

DTO：`com.huawei.aiops.databp.datamodel.dto.NodeMatchDto`（字段 `id/nameCn/nameEn/depth/path`，需有 public getter）。

### 3.3 MCP 工具注册（swagger 2.0 yaml，上传到 MCP 网关平台）

```yaml
/edge/WiseEyeAIOpsService/aiops/gateway/api/databp/v1/model/locateNode:
  get:
    operationId: "locateNode"
    parameters:
    - name: "keyword"
      in: "query"
      required: true
      type: "string"
    responses:
      "200":
        schema:
          $ref: "#/definitions/LocateNodeResponse"   # WiseEyeResponse 外壳 + data: NodeMatchDto 数组
```

云上真实地址：`https://console-wisedevops.hwcloudtest.cn/edge/WiseEyeAIOpsService/aiops/gateway/api/databp/v1/model/locateNode?keyword=...`

### 3.4 行为

- 输入：`keyword`（如 `小艺`）。中英文均可，大小写不敏感，「包含」即命中。
- 输出：`WiseEyeResponse`，`data` 为命中节点数组，含祖先与后代（如「小艺」会同时命中 `业务&平台>小艺` 与 `...>小艺_修图`）。
- ⚠️ **`depth` 字段不可靠**（存在深层节点 depth=1 的情况），用户决定暂不修。**层级判断一律用点分 ID 前缀关系**（`A` 是 `B` 的祖先 ⟺ `B` 以 `A+"."` 开头），不要用 depth。

## 4. 踩坑史与根因（按时间顺序，都是真实发生的）

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | 最初把 locateNode 写在 **topology gateway 服务**（`OntologyQueryController` + `ModelTreeCacheService`），用 `BackendService.get`/`ApigatewayBackendService` HTTP 调 databp 的 getModelTree：相对路径报 404 `NuwaAGW:Api Not Found`，绝对 URL 报 `NullPointerException: Endpoint`（URIAuthority 为 null），且异常被 catch 吞掉后表现为「0 matches 假成功」 | ① getModelTree 是 `AUTH_WITH_PORTAL` 门户接口，服务账号走 AGW 路由不到；② `BackendService` 需要预配置的服务名+相对路径，塞绝对 URL 拿不到 endpoint；③ gateway 与 databp **环境隔离，gateway 侧永远拿不到 databp 真实数据** | **彻底放弃 gateway + HTTP 方案**。locateNode 必须写进 databp 服务，进程内直调 `treeModelView()` |
| 2 | keyword 中文到服务端变 `??`（codePoints `[63,63]`） | 测试客户端（PowerShell `Invoke-RestMethod`）没按 UTF-8 发中文 | 客户端显式 UTF-8（`[System.Text.Encoding]::UTF8.GetBytes` + `charset=utf-8`）。服务端无问题 |
| 3 | 云上调用返回 `{"message": "Not Found"}` | 在 JAX-RS 风格 controller（`@GET`+`@Path`）里混用了 **Spring 的 `@RequestParam`**，ServiceComb 注册该 operation 失败 → 路由不存在 | 换成 `jakarta.ws.rs.QueryParam`。这类「参数注解体系混用」之前在 echoLog 调试时也踩过（nuwa 的 QueryParam 同样不行，会被当成 body 参数） |
| 4 | **本地测试完全正常，云上永远返回空 `{}`**（连 code/message 都没有）。写死返回值的探针也返回 `{}`，说明与数据/搜索逻辑无关 | `@ApiOperation` 的 `tags = Constants.AUTH_WITH_MACHINE`，而 getModelTree 用的是 `AUTH_WITH_PORTAL`。**tags 决定接口走哪套鉴权**；agent/MCP 链路提供的是门户会话，MACHINE 鉴权不过 → 网关静默返回空 `{}`（不报 401）。直连 curl 返回 `authorization is invalid` 提供了线索 | tags 改为 `Constants.AUTH_WITH_PORTAL`，与 getModelTree 完全一致。**这是最后一个也是最隐蔽的坑** |
| 5 | （调试中顺带修正）返回类型原为 `WiseEyeResponse<List<NodeMatchDto>>` | ServiceComb 从方法签名生成契约时，带泛型的返回类型可能解析异常 | 改为裸 `WiseEyeResponse`，与 getModelTree 对齐 |

## 5. 云上环境铁律（新接口 checklist，防止「本地能跑云上不行」）

在 databp/这套 ServiceComb + Nuwa 体系里给 agent 加新接口时，**逐条对照**：

1. **写在 databp 服务里**，且与 `getModelTree` 同一个 controller 类（同一个 `@RestSchema`）。需要树数据时**进程内调 `dataModelService.treeModelView()`**。
2. **禁止**用 `BackendService` / `ApigatewayBackendService` 跨服务 HTTP 取数——这条链路在云上已被证明不通（404/NPE）。跨服务需求走 `um.databp.invoke` 现成 SDK（如 `FieldRelationInvokeService` 的用法），没有现成方法就把逻辑挪到数据所在服务。
3. **注解只用 JAX-RS（`jakarta.ws.rs.*`）**：`@GET/@POST/@Path/@QueryParam/@PathParam`。**绝不**混入 Spring 的 `@RequestParam/@GetMapping`、nuwa 的 `QueryParam`、Spring 的 `MediaType`（注解常量需编译期常量，Spring MediaType 是对象，会报 `Attribute value must be constant`；要用就用 `jakarta.ws.rs.core.MediaType`）。
4. **`@ApiOperation` 的 `tags` 必须是 `Constants.AUTH_WITH_PORTAL`**（与 getModelTree 一致）。用 `AUTH_WITH_MACHINE` 会导致 agent 链路鉴权静默失败，云上表现为返回空 `{}`。
5. **返回类型用裸 `WiseEyeResponse`**，不带泛型。
6. DTO 放 `com.huawei.aiops.databp.datamodel.dto`，**必须有 public getter**（Jackson 序列化靠 getter；内部类 + Lombok 有过不生效的先例，稳妥起见手写或用独立类）。
7. 改完代码：**重新构建并部署云上 databp** → **MCP 平台上传/刷新 yaml 契约**。两步缺一不可，契约缓存旧签名会导致各种诡异 400/404。
8. yaml 契约与代码必须对齐：代码是 query 参数，yaml 就写 `in: query`；body 参数（swagger 2.0）必须用 `schema: $ref`，不能带 `type`。response schema 是**字段白名单**（没声明的字段会被网关投影裁掉），声明结构与真实返回结构不匹配会被裁成空。
9. 中文参数测试时客户端务必显式 UTF-8；稳妥做法是中文走 POST body（JSON）。
10. 本地起服务的已知坑：JCE 报 `cannot authenticate the provider BC`（nuwa-share-libs 内嵌 bcprov 未签名）→ 从 Maven 中央仓库下载官方签名版 `bcprov-jdk18on-1.78.1.jar`，在 IDEA Project Structure → Modules → Dependencies 加入并**置顶**（不要用 `-Xbootclasspath`，会因 CodeSource URL 为 null 而 NPE）。

## 6. 调试方法论（这次验证有效，推荐沿用）

- **写死返回探针**：接口直接返回 hardcode 数据，一次性区分「数据问题」vs「契约/序列化/鉴权问题」。云上连 hardcode 都返回 `{}`，就与业务逻辑无关。
- **DIAG 探针**：把「收到的入参原文 + 数据源 size」塞进返回体，绕过看不到服务端日志的限制。
- **直连 curl 对比**：绕开 agent 直接打云上 URL，把「MCP 层问题」与「后端问题」切开。本次 `authorization is invalid` 直接指向了鉴权 tag 差异。
- **与已知能用的接口逐项对比**：getModelTree 是「云上确认能用」的基准，locateNode 每个坑最终都是靠「找出与 getModelTree 的差异」定位的（注解体系、返回类型、鉴权 tag）。**新接口一切向能用的基准看齐。**

## 7. 遗留问题与注意事项

- **`depth` 不可靠**：已知 bug，用户暂不修。任何层级逻辑用点分 ID 前缀，别碰 depth。
- **`getNextLevelNode` 递归返回全部后代实体且无分页**：对高层分类调用会返回巨量数据。agent 侧靠 `skills/metric-query/SKILL.md` 的「最小覆盖根剪枝 + 只对剪枝后节点调用」控制。若未来单分类实体数失控，需要推动后端加分页/过滤（目前 databp 不可改）。
- **`getLogicEntityRealModel` 已返回已部署指标（含 SQL）**，不是空对象。后续数值/画图链路：选定逻辑实体与指标 → 调该接口取 SQL → 在只读数据通道执行 → 按 `output-format.md` 绘图。执行通道与权限不在 databp 本接口内。
- **`locateNode` 匹配算法是朴素 contains**：关键词必须出现在节点名/别名中。口语化指标定位（概念不在节点名里、多指标口径歧义）不靠继续堆同义词解决，而走**本体语义层**（见 `docs/metric-ontology-enhancement.md` 与 `ontology/metric-shelf/`），由 Skill Stage 1.5 / 5.7 锚定与消歧。
- **平台鉴权语义**：agent/MCP 链路 = 门户会话（PORTAL）。若未来出现「必须 MACHINE 鉴权」的接口需求，需先在平台侧确认 agent 能否携带服务账号凭据，别直接写代码试。

## 8. 相关文件

| 位置 | 内容 |
|---|---|
| `skills/metric-query/SKILL.md` | agent 工作流（意图→本体锚定→定位→剪枝→取实体→取指标→筛选→消歧→呈现→可选 RealModel 取数） |
| `skills/metric-query/references/tools.md` | MCP 工具入参/出参/要点（含 getLogicEntityRealModel） |
| `skills/metric-query/references/output-format.md` | 指标字段规范、筛选映射、表格/消歧/图表模板 |
| `skills/metric-query/references/ontology.md` | 本体锚定与消歧规程 |
| `docs/metric-ontology-enhancement.md` | 指标增强：本体语义层方案 |
| `ontology/metric-shelf/` | TBox + 运行时 concepts.yaml |
| databp 服务代码（不在本仓库） | locateNode controller/service/DTO，与 getModelTree 同类 |
| MCP 平台的 swagger yaml（不在本仓库） | 工具注册契约，最新版含 locateNode，见第 3.3 节 |

## 9. 快速验证（接手后先跑一遍）

1. 经 agent 调 `locateNode`，keyword=`小艺`：应返回多条命中（含 `业务&平台 > 小艺` 及其后代），`data` 非空、每条有 `id/nameCn/nameEn/path`。
2. keyword 用不存在的词：应返回 `data: []`（空数组），而不是 `{}`。**若看到纯 `{}`，第一时间查鉴权 tag 和契约（见第 4 节坑 4）。**
3. 改动任何后端代码后：重部署 databp → 刷新 MCP 契约 → 先跑 1、2 再继续开发。
