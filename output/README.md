# WF_Report_Crystallizer 工作流说明

## 两个版本（请先导入可运行版）

| 文件 | 用途 | 结构 |
|------|------|------|
| **`WF_Report_Crystallizer_MVP_1-V0_minimal.json`** | **确保能运行** | `START → LLM → Output → End` |
| `WF_Report_Crystallizer_MVP_1-V0_full.json` | 完整业务逻辑 | `START → 拼接×2 → 选择器 → LLM/占位 → 汇聚 → Output → End` |

### 可运行版（minimal）

- 无文本预处理节点、无选择器
- 评分量表与轨迹分组逻辑**内嵌在 LLM System/User Prompt**
- 与 `WF_Interview_Session_Engine_MVP_1` 同样简洁，已验证可跑通的路径

### 完整逻辑版（full）

| 分支 | 条件 | 路径 | 行为 |
|------|------|------|------|
| KILL_SWITCH | `kill_switch_reason` 非空 | 预处理 → **LLM** → 校验 → 汇聚 | 异常结束报告 |
| NORMAL | `is_finished=true` 且无 kill_switch | 预处理 → **LLM** → 校验 → 汇聚 | 完整终版报告 |
| INCOMPLETE（否则） | 其他 | 预处理 → **占位拼接** → 汇聚 | **不调用 LLM** |

文本节点已拆为独立「字符串拼接_xxx」组件：
- 描述仅保留拼接模式，**已移除 split 相关配置字段**
- 统一输出字段名为 `output`（避免平台切换拼接/分隔后模板丢失）

## 测试数据

| 文件 | 场景 | 用于版本 |
|------|------|----------|
| `test_data_TC01_试运行专用.json` | NORMAL 快速试跑 | minimal / full |
| `test_data_TC01_NORMAL_FINISHED.json` | 正常结束 | full |
| `test_data_TC02_KILL_SWITCH.json` | 守卫触发 | full |

试运行时请在开始节点同时传入顶层字段（与 `session_state` 保持一致）：

```json
"is_finished": true,
"kill_switch_reason": ""
```

## 推荐步骤

1. 先导入 **`WF_Report_Crystallizer_MVP_1-V0_minimal.json`**，用 `test_data_TC01_试运行专用.json` 验证
2. 确认能跑通后，再导入 **`WF_Report_Crystallizer_MVP_1-V0_full.json`** 验证三分支
3. INCOMPLETE 测试：将 `is_finished` 设为 `false`，`kill_switch_reason` 留空

## 重新生成 JSON

```bash
python3 scripts/build_workflow_versions.py
```
