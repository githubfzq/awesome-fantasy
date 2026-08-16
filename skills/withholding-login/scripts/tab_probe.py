# tab_probe.py — 读取登录窗 PageControl 的真实 tab 文本与顺序（程序化定位，不依赖截图）
import ctypes
from ctypes import wintypes

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"

TCM_FIRST = 0x1300
TCM_GETITEMCOUNT = TCM_FIRST + 4
TCM_GETITEMW = TCM_FIRST + 11
TCM_SETCURSEL = TCM_FIRST + 12
TCIF_TEXT = 0x0001


class TCITEM(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("dwState", wintypes.UINT),
        ("dwStateMask", wintypes.UINT),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
    ]


def read_tab_texts(u32, page_hwnd):
    count = u32.SendMessageW(page_hwnd, TCM_GETITEMCOUNT, 0, 0)
    texts = []
    for i in range(max(count, 0)):
        buf = ctypes.create_unicode_buffer(256)
        item = TCITEM()
        item.mask = TCIF_TEXT
        item.pszText = ctypes.cast(ctypes.addressof(buf), ctypes.c_void_p)
        item.cchTextMax = 255
        rc = u32.SendMessageW(page_hwnd, TCM_GETITEMW, i, ctypes.byref(item))
        texts.append((i, buf.value if rc else "", rc))
    return count, texts


def main(r):
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if not lw:
        r.fail("preflight", "登录窗未找到")

    kids = R.enum_children(lw["hwnd"])
    page = [k for k in kids if "PageControl" in k["class"]]
    sheet = [k for k in kids if "TabSheet" in k["class"]]

    result = {"window_rect": lw["rect"], "page_controls": [], "tab_sheets": []}
    for p in page:
        cnt, texts = read_tab_texts(R.user32, p["hwnd"])
        result["page_controls"].append({
            "class": p["class"], "rect": p["rect"],
            "tab_count": cnt, "tabs": [
                {"index": i, "text": t, "raw_ok": ok} for i, t, ok in texts
            ],
        })
    for s in sheet:
        result["tab_sheets"].append({
            "class": s["class"], "title": s["title"], "rect": s["rect"],
        })

    r.emit("probe", detail=result)
    return result


if __name__ == "__main__":
    R.Runner("tab_probe", expected_windows={LOGIN_CLS}).run(main)
