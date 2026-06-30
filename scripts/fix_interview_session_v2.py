#!/usr/bin/env python3
"""
Fix conversation_trace not updating (stays at input).

Root cause on Xiaoyi:
- Object-typed input/output with same semantic field pass through input unchanged
- LLM JSON nested object mapping to output params is unreliable

Fix:
- Input param: history_trace (String, JSON text)
- Output param: conversation_trace (String, JSON text) — enabled
- Enable all JSON output fields for mapping
- END returns session_step_json String
"""

import json

START = "START2e5c8578e5ad405aac34381256907cc0"
LLM_STEP1 = "LLM1979f9a7d4f541a79c6babe12f61cb31"
LLM_STEP2 = "LLM703a1311197a49509c6973146daa59b6"
QUESTIONER = "Questioner358948a33f8c48c0aa009b50b57e2935"
OUTPUT_MAIN = "outputComponent326977145f934cf69c6dec7d4afb2472"
OUTPUT_Q = "outputComponent0673505583e941029b0f043355afa099"
END = "ENDf3e1bcb7064b41db9fd52aaad1b4af32"

SYSTEM_PROMPT = """你是“算法面试会话状态机”。

每次调用只推进一个 step，必须输出严格 JSON（无 Markdown、无代码块、无解释）。

关键要求：
1. 读取 history_trace（JSON 字符串），解析其中 turns 数组
2. 本轮必须在 turns 末尾追加或更新记录，禁止原样返回空 turns
3. 输出的 conversation_trace 必须是更新后的完整 JSON 字符串（含 turns 数组）
4. session_step_json 必须等于本次输出的完整 JSON 对象（字符串形式）
5. 面试阶段：X_BASE → Y_PROJECT → Z_EXTEND → DONE"""

USER_PROMPT = """推进一次面试，输出严格 JSON。

prompt_pack: {prompt_pack}
runtime_config: {runtime_config}
session_state: {session_state}
history_trace: {history_trace}
user_answer: {user_answer}
current_stage: {current_stage}

规则：
1. 解析 history_trace JSON 字符串，读取 turns 数组（若为空则 turns=[]）
2. 若 user_answer 为空（首题）：在 turns 追加一条 answer 为空的记录，question=interviewer_question
3. 若 user_answer 非空：更新 turns 最后一条的 answer，或追加新记录
4. conversation_trace 字段输出更新后的 JSON 字符串，格式：{"turns":[...]}
5. 禁止 conversation_trace 与 history_trace 完全相同（除非 turns 确实无变化且已记录本题）

输出 JSON（所有字段必填）：
{
  "session_state": {
    "current_stage": "X_BASE|Y_PROJECT|Z_EXTEND|DONE",
    "stage_round_counter": {"X_BASE": 0, "Y_PROJECT": 0, "Z_EXTEND": 0},
    "turn_counter_in_current_round": 0,
    "is_finished": false,
    "kill_switch_reason": "",
    "last_question": "",
    "last_stage": "",
    "last_round_index": 0,
    "last_turn_index": 0
  },
  "conversation_trace": "{\\"turns\\":[...]}",
  "interviewer_question": "string",
  "current_stage_out": "X_BASE|Y_PROJECT|Z_EXTEND|DONE",
  "is_finished_out": false,
  "session_step_json": "{\\"...full json...\\"}"
}"""


def ref(node, path):
    return f"${{{node}.{path}}}"


def start(path):
    return ref(START, f"userFields.{path}")


def llm_outputs():
    return [
        {"name": "session_step_json", "type": "String", "description": "完整步骤 JSON 字符串", "required": True, "enabled": True},
        {"name": "interviewer_question", "type": "String", "description": "当前问题", "required": True, "enabled": True},
        {"name": "current_stage_out", "type": "String", "description": "当前阶段", "required": True, "enabled": True},
        {"name": "is_finished_out", "type": "Boolean", "description": "是否结束", "required": True, "enabled": True},
        {"name": "conversation_trace", "type": "String", "description": "更新后问答记录 JSON 字符串", "required": True, "enabled": True},
        {"name": "session_state", "type": "Object", "description": "会话状态", "required": True, "enabled": True},
    ]


