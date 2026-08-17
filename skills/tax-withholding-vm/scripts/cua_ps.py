#!/usr/bin/env python3
"""
cua_ps.py — 在 Windows 11 VM 内运行 PowerShell 脚本（无转义地狱）。

用法:
  # 从 stdin 读短脚本（直接 inline 执行，注意命令行长度限制）
  echo "Get-Process" | python3 cua_ps.py

  # 运行脚本文件：先落地到 VM 的 C:\\cua_scripts\\<name>，再 powershell -File 执行
  python3 cua_ps.py close_popup.ps1 "ProcDataDeal" "确定"

  # 指定落地目录（可选，默认 C:\\cua_scripts）
  CUA_SCRIPT_DIR='C:\\temp\\ps' python3 cua_ps.py foo.ps1

依赖: 环境变量 CUA_MCP_CALL 指向 mcp_call.py
     （默认 /Users/fanzuquan/.workbuddy/skills/cua-computer-use/scripts/mcp_call.py）
Endpoint: 环境变量 CUA_ENDPOINT，默认 http://10.211.55.5:8000/mcp
"""
import sys, os, base64, json, importlib.util

DEFAULT_CALL = "/Users/fanzuquan/.workbuddy/skills/cua-computer-use/scripts/mcp_call.py"
DEFAULT_ENDPOINT = "http://10.211.55.5:8000/mcp"
DEFAULT_SCRIPT_DIR = "C:\\cua_scripts"


def _load_call_tool():
    path = os.environ.get("CUA_MCP_CALL", DEFAULT_CALL)
    spec = importlib.util.spec_from_file_location("mcp_call", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.call_tool


def _write_file(call_tool, endpoint, path, content):
    res = call_tool(endpoint, "computer_file_write", {"path": path, "content": content}, noproxy=True)
    if "error" in res:
        print("MCP error (write):", res["error"], file=sys.stderr)
        sys.exit(1)


def main():
    call_tool = _load_call_tool()
    endpoint = os.environ.get("CUA_ENDPOINT", DEFAULT_ENDPOINT)
    script_dir = os.environ.get("CUA_SCRIPT_DIR", DEFAULT_SCRIPT_DIR)

    argv = sys.argv[1:]
    if len(argv) == 0 or (len(argv) == 1 and argv[0] == "-"):
        script = sys.stdin.read()
        if not script.strip():
            print("usage: cua_ps.py [script.ps1 [args...]]  (or pipe via stdin)", file=sys.stderr)
            sys.exit(1)
        b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        cmd = f"powershell -NoProfile -EncodedCommand {b64}"
        res = call_tool(endpoint, "computer_run_command", {"command": cmd}, noproxy=True)
        if "error" in res:
            print("MCP error:", res["error"], file=sys.stderr); sys.exit(1)
        for item in res.get("result", {}).get("content", []):
            if item.get("type") == "text":
                sys.stdout.write(item.get("text", ""))
        return

    # 文件模式
    path = argv[0]
    with open(path, "r", encoding="utf-8") as f:
        script = f.read()
    if len(argv) > 1:
        injected = "\n".join(
            f"$arg{i+1} = {json.dumps(a, ensure_ascii=False)}"
            for i, a in enumerate(argv[1:])
        )
        script = injected + "\n" + script

    name = os.path.basename(path)
    vm_path = f"{script_dir}\\{name}"
    call_tool(endpoint, "computer_create_directory", {"path": script_dir}, noproxy=True)
    _write_file(call_tool, endpoint, vm_path, script)
    res = call_tool(endpoint, "computer_run_command",
                    {"command": f'powershell -NoProfile -File "{vm_path}"'}, noproxy=True)
    if "error" in res:
        print("MCP error:", res["error"], file=sys.stderr); sys.exit(1)
    for item in res.get("result", {}).get("content", []):
        if item.get("type") == "text":
            sys.stdout.write(item.get("text", ""))


if __name__ == "__main__":
    main()
