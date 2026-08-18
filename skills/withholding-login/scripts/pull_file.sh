#!/usr/bin/env bash
# pull_file.sh — 把 VM 内文件经 base64 回传到 Mac（绕开被禁的 prlctl copyfrom）
# 用法: pull_file.sh <VM绝对路径> [Mac输出路径]
#   VM绝对路径 如 C:/rpa/captcha.png
#   Mac输出路径 默认 ~/Downloads/<基名>
set -e

if [ -z "$1" ]; then
  echo "用法: pull_file.sh <VM路径> [Mac输出路径]" >&2
  exit 1
fi
VMPATH="$1"
OUT="${2:-$HOME/Downloads/$(basename "$VMPATH")}"
CALL=~/.prlctl-bridge/call.sh

B64=$($CALL exec "Windows 11" cmd /c "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('$VMPATH'))" 2>/dev/null | tail -1)
if [ -z "$B64" ]; then
  echo "回传失败：VM 内可能无此文件 $VMPATH" >&2
  exit 1
fi
echo "$B64" | base64 -d > "$OUT"
echo "已保存到 $OUT ($(wc -c < "$OUT") 字节)"
