#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jev 批量卡片查重 — 免进主页判断列表卡片是否已采集（实战验证 2026-11-01）
用法:
  from jev_batch import batch_judge
  results = batch_judge(card_label_sets, dup_label_sets)
  # {候选索引: True疑似重复/False新人/None失败}
设计: 一屏所有卡一次 systemone 请求（比逐卡快 6 倍）；
     精确集合命中在调用方短路，这里只处理需问 Jev 的子集。
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_client import _ask, MODEL

def batch_judge(card_label_sets, dup_label_sets, timeout=15, threshold=0.6):
    """card_label_sets: 候选卡 [labels(list)]; dup_label_sets: 已采 [labels(list)]
    threshold: noul 门槛，低于则当新人（0.6 防误跳）"""
    if not card_label_sets:
        return {}
    questions = {}
    for i, labs in enumerate(card_label_sets):
        questions[f"c{i}"] = {
            "type": "noul",
            "instructions": (f"card_{i}_is_duplicate: 候选卡片{i}的标签{sorted(set(labs))} "
                             f"是否与已采集列表中某一人高度相似(同一人的可能性>50%)")
        }
    state = [
        "约会APP列表页卡片查重。标签包括年龄/星座/学历/年薪/行业/同城等。",
        f"候选卡片({len(card_label_sets)}张):",
        json.dumps([sorted(set(x)) for x in card_label_sets], ensure_ascii=False),
        f"已采集用户标签({len(dup_label_sets)}人, 仅显示前60):",
        json.dumps([sorted(set(x)) for x in dup_label_sets[:60]], ensure_ascii=False),
    ]
    try:
        d = _ask({"model": MODEL, "state": state, "questions": questions}, timeout)
        out = {}
        for i in range(len(card_label_sets)):
            a = d.get("answers", {}).get(f"c{i}")
            if a is None:
                out[i] = None
            else:
                p = a.get("noul", 0)
                out[i] = bool(p >= threshold)
        return out
    except Exception as e:
        print(f"[jev-batch fail] {e}", flush=True)
        return {i: None for i in range(len(card_label_sets))}

if __name__ == "__main__":
    # 冒烟测试: 3张卡, 其中2张与历史重复
    sys.path.insert(0, os.path.expanduser("~/.hermes/cache/qingteng"))
    try:
        from collect import load_dup_labels
        dl = load_dup_labels()
        cards = [dl[0], ["999岁", "外星人座"], dl[5] if len(dl) > 5 else ["a", "b"]]
        print(batch_judge(cards, dl))
    except ImportError:
        dl = [["28岁", "射手座"], ["211硕士", "年薪30w+"]]
        print(batch_judge([dl[0], ["999岁", "外星人座"]], dl))
