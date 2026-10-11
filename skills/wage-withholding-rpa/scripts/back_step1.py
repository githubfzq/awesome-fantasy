# -*- coding: utf-8 -*-
# back_step1.py — 点明细页【返回】回步骤1，等页判定为 Tfrm_SelectSDXM
import time, json
import rpa_core as R
mf = R.find_window("Tfrm_MainFrame", visible_only=True)
out = {}
target = None
def dfs(hwnd):
    global target
    for k in R.enum_children(hwnd):
        if k["class"].startswith(("TITSSpeedButton","TModalSpeedButton","TButton","TBitBtn")) and k["visible"]:
            t = ""
            try: t = R.wm_get_text(k["hwnd"]) or ""
            except Exception: pass
            if t.strip() == "返回":
                target = k
        dfs(k["hwnd"])
dfs(mf["hwnd"])
if target:
    cx, cy = R.center(target["rect"])
    out["via"] = "text=返回"; out["at"] = [cx, cy]
    R.click_at(int(cx), int(cy))
else:
    cx, cy = mf["rect"][0] + 253, mf["rect"][1] + 197
    out["via"] = "fallback_geo"; out["at"] = [cx, cy]
    R.click_at(int(cx), int(cy))
t0 = time.time(); ok = False
while time.time() - t0 < 12:
    # 步骤1 页判据：主窗子树出现 Tfrm_SelectSDXM
    found = [False]
    def check(hwnd):
        for k in R.enum_children(hwnd):
            if k["class"] == "Tfrm_SelectSDXM":
                found[0] = True
            check(k["hwnd"])
    check(mf["hwnd"])
    if found[0]:
        ok = True; break
    time.sleep(0.8)
out["back_ok"] = ok
with open(r"\Mac\Home\Documents\rpa\back_out.json","w") as f:
    json.dump(out, f)
