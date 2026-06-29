#!/usr/bin/env python3
"""Build the production-ready WF_Report_Crystallizer workflow JSON."""

import json
from copy import deepcopy

# ---------------------------------------------------------------------------
# Shared field helpers
# ---------------------------------------------------------------------------

def input_field(name, ftype, required=True, description="", value=""):
    return {
        "name": name,
        "type": ftype,
        "required": required,
        "description": description,
        "value": value,
        "sourceType": "input",
        "expanded": False,
        "descExpanded": False,
    }


def output_field(name, ftype, required=True, description=""):
    return {
        "name": name,
        "type": ftype,
        "required": required,
        "description": description,
    }


def text_processing_node(
    node_id,
    label,
    position,
    inputs,
    outputs,
    concat_template,
    functionality="concat",
):
    return {
        "id": node_id,
        "type": "jiuwen.TextProcessingComponent",
        "dimensions": {"width": 248, "height": 147},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": position,
        "events": {},
        "label": label,
        "description": "对前序节点输入的内容进行字符串拼接、字符串分隔",
        "inputs": [{"name": "userFields", "fields": inputs}],
        "outputs": [{"name": "preDefinedFields", "fields": outputs}],
        "configs": {
            "functionality": functionality,
            "listJoinString": "\n",
            "concatTemplate": concat_template,
            "splitStringList": [],
            "customSeparatorList": [],
            "customConnectionList": [],
        },
    }


SCORE_RUBRIC_TEMPLATE = """# 固定评分量表 Score Rubric v1.0
<!-- [MOCK/PLACEHOLDER] prompt_pack 来自上游 WF_PromptPack，将来替换为真实数据 -->

## 元信息
- rubric_version: 1.0.0
- session_id: {session_state}
- candidate: {candidate_profile}

## 评分维度（每项 0-5 整数分，必须附 evidence 原话引用）

### core_component_innovation
| 分数 | 锚点描述 |
|------|----------|
| 0 | 无法说明任何组件职责 |
| 1 | 仅列举组件名称，无创新点 |
| 2 | 描述 1 个组件的基本实现 |
| 3 | 说明 2+ 组件协作与创新动机 |
| 4 | 有量化指标或对比实验支撑 |
| 5 | 清晰架构演进路径与可复用抽象 |

### state_machine_flow_control
| 分数 | 锚点描述 |
|------|----------|
| 0 | 不理解状态机或流程控制 |
| 1 | 能说出状态名称但无法解释转移条件 |
| 2 | 能描述线性流程，缺少分支/异常处理 |
| 3 | 能说明关键状态转移与守卫条件 |
| 4 | 能设计可恢复/可回滚的状态机 |
| 5 | 能结合业务场景优化状态粒度与并发控制 |

### prompt_engineering_defense
| 分数 | 锚点描述 |
|------|----------|
| 0 | 无法解释 Prompt 设计 |
| 1 | 仅复述模板，无防御策略 |
| 2 | 有基础 system/user 分层 |
| 3 | 有输入校验或 guard 联动说明 |
| 4 | 有多层防御（guard + 事实约束 + 拒答策略） |
| 5 | 有可观测的 prompt 版本管理与 A/B 证据 |

### data_crystallization_presentation
| 分数 | 锚点描述 |
|------|----------|
| 0 | 输出混乱，无法阅读 |
| 1 | 有文本但缺少结构 |
| 2 | 有基础 Markdown 分段 |
| 3 | 必填 section 齐全但证据薄弱 |
| 4 | section 齐全且 evidence 可溯源 |
| 5 | 报告可直接用于次日准备与决策 |

## 评分硬性规则
1. 仅依据 conversation_trace 原话与 paper_facts 评分，禁止臆测。
2. 证据不足时该维度 score=0，evidence 写 "evidence_gap"。
3. 四维度分数方差 > 2 时，在 score_table 备注 "score_variance_high"。
4. 若 prompt_pack 含 scoring_override，以 override 为准（当前为占位）。

prompt_pack 快照: {prompt_pack}"""


