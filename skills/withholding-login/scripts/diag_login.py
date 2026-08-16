# diag_login.py — dump login window rect + descendant controls (tabs/edits/buttons/selector)
import rpa_core as R

def rec(h, depth, out):
    for c in R.enum_children(h):
        out.append({"depth": depth, "class": c["class"], "title": c.get("title"),
                    "rect": c["rect"], "visible": c["visible"]})
        rec(c["hwnd"], depth + 1, out)

def main(r):
    lw = R.find_window("Tfrm_LoginViewer", visible_only=True)
    if not lw:
        r.emit("no_login", detail={})
        return {"found": False}
    out = []
    rec(lw["hwnd"], 0, out)
    keys = ("Tab", "Edit", "SpeedButton", "IntelligentSearch", "TITSTab", "Panel", "TITSPage")
    interesting = [x for x in out if any(k in x["class"] for k in keys)]
    r.emit("login_tree", detail={"win_rect": lw["rect"],
                                  "interesting": interesting,
                                  "all_count": len(out)})
    return {"win_rect": lw["rect"], "interesting": interesting}

if __name__ == "__main__":
    R.Runner("diag_login").run(main)
