#!/usr/bin/env bash
# close_app.sh — 关闭扣缴端（含退出确认弹窗链）Mac 侧入口
#
# 用法: close_app.sh
# 输出: close_declare.py 的 last_result.json + 最后一行 STATUS=closed|partial|error
#   closed  主窗与登录窗均已关闭，无残留确认弹窗
#   partial 主窗/登录窗未完全关闭（final_modal 或 closed=false），需人工查看

set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

OUT="$("$DIR/run_vm.sh" "$DIR/close_declare.py" 2>&1)"
echo "$OUT" | grep -vE '^\* |^\[!\]|^\[ok\]|^\[x\]' | sed '/^$/d'

STATUS="$(printf '%s' "$OUT" | tr -d '\r' | sed -n '/last_result\.json/,$p' | sed '1s/.*----- last_result\.json -----//' | tail -n +2 | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("error"); raise SystemExit
closed = d.get("closed") is True
final = d.get("final_modal") is True
if closed and not final:
    print("closed")
elif d.get("failed_step"):
    print("error:" + d["failed_step"])
elif closed:
    print("partial")
else:
    print("partial")
')"
echo "STATUS=$STATUS"
