#!/usr/bin/env python3
"""Generate minimal (guaranteed runnable) and full-logic workflow JSON files."""

import json
import uuid

# Shared node IDs (stable for import/update)
START = "START7a3622b906c048ea9c33c7e5da72bfbc"
RUBRIC = "TextHandlerConcatRubric7a2b3c4d5e6f708192a3b4c5d6e7f809"
GROUPER = "TextHandlerConcatGrouper8b3c4d5e6f708192a3b4c5d6e7f8091a2"
BRANCH = "Branch05e4030b71a945e6bf266c3804a0312f"
LLM = "LLM5f7a74b1e7f04d0e9a5dbe54b91f3a40"
SCHEMA = "TextHandlerConcatSchema9c4d5e6f708192a3b4c5d6e7f8091a2b3"
INCOMPLETE = "TextHandlerConcatIncomplete0d5e6f708192a3b4c5d6e7f8091a2b3c4"
MERGE = "TextHandlerConcatMerge1e6f708192a3b4c5d6e7f8091a2b3c4d5"
OUTPUT = "outputComponent81923859930141d5a4e710f4e96002dc8db93a21cb79413abcb218f63a0ea875"
END = "END0990bdf9a33748179a3fd2b2dbee8220"

ICON_URI = "D1EVanKXpccTn6brOCCmwSLsw"
ICON_URL = (
    "https://contentcenter-drcn.dbankcdn.com/pub_21/FaStore_fa_900_9/bb/v3/fa/osms/1/1/"
    "854afb3eb8ce40849ce3ddcb7fecb76c/50836c5b19a246cd88743cad2ec32f5c.png"
)

SCORE_RUBRIC_STATIC = """# 固定评分量表 Score Rubric v1.0
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
| 0 | 无防御意识 |
| 1 | 知道 prompt 注入风险 |
| 2 | 能列举 1 种防御手段 |
| 3 | 能说明输入过滤与角色锁定 |
| 4 | 有多层防御与审计策略 |
| 5 | 能设计可验证的防御闭环 |
### data_crystallization_presentation
| 分数 | 锚点描述 |
|------|----------|
| 0 | 无法结构化表达 |
| 1 | 仅罗列事实 |
| 2 | 有基本分段 |
| 3 | 能按维度组织证据 |
| 4 | 有清晰评分与引用 |
| 5 | 报告可直接用于决策"""

SCORE_RUBRIC_TEMPLATE = SCORE_RUBRIC_STATIC + """
## 元信息
- session_id: {session_state}
- candidate: {candidate_profile}
prompt_pack 快照: {prompt_pack}"""

GROUPER_TEMPLATE = """# 会话轨迹阶段分组
## 报告模式判定（LLM 必须遵守）
1. kill_switch_reason 非空 → KILL_SWITCH
2. is_finished=true 且无 kill_switch → NORMAL
3. 其他 → INCOMPLETE
当前 session_state: {session_state}
## 原始 conversation_trace（请按 X/Y/Z 阶段自行分组）
{conversation_trace}
## 评分量表（上一步拼接结果）
{score_rubric}
guard_status: {guard_status}
paper_status: {paper_status}"""

SCHEMA_TEMPLATE = """# 报告完整性校验
必填 Section: candidate_summary / interview_rounds / score_table / kill_switch_info / paper_facts_snapshot / next_day_prep_actions
校验提示: 若缺 section 或 score_table 缺四指标，必须补全。
---
{markdown_report}"""

INCOMPLETE_TEMPLATE = """# 面试报告（会话未完成）

> **report_mode**: INCOMPLETE
> 会话尚未结束，跳过 LLM 全量报告生成。

## candidate_summary
- 候选人: {candidate_profile}
- 会话状态: 进行中

## interview_rounds
{conversation_trace}

## score_table
| metric | score | evidence |
|--------|-------|----------|
| core_component_innovation | N/A | 会话未完成 |
| state_machine_flow_control | N/A | 会话未完成 |
| prompt_engineering_defense | N/A | 会话未完成 |
| data_crystallization_presentation | N/A | 会话未完成 |

## kill_switch_info
- triggered: false

## paper_facts_snapshot
{paper_facts}

## next_day_prep_actions
1. 继续完成面试轮次后再触发本工作流。
2. 确认 session_state.is_finished 为 true。"""

