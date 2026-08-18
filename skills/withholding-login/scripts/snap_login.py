# snap_login.py — 登录窗诊断：前台聚焦 → 窗口裁剪截图 + 顶部页签候选枚举
#
# 输出:
#   1) C:\rpa\screenshots\login_win.png — 登录窗裁剪截图（bbox=GetWindowRect）
#   2) JSONL 日志: login_rect, 顶部区域(y<top+90px)可见子控件列表(含title)
import ctypes
import os
import sys
import time

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
EXE = r"C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe"
PSEXEC = r"C:\rpa\pstools\PsExec64.exe"
VM_SHOT_DIR = r"C:\rpa\screenshots"


def main(r):
    # ---- 找 / 启动登录窗 ----
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if not lw or not lw["enabled"]:
        r.emit("launch", detail={"reason": "登录窗未找到，尝试启动"})
        import subprocess
        cmd = '%s -i 1 -d -accepteula -w %s %s' % (PSEXEC, r"C:\ITSKHD\EPPortal_DS3.0", EXE)
        subprocess.Popen(cmd, shell=True)

        def ready():
            w = R.find_window(LOGIN_CLS, visible_only=True)
            return {"win": w} if w and w["enabled"] else None

        _, elapsed = R.wait_until(ready, timeout=45, interval=0.5)
        lw = R.find_window(LOGIN_CLS, visible_only=True)
        r.emit("launched", detail={"elapsed_s": elapsed, "rect": lw["rect"]})
    else:
        r.emit("already_visible", detail=lw)

    # ---- 前台聚焦 ----
    hwnd = lw["hwnd"]
    # ctypes 直接调 SetForegroundWindow + BringToTop
    try:
        R.user32.SetForegroundWindow(hwnd)
        R.user32.BringWindowToTop(hwnd)
    except Exception as e:
        r.emit("foreground_warn", detail={"error": repr(e)})
    time.sleep(0.8)  # 等待渲染稳定

    # ---- 窗口裁剪截图 ----
    rc = tuple(R.rect_of(hwnd))
    os.makedirs(VM_SHOT_DIR, exist_ok=True)
    shot_path = os.path.join(VM_SHOT_DIR, "login_win.png")
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=rc)
        img.save(shot_path)
        r.emit("screenshot", detail={
            "path": shot_path,
            "rect": list(rc),
            "size": img.size,
            "mode": img.mode,
        })
    except Exception as e:
        r.emit("screenshot_error", detail={"error": repr(e)})
        shot_path = None

    # ---- 枚举顶部区域控件（y < top+90px 的可见后代）----
    top_y = rc[1] + 90
    all_kids = R.enum_children(hwnd)
    top_kids = [k for k in all_kids
                if k["visible"] and k["rect"][3] > k["rect"][1] and k["rect"][1] < top_y]
    top_kids.sort(key=lambda k: (k["rect"][1], k["rect"][0]))

    r.emit("top_controls", detail={
        "window_rect": list(rc),
        "total_descendants": len(all_kids),
        "top_region_count": len(top_kids),
        "controls": [
            {
                "class": k["class"],
                "title": (k["title"] or "")[:60],
                "rect": k["rect"],
                "rel_y": round(k["rect"][1] - rc[1], 1),
                "rel_x": round(k["rect"][0] - rc[0], 1),
                "w": k["rect"][2] - k["rect"][0],
                "h": k["rect"][3] - k["rect"][1],
            }
            for k in top_kids[:40]
        ],
    })

    # ---- 特别标注含 Tab / Page / Sheet 关键字的 ----
    tab_like = [k for k in top_kids
                if any(kw in k["class"].lower() for kw in ("tab", "page", "sheet"))]
    tab_like.sort(key=lambda k: (k["rect"][1], k["rect"][0]))
    r.emit("tab_candidates", detail={
        "count": len(tab_like),
        "items": [
            {
                "class": t["class"],
                "title": (t["title"] or "")[:60],
                "rect": t["rect"],
                "center": R.center(t["rect"]),
                "rel_center": (
                    round(R.center(t["rect"])[0] - rc[0], 1),
                    round(R.center(t["rect"])[1] - rc[1], 1),
                ),
            }
            for t in tab_like[:20]
        ],
    })

    return {"done": True, "shot_path": shot_path}


if __name__ == "__main__":
    R.Runner("snap_login", expected_windows={LOGIN_CLS}).run(main)
