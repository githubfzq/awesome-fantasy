import json, sys
from pywinauto import Application

out = {}
try:
    app = Application(backend="win32").connect(title_re="自然人电子税务局", timeout=15)
    dlg = app.top_window()
    dr = dlg.rectangle()
    out["dialog"] = {
        "title": dlg.window_text(),
        "class": dlg.class_name(),
        "pid": dlg.process_id(),
        "l": dr.left, "t": dr.top, "r": dr.right, "b": dr.bottom,
        "w": dr.right - dr.left, "h": dr.bottom - dr.top,
    }

    # 1) search descendants for tab buttons by their Chinese caption
    named_tabs = []
    for c in dlg.descendants():
        try:
            n = c.window_text() or ""
            if n in ("申报密码登录", "实名登录", "离线登录"):
                r = c.rectangle()
                named_tabs.append({
                    "name": n, "cls": c.class_name(),
                    "l": r.left, "t": r.top, "r": r.right, "b": r.bottom,
                    "cx": (r.left + r.right) // 2, "cy": (r.top + r.bottom) // 2,
                    "w": r.right - r.left, "h": r.bottom - r.top,
                })
        except Exception:
            pass
    out["named_tabs"] = named_tabs

    # 2) direct children (top-level layout) with rects
    children = []
    for c in dlg.children():
        try:
            r = c.rectangle()
            children.append({
                "cls": c.class_name(), "name": c.window_text() or "",
                "l": r.left, "t": r.top, "r": r.right, "b": r.bottom,
                "w": r.right - r.left, "h": r.bottom - r.top,
            })
        except Exception as e:
            children.append({"err": str(e)})
    out["children"] = children

    # 3) spDeclare panel rect (申报密码登录 page)
    for c in dlg.descendants():
        try:
            if (c.window_text() or "") == "spDeclare":
                r = c.rectangle()
                out["spDeclare"] = {"l": r.left, "t": r.top, "r": r.right, "b": r.bottom}
                break
        except Exception:
            pass

    out["status"] = "ok"
except Exception as e:
    out["status"] = "error"
    out["err"] = repr(e)

open(r"C:\rpa\tab_probe.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))