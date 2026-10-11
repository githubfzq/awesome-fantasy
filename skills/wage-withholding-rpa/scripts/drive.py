#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive.py — macOS 侧驱动助手：在 Parallels Windows 11 VM 的交互会话(session 1)
里运行 C:\\rpa\\rpa.py，读回 C:\\rpa\\last_result.json，并把截图 b64 解码保存到工作区。

用法:
  python3 drive.py screenshot                  # 截图并解码到工作区 screenshots/
  python3 drive.py uia_tree --title 自然人电子税务局 --depth 4
  python3 drive.py mouse_click --x 1512 --y 791
  python3 drive.py keyboard_type --text 关珍
  python3 drive.py uia_locate --title 自然人电子税务局 --class_name TXPFamerEditEx

任何 rpa.py 的子命令 + 参数都可直接透传。若结果含 b64（截图），自动写 png 到 WORKSPACE/screenshots/。
"""
import os
import sys
import json
import time
import base64
import subprocess

HOME = os.path.expanduser("~")
BRIDGE_CALL = os.path.join(HOME, ".prlctl-bridge", "call.sh")
VM_NAME = os.environ.get("RPA_VM", "Windows 11")
PSEXEC = os.environ.get("RPA_PSEXEC", r"C:\rpa\pstools\PsExec64.exe")
VENV_PY = os.environ.get("RPA_VENV_PY", r"C:\venv\Scripts\pythonw.exe")
RPA_PY = os.environ.get("RPA_PY", r"C:\rpa\rpa.py")
RESULT_FILE = os.environ.get("RPA_RESULT_FILE", r"C:\rpa\last_result.json")
WORKSPACE = os.environ.get("RPA_WORKSPACE",
                           "/Users/fanzuquan/WorkBuddy/2026-08-15-15-49-59")
SHOT_DIR = os.path.join(WORKSPACE, "screenshots")


def _to_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def bridge_exec(args, timeout=None):
    if timeout is None:
        timeout = _to_env("RPA_BRIDGE_TIMEOUT", 120)
    cmd = [BRIDGE_CALL, "exec", VM_NAME] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.returncode


def rpa_run(sub_args, timeout=None):
    if timeout is None:
        timeout = _to_env("RPA_TIMEOUT", 90)
    launch = [PSEXEC, "-i", "1", "-accepteula", VENV_PY, RPA_PY] + list(sub_args)
    bridge_exec(launch, timeout=timeout)                      # 等待 session-1 进程结束
    raw, _ = bridge_exec(["cmd", "/c", f"type {RESULT_FILE}"], timeout=30)
    raw = raw.strip()
    try:
        res = json.loads(raw)
    except json.JSONDecodeError:
        s = raw.rfind("{")
        e = raw.rfind("}") + 1
        if s >= 0 and e > s:
            try:
                res = json.loads(raw[s:e])
            except Exception:
                return {"_raw": raw, "status": "parse_error"}
        else:
            return {"_raw": raw, "status": "parse_error"}
    # 截图 b64 -> 落盘
    if isinstance(res, dict) and res.get("b64"):
        os.makedirs(SHOT_DIR, exist_ok=True)
        ts = int(time.time())
        path = os.path.join(SHOT_DIR, f"shot_{ts}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(res["b64"]))
        res["_png"] = path
    return res


def main():
    if len(sys.argv) < 2:
        print("用法: python3 drive.py <rpa.py 子命令及参数>")
        sys.exit(2)
    sub = sys.argv[1:]
    # 截图命令若没带 --b64，自动补上以便回看
    if sub[0] == "screenshot" and "--b64" not in sub:
        sub = sub + ["--b64"]
    res = rpa_run(sub)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
