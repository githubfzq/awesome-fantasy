from pywinauto import Application
import json, sys

out = {}
try:
    app = Application(backend="win32").connect(title_re="自然人电子税务局", timeout=15)
    dlg = app.top_window()
    sp = None
    for c in dlg.descendants():
        if (c.window_text() or "") == "spDeclare":
            sp = c
            break
    if sp is None:
        out["status"] = "error"
        out["err"] = "spDeclare not found"
    else:
        kids = []
        for c in sp.descendants():
            try:
                r = c.rectangle()
                kids.append({
                    "cls": c.class_name(),
                    "name": c.window_text() or "",
                    "l": r.left, "t": r.top, "r": r.right, "b": r.bottom,
                    "w": r.right - r.left, "h": r.bottom - r.top,
                    "cx": (r.left + r.right) // 2, "cy": (r.top + r.bottom) // 2,
                })
            except Exception:
                pass
        out["status"] = "ok"
        out["spDeclare_descendants"] = kids
except Exception as e:
    out["status"] = "error"
    out["err"] = repr(e)

open(r"C:\rpa\spd.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))