#!/usr/bin/env python3
"""Fix WF_Interview_Session_Engine_MVP_V2 conversation_trace and related bindings."""

import json

START = "START2e5c8578e5ad405aac34381256907cc0"
LLM_INIT = "LLM12dbd76faf2b426da45439d3b7c4e019"
LLM_STEP1 = "LLM1979f9a7d4f541a79c6babe12f61cb31"
LLM_STEP2 = "LLM703a1311197a49509c6973146daa59b6"
QUESTIONER = "Questioner358948a33f8c48c0aa009b50b57e2935"
OUTPUT_MAIN = "outputComponent326977145f934cf69c6dec7d4afb2472"
OUTPUT_Q = "outputComponent0673505583e941029b0f043355afa099"
END = "ENDf3e1bcb7064b41db9fd52aaad1b4af32"

SYSTEM_PROMPT = """你是“算法面试会话状态机”，不是普通聊天助手。

你的唯一任务是根据输入的 prompt_pack、runtime_config、session_state、conversation_trace、user_answer、current_stage、stage_list，推进一次面试会话状态，并生成下一步面试问题或结束状态。

你必须严格遵守以下原则：

1. 只推进一次面试状态
2. 面试阶段固定为：X_BASE → Y_PROJECT → Z_EXTEND → DONE
3. stage_round_counter 与 turn_counter_in_current_round 分开计数
4. conversation_trace 必须是数组，每轮追加记录，禁止覆盖历史
5. 只输出严格 JSON，不要 Markdown，不要代码块，不要解释
6. conversation_trace 为空时使用 []
7. current_stage 为空时使用 X_BASE
8. interviewer_question 必须是当前要展示给用户的问题；若 current_stage=DONE 则输出「面试已完成，正在生成最终报告」"""

USER_PROMPT = """你是面试会话引擎。推进一次面试状态，输出严格 JSON。

prompt_pack: {prompt_pack}
runtime_config: {runtime_config}
session_state: {session_state}
conversation_trace: {conversation_trace}
user_answer: {user_answer}
current_stage: {current_stage}
stage_list: {stage_list}

规则：
1. 首次运行 current_stage 优先用入参，否则从 session_state.current_stage 推断，仍为空则 X_BASE
2. user_answer 非空时，把上一题和答案追加到 conversation_trace 数组末尾
3. 按 X_BASE → Y_PROJECT → Z_EXTEND 推进，完成后 current_stage=DONE、is_finished=true
4. conversation_trace 必须输出完整数组（包含历史 + 本轮新增）
5. stage_list 是难度参考列表，不要与 current_stage 混淆

输出 JSON Schema：
{
  "session_state": {
    "current_stage": "X_BASE|Y_PROJECT|Z_EXTEND|DONE",
    "stage_round_counter": {"X_BASE": 0, "Y_PROJECT": 0, "Z_EXTEND": 0},
    "turn_counter_in_current_round": 0,
    "is_finished": false,
    "kill_switch_reason": "",
    "last_question_id": "",
    "last_question": "",
    "last_stage": "",
    "last_round_index": 0,
    "last_turn_index": 0
  },
  "conversation_trace": [
    {
      "stage": "string",
      "round_index": 0,
      "turn_index": 0,
      "question": "string",
      "answer": "string",
      "trace_type": "normal|empty_answer|defense_rejection"
    }
  ],
  "interviewer_question": "string",
  "current_stage_out": "X_BASE|Y_PROJECT|Z_EXTEND|DONE",
  "is_finished_out": false,
  "session_step_json": {}
}"""

INIT_USER_PROMPT = """初始化工作流变量，只输出严格 JSON，不要其他文字。

要求：
1. conversation_trace 初始化为空数组 []
2. stage_list 固定为 ["easy", "easy", "middle", "middle", "hard", "hard"]

输出格式：
{
  "conversation_trace": [],
  "stage_list": ["easy", "easy", "middle", "middle", "hard", "hard"]
}"""


def ref(node, path):
    return f"${{{node}.{path}}}"


def start(path):
    return ref(START, f"userFields.{path}")


def llm_output_fields():
    return [
        {"name": "session_state", "type": "Object", "description": "会话状态", "required": False, "enabled": True},
        {"name": "conversation_trace", "type": "Object", "description": "问答记录数组", "required": False, "enabled": True},
        {"name": "interviewer_question", "type": "String", "description": "当前问题", "required": False, "enabled": True},
        {"name": "current_stage_out", "type": "String", "description": "当前阶段", "required": False, "enabled": True},
        {"name": "is_finished_out", "type": "Boolean", "description": "是否结束", "required": False, "enabled": True},
        {"name": "session_step_json", "type": "Object", "description": "完整步骤 JSON", "required": False, "enabled": True},
    ]


