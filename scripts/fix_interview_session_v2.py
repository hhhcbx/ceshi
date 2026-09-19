#!/usr/bin/env python3
"""
Fix Interview Session V2 - align types with working MVP_1, separate in/out trace fields.

Type errors (应为 boolean/object) caused by:
- String output fields when platform/LLM returns Object
- required:true on outputs (working ref uses required:false, enabled:false)
- END session_step_json type mismatch (Object vs String)
"""

import json

START = "START2e5c8578e5ad405aac34381256907cc0"
LLM_STEP1 = "LLM1979f9a7d4f541a79c6babe12f61cb31"
LLM_STEP2 = "LLM703a1311197a49509c6973146daa59b6"
QUESTIONER = "Questioner358948a33f8c48c0aa009b50b57e2935"
OUTPUT_MAIN = "outputComponent326977145f934cf69c6dec7d4afb2472"
END = "ENDf3e1bcb7064b41db9fd52aaad1b4af32"
LLM_INIT = "LLM12dbd76faf2b426da45439d3b7c4e019"

# Same prompts as working WF_Interview_Session_Engine_MVP_1, with turns wrapper
SYSTEM_PROMPT = """你是“算法面试会话状态机”，不是普通聊天助手。

你的唯一任务是根据输入的 prompt_pack、runtime_config、session_state、conversation_trace_in、user_answer、current_stage，推进一次面试会话状态，并生成下一步面试问题或结束状态。

你必须严格遵守以下原则：

1. 只推进一次面试状态
2. 面试阶段固定为：X_BASE → Y_PROJECT → Z_EXTEND → DONE
3. conversation_trace_out 必须是对象，格式为 {"turns": [...]}，每轮追加记录
4. 只输出严格 JSON，不要 Markdown，不要代码块，不要解释
5. conversation_trace_in.turns 为空时使用 []
6. current_stage 为空时使用 X_BASE"""

USER_PROMPT = """你是面试会话引擎。推进一次面试状态，输出严格 JSON，不要 Markdown。

prompt_pack: {prompt_pack}
runtime_config: {runtime_config}
session_state: {session_state}
conversation_trace_in: {conversation_trace_in}
user_answer: {user_answer}
current_stage: {current_stage}

规则：
1. 读取 conversation_trace_in.turns，本轮必须更新 conversation_trace_out.turns（追加或填写 answer）
2. user_answer 非空时，把上一题和答案写入 turns
3. 禁止 conversation_trace_out 与 conversation_trace_in 完全相同
4. 按 X_BASE → Y_PROJECT → Z_EXTEND 推进

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
  "conversation_trace_out": {
    "turns": [
      {
        "stage": "string",
        "round_index": 0,
        "turn_index": 0,
        "question": "string",
        "answer": "string",
        "trace_type": "normal|empty_answer|defense_rejection"
      }
    ]
  },
  "interviewer_question": "string",
  "current_stage_out": "X_BASE|Y_PROJECT|Z_EXTEND|DONE",
  "is_finished_out": false
}"""


def ref(node, path):
    return f"${{{node}.{path}}}"


def start(path):
    return ref(START, f"userFields.{path}")


def llm_outputs_working():
    """Match working MVP_1 types + conversation_trace_out + session_state for chaining."""
    return [
        {"name": "session_step_json", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "interviewer_question", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "current_stage_out", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "is_finished_out", "type": "Boolean", "description": "", "required": False, "enabled": False},
        {"name": "session_state", "type": "Object", "description": "会话状态", "required": False, "enabled": True},
        {
            "name": "conversation_trace_out",
            "type": "Object",
            "description": "更新后的问答记录 {turns:[]}",
            "required": False,
            "enabled": True,
        },
    ]


def input_field(name, ftype, required, desc, value):
    return {
        "name": name,
        "type": ftype,
        "required": required,
        "description": desc,
        "value": value,
        "sourceType": "ref",
        "refType": ftype,
        "expanded": False,
        "descExpanded": False,
    }


def llm_inputs_step1():
    return [
        input_field("prompt_pack", "String", True, "面试官 Prompt 包", start("prompt_pack")),
        input_field("runtime_config", "Object", True, "运行配置", start("runtime_config")),
        input_field("session_state", "Object", False, "会话状态", start("session_state")),
        input_field("conversation_trace_in", "Object", False, "历史问答", start("conversation_trace")),
        input_field("user_answer", "String", False, "用户回答", start("user_answer")),
        input_field("current_stage", "String", False, "当前阶段", start("current_stage")),
    ]


