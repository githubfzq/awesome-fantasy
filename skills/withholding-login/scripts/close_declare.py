# close_declare.py — 关闭扣缴端主窗口（真实点击右上角系统关闭按钮）
#
# 用法（Mac 侧推荐）:
#   bash push_run.sh --lib rpa_core.py close_declare.py
#
# 退出流程的弹窗家族（均为 Delphi owner-drawn，按钮多为无文本圆角按钮）:
#   - Tfrm_MsgDlgRich  「确认信息」: 确定(左)/取消(右)，按钮 TModalSpeedButtonRound
#   - Tfrm_MsgDlg     「提示信息」(如数据库备份提示): 单按钮「确认」，按钮 TModalSpeedButton
#   本脚本循环处理所有这类确认弹窗（点确认/靠左按钮），直到主窗消失、无残留弹窗。
#
# 已知行为：扣缴端点系统关闭后窗体是「隐藏（托盘化）」而非销毁，进程驻留；
# 本脚本最后对 TApplication 窗发 WM_CLOSE 优雅退出，仍不退则 taskkill 兜底
# （用户已明确要求关闭应用）。返回 closed = 窗口不可见且无扣缴端进程。
#
# 每步带后置验证与结构化日志，符合 RPA 工程契约，绝不盲点。
import ctypes
import time
import rpa_core as R
from ctypes import wintypes

MAIN_CLS = "Tfrm_MainFrame"
LOGIN_CLS = "Tfrm_LoginViewer"  # 登录窗（未进主界面时也要能完整关闭）
# 两类退出相关确认弹窗
CONFIRM_CLS = ("Tfrm_MsgDlgRich", "Tfrm_MsgDlg")
WM_GETTITLEBARINFOEX = 0x033F
WM_CLOSE = 0x0010
CLOSE_BTN = 5
BTN_CLS_ALL = ("TITSSpeedButton", "TModalSpeedButtonRound", "TModalSpeedButton",
               "TButton", "TBitBtn")
# 扣缴端相关进程名片段（窗口关闭后进程可能仍驻留托盘）
APP_PROC_PATTERNS = ("EPPortal", "EPEvenue", "ProcDataDeal", "EPDataMgrTools")


class TITLEBARINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcTitleBar", wintypes.RECT),
        ("rgstate", wintypes.DWORD * 6),
        ("rgrect", wintypes.RECT * 6),
    ]


def close_rect(hwnd):
    """尽量用 WM_GETTITLEBARINFOEX 取系统关闭按钮精确屏幕坐标；失败回退估算。"""
    ti = TITLEBARINFOEX()
    ti.cbSize = ctypes.sizeof(TITLEBARINFOEX)
    try:
        ok = R.user32.SendMessageW(hwnd, WM_GETTITLEBARINFOEX, 0, ctypes.byref(ti))
    except Exception:
        ok = 0
    if ok:
        r = ti.rgrect[CLOSE_BTN]
        if r.right > r.left and r.bottom > r.top:
            return [r.left, r.top, r.right, r.bottom]
    rect = R.rect_of(hwnd)
    return [rect[2] - 20, rect[1] + 18, rect[2] - 4, rect[1] + 34]


def click_close(hwnd):
    cr = close_rect(hwnd)
    x, y = (cr[0] + cr[2]) // 2, (cr[1] + cr[3]) // 2
    R.click_at(x, y)
    return {"close_btn_rect": cr, "click_xy": [x, y],
            "method": "real_mouse" if cr[2] - cr[0] > 8 else "fallback_estimate"}


def find_confirm_modal():
    """枚举可见顶层窗口，返回第一个退出相关确认弹窗（Tfrm_MsgDlgRich/Tfrm_MsgDlg）。"""
    for w in R.enum_top_windows():
        if w["class"] in CONFIRM_CLS and w["visible"]:
            return w
    return None


def click_modal_default(modal):
    """点击确认按钮。优先标题文本匹配（确定/是/确认…）；否则按 x 升序取靠左按钮。
    扣缴端『确认信息』确定在左、取消在右；数据库备份『提示信息』通常单按钮（直接点）。"""
    kids = R.enum_children(modal["hwnd"])
    btns = [k for k in kids
            if k["class"] in BTN_CLS_ALL and k["visible"] and k["enabled"]]
    prefer = ("确定", "是", "确认", "退出", "OK", "Yes")
    for b in btns:
        if b["title"] in prefer:
            R.click_at(*R.center(b["rect"]))
            return {"clicked": b["title"], "method": "title_match", "rect": b["rect"]}
    if btns:
        btns.sort(key=lambda b: b["rect"][0])
        target = btns[0]
        R.click_at(*R.center(target["rect"]))
        return {"clicked": "leftmost(%s)" % target["class"],
                "method": "leftmost", "rect": target["rect"],
                "candidates": [[b["class"], b["rect"]] for b in btns]}
    return {"clicked": None, "candidates_total": len(kids)}


