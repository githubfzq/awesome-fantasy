# login_shot.py — screenshot login window + dump all TITSTabControl rects (for visual diagnosis)
import rpa_core as R
from PIL import ImageGrab
import os

def rec(h, out):
    for c in R.enum_children(h):
        out.append(c)
        rec(c["hwnd"], out)

def main(r):
    lw = R.find_window("Tfrm_LoginViewer", visible_only=True)
    if not lw:
        r.emit("no_login"); return {"found": False}
    rc = tuple(lw["rect"])
    os.makedirs(r"C:/rpa/screenshots", exist_ok=True)
    path = r"C:/rpa/screenshots/login_diag.png"
    try:
        ImageGrab.grab(bbox=rc).save(path)
    except Exception as e:
        r.emit("shot_err", detail={"error": repr(e)})
        path = None
    allc = []
    rec(lw["hwnd"], allc)
    tabs = [{"rect": c["rect"], "title": c.get("title"), "visible": c["visible"]}
            for c in allc if c["class"] == "TITSTabControl"]
    r.emit("diag", detail={"win": rc, "tab_count": len(tabs), "tabs": tabs[:12]})
    return {"path": path, "win": rc, "tab_count": len(tabs)}

if __name__ == "__main__":
    R.Runner("login_shot").run(main)