TRACE_GROUPER_TEMPLATE = """# 会话轨迹阶段分组 Stage-Grouped Conversation Trace
<!-- [MOCK/PLACEHOLDER] conversation_trace 来自上游 WF_Interview，将来替换为真实数据 -->

## 报告模式 report_mode（由 session_state 推导，报告节点必须遵守）
判定规则（按优先级）：
1. session_state.kill_switch_reason 非空 → report_mode=KILL_SWITCH
2. session_state.is_finished == true 且无 kill_switch → report_mode=NORMAL
3. 其他 → report_mode=INCOMPLETE

当前 session_state: {session_state}

## X 阶段｜基础认知与论文事实核验（stage_id=X）
筛选规则: conversation_trace.turns 中 stage=="X" 或 stage_id==1 或 round_type=="foundation"
<!-- 平台文本节点无法做 JSON 过滤，以下由 LLM 按规则从原始 trace 中提取 -->

## Y 阶段｜深度技术追问（stage_id=Y）
筛选规则: stage=="Y" 或 stage_id==2 或 round_type=="deep_dive"

## Z 阶段｜综合评估与反问（stage_id=Z）
筛选规则: stage=="Z" 或 stage_id==3 或 round_type=="synthesis"

## 分组统计（LLM 生成报告前必须计算）
- total_turns: conversation_trace.turns 长度
- x_turns / y_turns / z_turns: 各阶段轮次数
- guard_triggered_count: guard_status.triggered 为 true 的次数

guard_status: {guard_status}
paper_status: {paper_status}

## 原始 conversation_trace（完整备份，禁止删改）
{conversation_trace}

## 附：评分量表
{score_rubric}"""


SCHEMA_CHECK_TEMPLATE = """# 报告完整性校验 Report Schema Validation
<!-- 校验节点：检查 LLM 输出是否包含全部必填 section -->

## 必填 Section 清单（缺一不可）
- ## candidate_summary
- ## interview_rounds
- ## score_table
- ## kill_switch_info
- ## paper_facts_snapshot
- ## next_day_prep_actions

## score_table 必填指标
- core_component_innovation
- state_machine_flow_control
- prompt_engineering_defense
- data_crystallization_presentation

## 校验结果（文本节点静态模板 + LLM 自检）
validation_status: PENDING_LLM_SELF_CHECK
regenerate_hint: 若缺少任一 section 或 score_table 缺指标，必须补全后输出，禁止输出半成品。

---

## 待校验报告正文
{markdown_report}"""


INCOMPLETE_SESSION_TEMPLATE = """# 面试报告（会话未完成）

> **report_mode**: INCOMPLETE
> **说明**: 会话尚未结束（`session_state.is_finished != true`），本节点跳过 LLM 全量报告生成。
> **[MOCK/PLACEHOLDER]** 将来由上游 session_state 驱动真实状态。

## candidate_summary
- 候选人: {candidate_profile}
- 会话状态: 进行中，暂不可生成终版结晶化报告

## interview_rounds
{conversation_trace}

## score_table
| 指标 | 分数 | evidence |
|------|------|----------|
| core_component_innovation | N/A | 会话未完成 |
| state_machine_flow_control | N/A | 会话未完成 |
| prompt_engineering_defense | N/A | 会话未完成 |
| data_crystallization_presentation | N/A | 会话未完成 |

## kill_switch_info
- triggered: false
- reason: （无）

## paper_facts_snapshot
{paper_facts}

## next_day_prep_actions
1. 继续完成剩余面试轮次后再触发报告结晶化工作流。
2. 检查 session_state.is_finished 是否为 true。
3. 确认 conversation_trace 已包含 X/Y/Z 三阶段记录。"""


