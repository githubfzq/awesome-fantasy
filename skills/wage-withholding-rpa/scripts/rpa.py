#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rpa.py — Windows RPA 引擎（VM 内运行，GUI 会话 session 1）

由 windows-rpa 技能原版扩展：
  * 新增 UIA 控件级定位（pywinauto，优先于图像匹配）
  * 新增 uia_click / uia_type / uia_tree
  * 截图支持 --b64 直接回传 base64（便于 macOS 侧查看，无需共享文件夹）

子命令（全部返回 JSON）：
  screenshot           截图（--output 路径 / --b64 回传 base64）
  locate               模板匹配（pyautogui.locateOnScreen，--image / --confidence）
  uia_locate           UIA 控件定位（--title 窗口标题, --name/--auto_id/--control_type/--class_name）
  uia_click            UIA 控件点击
  uia_type             UIA 控件输入（--name/--auto_id + --text）
  uia_tree             导出某窗口 UIA 树（--title, --depth）
  mouse_move/click/drag/scroll/position
  keyboard_type/press/hotkey
  launch               启动应用（--app 别名或完整路径, --args）
  window_list / find_window / window_activate
  clipboard_get/set
  check / shell / get_state
"""
import sys
import os
import io
import time
import json
import argparse
import base64
import subprocess
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(os.environ.get("RPA_OUTPUT", str(Path(__file__).parent / "output")))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------------
# 依赖探测
# ----------------------------------------------------------------------------
def _have(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def check_pyautogui():
    return _have("pyautogui")


def check_pywinauto():
    return _have("pywinauto")


# ----------------------------------------------------------------------------
# 截图
# ----------------------------------------------------------------------------
def cmd_screenshot(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装。运行: pip install pyautogui pillow"}
    import pyautogui
    try:
        region = None
        if args.region:
            r = json.loads(args.region)
            region = (r.get("x", 0), r.get("y", 0), r.get("width", 800), r.get("height", 600))
        img = pyautogui.screenshot(region=region)
        out = {}
        if args.b64:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            out["b64"] = base64.b64encode(buf.getvalue()).decode("ascii")
        if not args.no_save:
            save_path = args.output or str(OUTPUT_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            img.save(save_path)
            out["path"] = save_path
        out["status"] = "ok"
        out["size"] = {"width": img.width, "height": img.height}
        return out
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------------
# 模板匹配（图像相似度）
# ----------------------------------------------------------------------------
def cmd_locate(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        kwargs = {"confidence": args.confidence}
        if args.grayscale:
            kwargs["grayscale"] = True
        loc = pyautogui.locateOnScreen(args.image, **kwargs)
        if loc:
            return {
                "status": "ok", "found": True,
                "location": {"left": loc.left, "top": loc.top, "width": loc.width, "height": loc.height},
                "center": {"x": loc.left + loc.width // 2, "y": loc.top + loc.height // 2},
            }
        return {"status": "ok", "found": False, "message": "未找到匹配图像"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------------
# UIA 控件定位 / 操作（pywinauto，优先路径）
# ----------------------------------------------------------------------------
def _connect_window(title, timeout=10, backend="win32"):
    from pywinauto import Application
    try:
        return Application(backend=backend).connect(title_re=title, timeout=timeout)
    except Exception:
        return Application(backend=backend).connect(title=title, timeout=timeout)


def _find_control(wrapper, name=None, auto_id=None, control_type=None, class_name=None, backend="win32"):
    """win32 后端：title=窗口文本(name)，class_name，control_id；不支持 auto_id/control_type 直接映射。
    优先 child_window 精确匹配，再 descendants 子串回退。"""
    specs = {}
    if name:
        specs["title"] = name
    if class_name:
        specs["class_name"] = class_name
    # win32 不直接支持 auto_id/control_type 过滤 -> 走精确 specs
    try:
        c = wrapper.child_window(**specs)
        if c.exists():
            return c.wrapper_object()
    except Exception:
        pass
    # 子串回退：扫描 descendants，按 window_text 子串匹配
    best = None
    try:
        for desc in wrapper.descendants():
            try:
                t = desc.window_text() or ""
                cn = desc.class_name() or ""
                if name and name in t:
                    if class_name is None or cn == class_name:
                        best = desc; break
                if auto_id and auto_id in t:
                    if class_name is None or cn == class_name:
                        best = desc; break
            except Exception:
                continue
    except Exception:
        pass
    return best


def cmd_uia_locate(args):
    if not check_pywinauto():
        return {"status": "error", "message": "pywinauto 未安装。运行: pip install pywinauto"}
    try:
        app = _connect_window(args.title)
        dlg = app.top_window()
        ctrl = _find_control(dlg, name=args.name, auto_id=args.auto_id,
                             control_type=args.control_type, class_name=args.class_name)
        if ctrl is None:
            return {"status": "ok", "found": False, "message": "UIA 未找到控件"}
        r = ctrl.rectangle()
        return {
            "status": "ok", "found": True,
            "rect": {"left": r.left, "top": r.top, "right": r.right, "bottom": r.bottom},
            "center": {"x": (r.left + r.right) // 2, "y": (r.top + r.bottom) // 2},
            "name": ctrl.window_text(), "class_name": ctrl.class_name(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_uia_click(args):
    if not check_pywinauto():
        return {"status": "error", "message": "pywinauto 未安装"}
    try:
        app = _connect_window(args.title)
        dlg = app.top_window()
        ctrl = _find_control(dlg, name=args.name, auto_id=args.auto_id,
                             control_type=args.control_type, class_name=args.class_name)
        if ctrl is None:
            return {"status": "error", "message": "UIA 未找到控件"}
        ctrl.click_input()
        r = ctrl.rectangle()
        return {"status": "ok", "center": {"x": (r.left + r.right) // 2, "y": (r.top + r.bottom) // 2}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_uia_type(args):
    if not check_pywinauto():
        return {"status": "error", "message": "pywinauto 未安装"}
    try:
        app = _connect_window(args.title)
        dlg = app.top_window()
        ctrl = _find_control(dlg, name=args.name, auto_id=args.auto_id,
                             control_type=args.control_type, class_name=args.class_name)
        if ctrl is None:
            return {"status": "error", "message": "UIA 未找到控件"}
        ctrl.set_focus()
        if args.append:
            ctrl.type_keys(args.text)
        else:
            try:
                ctrl.set_edit_text(args.text)
            except Exception:
                ctrl.type_keys(args.text, with_spaces=True)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_uia_tree(args):
    if not check_pywinauto():
        return {"status": "error", "message": "pywinauto 未安装"}
    try:
        app = _connect_window(args.title)
        dlg = app.top_window()

        def walk(el, depth):
            if depth > args.depth:
                return []
            try:
                line = "  " * depth + f"[{el.class_name() or '?'}] name={el.window_text()!r}"
            except Exception:
                line = "  " * depth + "[?] <unreadable>"
            out = [line]
            for c in el.children():
                out += walk(c, depth + 1)
            return out

        tree = "\n".join(walk(dlg, 0))
        return {"status": "ok", "tree": tree}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------------
# 鼠标 / 键盘
# ----------------------------------------------------------------------------
def cmd_mouse_move(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.moveTo(args.x, args.y, duration=args.duration)
        return {"status": "ok", "position": {"x": args.x, "y": args.y}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_mouse_click(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.click(x=args.x, y=args.y, button=args.button, clicks=args.clicks)
        pos = pyautogui.position()
        return {"status": "ok", "button": args.button, "position": {"x": pos[0], "y": pos[1]}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_mouse_drag(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.moveTo(args.start_x, args.start_y)
        pyautogui.drag(args.end_x - args.start_x, args.end_y - args.start_y,
                       duration=args.duration, button=args.button)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_mouse_scroll(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.scroll(args.clicks, x=args.x, y=args.y)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_mouse_position(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    x, y = pyautogui.position()
    return {"status": "ok", "position": {"x": x, "y": y}}


def cmd_keyboard_type(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.typewrite(args.text, interval=args.interval)
        return {"status": "ok", "length": len(args.text)}
    except Exception as e:
        try:
            import pyperclip
            pyperclip.copy(args.text)
            pyautogui.hotkey("ctrl", "v")
            return {"status": "ok", "action": "type_via_clipboard", "length": len(args.text)}
        except Exception as e2:
            return {"status": "error", "message": f"{e} | clipboard:{e2}"}


def cmd_keyboard_press(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.press(args.key, presses=args.presses)
        return {"status": "ok", "key": args.key}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_keyboard_hotkey(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    try:
        pyautogui.hotkey(*args.keys.split(","))
        return {"status": "ok", "keys": args.keys}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_screen_size(args):
    if not check_pyautogui():
        return {"status": "error", "message": "pyautogui 未安装"}
    import pyautogui
    w, h = pyautogui.size()
    return {"status": "ok", "screen": {"width": w, "height": h}}


# ----------------------------------------------------------------------------
# 应用 / 窗口 / 剪贴板 / 环境
# ----------------------------------------------------------------------------
APP_PATHS = {
    "notepad": "notepad.exe", "word": "winword.exe", "excel": "excel.exe",
    "chrome": "chrome.exe", "edge": "msedge.exe", "calc": "calc.exe",
    "cmd": "cmd.exe", "powershell": "powershell.exe",
}


def cmd_launch(args):
    app = APP_PATHS.get(args.app.lower(), args.app)
    try:
        cmd = f'start "" "{app}"' + (f' {args.args}' if args.args else '')
        subprocess.Popen(cmd, shell=True)
        return {"status": "ok", "app": args.app, "path": app}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_window_list(args):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object ProcessName,MainWindowTitle,Id | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10)
        wins = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
        if not isinstance(wins, list):
            wins = [wins]
        return {"status": "ok", "windows": [{"process": w.get("ProcessName"),
                                             "title": w.get("MainWindowTitle"), "pid": w.get("Id")} for w in wins[:20]]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_find_window(args):
    try:
        f = args.title_contains or ""
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Get-Process | Where-Object {{$_.MainWindowTitle -like "*{f}*"}} | Select-Object ProcessName,MainWindowTitle,Id | ConvertTo-Json'],
            capture_output=True, text=True, timeout=10)
        wins = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
        if not isinstance(wins, list):
            wins = [wins]
        return {"status": "ok", "windows": [{"process": w.get("ProcessName"),
                                             "title": w.get("MainWindowTitle"), "pid": w.get("Id")} for w in wins]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_window_activate(args):
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f'(New-Object -ComObject WScript.Shell).AppActivate("{args.title_pattern}")'],
                       capture_output=True, text=True, timeout=5)
        return {"status": "ok", "title_pattern": args.title_pattern}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_clipboard_get(args):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                           capture_output=True, text=True, timeout=5)
        return {"status": "ok", "content": r.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_clipboard_set(args):
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f'Set-Clipboard -Value "{args.text}"'],
                       capture_output=True, text=True, timeout=5)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_check(args):
    res = {"platform": sys.platform, "pyautogui": check_pyautogui(),
           "pywinauto": check_pywinauto(), "python": sys.version}
    if check_pyautogui():
        import pyautogui
        res["screen_size"] = {"width": pyautogui.size()[0], "height": pyautogui.size()[1]}
    return {"status": "ok", "environment": res}


def cmd_shell(args):
    try:
        sh = ["powershell", "-NoProfile", "-Command", args.command] if args.shell_type == "powershell" else ["cmd", "/c", args.command]
        r = subprocess.run(sh, capture_output=True, text=True, timeout=60)
        return {"status": "ok", "stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "命令超时"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    # 看门狗：任何子命令（尤其是发送输入的 mouse/keyboard）若卡死，
    # 最多 WATCHDOG 秒后强制退出，避免 session-1 孤儿进程堵死 prlctl 桥。
    import threading
    watchdog = int(os.environ.get("RPA_WATCHDOG", "25"))
    def _wd():
        time.sleep(watchdog)
        try:
            with open(os.environ.get("RPA_RESULT_FILE",
                       str(Path(__file__).parent / "last_result.json")), "w", encoding="utf-8") as _f:
                _f.write(json.dumps({"status": "error", "message": f"watchdog 超时({watchdog}s)"},
                                    ensure_ascii=False))
        except Exception:
            pass
        os._exit(3)
    threading.Thread(target=_wd, daemon=True).start()

    p = argparse.ArgumentParser(description="Windows RPA 引擎")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("screenshot"); s.add_argument("--region"); s.add_argument("--output", "-o")
    s.add_argument("--b64", action="store_true"); s.add_argument("--no_save", action="store_true"); s.set_defaults(func=cmd_screenshot)

    s = sub.add_parser("locate"); s.add_argument("--image", required=True); s.add_argument("--confidence", type=float, default=0.9)
    s.add_argument("--grayscale", action="store_true"); s.set_defaults(func=cmd_locate)

    s = sub.add_parser("uia_locate"); s.add_argument("--title", required=True)
    s.add_argument("--name"); s.add_argument("--auto_id"); s.add_argument("--control_type"); s.add_argument("--class_name")
    s.set_defaults(func=cmd_uia_locate)

    s = sub.add_parser("uia_click"); s.add_argument("--title", required=True)
    s.add_argument("--name"); s.add_argument("--auto_id"); s.add_argument("--control_type"); s.add_argument("--class_name")
    s.set_defaults(func=cmd_uia_click)

    s = sub.add_parser("uia_type"); s.add_argument("--title", required=True)
    s.add_argument("--name"); s.add_argument("--auto_id"); s.add_argument("--control_type"); s.add_argument("--class_name")
    s.add_argument("--text", required=True); s.add_argument("--append", action="store_true"); s.set_defaults(func=cmd_uia_type)

    s = sub.add_parser("uia_tree"); s.add_argument("--title", required=True); s.add_argument("--depth", type=int, default=4)
    s.set_defaults(func=cmd_uia_tree)

    s = sub.add_parser("mouse_move"); s.add_argument("--x", type=int, required=True); s.add_argument("--y", type=int, required=True)
    s.add_argument("--duration", type=float, default=0.5); s.set_defaults(func=cmd_mouse_move)

    s = sub.add_parser("mouse_click"); s.add_argument("--x", type=int); s.add_argument("--y", type=int)
    s.add_argument("--button", default="left"); s.add_argument("--clicks", type=int, default=1); s.set_defaults(func=cmd_mouse_click)

    s = sub.add_parser("mouse_drag"); s.add_argument("--start-x", type=int, required=True); s.add_argument("--start-y", type=int, required=True)
    s.add_argument("--end-x", type=int, required=True); s.add_argument("--end-y", type=int, required=True)
    s.add_argument("--duration", type=float, default=1.0); s.add_argument("--button", default="left"); s.set_defaults(func=cmd_mouse_drag)

    s = sub.add_parser("mouse_scroll"); s.add_argument("--clicks", type=int, required=True); s.add_argument("--x", type=int); s.add_argument("--y", type=int)
    s.set_defaults(func=cmd_mouse_scroll)

    s = sub.add_parser("mouse_position"); s.set_defaults(func=cmd_mouse_position)

    s = sub.add_parser("keyboard_type"); s.add_argument("--text", required=True); s.add_argument("--interval", type=float, default=0.05)
    s.set_defaults(func=cmd_keyboard_type)

    s = sub.add_parser("keyboard_press"); s.add_argument("--key", required=True); s.add_argument("--presses", type=int, default=1)
    s.set_defaults(func=cmd_keyboard_press)

    s = sub.add_parser("keyboard_hotkey"); s.add_argument("--keys", required=True); s.set_defaults(func=cmd_keyboard_hotkey)

    s = sub.add_parser("screen_size"); s.set_defaults(func=cmd_screen_size)

    s = sub.add_parser("launch"); s.add_argument("--app", required=True); s.add_argument("--args"); s.set_defaults(func=cmd_launch)

    s = sub.add_parser("window_list"); s.set_defaults(func=cmd_window_list)
    s = sub.add_parser("find_window"); s.add_argument("--title_contains", default=""); s.set_defaults(func=cmd_find_window)
    s = sub.add_parser("window_activate"); s.add_argument("--title_pattern", required=True); s.set_defaults(func=cmd_window_activate)
    s = sub.add_parser("clipboard_get"); s.set_defaults(func=cmd_clipboard_get)
    s = sub.add_parser("clipboard_set"); s.add_argument("--text", required=True); s.set_defaults(func=cmd_clipboard_set)
    s = sub.add_parser("check"); s.set_defaults(func=cmd_check)
    s = sub.add_parser("shell"); s.add_argument("--command", required=True); s.add_argument("--shell_type", default="powershell")
    s.set_defaults(func=cmd_shell)

    args = p.parse_args()
    if args.command is None:
        p.print_help(); sys.exit(1)
    result = args.func(args)
    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    print(out_json)
    # 桥接侧（session 0）无法直接捕获 session 1 的 stdout，故同时写入结果文件。
    # 默认 C:\rpa\last_result.json（与脚本同目录），可用环境变量 RPA_RESULT_FILE 覆盖。
    try:
        rf = os.environ.get("RPA_RESULT_FILE", str(Path(__file__).parent / "last_result.json"))
        with open(rf, "w", encoding="utf-8") as _f:
            _f.write(out_json)
    except Exception:
        pass


if __name__ == "__main__":
    main()
