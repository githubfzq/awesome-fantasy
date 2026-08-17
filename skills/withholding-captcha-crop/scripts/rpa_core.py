# rpa_core.py — VM 内 RPA 执行内核（所有操作脚本必须经它执行）
#
# 设计契约（不可绕过）：
#   每个步骤 = 前置守卫(guard) → 前置条件(pre) → 动作(action) → 后置验证(verify，条件轮询+超时) → 结构化日志
#   验证不通过 = 立即中止(fail-fast) + 冻结现场(窗口树 JSON + 全屏 PNG)，绝不继续点击下一步。
#
# 为什么必须这样：pythonw.exe 无控制台，print 全部丢失；固定 sleep 无法判定成功；
#   Delphi owner-drawn 隐形模态弹窗会禁用主窗并吃掉所有点击 → 盲点会走进不可控状态。
#
# 日志：C:\rpa\logs\<run_id>.jsonl（逐事件追加）+ C:\rpa\logs\latest.jsonl（本次运行副本）
# 结果：C:\rpa\last_result.json（供 Mac 编排端读回）
import base64
import ctypes
import json
import os
import sys
import time
import traceback
import uuid
from ctypes import wintypes

user32 = ctypes.windll.user32

LOG_DIR = r"C:\rpa\logs"
RESULT_PATH = r"C:\rpa\last_result.json"

WM_SETTEXT = 0x0C
WM_GETTEXTLENGTH = 0x0E
LB_GETCOUNT = 0x018B
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A
LB_SETCURSEL = 0x0186
LB_GETITEMRECT = 0x0198

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# 已知的良性弹窗类名（不视为"未预期窗口"）
KNOWN_MODAL_CLASS = "Tfrm_MsgDlgRich"


class StepFailed(Exception):
    """步骤验证失败 → 中止整个流程。"""

    def __init__(self, step, reason, detail=None):
        super().__init__("%s: %s" % (step, reason))
        self.step = step
        self.reason = reason
        self.detail = detail or {}


# ---------------------------------------------------------------- win32 原语
def get_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def rect_of(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right, r.bottom]


def center(rect):
    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)


