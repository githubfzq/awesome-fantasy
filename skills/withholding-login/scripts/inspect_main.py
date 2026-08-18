# -*- coding: utf-8 -*-
# inspect_main.py — 登录后主窗口控件树巡检（读系统状态，不点击）
import os
import re
import ctypes
from ctypes import wintypes
import rpa_core as R

user32 = ctypes.windll.user32
GW_CHILD = 5
GW_HWNDNEXT = 2

OUT_TXT = r"\\Mac\Home\Documents\rpa\inspect_main.txt"
OUT_PNG = r"\\Mac\Home\Documents\rpa\main_window.png"
SHARE = r"\\Mac\Home\Documents\rpa"

nodes = []  # (depth, class, title, rect, visible, enabled)


def children_of(hwnd):
    res = []
    h = user32.GetWindow(hwnd, GW_CHILD)
    while h:
        res.append(h)
        h = user32.GetWindow(h, GW_HWNDNEXT)
    return res


def walk(hwnd, depth):
    if depth > 16 or len(nodes) > 2500:
        return
    info = R.win_info(hwnd)
    cls, title, rect = info["class"], info["title"], info["rect"]
    nodes.append((depth, cls, title, rect, info["visible"], info["enabled"]))
    for c in children_of(hwnd):
        walk(c, depth + 1)


def main():
    lines = []
    wins = R.enum_top_windows()
    # 找主窗
    main = None
    for w in wins:
        t = w["title"] or ""
        if "扣缴端" in t or "电子税务" in t:
            main = w
            break
    if main is None:
        cands = [w for w in wins if w["visible"]
                 and (w["rect"][2] - w["rect"][0]) > 800]
        cands.sort(key=lambda w: -((w["rect"][2] - w["rect"][0]) *
                                   (w["rect"][3] - w["rect"][1])))
        main = cands[0] if cands else (wins[0] if wins else None)

    lines.append("=== 顶层窗口 (共 %d) ===" % len(wins))
    for w in wins:
        if w["visible"] and (w["title"] or (w["rect"][2]-w["rect"][0]) > 200):
            lines.append("  WIN cls=%s title=%r rect=%s" %
                         (w["class"], w["title"], w["rect"]))

    if main is None:
        lines.append("!!! 未找到主窗口")
        open(OUT_TXT, "w", encoding="utf-8").write("\n".join(lines))
        return

    lines.append("")
    lines.append("=== 主窗口: cls=%s title=%r rect=%s ===" %
                 (main["class"], main["title"], main["rect"]))
    walk(main["hwnd"], 0)

    # 打印树（只打印有标题或可见的节点，最多 2500）
    lines.append("")
    lines.append("=== 控件树 (depth cls title rect vis en) ===")
    for depth, cls, title, rect, vis, en in nodes:
        if title or vis:
            lines.append("%s[%s] %r rect=%s vis=%s en=%s" %
                         ("  " * depth, cls, title, rect, vis, en))

    # ---- 定向提取 ----
    lines.append("")
    lines.append("=== 定向提取 ===")
    # 1) 税款所属月份候选
    month_re = re.compile(r"\d{4}年\d{1,2}月|\d{4}-\d{1,2}|税款所属")
    month_hits = [(cls, title, rect) for (_, cls, title, rect, _, _) in nodes
                  if title and month_re.search(title)]
    lines.append("-- 税款所属月份候选 --")
    for cls, title, rect in month_hits:
        lines.append("   %r (cls=%s rect=%s)" % (title, cls, rect))

    # 1b) DateTimePicker 直读（WM_GETTEXT，绕过 GetWindowTextW 缓存 caption 为空）
    lines.append("-- 税款所属月份 直读 (WM_GETTEXT on TXPFarmerDTPicker) --")
    dtp = []

    def find_cls(hwnd, target):
        if R.get_class(hwnd) == target:
            dtp.append(hwnd)
        for c in children_of(hwnd):
            find_cls(c, target)

    find_cls(main["hwnd"], "TXPFarmerDTPicker")
    for h in dtp:
        try:
            val = R.wm_get_text(h)
            lines.append("   hwnd=%d -> %r" % (h, val))
        except Exception as e:
            lines.append("   hwnd=%d 读失败: %r" % (h, e))

    # 2) 常用功能及其子项
    lines.append("-- 常用功能区 --")
    found_cf = False
    for i, (depth, cls, title, rect, vis, en) in enumerate(nodes):
        if title and "常用功能" in title:
            found_cf = True
            lines.append("   命中标题: %r (cls=%s rect=%s depth=%d)" %
                         (title, cls, rect, depth))
            # 列出其后续同级/子级（depth+1）作为模块候选
            j = i + 1
            while j < len(nodes) and nodes[j][0] > depth:
                d2, c2, t2, r2, v2, e2 = nodes[j]
                if t2:
                    lines.append("     子项: %r (cls=%s rect=%s)" % (t2, c2, r2))
                j += 1
    if not found_cf:
        lines.append("   未直接命中'常用功能'标题，列出所有含'功能'的节点：")
        for (depth, cls, title, rect, vis, en) in nodes:
            if title and "功能" in title:
                lines.append("   %r (cls=%s rect=%s)" % (title, cls, rect))

    txt = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8", errors="replace") as f:
        f.write(txt)

    # 截图（视觉交叉验证）
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(OUT_PNG)
    except Exception as e:
        lines.append("截图失败: %r" % e)
        with open(OUT_TXT, "w", encoding="utf-8", errors="replace") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    main()