def llm_inputs_step1():
    return [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "面试官 Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": start("session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "conversation_trace", "type": "Object", "required": False, "description": "历史问答", "value": ref(LLM_INIT, "userFields.conversation_trace"), "sourceType": "ref", "refType": "Object"},
        {"name": "user_answer", "type": "String", "required": False, "description": "用户回答", "value": start("user_answer"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": start("current_stage"), "sourceType": "ref", "refType": "String"},
        {"name": "stage_list", "type": "Array<String>", "required": False, "description": "难度列表", "value": ref(LLM_INIT, "userFields.stage_list"), "sourceType": "ref", "refType": "Array<String>"},
    ]


def llm_inputs_step2():
    return [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "面试官 Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": ref(LLM_STEP1, "userFields.session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "conversation_trace", "type": "Object", "required": False, "description": "历史问答", "value": ref(LLM_STEP1, "userFields.conversation_trace"), "sourceType": "ref", "refType": "Object"},
        {"name": "user_answer", "type": "String", "required": False, "description": "用户本轮回答", "value": ref(QUESTIONER, "userResponse"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": ref(LLM_STEP1, "userFields.current_stage_out"), "sourceType": "ref", "refType": "String"},
        {"name": "stage_list", "type": "Array<String>", "required": False, "description": "难度列表", "value": ref(LLM_INIT, "userFields.stage_list"), "sourceType": "ref", "refType": "Array<String>"},
    ]


def build():
    with open(
        "/home/ubuntu/.cursor/projects/workspace/uploads/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_9630.json",
        encoding="utf-8",
    ) as f:
        wf = json.load(f)

    components = {c["id"]: c for c in wf["schema"]["components"]}

    # --- START: conversation_trace description ---
    start_node = components[START]
    for field in start_node["outputs"][1]["fields"]:
        if field["name"] == "conversation_trace":
            field["description"] = "历史问答记录数组；首次传 [] 或留空"
        if field["name"] == "current_stage":
            field["description"] = "当前阶段 X_BASE|Y_PROJECT|Z_EXTEND|DONE；首次可空"

    # --- LLM Init ---
    init = components[LLM_INIT]
    init["label"] = "初始化变量"
    init["configs"]["templateContent"] = [
        {"role": "system", "content": "你只负责初始化变量，输出严格 JSON。"},
        {"role": "user", "content": INIT_USER_PROMPT},
    ]
    init["outputs"][0]["fields"] = [
        {"name": "conversation_trace", "type": "Object", "description": "初始空数组", "required": False, "enabled": True},
        {"name": "stage_list", "type": "Array<String>", "description": "难度列表", "required": False, "enabled": True},
    ]

    # --- LLM Step 1 ---
    step1 = components[LLM_STEP1]
    step1["inputs"][0]["fields"] = llm_inputs_step1()
    step1["outputs"][0]["fields"] = llm_output_fields()
    step1["configs"]["templateContent"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    # --- LLM Step 2 ---
    step2 = components[LLM_STEP2]
    step2["inputs"][0]["fields"] = llm_inputs_step2()
    step2["outputs"][0]["fields"] = llm_output_fields()
    step2["configs"]["templateContent"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    # --- END ---
    end = components[END]
    end["outputs"][0]["fields"][0]["value"] = ref(LLM_STEP2, "userFields.session_step_json")
    end["outputs"][0]["fields"][0]["description"] = "完整步骤 JSON（含 session_state 与 conversation_trace）"

    # --- Output main ---
    out_main = components[OUTPUT_MAIN]
    out_main["outputs"][0]["fields"] = [
        {
            "name": "interviewer_question",
            "type": "String",
            "required": True,
            "description": "当前面试问题",
            "value": ref(LLM_STEP2, "userFields.interviewer_question"),
            "sourceType": "ref",
            "refType": "String",
            "isStreamOut": False,
        },
        {
            "name": "conversation_trace",
            "type": "Object",
            "required": True,
            "description": "累积问答记录",
            "value": ref(LLM_STEP2, "userFields.conversation_trace"),
            "sourceType": "ref",
            "refType": "Object",
            "isStreamOut": False,
        },
        {
            "name": "session_state",
            "type": "Object",
            "required": True,
            "description": "会话状态",
            "value": ref(LLM_STEP2, "userFields.session_state"),
            "sourceType": "ref",
            "refType": "Object",
            "isStreamOut": False,
        },
    ]
    out_main["configs"]["responseTemplate"] = "问题：{interviewer_question}\n\n对话记录：{conversation_trace}"

    wf["description"] = "面试会话引擎 V2（已修复 conversation_trace 传递）：初始化→首题→提问器→推进"

    return wf


if __name__ == "__main__":
    out = "/workspace/output/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_fixed.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=4)
    print(f"Wrote {out}")