MERGE_TEMPLATE = "{llm_path_report}{incomplete_path_report}"

SYSTEM_PROMPT_FULL = """你是「面试报告结晶化引擎」。根据输入生成仅含事实的 Markdown 报告。

## 报告模式（由预处理分组说明判定）
- KILL_SWITCH: 异常结束报告，kill_switch_info 必填
- NORMAL: 完整终版报告，interview_rounds 按 X→Y→Z 组织
- INCOMPLETE: 不应到达本节点（由另一分支处理）

## 输出格式（6 个二级标题缺一不可）
## candidate_summary
## interview_rounds
## score_table
## kill_switch_info
## paper_facts_snapshot
## next_day_prep_actions

## score_table 四指标
core_component_innovation / state_machine_flow_control / prompt_engineering_defense / data_crystallization_presentation
格式: | metric | score(0-5) | evidence | notes |

## 约束
1. evidence 引用 turn_id 或原话；不足则 score=0 并标注 evidence_gap
2. 禁止编造未出现的问答或事实
3. 只输出 Markdown 正文"""

SYSTEM_PROMPT_MINIMAL = SYSTEM_PROMPT_FULL + """

## 内置评分量表（直接使用，无需外部预处理）
""" + SCORE_RUBRIC_STATIC

USER_PROMPT_FULL = """请生成报告。

## 预处理：分组轨迹与模式说明
{grouped_trace}

## 预处理：评分量表
{score_rubric}

## 候选人画像
{candidate_profile}

## 论文事实
{paper_facts}

## Prompt 包
{prompt_pack}

## 会话状态
{session_state}

## 守卫 / 论文状态
guard_status: {guard_status}
paper_status: {paper_status}"""

USER_PROMPT_MINIMAL = """请生成报告。

## 评分量表
""" + SCORE_RUBRIC_STATIC + """

## 候选人画像
{candidate_profile}

## 论文事实
{paper_facts}

## Prompt 包
{prompt_pack}

## 会话状态
{session_state}

## 问答记录（请自行按 X/Y/Z 阶段分组）
{conversation_trace}

## 守卫 / 论文状态
guard_status: {guard_status}
paper_status: {paper_status}

## 模式判定
- kill_switch_reason 非空 → KILL_SWITCH 报告
- is_finished=true 且无 kill_switch → NORMAL 报告
- 其他 → INCOMPLETE 占位报告（score_table 填 N/A）"""


def ref(node_id, field_path):
    return f"${{{node_id}.{field_path}}}"


def start_ref(field):
    return ref(START, f"userFields.{field}")


def input_field(name, ftype, required, description="", value=""):
    f = {
        "name": name,
        "type": ftype,
        "required": required,
        "description": description,
        "sourceType": "ref" if value else "input",
    }
    if value:
        f["value"] = value
        f["refType"] = ftype
    return f


def concat_node(node_id, short_label, position, inputs, concat_template):
    """Concat-only text node: no split config keys, unified output field name."""
    return {
        "id": node_id,
        "type": "jiuwen.TextProcessingComponent",
        "dimensions": {"width": 248, "height": 120},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": position,
        "events": {},
        "label": f"字符串拼接_{short_label}",
        "description": "字符串拼接（固定拼接模式，不支持分隔）",
        "inputs": [{"name": "userFields", "fields": inputs}],
        "outputs": [
            {
                "name": "preDefinedFields",
                "fields": [
                    {
                        "name": "output",
                        "type": "String",
                        "required": True,
                        "description": short_label,
                    }
                ],
            }
        ],
        "configs": {
            "functionality": "concat",
            "listJoinString": "\n",
            "concatTemplate": concat_template,
            "customConnectionList": [{"label": "\n", "value": "\n"}],
        },
    }