def app_processes():
    """返回仍在运行的扣缴端相关进程映像名列表（tasklist CSV）。"""
    import subprocess
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return []
    procs = []
    for line in out.splitlines():
        name = line.split('","', 1)[0].strip('"')
        if name and any(p in name for p in APP_PROC_PATTERNS) and name not in procs:
            procs.append(name)
    return procs


def ensure_processes_exit(r):
    """窗口已关但进程仍驻留（托盘化）时的收尾：优雅 WM_CLOSE → 兜底 taskkill。
    返回 {"procs_before": [...], "method": "...", "procs_after": [...]}"""
    before = app_processes()
    if not before:
        return {"procs_before": [], "method": "none", "procs_after": []}
    # 1) 优雅关闭：对扣缴端 TApplication 顶层窗发 WM_CLOSE（可能弹确认框，交给下一轮模态处理）
    sent = 0
    for w in R.enum_top_windows():
        if w["class"] == "TApplication" and w["title"] in ("自然人电子税务局（扣缴端）", "数据处理"):
            R.user32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
            sent += 1
    time.sleep(2.0)
    # 2) 处理 WM_CLOSE 可能带出的确认弹窗
    while find_confirm_modal() is not None:
        modal = find_confirm_modal()
        click_modal_default(modal)
        time.sleep(0.8)
    # 3) 仍未退 → 兜底强杀（用户已明确要求关闭应用）
    after = app_processes()
    method = "wm_close"
    if after:
        import subprocess
        for name in after:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/IM", name],
                               capture_output=True, timeout=15)
            except Exception:
                pass
        time.sleep(1.5)
        method = "taskkill"
    return {"procs_before": before, "method": method, "procs_after": app_processes()}


def main(r):
    # 1) 若登录窗可见且无确认弹窗挡着，先点其系统关闭按钮（覆盖『仍在登录窗』状态）
    #    注：扣缴端点关闭后窗体是「隐藏（托盘化）」而非销毁，verify 以「不再可见」为准。
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if lw and find_confirm_modal() is None:
        r.step("click_close_login",
               action=lambda: click_close(lw["hwnd"]),
               verify=lambda: (R.find_window(LOGIN_CLS, visible_only=True) is None)
                              or (find_confirm_modal() is not None),
               verify_desc="登录窗已隐藏或出现退出确认弹窗",
               timeout=8.0)
    # 2) 若主窗可见且无确认弹窗挡着，点系统关闭按钮
    mw = R.find_window(MAIN_CLS, visible_only=True)
    if mw and find_confirm_modal() is None:
        r.step("click_close_main",
               action=lambda: click_close(mw["hwnd"]),
               verify=lambda: (R.find_window(MAIN_CLS, visible_only=True) is None)
                              or (find_confirm_modal() is not None),
               verify_desc="主窗已隐藏或出现退出确认弹窗",
               timeout=8.0)

    # 2.5) 沉降等待：主窗关闭后，EPDataMgrTools.exe 会「延迟」弹出「提示信息」(Tfrm_MsgDlg)，
    # 先等其浮现再进弹窗循环，避免单轮漏收需补跑一轮。
    time.sleep(2.5)

    # 2) 循环处理所有退出相关确认弹窗，直到无残留
    handled = 0
    while find_confirm_modal() is not None:
        modal = find_confirm_modal()
        cls = modal["class"]
        r.step("confirm_modal_%d" % handled,
               action=lambda m=modal: click_modal_default(m),
               verify=lambda c=cls: R.find_window(class_name=c, visible_only=True) is None,
               verify_desc="确认弹窗(%s)已关闭" % cls,
               timeout=8.0,
               guard=False)
        handled += 1
        if handled > 6:
            r.fail("确认弹窗链过长，疑似异常", detail={"handled": handled})
            break
        # 级间沉降：给下一级延迟确认框（如 EPDataMgrTools 后置弹窗）浮现时间
        time.sleep(0.8)

    # 2.6) 最终再探一次：捕获循环退出后才浮现的延迟弹窗（EPDataMgrTools 偶发后置）。
    # 单轮兜底，避免「主窗已关、残留提示信息框未收」需另起一轮。
    time.sleep(1.5)
    late = find_confirm_modal()
    if late is not None:
        cls = late["class"]
        r.step("confirm_modal_late",
               action=lambda m=late: click_modal_default(m),
               verify=lambda c=cls: R.find_window(class_name=c, visible_only=True) is None,
               verify_desc="延迟确认弹窗(%s)已关闭" % cls,
               timeout=8.0,
               guard=False)
        handled += 1

    # 3) 进程收尾：窗口已隐藏但进程驻留托盘 → 优雅 WM_CLOSE → 兜底 taskkill
    proc = ensure_processes_exit(r)

    return {"closed": (R.find_window(MAIN_CLS, visible_only=True) is None
                       and R.find_window(LOGIN_CLS, visible_only=True) is None
                       and not proc["procs_after"]),
            "final_modal": find_confirm_modal() is not None,
            "modals_handled": handled,
            "process": proc}


if __name__ == "__main__":
    R.Runner("close_declare", expected_windows={MAIN_CLS, LOGIN_CLS, *CONFIRM_CLS}).run(main)
