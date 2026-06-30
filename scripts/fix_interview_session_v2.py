#!/usr/bin/env python3
"""
Fix conversation_trace {0} issue for Interview Session Engine V2.

Root cause: JSON array [] stored in Object-typed field gets serialized as {0:..., 1:...}.
Fix: wrap as { "turns": [...] }, pass from START (not LLM init), align with working MVP_1.
"""

import json

START = "START2e5c8578e5ad405aac34381256907cc0"
LLM_STEP1 = "LLM1979f9a7d4f541a79c6babe12f61cb31"
LLM_STEP2 = "LLM703a1311197a49509c6973146daa59b6"
QUESTIONER = "Questioner358948a33f8c48c0aa009b50b57e2935"
OUTPUT_MAIN = "outputComponent326977145f934cf69c6dec7d4afb2472"
OUTPUT_Q = "outputComponent0673505583e941029b0f043355afa099"
END = "ENDf3e1bcb7064b41db9fd52aaad1b4af32"
LLM_INIT = "LLM12dbd76faf2b426da45439d3b7c4e019"

# Same system prompt style as working WF_Interview_Session_Engine_MVP_1
SYSTEM_PROMPT = """你是“算法面试会话状态机”，不是普通聊天助手。

你的唯一任务是根据输入的 prompt_pack、runtime_config、session_state、conversation_trace、user_answer、current_stage，推进一次面试会话状态，并生成下一步面试问题或结束状态。

你必须严格遵守以下原则：

1. 只推进一次面试状态
2. 面试阶段固定为：X_BASE → Y_PROJECT → Z_EXTEND → DONE
3. stage_round_counter 与 turn_counter_in_current_round 分开计数
4. conversation_trace 必须是对象，内含 turns 数组；每轮追加到 turns，禁止覆盖历史
5. 只输出严格 JSON，不要 Markdown，不要代码块，不要解释
6. conversation_trace.turns 为空时使用 []
7. current_stage 为空时使用 X_BASE
8. interviewer_question 必须是当前要展示给用户的问题；若 current_stage=DONE 则输出「面试已完成，正在生成最终报告」"""

USER_PROMPT = """你是面试会话引擎。请根据 prompt_pack、runtime_config、session_state、conversation_trace、user_answer、current_stage，推进一次面试状态，输出严格 JSON，不要 Markdown。

prompt_pack: {prompt_pack}
runtime_config: {runtime_config}
session_state: {session_state}
conversation_trace: {conversation_trace}
user_answer: {user_answer}
current_stage: {current_stage}

规则：
1. 首次运行时初始化 current_stage=X_BASE
2. user_answer 非空时，把上一题和答案追加到 conversation_trace.turns 数组末尾
3. 按 X_BASE → Y_PROJECT → Z_EXTEND 顺序推进
4. 全部阶段完成后 current_stage=DONE，is_finished=true
5. conversation_trace 必须输出完整对象（含历史 turns）

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
  "conversation_trace": {
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
  "is_finished_out": false,
  "session_step_json": "string"
}"""


def ref(node, path):
    return f"${{{node}.{path}}}"


def start(path):
    return ref(START, f"userFields.{path}")


def llm_outputs_working_style():
    """Match working MVP_1: session_step_json as String, no separate conversation_trace output."""
    return [
        {"name": "session_step_json", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "interviewer_question", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "current_stage_out", "type": "String", "description": "", "required": False, "enabled": False},
        {"name": "is_finished_out", "type": "Boolean", "description": "", "required": False, "enabled": False},
        {
            "name": "conversation_trace",
            "type": "Object",
            "description": "问答记录 {turns:[]}",
            "required": False,
            "enabled": True,
        },
        {
            "name": "session_state",
            "type": "Object",
            "description": "会话状态",
            "required": False,
            "enabled": True,
        },
    ]