def start_node():
    return {
        "id": START,
        "type": "agentStart",
        "dimensions": {"width": 248, "height": 380},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 0, "y": 0},
        "events": {},
        "label": "开始_报告结晶化",
        "description": "工作流开始的节点，用于设定启动工作流需要的信息",
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
                        "fieldType": "systemFields",
                        "sourceType": "ref",
                    },
                    {
                        "name": "FILES_INPUT",
                        "type": "Array<String>",
                        "description": "本次对话上传的文件地址",
                        "required": False,
                        "value": "",
                        "fieldType": "systemFields",
                        "sourceType": "ref",
                    },
                    {
                        "name": "EVENT_INPUT",
                        "type": "Object",
                        "description": "本次对话的事件内容",
                        "required": False,
                        "value": "",
                        "fieldType": "systemFields",
                        "sourceType": "ref",
                    },
                ],
            },
            {
                "name": "userFields",
                "fields": [
                    {"name": "candidate_profile", "type": "Object", "description": "候选人画像", "required": True, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "paper_facts", "type": "Object", "description": "论文事实", "required": True, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "prompt_pack", "type": "Object", "description": "Prompt 包", "required": False, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "session_state", "type": "Object", "description": "会话状态", "required": True, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "conversation_trace", "type": "Object", "description": "问答记录", "required": True, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "guard_status", "type": "Object", "description": "守卫状态", "required": False, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "paper_status", "type": "Object", "description": "论文状态", "required": False, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "is_finished", "type": "Boolean", "description": "是否结束（选择器用，与 session_state 保持一致）", "required": False, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                    {"name": "kill_switch_reason", "type": "String", "description": "异常原因（选择器用，与 session_state 保持一致）", "required": False, "value": "", "fieldType": "userFields", "sourceType": "ref"},
                ],
            },
        ],
    }


def branch_node():
    return {
        "id": BRANCH,
        "type": "AgentBranch",
        "dimensions": {"width": 248, "height": 160},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 840, "y": 0},
        "events": {},
        "label": "选择器_报告模式",
        "description": "KILL_SWITCH / NORMAL 走 LLM；INCOMPLETE(否则) 走占位报告，不调用 LLM",
        "branches": [
            {
                "id": "KILL_SWITCH",
                "condition": "&&",
                "expression": [
                    {
                        "leftVar": {"value": start_ref("kill_switch_reason"), "fieldType": "String", "label": "kill_switch_reason"},
                        "condition": "!=",
                        "rightVar": {"sourceType": "input", "value": "", "fieldType": "String", "label": ""},
                    }
                ],
            },
            {
                "id": "NORMAL",
                "condition": "&&",
                "expression": [
                    {
                        "leftVar": {"value": start_ref("is_finished"), "fieldType": "Boolean", "label": "is_finished"},
                        "condition": "==",
                        "rightVar": {"sourceType": "input", "value": "true", "fieldType": "Boolean", "label": "true"},
                    },
                    {
                        "leftVar": {"value": start_ref("kill_switch_reason"), "fieldType": "String", "label": "kill_switch_reason"},
                        "condition": "==",
                        "rightVar": {"sourceType": "input", "value": "", "fieldType": "String", "label": ""},
                    },
                ],
            },
            {"id": "default"},
        ],
    }


def llm_node(*, full_logic):
    if full_logic:
        inputs = [
            input_field("grouped_trace", "String", True, "分组轨迹", ref(GROUPER, "output")),
            input_field("score_rubric", "String", True, "评分量表", ref(RUBRIC, "output")),
            input_field("candidate_profile", "Object", True, "", start_ref("candidate_profile")),
            input_field("paper_facts", "Object", True, "", start_ref("paper_facts")),
            input_field("prompt_pack", "Object", False, "", start_ref("prompt_pack")),
            input_field("session_state", "Object", True, "", start_ref("session_state")),
            input_field("guard_status", "Object", False, "", start_ref("guard_status")),
            input_field("paper_status", "Object", False, "", start_ref("paper_status")),
        ]
        system_prompt = SYSTEM_PROMPT_FULL
        user_prompt = USER_PROMPT_FULL
    else:
        inputs = [
            input_field("candidate_profile", "Object", True, "", start_ref("candidate_profile")),
            input_field("paper_facts", "Object", True, "", start_ref("paper_facts")),
            input_field("prompt_pack", "Object", False, "", start_ref("prompt_pack")),
            input_field("session_state", "Object", True, "", start_ref("session_state")),
            input_field("conversation_trace", "Object", True, "", start_ref("conversation_trace")),
            input_field("guard_status", "Object", False, "", start_ref("guard_status")),
            input_field("paper_status", "Object", False, "", start_ref("paper_status")),
        ]
        system_prompt = SYSTEM_PROMPT_MINIMAL
        user_prompt = USER_PROMPT_MINIMAL

    return {
        "id": LLM,
        "type": "AgentLargeModel",
        "dimensions": {"width": 248, "height": 56},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1120, "y": -40},
        "events": {},
        "label": "大模型_生成结晶化报告",
        "description": "调用大模型生成 Markdown 报告",
        "inputs": [{"name": "userFields", "fields": inputs}],
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    {
                        "name": "markdown_report",
                        "type": "String",
                        "description": "Markdown 报告",
                        "required": False,
                        "enabled": False,
                    }
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
                "hyperParameters": [{"temperature": 0.2, "topP": 1, "topK": 128, "llmId": "AGENT-PLATFORM-DEEPSEEK-V3-SFT"}],
                "llmLogo": "https://hag-ability-test.obs.cn-north-1.myhuaweicloud.com/osms/1/1/90c091f8f35f40329260d30fb279220c/b5271b5a1a8b41fba98bc506eac5d4e4.png",
            },
            "templateContent": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "responseFormat": {"type": "markdown"},
            "skillList": [],
            "context": {"dialogueHistorySwitch": True, "dialogueHistoryType": "self"},
        },
        "isRunLoading": False,
        "stopRunning": True,
        "isOpenRunDrawer": False,
        "drawerVisible": False,
    }


