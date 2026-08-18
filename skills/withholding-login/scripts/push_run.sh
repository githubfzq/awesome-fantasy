#!/usr/bin/env bash
# push_run.sh — 把本地 .py（含依赖库）推到 VM，用 PsExec session1 pythonw 运行，回读结果
#
# 用法:
#   push_run.sh [--lib rpa_core.py]... [--args-json '<json>'] [--no-run] <main.py> [额外参数...]
# 示例:
#   push_run.sh --lib rpa_core.py --args-json '{"unit":"修文县关珍养殖场","password":"xxx"}' login_declare.py
#
# 要点:
#   1) 运行前先做桥接健康检查，卡死则自动清孤儿进程 + 清 req/res 自愈（避免 90s 超时）
#   2) certutil 不覆盖已存在文件 → 每次先 Remove-Item
#   3) 参数用 base64(JSON) 传递，绕开桥接层中文/引号编码损坏
#   4) 结果读 last_result.json，用 powershell Get-Content（cmd type 会乱码）
set -uo pipefail

CALL="$HOME/.prlctl-bridge/call.sh"
VM="Windows 11"
LIBS=()
ARGS_JSON=""
NORUN=0

die() { echo "[x] $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --lib)        LIBS+=("$2"); shift 2 ;;
    --args-json)  ARGS_JSON="$2"; shift 2 ;;
    --no-run)     NORUN=1; shift ;;
    -h|--help)    sed -n '2,14p' "$0"; exit 0 ;;
    *)            break ;;
  esac
done

[ $# -ge 1 ] || die "缺少主脚本。用法见 --help"
MAIN="$1"; shift
[ -f "$MAIN" ] || die "找不到文件: $MAIN"

# ---------- 1) 桥接健康检查 + 自愈 ----------
bridge_ok() { "$CALL" exec "$VM" cmd /c "echo bridge_ok" >/dev/null 2>&1; }

if ! bridge_ok; then
  echo "[!] 桥接无响应，尝试自愈（清孤儿 prlctl exec + req/res）..." >&2
  pkill -9 -f 'prlctl exec' 2>/dev/null || true
  rm -f "$HOME/.prlctl-bridge/req" "$HOME/.prlctl-bridge/res"
  sleep 2
  bridge_ok || die "桥接自愈失败，请检查 LaunchAgent / VM 是否运行"
  echo "[ok] 桥接已恢复" >&2
fi

# ---------- 2) 推送文件 ----------
push_one() {
  local local_file="$1"
  local base remote b64
  base="$(basename "$local_file" .py)"
  remote="C:/rpa/$base"
  [ -f "$local_file" ] || die "找不到文件: $local_file"

  "$CALL" exec "$VM" cmd /c \
    "powershell -NoProfile -Command Remove-Item $remote.py,$remote.b64 -Force -ErrorAction SilentlyContinue" >/dev/null

  b64="$(base64 -i "$local_file" | tr -d '\n')"
  # 分块追加（单条命令过长会让桥接挂起）
  echo "$b64" | fold -w 1400 | while IFS= read -r chunk; do
    "$CALL" exec "$VM" cmd /c \
      "powershell -NoProfile -Command [IO.File]::AppendAllText('$remote.b64', '$chunk')" >/dev/null
  done

  "$CALL" exec "$VM" cmd /c "certutil -decode $remote.b64 $remote.py" >/dev/null \
    || die "解码失败: $base.py"
  echo "[ok] 已推送 $base.py" >&2
}

for lib in ${LIBS[@]+"${LIBS[@]}"}; do push_one "$lib"; done
push_one "$MAIN"

# 自动推送主脚本同目录的其它 .py（如 flow_lib.py 依赖），避免 VM 上 import 失败
MAIN_DIR="$(cd "$(dirname "$MAIN")" && pwd)"
for f in "$MAIN_DIR"/*.py; do
  [ -f "$f" ] || continue
  [ "$(basename "$f")" = "$(basename "$MAIN")" ] && continue
  push_one "$f"
done

MAIN_BASE="$(basename "$MAIN" .py)"
[ "$NORUN" -eq 1 ] && { echo "[i] --no-run，仅推送完成"; exit 0; }

# ---------- 3) 组装参数并运行 ----------
RUN_ARGS=""
if [ -n "$ARGS_JSON" ]; then
  ARGS_B64="$(printf '%s' "$ARGS_JSON" | base64 | tr -d '\n')"
  RUN_ARGS="--args-b64 $ARGS_B64"
fi
[ $# -gt 0 ] && RUN_ARGS="$RUN_ARGS $*"

"$CALL" exec "$VM" cmd /c \
  "C:/rpa/pstools/PsExec64.exe -i 1 -accepteula C:/venv/Scripts/pythonw.exe C:/rpa/$MAIN_BASE.py $RUN_ARGS"

# ---------- 4) 回读结果（base64 回传，避免中文被桥接层编码损坏） ----------
# 关键: 用 LC_ALL=C tr -cd 只保留 base64 字母表字符，剥离桥接混入的 safe-delete 噪声行/中文，
# 否则 tr 在默认 locale 下遇到多字节中文会报 "Illegal byte sequence"，且噪声行会吞掉真正的 base64。
echo "----- last_result.json -----"
RES_B64="$("$CALL" exec "$VM" cmd /c \
  "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('C:/rpa/last_result.json'))" \
  2>/dev/null | LC_ALL=C tr -cd '0-9A-Za-z+/=')"
if [ -n "$RES_B64" ]; then
  printf '%s' "$RES_B64" | base64 -d
  echo
else
  echo "[x] 读取 last_result.json 失败（文件可能不存在或脚本未产出）" >&2
fi
