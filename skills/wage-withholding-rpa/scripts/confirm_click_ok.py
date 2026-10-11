# -*- coding: utf-8 -*-
# confirm_click_ok.py — 点「确认信息」弹窗左钮【确定】（x 较小者），等弹窗消失
import time
import rpa_core as R

def find_confirm():
    for w in R.enum_top_windows():
        if w["visible"] and w["class"] == "Tfrm_MsgDlgRich" and (w["title"] or "") == "确认信息":
            return w
    return None

m = find_confirm()
if not m:
    with open(r"\Mac\Home\Documents\rpa\confirm_click_out.json","w") as f:
        json.dump({"status":"no_modal"}, f)
    raise SystemExit
btns = []
def dfs(hwnd):
    for k in R.enum_children(hwnd):
        if k["class"].startswith(("TITSSpeedButton","TModalSpeedButton","TButton","TBitBtn")) and k["visible"]:
            btns.append(k)
        dfs(k["hwnd"])
dfs(m["hwnd"])
# 去重（同 rect 只留一个）
uniq = {}
for b in btns:
    uniq[tuple(b["rect"])] = b
btns = sorted(uniq.values(), key=lambda b: b["rect"][0])
left = btns[0]  # x 最小 = 确定
cx, cy = R.center(left["rect"])
R.click_at(int(cx), int(cy))
# 等弹窗消失
t0 = time.time()
gone = False
while time.time() - t0 < 10:
    if not find_confirm():
        gone = True
        break
    time.sleep(0.5)
import json
with open(r"\Mac\Home\Documents\rpa\confirm_click_out.json","w") as f:
    json.dump({"status":"clicked" if gone else "still_there", "at":[cx,cy], "n_btns":len(btns)}, f)
