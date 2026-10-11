# -*- coding: utf-8 -*-
# close_result_box.py — 点结果框右钮【关闭】，等框消失
import time, json
import rpa_core as R
out = {}
boxes = [w for w in R.enum_top_windows() if w["visible"] and w["class"]=="TfrmBase"]
if boxes:
    box = boxes[0]
    btns = {}
    def dfs(hwnd):
        for k in R.enum_children(hwnd):
            if k["class"].startswith(("TModalSpeedButton","TITSSpeedButton","TButton","TBitBtn")) and k["visible"]:
                btns[tuple(k["rect"])] = k
            dfs(k["hwnd"])
    dfs(box["hwnd"])
    bs = sorted(btns.values(), key=lambda b: b["rect"][0])
    right = bs[-1]  # 右钮 = 关闭
    cx, cy = R.center(right["rect"])
    out["close_btn_rect"] = right["rect"]
    R.click_at(int(cx), int(cy))
    t0 = time.time(); gone = False
    while time.time() - t0 < 8:
        if not [w for w in R.enum_top_windows() if w["visible"] and w["class"]=="TfrmBase"]:
            gone = True; break
        time.sleep(0.5)
    out["status"] = "closed" if gone else "still_open"
else:
    out["status"] = "no_box"
with open(r"\Mac\Home\Documents\rpa\close_box_out.json","w") as f:
    json.dump(out, f)
