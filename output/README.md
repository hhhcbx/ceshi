# WF_Report_Crystallizer 测试数据说明

## 文件清单

| 文件 | 场景 | 预期分支 |
|------|------|----------|
| `test_data_TC01_NORMAL_FINISHED.json` | 面试正常结束 | `NORMAL` |
| `test_data_TC02_KILL_SWITCH.json` | 论文事实冲突触发守卫 | `KILL_SWITCH` |

## 在小艺开放平台试运行

1. 导入 `WF_Report_Crystallizer_MVP.json`
2. 打开工作流 **试运行**
3. 在「开始_报告结晶化」节点，将测试 JSON 中 `userFields`（及可选 `systemFields`）逐项填入对应输入参数
4. 观察选择器走向与最终 `markdown_report` 是否包含 6 个必填 section

## 预期行为

### TC01 — NORMAL

- 路径：`开始 → 评分量表 → 轨迹分组 → 选择器(NORMAL) → 大模型 → 完整性校验 → 流式输出 → 结束`
- `score_table` 四指标均有 0-5 分数与 evidence
- `kill_switch_info` 中 `triggered: false`

### TC02 — KILL_SWITCH

- 路径：`开始 → … → 选择器(KILL_SWITCH) → 大模型 → …`
- `kill_switch_info` 必须写明 `PAPER_FACT_CONFLICT` 及触发轮次 `t05`
- `score_table` 仍可输出，证据不足维度标注 `evidence_gap`

## 占位数据说明

所有 `_source: "[MOCK] ..."` 及 `_test_meta` 字段为测试/文档用途，**不要**传入生产工作流开始节点；接入时删除这些字段，改为上游真实输出。

## 可选第三场景（手动验证）

将 TC01 的 `session_state.is_finished` 改为 `false` 且清空 `kill_switch_reason`，可验证 **default / INCOMPLETE** 分支，输出占位报告而不调用全量 LLM。