def output_node(report_ref):
    return {
        "id": OUTPUT,
        "type": "xiaoyi.outputComponent",
        "dimensions": {"width": 248, "height": 144},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1680, "y": 0},
        "events": {},
        "label": "输出_报告流式输出",
        "description": "",
        "inputs": [],
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    {
                        "name": "output",
                        "type": "String",
                        "required": True,
                        "description": "",
                        "value": report_ref,
                        "sourceType": "ref",
                        "refType": "String",
                        "isStreamOut": False,
                    }
                ],
            },
            {"name": "combinationConfig", "fields": []},
        ],
        "configs": {
            "responseTemplate": "${output}",
            "isStreamOut": True,
            "isStreamingText": True,
            "outputMode": "OutputStream",
            "context": {"dialogueHistorySwitch": True},
        },
    }


def end_node(report_ref):
    return {
        "id": END,
        "type": "agentEnd",
        "dimensions": {"width": 248, "height": 44},
        "selected": False,
        "dragging": False,
        "resizing": False,
        "initialized": False,
        "isParent": False,
        "position": {"x": 1960, "y": 0},
        "events": {},
        "label": "结束",
        "description": "工作流的结束节点，工作流的运行结果将返回给智能体",
        "outputs": [
            {
                "name": "userFields",
                "fields": [
                    {
                        "name": "markdown_report",
                        "type": "String",
                        "required": True,
                        "description": "最终 Markdown 报告",
                        "sourceType": "ref",
                        "value": report_ref,
                        "refType": "String",
                        "isStreamOut": True,
                    }
                ],
            },
            {"name": "combinationConfig", "fields": []},
        ],
        "configs": {
            "isStreamOut": False,
            "responseMode": "returnVariables",
            "responseTemplate": "",
            "responseLabel": "返回变量",
            "isStreamingText": False,
        },
    }


def edge(source, target, source_handle=None, target_handle=None, branch_id=None):
    conn = {
        "id": f"edge_{uuid.uuid4().hex[:12]}",
        "type": "custom",
        "source": source,
        "target": target,
        "style": {"stroke": "#777", "strokeWidth": 1},
    }
    if source_handle:
        conn["sourceHandle"] = source_handle
    if target_handle:
        conn["targetHandle"] = target_handle
    if branch_id:
        conn["branchId"] = branch_id
    return conn


def build_minimal():
    llm_ref = ref(LLM, "userFields.markdown_report")
    return {
        "description": "报告结晶化【可运行版】START→LLM→Output→End，无预处理、无选择器，逻辑内嵌于 Prompt",
        "iconUri": ICON_URI,
        "iconUrl": ICON_URL,
        "name": "WF_Report_Crystallizer_MVP_1_Minimal",
        "schema": {
            "components": [
                start_node(),
                llm_node(full_logic=False),
                output_node(llm_ref),
                end_node(llm_ref),
            ],
            "connections": [
                edge(START, LLM),
                edge(LLM, OUTPUT),
                edge(OUTPUT, END),
            ],
        },
        "version": "0",
        "workflowSide": "cloud",
    }