LLM_PROMPT = """你是「面试报告结晶化引擎」。根据结构化输入生成 **仅含事实** 的 Markdown 报告。

## 输入说明
- candidate_profile: 候选人画像
- paper_facts: 论文/项目事实（唯一事实源，禁止编造）
- prompt_pack: Prompt 包（含评分覆盖规则）
- session_state: 会话状态（含 is_finished、kill_switch_reason）
- grouped_conversation_trace: 已按 X/Y/Z 阶段分组的会话轨迹与 report_mode 判定规则
- score_rubric: 固定评分量表（降低打分随机性）
- guard_status / paper_status: 守卫与论文事实状态

grouped_conversation_trace:
{grouped_conversation_trace}

score_rubric:
{score_rubric}

candidate_profile: {candidate_profile}
paper_facts: {paper_facts}
prompt_pack: {prompt_pack}
session_state: {session_state}
guard_status: {guard_status}
paper_status: {paper_status}

## report_mode 行为（必须遵守 grouped_conversation_trace 中的判定）
### KILL_SWITCH
- 生成 **异常结束报告**；kill_switch_info 必须写明 reason、触发轮次、影响范围。
- score_table 仍须输出四指标，证据不足写 evidence_gap。

### NORMAL
- 生成 **完整终版报告**；interview_rounds 按 X→Y→Z 展示，每轮含 question/answer/evidence。

### INCOMPLETE
- 不应到达本节点（由选择器走未完成分支）；若到达，输出简短说明并标注 incomplete。

## 输出格式（严格 Markdown，必须包含以下二级标题，顺序不限）
## candidate_summary
## interview_rounds
## score_table
## kill_switch_info
## paper_facts_snapshot
## next_day_prep_actions

## score_table 格式
| metric | score(0-5) | evidence | notes |
|--------|------------|----------|-------|
| core_component_innovation | | | |
| state_machine_flow_control | | | |
| prompt_engineering_defense | | | |
| data_crystallization_presentation | | | |

## 硬性约束
1. 禁止编造 conversation_trace / paper_facts 中不存在的问答或事实。
2. 每条 evidence 必须可追溯到原话（引用 turn_id 或原文片段）。
3. 缺少必填 section 视为无效输出——生成前自检，缺则补全。
4. 只输出 Markdown 报告正文，不要输出 JSON 包裹或解释性前言。"""