def llm_inputs_step1():
    return [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": start("session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "history_trace", "type": "String", "required": False, "description": "历史问答 JSON 字符串", "value": start("conversation_trace"), "sourceType": "ref", "refType": "String"},
        {"name": "user_answer", "type": "String", "required": False, "description": "用户回答", "value": start("user_answer"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": start("current_stage"), "sourceType": "ref", "refType": "String"},
    ]


def llm_inputs_step2():
    return [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": ref(LLM_STEP1, "userFields.session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "history_trace", "type": "String", "required": False, "description": "上一步问答 JSON", "value": ref(LLM_STEP1, "userFields.conversation_trace"), "sourceType": "ref", "refType": "String"},
        {"name": "user_answer", "type": "String", "required": False, "description": "提问器回答", "value": ref(QUESTIONER, "preDefinedFields.userResponse"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": ref(LLM_STEP1, "userFields.current_stage_out"), "sourceType": "ref", "refType": "String"},
    ]


def build():
    with open("/workspace/output/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_fixed.json", encoding="utf-8") as f:
        wf = json.load(f)

    components = {c["id"]: c for c in wf["schema"]["components"]}

    start_node = components[START]
    for field in start_node["outputs"][1]["fields"]:
        if field["name"] == "conversation_trace":
            field["type"] = "String"
            field["description"] = '历史问答 JSON 字符串，首次传 {"turns":[]}（注意是字符串类型）'
            field.pop("nextOutputParamInfo", None)

    for lid in (LLM_STEP1, LLM_STEP2):
        llm = components[lid]
        llm["inputs"][0]["fields"] = llm_inputs_step1() if lid == LLM_STEP1 else llm_inputs_step2()
        llm["outputs"][0]["fields"] = llm_outputs()
        llm["configs"]["templateContent"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ]

    end = components[END]
    end["outputs"][0]["fields"][0]["value"] = ref(LLM_STEP2, "userFields.session_step_json")

    out_main = components[OUTPUT_MAIN]
    out_main["outputs"][0]["fields"] = [
        {
            "name": "interviewer_question",
            "type": "String",
            "required": True,
            "description": "",
            "value": ref(LLM_STEP2, "userFields.interviewer_question"),
            "sourceType": "ref",
            "refType": "String",
            "isStreamOut": False,
        },
        {
            "name": "conversation_trace",
            "type": "String",
            "required": True,
            "description": "",
            "value": ref(LLM_STEP2, "userFields.conversation_trace"),
            "sourceType": "ref",
            "refType": "String",
            "isStreamOut": False,
        },
        {
            "name": "session_step_json",
            "type": "String",
            "required": True,
            "description": "",
            "value": ref(LLM_STEP2, "userFields.session_step_json"),
            "sourceType": "ref",
            "refType": "String",
            "isStreamOut": False,
        },
    ]
    out_main["configs"]["responseTemplate"] = "${interviewer_question}"

    wf["description"] = "面试会话引擎 V2 v3-fix：conversation_trace 改为 String JSON，入参 history_trace 与出参分离"
    return wf


if __name__ == "__main__":
    out = "/workspace/output/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_fixed.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=4)

    test = {
        "prompt_pack": "你是技术面试官，请出算法题。",
        "runtime_config": {"round_x": 1, "round_y": 1, "round_z": 1, "max_turns_per_round": 2},
        "session_state": {},
        "conversation_trace": '{"turns": []}',
        "user_answer": "",
        "current_stage": "",
    }
    with open("/workspace/output/test_data_Interview_Session_V2_trial.json", "w", encoding="utf-8") as f:
        json.dump(test, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out}")
