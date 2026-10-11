# -*- coding: utf-8 -*-
# wizard_import.py — 点【导入】→ 等结果框（TfrmBase）→ 读取结果文字 + 按钮
import time, json
import rpa_core as R
out = {}
wiz = R.find_window("TFrm_ImportConfig", visible_only=True)
assert wiz
# 导入钮 = 向导内 x 较小的按钮 [715,555,775,587]
btns = {}
def dfs(hwnd):
    for k in R.enum_children(hwnd):
        if k["class"].startswith(("TITSSpeedButton","TModalSpeedButton","TButton","TBitBtn")) and k["visible"]:
            btns[tuple(k["rect"])] = k
        dfs(k["hwnd"])
dfs(wiz["hwnd"])
bs = sorted(btns.values(), key=lambda b: b["rect"][0])
imp = bs[0]
cx, cy = R.center(imp["rect"])
out["import_btn_rect"] = imp["rect"]
R.click_at(int(cx), int(cy))
# 等结果框
t0 = time.time(); box = None
while time.time() - t0 < 20:
    boxes = [w for w in R.enum_top_windows() if w["visible"] and w["class"] == "TfrmBase"]
    if boxes:
        box = boxes[0]; break
    time.sleep(0.6)
if box:
    time.sleep(1.2)  # 让结果文字写完
    texts = []
    def dfs2(hwnd):
        for k in R.enum_children(hwnd):
            t = ""
            try: t = R.wm_get_text(k["hwnd"]) or ""
            except Exception: pass
            if t.strip(): texts.append({"cls": k["class"], "t": t.strip()})
            dfs2(k["hwnd"])
    dfs2(box["hwnd"])
    out["box_rect"] = box["rect"]
    out["box_texts"] = texts
else:
    out["box"] = None
with open(r"\Mac\Home\Documents\rpa\wizard_import_out.json","w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
