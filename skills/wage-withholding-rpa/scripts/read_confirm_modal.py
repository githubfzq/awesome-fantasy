# -*- coding: utf-8 -*-
# read_confirm_modal.py v2 — 读 Tfrm_MsgDlgRich 弹窗文字/按钮，结果写共享盘 JSON，0 点击
import json
import rpa_core as R

out = {"modals": []}
for w in R.enum_top_windows():
    if not w["visible"]:
        continue
    if w["class"] not in ("Tfrm_MsgDlgRich", "TFrm_ImportConfig", "TfrmBase"):
        continue
    m = {"class": w["class"], "title": w["title"], "rect": w["rect"], "texts": [], "buttons": []}
    def dfs(hwnd):
        for k in R.enum_children(hwnd):
            t = ""
            try: t = R.wm_get_text(k["hwnd"]) or ""
            except Exception: pass
            if t.strip():
                m["texts"].append({"class": k["class"], "text": t.strip()})
            if k["class"].startswith(("TButton","TBitBtn","TITSSpeedButton","TModalSpeedButton")):
                m["buttons"].append({"class": k["class"], "text": t.strip(), "rect": k["rect"], "enabled": k["enabled"]})
            dfs(k["hwnd"])
    dfs(w["hwnd"])
    out["modals"].append(m)
with open(r"\Mac\Home\Documents\rpa\modal_read.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
