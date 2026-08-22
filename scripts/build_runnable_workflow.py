#!/usr/bin/env python3
"""Build WF_Report_Crystallizer aligned with working Xiaoyi reference workflow."""

import json

START = "START7a3622b906c048ea9c33c7e5da72bfbc"
RUBRIC = "TextHandler2ed1041c56764a75b02662425a757c30"
GROUPER = "TextHandler0702229e3d50489fa766ec3943e51006"
BRANCH = "Branch05e4030b71a945e6bf266c3804a0312f"
LLM = "LLM5f7a74b1e7f04d0e9a5dbe54b91f3a40"
OUTPUT = "outputComponent81923859930141d5a4e710f4e96002dc8db93a21cb79413abcb218f63a0ea875"
END = "END0990bdf9a33748179a3fd2b2dbee8220"

SCORE_RUBRIC_TEMPLATE = """# 固定评分量表 Score Rubric v1.0
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
| 5 | 报告可直接用于决策
prompt_pack 快照: {prompt_pack}"""

GROUPER_TEMPLATE = """# 会话轨迹阶段分组 Stage-Grouped Conversation Trace
## 报告模式 report_mode（由分支选择器判定）
1. kill_switch_reason 非空 → KILL_SWITCH
2. is_finished=true 且无 kill_switch → NORMAL
3. 其他 → INCOMPLETE
当前 session_state: {session_state}
## X 阶段 / Y 阶段 / Z 阶段
{conversation_trace}
## 附：评分量表
{score_rubric}
guard_status: {guard_status}
paper_status: {paper_status}"""

SYSTEM_PROMPT = """你是「面试报告结晶化引擎」。根据用户提供的结构化输入，生成仅含事实的 Markdown 面试结晶化报告。

## 你的职责
- 依据 conversation_trace 原话与 paper_facts 写报告，禁止编造未出现的问答或事实
- 严格使用 score_rubric 中的四维度 0-5 锚点评分
- 根据 session_state 判断报告模式：
  - kill_switch_reason 非空 → 异常结束报告（KILL_SWITCH）
  - is_finished=true 且无 kill_switch → 完整终版报告（NORMAL）
  - 其他 → 进行中占位报告（INCOMPLETE）

## 输出格式（必须包含以下 6 个二级标题，缺一不可）
## candidate_summary
## interview_rounds
## score_table
## kill_switch_info
## paper_facts_snapshot
## next_day_prep_actions

## score_table 四指标（每行必填）
- core_component_innovation
- state_machine_flow_control
- prompt_engineering_defense
- data_crystallization_presentation

表格格式：
| metric | score(0-5) | evidence | notes |

## 硬性约束
1. evidence 必须引用 turn_id 或原话片段，证据不足写 evidence_gap，该维度 score=0
2. KILL_SWITCH 时 kill_switch_info 必须写清 reason、触发轮次、影响范围
3. NORMAL 时 interview_rounds 按 X→Y→Z 阶段组织
4. INCOMPLETE 时输出简短占位报告并标注进行中，score_table 填 N/A
5. 只输出 Markdown 正文，不要 JSON 包裹，不要解释性前言"""

USER_PROMPT = """请根据以下输入生成报告。

## 分组会话轨迹（含 report_mode 判定说明）
{grouped_conversation_trace}

## 固定评分量表
{score_rubric}

## 候选人画像
{candidate_profile}

## 论文事实（唯一事实源）
{paper_facts}

## Prompt 包
{prompt_pack}

## 会话状态
{session_state}

## 守卫状态
{guard_status}

## 论文事实状态
{paper_status}

请按 System 中的格式与约束，直接输出 Markdown 报告。"""


def ref(start_field):
    return f"${{{START}.userFields.{start_field}}}"


def branch_ref(field):
    """Top-level branch fields (same pattern as working ref current_stage)."""
    return f"${{{START}.userFields.{field}}}"


