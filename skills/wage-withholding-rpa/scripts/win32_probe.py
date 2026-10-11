from pywinauto import Application
import json, sys
out = {}
try:
    app = Application(backend="win32").connect(title_re="自然人电子税务局", timeout=10)
    dlg = app.top_window()
    out["title"] = dlg.window_text()
    out["pid"] = dlg.process_id()
    out["class"] = dlg.class_name()
    out["n_children"] = len(list(dlg.children()))
    ctrls = []
    def walk(w, d):
        if d > 4: return
        try:
            r = w.rectangle()
            ctrls.append({"d": d, "name": w.window_text(), "class": w.class_name(),
                          "rect": [r.left, r.top, r.right, r.bottom]})
        except Exception:
            pass
        for c in w.children():
            walk(c, d + 1)
    walk(dlg, 0)
    out["controls"] = ctrls
    out["status"] = "ok"
except Exception as e:
    out["status"] = "error"
    out["err"] = repr(e)
    out["traceback"] = sys.exc_info()[0].__name__ if sys.exc_info()[0] else None
open(r"C:\rpa\w32.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))