# -*- coding: utf-8 -*-
import json
import rpa_core as R
state = {"windows": [], "wizard": None}
for w in R.enum_top_windows():
    if w["visible"] and w["class"] in ("TFrm_ImportConfig","TfrmBase","Tfrm_MsgDlgRich","Tfrm_MainFrame"):
        state["windows"].append({"class": w["class"], "title": w["title"], "rect": w["rect"]})
        if w["class"] == "TFrm_ImportConfig":
            state["wizard"] = w
with open(r"\Mac\Home\Documents\rpa\state_probe.json","w",encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=1)