def build():
    workflow = {
        "description": "报告结晶化：对齐小艺可运行结构 START→预处理→Branch→LLM→Output→End",
        "iconUri": "D1EVanKXpccTn6brOCCmwSLsw",
        "iconUrl": "https://contentcenter-drcn.dbankcdn.com/pub_21/FaStore_fa_900_9/bb/v3/fa/osms/1/1/854afb3eb8ce40849ce3ddcb7fecb76c/50836c5b19a246cd88743cad2ec32f5c.png",
        "name": "WF_Report_Crystallizer_MVP_1",
        "schema": {
            "components": [
                {
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
                                {
                                    "name": "candidate_profile",
                                    "type": "Object",
                                    "description": "候选人画像",
                                    "required": True,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "paper_facts",
                                    "type": "Object",
                                    "description": "论文事实",
                                    "required": True,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "prompt_pack",
                                    "type": "Object",
                                    "description": "Prompt 包",
                                    "required": False,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "session_state",
                                    "type": "Object",
                                    "description": "会话状态",
                                    "required": True,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "conversation_trace",
                                    "type": "Object",
                                    "description": "问答记录",
                                    "required": True,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "guard_status",
                                    "type": "Object",
                                    "description": "输入守卫状态",
                                    "required": False,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "paper_status",
                                    "type": "Object",
                                    "description": "论文事实状态",
                                    "required": False,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "is_finished",
                                    "type": "Boolean",
                                    "description": "会话是否结束（供选择器使用，可与 session_state.is_finished 一致）",
                                    "required": False,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                                {
                                    "name": "kill_switch_reason",
                                    "type": "String",
                                    "description": "异常终止原因（供选择器使用，可与 session_state.kill_switch_reason 一致）",
                                    "required": False,
                                    "value": "",
                                    "fieldType": "userFields",
                                    "sourceType": "ref",
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": RUBRIC,
                    "type": "jiuwen.TextProcessingComponent",
                    "dimensions": {"width": 248, "height": 214},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 280, "y": 0},
                    "events": {},
                    "label": "预处理_评分量表构建",
                    "description": "对前序节点输入的内容进行字符串拼接、字符串分隔",
                    "inputs": [
                        {
                            "name": "userFields",
                            "fields": [
                                {
                                    "name": "candidate_profile",
                                    "type": "Object",
                                    "required": True,
                                    "description": "",
                                    "value": ref("candidate_profile"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "session_state",
                                    "type": "Object",
                                    "required": True,
                                    "description": "",
                                    "value": ref("session_state"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "prompt_pack",
                                    "type": "Object",
                                    "required": False,
                                    "description": "",
                                    "value": ref("prompt_pack"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                            ],
                        }
                    ],
                    "outputs": [
                        {
                            "name": "preDefinedFields",
                            "fields": [
                                {
                                    "name": "output",
                                    "type": "String",
                                    "required": True,
                                    "description": "",
                                }
                            ],
                        }
                    ],
                    "configs": {
                        "functionality": "concat",
                        "listJoinString": "\n",
                        "concatTemplate": SCORE_RUBRIC_TEMPLATE,
                        "splitStringList": [],
                        "customSeparatorList": [],
                        "customConnectionList": [{"label": "\n", "value": "\n"}],
                    },
                },
                {
                    "id": GROUPER,
                    "type": "jiuwen.TextProcessingComponent",
                    "dimensions": {"width": 248, "height": 234},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 560, "y": 0},
                    "events": {},
                    "label": "预处理_轨迹按阶段分组",
                    "description": "对前序节点输入的内容进行字符串拼接、字符串分隔",
                    "inputs": [
                        {
                            "name": "userFields",
                            "fields": [
                                {
                                    "name": "conversation_trace",
                                    "type": "Object",
                                    "required": True,
                                    "description": "问答记录",
                                    "value": ref("conversation_trace"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "session_state",
                                    "type": "Object",
                                    "required": True,
                                    "description": "会话状态",
                                    "value": ref("session_state"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "score_rubric",
                                    "type": "String",
                                    "required": True,
                                    "description": "评分量表",
                                    "value": f"${{{RUBRIC}.output}}",
                                    "sourceType": "ref",
                                    "refType": "String",
                                },
                                {
                                    "name": "guard_status",
                                    "type": "Object",
                                    "required": False,
                                    "description": "守卫状态",
                                    "value": ref("guard_status"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "paper_status",
                                    "type": "Object",
                                    "required": False,
                                    "description": "论文状态",
                                    "value": ref("paper_status"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                            ],
                        }
                    ],
                    "outputs": [
                        {
                            "name": "preDefinedFields",
                            "fields": [
                                {
                                    "name": "grouped_conversation_trace",
                                    "type": "String",
                                    "required": True,
                                    "description": "按 X/Y/Z 分组后的轨迹",
                                }
                            ],
                        }
                    ],
                    "configs": {
                        "functionality": "concat",
                        "listJoinString": "\n",
                        "concatTemplate": GROUPER_TEMPLATE,
                        "splitStringList": [],
                        "customSeparatorList": [],
                        "customConnectionList": [{"label": "\n", "value": "\n"}],
                    },
                },
                {
                    "id": BRANCH,
                    "type": "AgentBranch",
                    "dimensions": {"width": 248, "height": 140},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 840, "y": 0},
                    "events": {},
                    "label": "选择器_报告模式",
                    "description": "按 is_finished / kill_switch_reason 选择路径，三路均汇入同一 LLM",
                    "branches": [
                        {
                            "id": "KILL_SWITCH",
                            "condition": "&&",
                            "expression": [
                                {
                                    "leftVar": {
                                        "value": branch_ref("kill_switch_reason"),
                                        "fieldType": "String",
                                        "label": "开始_报告结晶化-kill_switch_reason",
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
                                        "value": branch_ref("is_finished"),
                                        "fieldType": "Boolean",
                                        "label": "开始_报告结晶化-is_finished",
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
                                        "value": branch_ref("kill_switch_reason"),
                                        "fieldType": "String",
                                        "label": "开始_报告结晶化-kill_switch_reason",
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
                },
                {
                    "id": LLM,
                    "type": "AgentLargeModel",
                    "dimensions": {"width": 248, "height": 56},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 1120, "y": 0},
                    "events": {},
                    "label": "大模型_生成结晶化报告",
                    "description": "调用大模型生成结构化 Markdown 结晶化报告",
                    "inputs": [
                        {
                            "name": "userFields",
                            "fields": [
                                {
                                    "name": "candidate_profile",
                                    "type": "Object",
                                    "required": True,
                                    "description": "候选人画像",
                                    "value": ref("candidate_profile"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "paper_facts",
                                    "type": "Object",
                                    "required": True,
                                    "description": "论文事实",
                                    "value": ref("paper_facts"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "prompt_pack",
                                    "type": "Object",
                                    "required": False,
                                    "description": "Prompt 包",
                                    "value": ref("prompt_pack"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "session_state",
                                    "type": "Object",
                                    "required": True,
                                    "description": "会话状态",
                                    "value": ref("session_state"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "grouped_conversation_trace",
                                    "type": "String",
                                    "required": True,
                                    "description": "分组后会话轨迹",
                                    "value": f"${{{GROUPER}.grouped_conversation_trace}}",
                                    "sourceType": "ref",
                                    "refType": "String",
                                },
                                {
                                    "name": "score_rubric",
                                    "type": "String",
                                    "required": True,
                                    "description": "固定评分量表",
                                    "value": f"${{{RUBRIC}.output}}",
                                    "sourceType": "ref",
                                    "refType": "String",
                                },
                                {
                                    "name": "guard_status",
                                    "type": "Object",
                                    "required": False,
                                    "description": "守卫状态",
                                    "value": ref("guard_status"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                                {
                                    "name": "paper_status",
                                    "type": "Object",
                                    "required": False,
                                    "description": "论文状态",
                                    "value": ref("paper_status"),
                                    "sourceType": "ref",
                                    "refType": "Object",
                                },
                            ],
                        }
                    ],
                    "outputs": [
                        {
                            "name": "userFields",
                            "fields": [
                                {
                                    "name": "markdown_report",
                                    "type": "String",
                                    "description": "Markdown 结晶化报告",
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
                        "templateContent": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": USER_PROMPT},
                        ],
                        "responseFormat": {"type": "markdown"},
                        "skillList": [],
                        "context": {
                            "dialogueHistorySwitch": True,
                            "dialogueHistoryType": "self",
                        },
                    },
                    "isRunLoading": False,
                    "stopRunning": True,
                    "isOpenRunDrawer": False,
                    "drawerVisible": False,
                },
                {
                    "id": OUTPUT,
                    "type": "xiaoyi.outputComponent",
                    "dimensions": {"width": 248, "height": 144},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 1400, "y": 0},
                    "events": {},
                    "label": "输出_报告流式输出",
                    "description": "",
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "userFields",
                            "fields": [
                                {
                                    "name": "markdown_report",
                                    "type": "String",
                                    "required": True,
                                    "description": "流式输出报告正文",
                                    "value": f"${{{LLM}.userFields.markdown_report}}",
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
                },
                {
                    "id": END,
                    "type": "agentEnd",
                    "dimensions": {"width": 248, "height": 44},
                    "selected": False,
                    "dragging": False,
                    "resizing": False,
                    "initialized": False,
                    "isParent": False,
                    "position": {"x": 1680, "y": 0},
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
                                    "value": f"${{{LLM}.userFields.markdown_report}}",
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
                },
            ],
            "connections": [
                {
                    "id": "edge_start_rubric",
                    "type": "custom",
                    "source": START,
                    "target": RUBRIC,
                    "style": {"stroke": "#777", "strokeWidth": 1},
                },
                {
                    "id": "edge_rubric_grouper",
                    "type": "custom",
                    "source": RUBRIC,
                    "target": GROUPER,
                    "style": {"stroke": "#777", "strokeWidth": 1},
                },
                {
                    "id": "edge_grouper_branch",
                    "type": "custom",
                    "source": GROUPER,
                    "target": BRANCH,
                    "style": {"stroke": "#777", "strokeWidth": 1},
                },
                *[
                    {
                        "id": f"edge_branch_{bid}_llm",
                        "type": "custom",
                        "source": BRANCH,
                        "target": LLM,
                        "sourceHandle": bid,
                        "targetHandle": "model_left",
                        "branchId": bid,
                        "style": {"stroke": "#777", "strokeWidth": 1},
                    }
                    for bid in ("KILL_SWITCH", "NORMAL", "default")
                ],
                {
                    "id": "edge_llm_output",
                    "type": "custom",
                    "source": LLM,
                    "target": OUTPUT,
                    "style": {"stroke": "#777", "strokeWidth": 1},
                },
                {
                    "id": "edge_output_end",
                    "type": "custom",
                    "source": OUTPUT,
                    "target": END,
                    "style": {"stroke": "#777", "strokeWidth": 1},
                },
            ],
        },
        "version": "0",
        "workflowSide": "cloud",
    }
    return workflow


if __name__ == "__main__":
    out = "/workspace/output/WF_Report_Crystallizer_MVP_1-V0_runnable.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=4)
    print(f"Wrote {out}")