def is_visible(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


def is_enabled(hwnd):
    return bool(user32.IsWindowEnabled(hwnd))


def win_info(hwnd):
    return {
        "hwnd": int(hwnd),
        "class": get_class(hwnd),
        "title": get_title(hwnd),
        "visible": is_visible(hwnd),
        "enabled": is_enabled(hwnd),
        "rect": rect_of(hwnd),
    }


def enum_top_windows():
    out = []

    @EnumWindowsProc
    def cb(hwnd, lparam):
        out.append(win_info(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return out


def find_window(class_name, visible_only=True):
    """按类名找顶层窗，返回 win_info 或 None。"""
    for w in enum_top_windows():
        if w["class"] == class_name and (w["visible"] or not visible_only):
            return w
    return None


def enum_children(hwnd):
    """枚举全部后代窗口（EnumChildWindows 本身即递归）。"""
    out = []

    @EnumWindowsProc
    def cb(child, lparam):
        out.append(win_info(child))
        return True

    user32.EnumChildWindows(hwnd, cb, 0)
    return out


def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    user32.mouse_event(0x0002, int(x), int(y), 0, 0)  # LEFTDOWN
    user32.mouse_event(0x0004, int(x), int(y), 0, 0)  # LEFTUP


def wm_set_text(hwnd, text):
    """绕过中文输入法直接写入文本（type_keys 会被 IME 组词，长度错乱）。"""
    return user32.SendMessageW(hwnd, WM_SETTEXT, 0, ctypes.c_wchar_p(text))


def wm_get_len(hwnd):
    return int(user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0))


def wm_get_text(hwnd):
    n = wm_get_len(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.SendMessageW(hwnd, 0x000D, n + 1, buf)  # WM_GETTEXT
    return buf.value


# -------------------------------------------------------------- ListBox 原语
def listbox_items(hwnd):
    n = int(user32.SendMessageW(hwnd, LB_GETCOUNT, 0, 0))
    items = []
    for i in range(max(n, 0)):
        ln = int(user32.SendMessageW(hwnd, LB_GETTEXTLEN, i, 0))
        buf = ctypes.create_unicode_buffer(max(ln, 0) + 1)
        user32.SendMessageW(hwnd, LB_GETTEXT, i, buf)
        items.append(buf.value)
    return items


def listbox_click_item(hwnd, index):
    """真实鼠标点击列表项 —— 必须真点才会触发 Delphi 的 OnClick（联动带出识别号）。
    仅 LB_SETCURSEL 不触发业务逻辑。"""
    user32.SendMessageW(hwnd, LB_SETCURSEL, index, 0)
    r = wintypes.RECT()
    user32.SendMessageW(hwnd, LB_GETITEMRECT, index, ctypes.byref(r))
    pt = wintypes.POINT()
    pt.x = (r.left + r.right) // 2
    pt.y = (r.top + r.bottom) // 2
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    click_at(pt.x, pt.y)
    return {"index": index, "screen_point": [pt.x, pt.y]}


# ------------------------------------------------------------------ 等待原语
def wait_until(fn, timeout=10.0, interval=0.3):
    """轮询 fn() 直到返回真值。返回 (value, elapsed_s)；超时返回 (None, elapsed_s)。
    禁止用 time.sleep 代替本函数作为"验证"。"""
    t0 = time.time()
    while True:
        try:
            v = fn()
        except Exception:
            v = None
        if v:
            return v, round(time.time() - t0, 2)
        if time.time() - t0 >= timeout:
            return None, round(time.time() - t0, 2)
        time.sleep(interval)


def mask(secret):
    """敏感值脱敏：日志只记长度，绝不落明文。"""
    return "***len=%d" % len(secret or "")


# -------------------------------------------------------------------- Runner
class Runner:
    def __init__(self, name, expected_windows=None, meta=None):
        self.name = name
        self.run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.seq = 0
        self.steps = []
        self.t0 = time.time()
        # 预期存在的顶层窗类名，用于检测"未预期弹窗"
        self.expected_windows = set(expected_windows or [])
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
        except Exception:
            pass
        self.log_path = os.path.join(LOG_DIR, self.run_id + ".jsonl")
        self.latest_path = os.path.join(LOG_DIR, "latest.jsonl")
        # latest 每次运行重置，便于 Mac 侧固定读取本次日志
        try:
            open(self.latest_path, "w", encoding="utf-8").close()
        except Exception:
            pass
        self.emit("run_start", detail={"name": name, "run_id": self.run_id,
                                       "meta": meta or {}})

    # ---- 日志 ----
    def emit(self, event, step=None, **kw):
        self.seq += 1
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_id": self.run_id,
            "seq": self.seq,
            "event": event,
        }
        if step:
            rec["step"] = step
        rec.update(kw)
        line = json.dumps(rec, ensure_ascii=False)
        for p in (self.log_path, self.latest_path):
            try:
                with open(p, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
        return rec

    # ---- 现场冻结 ----
    def snapshot(self, tag):
        """失败/异常时冻结现场：窗口树 JSON + 全屏 PNG，供事后追溯。"""
        art = {}
        wins_path = os.path.join(LOG_DIR, "%s-%s-windows.json" % (self.run_id, tag))
        try:
            with open(wins_path, "w", encoding="utf-8") as f:
                json.dump(enum_top_windows(), f, ensure_ascii=False, indent=2)
            art["windows"] = wins_path
        except Exception as e:
            art["windows_error"] = repr(e)
        png_path = os.path.join(LOG_DIR, "%s-%s-screen.png" % (self.run_id, tag))
        try:
            from PIL import ImageGrab
            ImageGrab.grab().save(png_path)
            art["screen"] = png_path
        except Exception as e:
            art["screen_error"] = repr(e)
        self.emit("snapshot", tag=tag, artifacts=art)
        return art

    # ---- 守卫 ----
    def blocking_modal(self):
        """返回挡窗的可见模态弹窗 info，或 None。"""
        for w in enum_top_windows():
            if w["class"] == KNOWN_MODAL_CLASS and w["visible"]:
                return w
        return None

    def unexpected_windows(self):
        """检测预期之外的可见弹窗（异常弹窗）。仅在声明了 expected_windows 时生效。"""
        if not self.expected_windows:
            return []
        out = []
        for w in enum_top_windows():
            if not w["visible"] or not w["title"]:
                continue
            if w["class"] in self.expected_windows:
                continue
            if w["class"] == KNOWN_MODAL_CLASS:
                out.append(w)
        return out

    def guard(self, step):
        """动作前统一守卫：存在阻塞模态弹窗时禁止任何点击。"""
        m = self.blocking_modal()
        if m:
            self.fail(step, "存在阻塞模态弹窗，已中止（禁止在被遮挡状态下盲点）",
                      {"modal": m,
                       "hint": "先运行 close_modal.py 关闭，确认原因后再重试"})

    # ---- 失败 ----
    def fail(self, step, reason, detail=None):
        art = self.snapshot("fail-" + step)
        self.emit("step_fail", step=step, reason=reason,
                  detail=detail or {}, artifacts=art)
        self.steps.append({"step": step, "ok": False, "reason": reason})
        raise StepFailed(step, reason, detail)

    # ---- 核心：带验证的步骤 ----
    def step(self, name, action=None, verify=None, verify_desc="",
             timeout=10.0, interval=0.3, guard=True, pre=None,
             detail=None, allow_no_verify=False):
        """
        name        步骤名（写入日志）
        action      callable，执行动作；可返回 dict 作为日志 detail
        verify      callable，后置验证；轮询直到真值，超时即失败。返回值写入日志
        pre         callable，前置条件；返回 falsy 直接中止（不执行动作）
        guard       True = 动作前检查无阻塞模态弹窗
        allow_no_verify  显式承认该步无需验证（仅用于纯读取步骤）
        """
        if verify is None and not allow_no_verify:
            self.fail(name, "违反执行契约：动作步骤必须提供 verify 后置验证")
        t0 = time.time()
        self.emit("step_start", step=name, detail=detail or {},
                  verify=verify_desc, timeout=timeout)

        if guard:
            self.guard(name)

        if pre is not None:
            pv, pel = wait_until(pre, timeout=timeout, interval=interval)
            if not pv:
                self.fail(name, "前置条件不满足（%.1fs 超时）" % timeout,
                          {"waited_s": pel, "phase": "pre"})
            self.emit("pre_ok", step=name, waited_s=pel)

        act_detail = None
        if action is not None:
            try:
                act_detail = action()
            except StepFailed:
                raise
            except Exception as e:
                self.emit("action_error", step=name, error=repr(e),
                          traceback=traceback.format_exc())
                self.fail(name, "动作抛出异常: %r" % e)
            self.emit("action_done", step=name, detail=act_detail)

        if verify is not None:
            v, el = wait_until(verify, timeout=timeout, interval=interval)
            if not v:
                self.fail(name,
                          "后置验证失败（%s，%.1fs 超时）" % (verify_desc or "verify", timeout),
                          {"waited_s": el, "phase": "verify",
                           "action_detail": act_detail})
            self.emit("step_ok", step=name, waited_s=el,
                      verify=verify_desc, verified=v if isinstance(v, (dict, list, str, int)) else True,
                      elapsed_s=round(time.time() - t0, 2))
            self.steps.append({"step": name, "ok": True, "waited_s": el,
                               "verify": verify_desc})
            return v

        self.emit("step_ok", step=name, verify="(none)",
                  elapsed_s=round(time.time() - t0, 2))
        self.steps.append({"step": name, "ok": True, "verify": "(none)"})
        return act_detail

    # ---- 收尾 ----
    def finish(self, ok, **out):
        res = {
            "ok": bool(ok),
            "run": self.name,
            "run_id": self.run_id,
            "elapsed_s": round(time.time() - self.t0, 2),
            "log": self.log_path,
            "steps": self.steps,
        }
        res.update(out)
        try:
            with open(RESULT_PATH, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self.emit("run_end", ok=bool(ok),
                  elapsed_s=res["elapsed_s"],
                  reason=out.get("reason"))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return res

    def run(self, fn):
        """顶层执行包装：捕获一切异常并落盘（pythonw 无控制台，不落盘就永远查不到原因）。"""
        try:
            out = fn(self) or {}
            return self.finish(True, **out)
        except StepFailed as e:
            return self.finish(False, reason=e.reason, failed_step=e.step,
                               detail=e.detail)
        except Exception as e:
            tb = traceback.format_exc()
            self.emit("crash", error=repr(e), traceback=tb)
            self.snapshot("crash")
            return self.finish(False, reason="未捕获异常: %r" % e, traceback=tb)


# ------------------------------------------------------------------ 参数传递
def parse_args_b64(argv=None):
    """从 --args-b64 <base64(json)> 读取参数，绕开桥接层中文/引号编码问题。
    也兼容直接给 JSON 的 --args-json。"""
    argv = list(argv if argv is not None else sys.argv[1:])
    d = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--args-b64" and i + 1 < len(argv):
            d = json.loads(base64.b64decode(argv[i + 1]).decode("utf-8"))
            i += 2
        elif argv[i] == "--args-json" and i + 1 < len(argv):
            d = json.loads(argv[i + 1])
            i += 2
        else:
            i += 1
    return d
