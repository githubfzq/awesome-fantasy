# -*- coding: utf-8 -*-
# wizard_copy.py — 向导：选①复制上月 → BM_GETCHECK 断言 → 导入 → 读结果框文字
import time, json, ctypes
import rpa_core as R
BM_GETCHECK = 0x00F0
out = {}
wiz = R.find_window("TFrm_ImportConfig", visible_only=True)
assert wiz, "wizard missing"
ox, oy = wiz["rect"][0], wiz["rect"][1]

# 1) 收集单选钮
radios = {}
def dfs(hwnd):
    for k in R.enum_children(hwnd):
        if k["class"] in ("TRadioButton","TXPFarmerRadioButton") or "Radio" in (k["class"] or ""):
            radios[tuple(k["rect"])] = k
        dfs(k["hwnd"])
dfs(wiz["hwnd"])
rads = sorted(radios.values(), key=lambda b: (b["rect"][1], b["rect"][0]))
out["n_radios"] = len(rads)
out["radio_rects"] = [b["rect"] for b in rads]
# 选第①个（最上）
r0 = rads[0]
if ctypes.windll.user32.SendMessageW(r0["hwnd"], BM_GETCHECK, 0, 0) == 0:
    cx, cy = R.center(r0["rect"])
    R.click_at(int(cx), int(cy))
    time.sleep(0.6)
chk = ctypes.windll.user32.SendMessageW(r0["hwnd"], BM_GETCHECK, 0, 0)
out["radio1_checked"] = (chk == 1)
with open(r"\Mac\Home\Documents\rpa\wizard_copy_out.json","w") as f:
    json.dump(out, f, ensure_ascii=False)