def build_workflow():
    start_id = "STARTReportCrystallizer875c481ae73b4d52bb5faa33eef6"
    rubric_id = "TextHandlerReportRubric429eff27957240f983f01908dfe3"
    grouper_id = "TextHandlerReportTraceGroupd4426f2203e049d39e22d0816fc1"
    branch_id = "BranchReportModed7f02c7f85e54778958b9fd69f25"
    llm_id = "LLMGenerateReport25a1ac0d86304dd7aaf1c640d43d"
    schema_id = "TextHandlerReportCheckb2e54f0b570641ed8100b7b54c14"
    incomplete_id = "TextHandlerIncompleteSession8c3a1f2b9d4e5f60718293a4b5c6d7e"
    output_id = "outputComponentReportOutputa8358d502a2844e1bbc0455a26cc"
    output_incomplete_id = "outputComponentIncompleteOut9f8e7d6c5b4a39281706f5e4d3c2b1a"
    end_id = "ENDReportCrystallizerf0e92736ebd7431182823565ddf8"
    end_incomplete_id = "ENDReportIncomplete5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d"

    start_node = {
        "id": start_id,
        "type": "agentStart",
        "dimensions": {"width": 248, "height": 141},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 0, "y": 0},
        "events": {},
        "label": "开始_报告结晶化",
        "description": "工作流入口：接收候选人画像、论文事实、会话状态、问答轨迹等上游数据",
        "outputs": [
            {
                "name": "systemFields",
                "fields": [
                    {
                        "name": "USER_INPUT",
                        "type": "String",
                        "description": "本次对话输入内容",
                        "required": False,
                        "value": "",
                        "sourceType": "ref",
                        "expanded": False,
                        "descExpanded": True,
                        "fieldType": "systemFields",
                    },
                    {
                        "name": "FILES_INPUT",
                        "type": "Array<String>",
                        "description": "本次对话上传的文件地址",
                        "required": False,
                        "value": "",
                        "sourceType": "ref",
                        "expanded": False,
                        "descExpanded": False,
                        "fieldType": "systemFields",
                    },
                    {
                        "name": "EVENT_INPUT",
                        "type": "Object",
                        "description": "本次对话的事件内容",
                        "required": False,
                        "value": "",
                        "sourceType": "ref",
                        "expanded": False,
                        "descExpanded": False,
                        "fieldType": "systemFields",
                    },
                ],
            },
            {
                "name": "userFields",
                "fields": [
                    {
                        "name": "candidate_profile",
                        "type": "Object",
                        "required": True,
                        "description": "候选人画像 [上游: WF_ProfileBuilder]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "paper_facts",
                        "type": "Object",
                        "required": True,
                        "description": "论文事实 [上游: WF_PaperFactExtractor]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "prompt_pack",
                        "type": "Object",
                        "required": False,
                        "description": "Prompt 包 [上游: WF_PromptPack]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "session_state",
                        "type": "Object",
                        "required": True,
                        "description": "会话状态 [上游: WF_SessionManager]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "conversation_trace",
                        "type": "Object",
                        "required": True,
                        "description": "问答记录 [上游: WF_Interview]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "guard_status",
                        "type": "Object",
                        "required": False,
                        "description": "输入守卫状态 [上游: WF_InputGuard]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                    {
                        "name": "paper_status",
                        "type": "Object",
                        "required": False,
                        "description": "论文事实状态 [上游: WF_PaperFactValidator]",
                        "value": "",
                        "sourceType": "ref",
                        "fieldType": "userFields",
                    },
                ],
            },
        ],
    }

    rubric_node = text_processing_node(
        rubric_id,
        "预处理_评分量表构建",
        {"x": 280, "y": 0},
        [
            input_field("candidate_profile", "Object", True, "候选人画像"),
            input_field("session_state", "Object", True, "会话状态"),
            input_field("prompt_pack", "Object", False, "Prompt 包"),
            input_field("conversation_trace", "Object", True, "用于评分上下文"),
        ],
        [
            output_field("score_rubric", "String", True, "固定评分量表文本"),
        ],
        SCORE_RUBRIC_TEMPLATE,
    )

    grouper_node = text_processing_node(
        grouper_id,
        "预处理_轨迹按阶段分组",
        {"x": 560, "y": 0},
        [
            input_field("conversation_trace", "Object", True, "问答记录"),
            input_field("session_state", "Object", True, "会话状态"),
            input_field("score_rubric", "String", True, "评分量表"),
            input_field("guard_status", "Object", False, "守卫状态"),
            input_field("paper_status", "Object", False, "论文状态"),
        ],
        [
            output_field(
                "grouped_conversation_trace",
                "String",
                True,
                "按 X/Y/Z 分组后的轨迹与 report_mode 规则",
            ),
        ],
        TRACE_GROUPER_TEMPLATE,
    )

    branch_node = {
        "id": branch_id,
        "type": "AgentBranch",
        "dimensions": {"width": 248, "height": 149},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 840, "y": 0},
        "events": {},
        "label": "选择器_报告模式",
        "description": "按 session_state 选择报告生成路径：KILL_SWITCH > NORMAL > INCOMPLETE(否则)",
        "branches": [
            {
                "id": "KILL_SWITCH",
                "condition": "&&",
                "expression": [
                    {
                        "leftVar": {
                            "sourceType": "input",
                            "value": "session_state.kill_switch_reason",
                            "fieldType": "String",
                            "label": "session_state.kill_switch_reason",
                        },
                        "condition": "!=",
                        "rightVar": {
                            "sourceType": "input",
                            "value": "",
                            "fieldType": "String",
                            "label": "",
                        },
                    }
                ],
            },
            {
                "id": "NORMAL",
                "condition": "&&",
                "expression": [
                    {
                        "leftVar": {
                            "sourceType": "input",
                            "value": "session_state.is_finished",
                            "fieldType": "Boolean",
                            "label": "session_state.is_finished",
                        },
                        "condition": "==",
                        "rightVar": {
                            "sourceType": "input",
                            "value": "true",
                            "fieldType": "Boolean",
                            "label": "true",
                        },
                    },
                    {
                        "leftVar": {
                            "sourceType": "input",
                            "value": "session_state.kill_switch_reason",
                            "fieldType": "String",
                            "label": "session_state.kill_switch_reason",
                        },
                        "condition": "==",
                        "rightVar": {
                            "sourceType": "input",
                            "value": "",
                            "fieldType": "String",
                            "label": "",
                        },
                    },
                ],
            },
            {"id": "default"},
        ],
    }

    llm_node = {
        "id": llm_id,
        "type": "AgentLargeModel",
        "dimensions": {"width": 248, "height": 277},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1120, "y": -80},
        "events": {},
        "label": "大模型_生成结晶化报告",
        "description": "调用大模型生成结构化 Markdown 结晶化报告",
        "inputs": [
            {
                "name": "userFields",
                "fields": [
                    input_field("candidate_profile", "Object", True, "候选人画像"),
                    input_field("paper_facts", "Object", True, "论文事实"),
                    input_field("prompt_pack", "Object", False, "Prompt 包"),
                    input_field("session_state", "Object", True, "会话状态"),
                    input_field(
                        "grouped_conversation_trace",
                        "String",
                        True,
                        "分组后会话轨迹",
                    ),
                    input_field("score_rubric", "String", True, "固定评分量表"),
                    input_field("guard_status", "Object", False, "守卫状态"),
                    input_field("paper_status", "Object", False, "论文状态"),
                ],
            }
        ],
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    output_field(
                        "markdown_report",
                        "String",
                        True,
                        "LLM 输出的 Markdown 报告正文",
                    )
                ],
            }
        ],
        "configs": {
            "deployMode": "workflow",
            "model": {
                "llmId": "AGENT-PLATFORM-DEEPSEEK-V3-SFT",
                "llmBrand": "DeepSeek",
                "llmName": "DeepSeek-V3 增强版",
                "llmContextLength": "32k",
                "llmOwner": 1,
                "hyperParameters": [
                    {
                        "temperature": 0.2,
                        "topP": 1,
                        "topK": 128,
                        "llmId": "AGENT-PLATFORM-DEEPSEEK-V3-SFT",
                    }
                ],
                "llmLogo": "https://hag-ability-test.obs.cn-north-1.myhuaweicloud.com/osms/1/1/90c091f8f35f40329260d30fb279220c/b5271b5a1a8b41fba98bc506eac5d4e4.png",
            },
            "templateContent": [{"role": "user", "content": LLM_PROMPT}],
            "responseFormat": {"type": "markdown"},
            "skillList": [],
            "context": {
                "dialogueHistorySwitch": True,
                "dialogueHistoryType": "self",
            },
        },
    }

    schema_node = text_processing_node(
        schema_id,
        "后处理_报告完整性校验",
        {"x": 1400, "y": -80},
        [
            input_field("markdown_report", "String", True, "LLM 原始报告"),
            input_field("session_state", "Object", True, "用于校验 kill_switch 一致性"),
        ],
        [
            output_field(
                "validated_markdown_report",
                "String",
                True,
                "附带校验元数据的报告（供流式输出）",
            ),
            output_field(
                "schema_validation_result",
                "String",
                True,
                "校验结果摘要",
            ),
        ],
        SCHEMA_CHECK_TEMPLATE,
    )

    incomplete_node = text_processing_node(
        incomplete_id,
        "分支_未完成会话报告",
        {"x": 1120, "y": 160},
        [
            input_field("candidate_profile", "Object", True, "候选人画像"),
            input_field("conversation_trace", "Object", True, "当前轨迹"),
            input_field("paper_facts", "Object", True, "论文事实"),
            input_field("session_state", "Object", True, "会话状态"),
        ],
        [
            output_field(
                "markdown_report",
                "String",
                True,
                "未完成会话的占位报告",
            ),
        ],
        INCOMPLETE_SESSION_TEMPLATE,
    )

    output_node = {
        "id": output_id,
        "type": "xiaoyi.outputComponent",
        "dimensions": {"width": 248, "height": 145},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1680, "y": -80},
        "events": {},
        "label": "输出_报告流式输出",
        "description": "流式输出校验后的 Markdown 报告",
        "inputs": [
            {
                "name": "userFields",
                "fields": [
                    input_field(
                        "output",
                        "String",
                        True,
                        "流式输出内容",
                    )
                ],
            },
            {"name": "combinationConfig", "fields": []},
        ],
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    input_field("output", "String", True, ""),
                ],
            },
            {"name": "combinationConfig", "fields": []},
        ],
        "configs": {
            "responseTemplate": "{{validated_markdown_report}}",
            "isStreamOut": True,
            "isStreamingText": True,
            "outputMode": "OutputStream",
            "context": {"dialogueHistorySwitch": True},
        },
    }

    output_incomplete_node = deepcopy(output_node)
    output_incomplete_node["id"] = output_incomplete_id
    output_incomplete_node["label"] = "输出_未完成会话流式输出"
    output_incomplete_node["position"] = {"x": 1400, "y": 160}
    output_incomplete_node["configs"]["responseTemplate"] = "{{markdown_report}}"

    end_node = {
        "id": end_id,
        "type": "agentEnd",
        "dimensions": {"width": 248, "height": 79},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1960, "y": -80},
        "events": {},
        "label": "结束_完整报告",
        "description": "返回校验后的 Markdown 结晶化报告",
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    {
                        "name": "markdown_report",
                        "type": "String",
                        "required": True,
                        "description": "最终 Markdown 报告",
                        "sourceType": "input",
                        "value": "",
                    },
                    {
                        "name": "schema_validation_result",
                        "type": "String",
                        "required": False,
                        "description": "报告 schema 校验摘要",
                        "sourceType": "input",
                        "value": "",
                    },
                ],
            },
            {
                "name": "combinationConfig",
                "fields": [
                    {
                        "name": "stepInfo",
                        "type": "String",
                        "required": True,
                        "description": "思考状态，请勿引用流式变量",
                        "value": "",
                        "sourceType": "input",
                        "unEditName": True,
                        "deleteDisabled": True,
                        "typeDisabled": True,
                    },
                    {
                        "name": "outputId",
                        "displayName": "streamingTextId",
                        "type": "String",
                        "required": False,
                        "description": "输出流id，请勿引用流式变量，最大长度为50个字符",
                        "value": "",
                        "sourceType": "input",
                        "unEditName": True,
                        "deleteDisabled": True,
                        "typeDisabled": True,
                        "maxlength": 50,
                    },
                ],
            },
        ],
        "configs": {},
    }

    end_incomplete_node = deepcopy(end_node)
    end_incomplete_node["id"] = end_incomplete_id
    end_incomplete_node["label"] = "结束_未完成会话"
    end_incomplete_node["position"] = {"x": 1680, "y": 160}
    end_incomplete_node["outputs"][0]["fields"] = [
        {
            "name": "markdown_report",
            "type": "String",
            "required": True,
            "description": "未完成会话占位报告",
            "sourceType": "input",
            "value": "",
        }
    ]

    def edge(source, target, source_handle=None):
        conn = {
            "id": f"edge_{source[:8]}_{target[:8]}",
            "type": "custom",
            "source": source,
            "target": target,
            "style": {"stroke": "#777", "strokeWidth": 1},
        }
        if source_handle:
            conn["sourceHandle"] = source_handle
        return conn

    connections = [
        edge(start_id, rubric_id),
        edge(rubric_id, grouper_id),
        edge(grouper_id, branch_id),
        edge(branch_id, llm_id, "KILL_SWITCH"),
        edge(branch_id, llm_id, "NORMAL"),
        edge(branch_id, incomplete_id, "default"),
        edge(llm_id, schema_id),
        edge(schema_id, output_id),
        edge(output_id, end_id),
        edge(incomplete_id, output_incomplete_id),
        edge(output_incomplete_id, end_incomplete_id),
    ]

    return {
        "description": "报告结晶化：输入完整会话上下文，经评分量表沉淀、轨迹分组、模式选择、LLM 生成与 schema 校验后，输出 Markdown 报告。",
        "iconUri": "D1EeXNBh1oBRFSV5CNi2Pw8dA",
        "iconUrl": "https://contentcenter-drcn.dbankcdn.com/pub_21/FaStore_fa_900_9/bb/v3/fa/osms/1/1/ead51197f88143c09945134e9af5ce56/cdfb2c59c2fa47d3bc52801b7b00f6bc.png",
        "name": "WF_Report_Crystallizer_MVP",
        "schema": {"components": [
            start_node,
            rubric_node,
            grouper_node,
            branch_node,
            llm_node,
            schema_node,
            incomplete_node,
            output_node,
            output_incomplete_node,
            end_node,
            end_incomplete_node,
        ], "connections": connections},
        "version": "1",
        "workflowSide": "cloud",
    }


if __name__ == "__main__":
    workflow = build_workflow()
    out_path = "/workspace/output/WF_Report_Crystallizer_MVP.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")