def build():
    src = "/home/ubuntu/.cursor/projects/workspace/uploads/WF_Interview_Session_Engine_MVP_V2_hn_3-V0_9630.json"
    with open(src, encoding="utf-8") as f:
        wf = json.load(f)

    components = {c["id"]: c for c in wf["schema"]["components"]}

    # Remove init LLM from components list
    wf["schema"]["components"] = [c for c in wf["schema"]["components"] if c["id"] != LLM_INIT]

    start_node = components[START]
    for field in start_node["outputs"][1]["fields"]:
        if field["name"] == "conversation_trace":
            field["description"] = "历史问答；首次传 {\"turns\":[]}，禁止传裸数组 []"
            field["nextOutputParamInfo"] = [
                {
                    "name": "turns",
                    "type": "Object",
                    "description": "问答轮次列表",
                    "required": False,
                    "value": "",
                    "sourceType": "ref",
                    "expanded": True,
                    "descExpanded": False,
                }
            ]

    step1 = components[LLM_STEP1]
    step1["inputs"][0]["fields"] = [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "面试官 Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": start("session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "conversation_trace", "type": "Object", "required": False, "description": "历史问答", "value": start("conversation_trace"), "sourceType": "ref", "refType": "Object"},
        {"name": "user_answer", "type": "String", "required": False, "description": "用户回答", "value": start("user_answer"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": start("current_stage"), "sourceType": "ref", "refType": "String"},
    ]
    step1["outputs"][0]["fields"] = llm_outputs_working_style()
    step1["configs"]["templateContent"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    step2 = components[LLM_STEP2]
    step2["inputs"][0]["fields"] = [
        {"name": "prompt_pack", "type": "String", "required": True, "description": "面试官 Prompt 包", "value": start("prompt_pack"), "sourceType": "ref", "refType": "String"},
        {"name": "runtime_config", "type": "Object", "required": True, "description": "运行配置", "value": start("runtime_config"), "sourceType": "ref", "refType": "Object"},
        {"name": "session_state", "type": "Object", "required": False, "description": "会话状态", "value": ref(LLM_STEP1, "userFields.session_state"), "sourceType": "ref", "refType": "Object"},
        {"name": "conversation_trace", "type": "Object", "required": False, "description": "历史问答", "value": ref(LLM_STEP1, "userFields.conversation_trace"), "sourceType": "ref", "refType": "Object"},
        {"name": "user_answer", "type": "String", "required": False, "description": "用户本轮回答", "value": ref(QUESTIONER, "preDefinedFields.userResponse"), "sourceType": "ref", "refType": "String"},
        {"name": "current_stage", "type": "String", "required": False, "description": "当前阶段", "value": ref(LLM_STEP1, "userFields.current_stage_out"), "sourceType": "ref", "refType": "String"},
    ]
    step2["outputs"][0]["fields"] = llm_outputs_working_style()
    step2["configs"]["templateContent"] = [
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
            "name": "conversation_trace",
            "type": "Object",
            "required": True,
            "description": "",
            "value": ref(LLM_STEP2, "userFields.conversation_trace"),
            "sourceType": "ref",
            "refType": "Object",
            "isStreamOut": False,
        },
    ]
    out_main["configs"]["responseTemplate"] = "${interviewer_question}"

    # Rewire: START → LLM197 (skip init LLM)
    wf["schema"]["connections"] = [
        {
            "id": "edge_start_step1",
            "type": "custom",
            "source": START,
            "target": LLM_STEP1,
            "targetHandle": "model_left",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
        {
            "id": "edge52ca3e6fe7214862ad9d9f8165d81856",
            "type": "custom",
            "source": OUTPUT_MAIN,
            "target": END,
            "sourceHandle": "code_right",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
        {
            "id": "edgefe9bd7744c3d4fc990ff3fb957856adb",
            "type": "custom",
            "source": LLM_STEP1,
            "target": OUTPUT_Q,
            "sourceHandle": "model_right",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
        {
            "id": "edge68cb647aad9543509e437c0e0a739bc7",
            "type": "custom",
            "source": OUTPUT_Q,
            "target": QUESTIONER,
            "sourceHandle": "code_right",
            "targetHandle": "model_left",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
        {
            "id": "edge0c0ef0df7d604edda02d0c904b07ca96",
            "type": "custom",
            "source": QUESTIONER,
            "target": LLM_STEP2,
            "sourceHandle": "questioner_reply_directly_right",
            "targetHandle": "model_left",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
        {
            "id": "edge01c9fc16414c459d9899d2ad72f33a5d",
            "type": "custom",
            "source": LLM_STEP2,
            "target": OUTPUT_MAIN,
            "sourceHandle": "model_right",
            "style": {"stroke": "#777", "strokeWidth": 1},
        },
    ]

    wf["description"] = "面试会话引擎 V2 v2-fix：conversation_trace 用 {turns:[]} 包装，从 START 直传"
    wf["name"] = "WF_Interview_Session_Engine_MVP_V2_hn_3"
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
    test_path = "/workspace/output/test_data_Interview_Session_V2_trial.json"
    with open(test_path, "w", encoding="utf-8") as f:
        json.dump(test, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out}")
    print(f"Wrote {test_path}")
