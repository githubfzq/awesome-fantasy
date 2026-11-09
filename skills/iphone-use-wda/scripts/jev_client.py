#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jev 决策客户端（Magpie 网关 systemone API）— 实战验证版 2026-11-01
用法:
  from jev_client import jev_noul, jev_choice, jev_score
  ok, prob = jev_noul("Is this greeting in English?", ["hello"])
  sel, probs = jev_choice("Which is a fruit?", ["apple","car","rose"], ["I need one to eat"])
注意: Jev 不是 chat 模型，/v1/chat/completions 会报错，必须走 /v1/systemone。
"""
import json, urllib.request

GATEWAY = "http://127.0.0.1:3425"
MODEL = "jev-latest"

def _ask(payload, timeout=12):
    req = urllib.request.Request(GATEWAY + "/v1/systemone",
        data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def jev_noul(instruction, state, timeout=12):
    """是/否判断 → (bool, prob)。失败返回 (None, 0)"""
    try:
        d = _ask({"model": MODEL, "state": state,
                  "questions": {"q": {"type": "noul", "instructions": instruction}}}, timeout)
        a = d["answers"]["q"]
        return a.get("noul", 0) >= 0.5, a.get("noul", 0)
    except Exception:
        return None, 0

def jev_choice(instruction, options, state, timeout=12):
    """选项决策 → (option_key_str, prob_map)。失败返回 (None, {})"""
    try:
        criteria = {str(i): opt for i, opt in enumerate(options)}
        d = _ask({"model": MODEL, "state": state,
                  "questions": {"q": {"type": "choice", "instructions": instruction,
                                       "criteria": criteria}}}, timeout)
        a = d["answers"]["q"]
        sel = a.get("choice", a.get("selected"))
        probs = a.get("probabilities", {})
        return sel, probs
    except Exception:
        return None, {}

def jev_score(instruction, levels, state, timeout=12):
    """有序评分 → (position, probs)。失败返回 (None, {})"""
    try:
        d = _ask({"model": MODEL, "state": state,
                  "questions": {"q": {"type": "score", "instructions": instruction,
                                       "criteria": {"levels": levels}}}}, timeout)
        a = d["answers"]["q"]
        return a.get("score", a.get("position")), a.get("probabilities", {})
    except Exception:
        return None, {}

def jev_batch_noul(instruction_prefix, questions_state, n, timeout=15):
    """一次请求发 n 个 noul 问题。questions_state: 共享 state(字符串数组)
    返回 {i: (bool, prob)}；失败返回 {i: (None,0)}"""
    try:
        questions = {f"q{i}": {"type": "noul",
                               "instructions": f"{instruction_prefix}_{i}: {instruction_prefix}"}
                     for i in range(n)}
        d = _ask({"model": MODEL, "state": questions_state, "questions": questions}, timeout)
        out = {}
        for i in range(n):
            a = d.get("answers", {}).get(f"q{i}", {})
            p = a.get("noul", 0)
            out[i] = (p >= 0.5, p)
        return out
    except Exception:
        return {i: (None, 0) for i in range(n)}

if __name__ == "__main__":
    print(jev_noul("Is this greeting in English?", ["hello"]))
    print(jev_choice("Which is a fruit?", ["apple", "car", "rose"], ["I need one to eat"]))
