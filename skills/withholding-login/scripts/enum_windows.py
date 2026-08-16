# enum_windows.py — 枚举全部顶层窗口，诊断隐形模态弹窗 / 校验登录态
# 依赖 rpa_core.py（需一并推送）。结果写 C:\rpa\last_result.json，并进 JSONL 日志。
import json
import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
MAIN_CLS = "Tfrm_MainFrame"
POP_CLS = "Tfrm_IntelligentSearchPop"
MODAL_CLS = "Tfrm_MsgDlgRich"


def main(r):
    wins = R.enum_top_windows()
    login = next((w for w in wins if w["class"] == LOGIN_CLS), None)
    main_w = next((w for w in wins if w["class"] == MAIN_CLS), None)
    modal = [w for w in wins if w["class"] == MODAL_CLS and w["visible"]]
    pop = next((w for w in wins if w["class"] == POP_CLS and w["visible"]), None)

    summary = {
        "login_visible": (login["visible"] if login else None),
        "login_enabled": (login["enabled"] if login else None),
        "main_visible": (main_w["visible"] if main_w else None),
        "picker_open": bool(pop),
        "blocking_modals": [{"hwnd": w["hwnd"], "title": w["title"],
                             "rect": w["rect"]} for w in modal],
        "login_ok": bool(login and login["enabled"] and not modal),
        "logged_in": bool(main_w and main_w["visible"]),
    }
    r.emit("diagnose", detail=summary)
    # 完整窗口树另存，避免 last_result.json 过大
    import os
    full = os.path.join(R.LOG_DIR, r.run_id + "-windows.json")
    try:
        with open(full, "w", encoding="utf-8") as f:
            json.dump(wins, f, ensure_ascii=False, indent=2)
    except Exception:
        full = None
    return {"summary": summary, "windows_dump": full}


if __name__ == "__main__":
    R.Runner("enum_windows").run(main)