def llm_inputs_step2():
    return [
        input_field("prompt_pack", "String", True, "面试官 Prompt 包", start("prompt_pack")),
        input_field("runtime_config", "Object", True, "运行配置", start("runtime_config")),
        input_field("session_state", "Object", False, "会话状态", ref(LLM_STEP1, "userFields.session_state")),
        input_field(
            "conversation_trace_in",
            "Object",
            False,
            "上一步问答记录",
            ref(LLM_STEP1, "userFields.conversation_trace_out"),
        ),
        input_field(
            "user_answer",
            "String",
            False,
            "提问器回答",
            ref(QUESTIONER, "preDefinedFields.userResponse"),
        ),
        input_field(
            "current_stage",
            "String",
            False,
            "当前阶段",
            ref(LLM_STEP1, "userFields.current_stage_out"),
        ),
    ]


def build():
    src = "/home/ubuntu/.cursor/projects/workspace/uploads/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_9630.json"
    with open(src, encoding="utf-8") as f:
        wf = json.load(f)

    wf["schema"]["components"] = [c for c in wf["schema"]["components"] if c["id"] != LLM_INIT]
    wf["schema"]["connections"] = [
        c
        for c in wf["schema"]["connections"]
        if c.get("target") != LLM_INIT and c.get("source") != LLM_INIT
    ]
    if not any(c.get("source") == START and c.get("target") == LLM_STEP1 for c in wf["schema"]["connections"]):
        wf["schema"]["connections"].insert(
            0,
            {
                "id": "edge_start_step1",
                "type": "custom",
                "source": START,
                "target": LLM_STEP1,
                "targetHandle": "model_left",
                "style": {"stroke": "#777", "strokeWidth": 1},
            },
        )

    components = {c["id"]: c for c in wf["schema"]["components"]}

    start_node = components[START]
    for field in start_node["outputs"][1]["fields"]:
        if field["name"] == "conversation_trace":
            field["type"] = "Object"
            field["description"] = '历史问答，首次传 {"turns":[]}'
            field["nextOutputParamInfo"] = [
                {
                    "name": "turns",
                    "type": "Object",
                    "description": "问答轮次",
                    "required": False,
                    "value": "",
                    "sourceType": "ref",
                    "expanded": True,
                    "descExpanded": False,
                }
            ]

    for lid in (LLM_STEP1, LLM_STEP2):
        llm = components[lid]
        llm["inputs"][0]["fields"] = llm_inputs_step1() if lid == LLM_STEP1 else llm_inputs_step2()
        llm["outputs"][0]["fields"] = llm_outputs_working()
        llm["configs"]["templateContent"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ]

    end = components[END]
    end["outputs"][0]["fields"][0]["name"] = "session_step_json"
    end["outputs"][0]["fields"][0]["type"] = "String"
    end["outputs"][0]["fields"][0]["value"] = ref(LLM_STEP2, "userFields.session_step_json")
    end["outputs"][0]["fields"][0]["refType"] = "String"

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
            "name": "conversation_trace_out",
            "type": "Object",
            "required": True,
            "description": "",
            "value": ref(LLM_STEP2, "userFields.conversation_trace_out"),
            "sourceType": "ref",
            "refType": "Object",
            "isStreamOut": False,
        },
    ]
    out_main["configs"]["responseTemplate"] = "${interviewer_question}"

    wf["description"] = "面试会话引擎 V2 v4：类型对齐 MVP_1，conversation_trace_in/out 分离"
    return wf


if __name__ == "__main__":
    out = "/workspace/output/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_fixed.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=4)

    test = {
        "prompt_pack": "你是技术面试官，请出算法题。",
        "runtime_config": {"round_x": 1, "round_y": 1, "round_z": 1, "max_turns_per_round": 2},
        "session_state": {},
        "conversation_trace": {"turns": []},
        "user_answer": "",
        "current_stage": "",
    }
    with open("/workspace/output/test_data_Interview_Session_V2_trial.json", "w", encoding="utf-8") as f:
        json.dump(test, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out}")
