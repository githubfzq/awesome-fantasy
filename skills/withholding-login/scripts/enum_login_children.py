import rpa_core as R


def main(r):
    lw = R.find_window("Tfrm_LoginViewer", visible_only=True)
    detail = {"login_rect": lw["rect"] if lw else None}
    if lw:
        kids = R.enum_children(lw["hwnd"])
        KEYS = ["Tab", "Page", "Intelligent", "Edit", "Button", "Tfrm_Login",
                "SpeedButton", "Label", "Panel", "Combo", "GroupBox", "TEdit",
                "TButton", "TITSTabControl", "TITSPageControl"]
        items = []
        for k in kids:
            c = k.get("class", "")
            if any(x in c for x in KEYS):
                items.append({kk: k.get(kk) for kk in
                              ("class", "rect", "title", "text", "enabled",
                               "visible", "hwnd")})
        detail["count"] = len(items)
        detail["items"] = items
    r.emit("login_children", detail=detail)


if __name__ == "__main__":
    R.Runner("enum_login_children").run(main)
