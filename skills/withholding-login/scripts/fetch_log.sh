#!/usr/bin/env bash
# fetch_log.sh — 取回 VM 内 RPA 逐步执行日志（JSONL），追溯每一步做了什么、验证结果如何
#
# 用法:
#   fetch_log.sh                 # 本次运行完整日志（latest.jsonl）
#   fetch_log.sh --brief         # 只看每步结论（step_ok / step_fail / run_end / crash）
#   fetch_log.sh --list          # 列出历史 run 与冻结现场文件
#   fetch_log.sh --run <run_id>  # 指定历史 run
#   fetch_log.sh --snap <run_id> # 取回该 run 失败截图到 ~/Downloads
#
# 注意: 文本一律走 base64 回传再本地解码 —— 桥接层 PowerShell→cmd 会把 UTF-8 中文截断成乱码。
set -uo pipefail

CALL="$HOME/.prlctl-bridge/call.sh"
VM="Windows 11"
LOGDIR="C:/rpa/logs"
MODE="full"
RUN_ID=""

while [ $# -gt 0 ]; do
  case "$1" in
    --brief) MODE="brief"; shift ;;
    --list)  MODE="list";  shift ;;
    --run)   RUN_ID="$2";  shift 2 ;;
    --snap)  MODE="snap"; RUN_ID="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) shift ;;
  esac
done

# 以 base64 回传远端文本文件，避免中文编码损坏
# 关键: LC_ALL=C tr -cd '0-9A-Za-z+/=' 只保留 base64 字符，剥离桥接混入的 safe-delete 噪声行/中文，
# 否则 tr 在默认 locale 下遇到多字节中文会报 "Illegal byte sequence" 并丢数据。
read_remote() {
  local path="$1" b64
  b64="$("$CALL" exec "$VM" cmd /c \
    "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('$path'))" \
    2>/dev/null | LC_ALL=C tr -cd '0-9A-Za-z+/=')"
  [ -n "$b64" ] || { echo "[x] 读取失败或文件不存在: $path" >&2; return 1; }
  printf '%s' "$b64" | base64 -d
}

TARGET="$LOGDIR/latest.jsonl"
[ -n "$RUN_ID" ] && TARGET="$LOGDIR/$RUN_ID.jsonl"

case "$MODE" in
  list)
    # 注意: PowerShell 脚本内的管道符必须用 ^| 转义，否则 cmd /c 会把 | 当成自己的管道，
    # 把 Sort-Object 当成独立命令执行而报“不是内部或外部命令”。
    "$CALL" exec "$VM" cmd /c \
      "powershell -NoProfile -Command Get-ChildItem $LOGDIR ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 30 Name,Length ^| Format-Table -AutoSize ^| Out-String -Width 200"
    ;;
  snap)
    [ -n "$RUN_ID" ] || { echo "需要 --snap <run_id>" >&2; exit 1; }
    PNG="$("$CALL" exec "$VM" cmd /c \
      "powershell -NoProfile -Command (Get-ChildItem $LOGDIR -Filter '$RUN_ID*screen.png' ^| Select-Object -First 1).FullName" \
      | LC_ALL=C tr -d '\r' | grep -v '^$' | tail -1)"
    [ -n "$PNG" ] || { echo "该 run 无截图（可能未失败）" >&2; exit 1; }
    OUT="$HOME/Downloads/$RUN_ID-screen.png"
    read_remote "$PNG" > "$OUT" || exit 1
    echo "已取回失败现场截图: $OUT"
    ;;
  brief)
    # 在 Mac 本地过滤，避免远端 Select-String 再引入一次编码转换
    read_remote "$TARGET" | grep -E '"event": ?"(step_ok|step_fail|run_end|crash|snapshot|already_logged_in)"'
    ;;
  *)
    read_remote "$TARGET"
    ;;
esac