def build_full():
    rubric = concat_node(
        RUBRIC,
        "评分量表",
        {"x": 280, "y": 0},
        [
            input_field("candidate_profile", "Object", True, "", start_ref("candidate_profile")),
            input_field("session_state", "Object", True, "", start_ref("session_state")),
            input_field("prompt_pack", "Object", False, "", start_ref("prompt_pack")),
        ],
        SCORE_RUBRIC_TEMPLATE,
    )
    grouper = concat_node(
        GROUPER,
        "轨迹分组",
        {"x": 560, "y": 0},
        [
            input_field("conversation_trace", "Object", True, "", start_ref("conversation_trace")),
            input_field("session_state", "Object", True, "", start_ref("session_state")),
            input_field("score_rubric", "String", True, "", ref(RUBRIC, "output")),
            input_field("guard_status", "Object", False, "", start_ref("guard_status")),
            input_field("paper_status", "Object", False, "", start_ref("paper_status")),
        ],
        GROUPER_TEMPLATE,
    )
    schema = concat_node(
        SCHEMA,
        "报告校验",
        {"x": 1400, "y": -60},
        [
            input_field("markdown_report", "String", True, "", ref(LLM, "userFields.markdown_report")),
        ],
        SCHEMA_TEMPLATE,
    )
    incomplete = concat_node(
        INCOMPLETE,
        "未完成占位",
        {"x": 1120, "y": 120},
        [
            input_field("candidate_profile", "Object", True, "", start_ref("candidate_profile")),
            input_field("conversation_trace", "Object", True, "", start_ref("conversation_trace")),
            input_field("paper_facts", "Object", True, "", start_ref("paper_facts")),
            input_field("session_state", "Object", True, "", start_ref("session_state")),
        ],
        INCOMPLETE_TEMPLATE,
    )
    merge = concat_node(
        MERGE,
        "汇聚报告",
        {"x": 1540, "y": 20},
        [
            input_field("llm_path_report", "String", False, "LLM+校验支路", ref(SCHEMA, "output")),
            input_field("incomplete_path_report", "String", False, "未完成支路", ref(INCOMPLETE, "output")),
        ],
        MERGE_TEMPLATE,
    )
    merge_ref = ref(MERGE, "output")
    return {
        "description": "报告结晶化【完整逻辑版】含预处理+三路分支：KILL/NORMAL→LLM，INCOMPLETE→占位",
        "iconUri": ICON_URI,
        "iconUrl": ICON_URL,
        "name": "WF_Report_Crystallizer_MVP_1_Full",
        "schema": {
            "components": [
                start_node(),
                rubric,
                grouper,
                branch_node(),
                llm_node(full_logic=True),
                schema,
                incomplete,
                merge,
                output_node(merge_ref),
                end_node(merge_ref),
            ],
            "connections": [
                edge(START, RUBRIC),
                edge(RUBRIC, GROUPER),
                edge(GROUPER, BRANCH),
                edge(BRANCH, LLM, "KILL_SWITCH", "model_left", "KILL_SWITCH"),
                edge(BRANCH, LLM, "NORMAL", "model_left", "NORMAL"),
                edge(BRANCH, INCOMPLETE, "default", branch_id="default"),
                edge(LLM, SCHEMA),
                edge(SCHEMA, MERGE),
                edge(INCOMPLETE, MERGE),
                edge(MERGE, OUTPUT),
                edge(OUTPUT, END),
            ],
        },
        "version": "0",
        "workflowSide": "cloud",
    }


if __name__ == "__main__":
    minimal_path = "/workspace/output/WF_Report_Crystallizer_MVP_1-V0_minimal.json"
    full_path = "/workspace/output/WF_Report_Crystallizer_MVP_1-V0_full.json"
    with open(minimal_path, "w", encoding="utf-8") as f:
        json.dump(build_minimal(), f, ensure_ascii=False, indent=4)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(build_full(), f, ensure_ascii=False, indent=4)
    print(f"Wrote {minimal_path}")
    print(f"Wrote {full_path}")
