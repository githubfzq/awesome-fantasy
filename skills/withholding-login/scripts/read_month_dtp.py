# -*- coding: utf-8 -*-
# read_month_dtp.py — 直接从 DateTimePicker 控件读税款所属月份（不靠截图）
import ctypes
from ctypes import wintypes
import rpa_core as R

user32 = ctypes.windll.user32

DTM_GETSYSTEMTIME = 0x1001  # DTM_FIRST+1


class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ("wYear", ctypes.c_ushort),
        ("wMonth", ctypes.c_ushort),
        ("wDayOfWeek", ctypes.c_ushort),
        ("wDay", ctypes.c_ushort),
        ("wHour", ctypes.c_ushort),
        ("wMinute", ctypes.c_ushort),
        ("wSecond", ctypes.c_ushort),
        ("wMilliseconds", ctypes.c_ushort),
    ]


def children_of(hwnd):
    res = []
    h = user32.GetWindow(hwnd, 5)  # GW_CHILD
    while h:
        res.append(h)
        h = user32.GetWindow(h, 2)  # GW_HWNDNEXT
    return res


def find_by_class(hwnd, target, out):
    if R.get_class(hwnd) == target:
        out.append(hwnd)
    for c in children_of(hwnd):
        find_by_class(c, target, out)


def main():
    lines = []
    main = None
    for w in R.enum_top_windows():
        if w["class"] == "Tfrm_MainFrame":
            main = w
            break
    if main is None:
        lines.append("!!! 未找到 Tfrm_MainFrame")
        open(r"\\Mac\Home\Documents\rpa\read_month.txt", "w", encoding="utf-8").write("\n".join(lines))
        return

    targets = []
    find_by_class(main["hwnd"], "TXPFarmerDTPicker", targets)
    lines.append("TXPFarmerDTPicker 数量 = %d" % len(targets))

    for i, hwnd in enumerate(targets):
        lines.append("--- DTPicker #%d hwnd=%d ---" % (i, hwnd))
        # 1) DTM_GETSYSTEMTIME — 直接读日期值
        st = SYSTEMTIME()
        ret = user32.SendMessageW(hwnd, DTM_GETSYSTEMTIME, 0, ctypes.byref(st))
        # 返回值: 0=GDT_VALID, 1=GDT_NONE, -1=GDT_ERROR
        lines.append("DTM_GETSYSTEMTIME ret=%s (0=VALID) -> %04d年%02d月%02d日" %
                     (ret, st.wYear, st.wMonth, st.wDay))
        # 2) WM_GETTEXT 再试一次（标准 0x000D）
        txt = R.wm_get_text(hwnd)
        lines.append("WM_GETTEXT=%r" % txt)

    txt = "\n".join(lines)
    open(r"\\Mac\Home\Documents\rpa\read_month.txt", "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        open(r"\\Mac\Home\Documents\rpa\read_month.txt", "w", encoding="utf-8").write(
            "CRASH: %r\n%s" % (e, traceback.format_exc()))
