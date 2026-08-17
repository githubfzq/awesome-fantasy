#!/usr/bin/env bash
# run_vm.sh — 通过 Parallels 共享文件夹(\\Mac\Home)直接在 VM 运行 Mac 上的 Python 脚本。
#
# 与旧 push_run.sh 的根本区别：
#   旧版把脚本 base64 推送进 VM、每次先 Remove-Item 再 certutil 解码 —— 产生大量文件删除，
#   触发"批量删除"安全告警。
#   本脚本不再传输/删除任何文件：代码固定在 ~/Documents/rpa（VM 侧即 \\Mac\Home\Documents\rpa），
#   VM 用 PsExec -i 1 在交互会话(session 1)里直接 pythonw 跑共享路径上的源码（扁平目录，
#   Python 自动把脚本目录加入 sys.path，跨文件 import 零配置）。改完 Mac 上的代码，VM 下次运行即时生效。
#
# 用法:
#   run_vm.sh [--args-json '<json>'] [--no-run] <~/Documents/rpa/.../main.py> [额外参数...]
#
# 要点:
#   1) 桥接自愈: 卡死时清孤儿 prlctl + req/res
#   2) Mac 路径 -> UNC: ~/Documents/rpa/foo.py -> \\Mac\Home\Documents\rpa\foo.py
#   3) PsExec -i 1 在交互会话运行（GUI RPA 必须），无需 PYTHONPATH（扁平目录自动可见）
#   4) 结果读 last_result.json（base64 回传 + tr -cd 过滤噪声）

set -uo pipefail

CALL="$HOME/.prlctl-bridge/call.sh"
VM="Windows 11"
MAC_ROOT="$HOME/Documents/rpa"
PSEXEC='C:\rpa\pstools\PsExec64.exe'
PYTHONW='C:\venv\Scripts\pythonw.exe'
# VM 侧看到的共享根（单引号保留反斜杠字面量，UNC 需要开头的双反斜杠）
SHARE='\\Mac\Home\Documents\rpa'

die() { echo "[x] $*" >&2; exit 1; }

ARGS_JSON=""; NORUN=0; MAIN=""; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --args-json) ARGS_JSON="$2"; shift 2 ;;
    --no-run)    NORUN=1; shift ;;
    -h|--help)   sed -n '2,19p' "$0"; exit 0 ;;
    *)           [ -z "$MAIN" ] && MAIN="$1" || EXTRA+=("$1"); shift ;;
  esac
done
[ -n "$MAIN" ] || die "缺少主脚本。用法见 --help"
[ -f "$MAIN" ] || die "找不到文件: $MAIN"

# ---------- 1) 桥接自愈 ----------
bridge_ok() { "$CALL" exec "$VM" cmd /c "echo bridge_ok" >/dev/null 2>&1; }
if ! bridge_ok; then
  echo "[!] 桥接无响应，尝试自愈（清孤儿 prlctl exec + req/res）..." >&2
  pkill -9 -f 'prlctl exec' 2>/dev/null || true
  rm -f "$HOME/.prlctl-bridge/req" "$HOME/.prlctl-bridge/res"
  sleep 2
  bridge_ok || die "桥接自愈失败，请检查 LaunchAgent / VM 是否运行"
  echo "[ok] 桥接已恢复" >&2
fi

# ---------- 2) Mac 路径 -> UNC ----------
to_unc() {
  local p="$1"
  local rel="${p#$MAC_ROOT/}"
  [ "$rel" != "$p" ] || die "脚本必须在 $MAC_ROOT 下: $p"
  rel="${rel//\//\\}"                       # / -> \
  printf '%s%s%s' "$SHARE" '\' "$rel"       # 三部分拼接，避免 printf 格式里的反斜杠歧义
}
MAIN_UNC="$(to_unc "$MAIN")"

# ---------- 3) 组装命令：PsExec -i 1 在交互会话直接 pythonw <UNC> ----------
ARGS="$MAIN_UNC"
[ -n "$ARGS_JSON" ] && ARGS="$ARGS --args-b64 $(printf '%s' "$ARGS_JSON" | base64 | tr -d '\n')"
[ ${#EXTRA[@]} -gt 0 ] && ARGS="$ARGS ${EXTRA[*]}"
RUN="$PSEXEC -i 1 -accepteula $PYTHONW $ARGS"

if [ "$NORUN" -eq 1 ]; then
  echo "[i] --no-run，命令如下:"; echo "$RUN"; exit 0
fi

# 确保 VM 侧结果目录存在（仅创建目录，不删任何文件）
"$CALL" exec "$VM" cmd /c "mkdir C:/rpa" >/dev/null 2>&1 || true

echo "[*] 运行: $MAIN_UNC" >&2
"$CALL" exec "$VM" "$RUN"

# ---------- 4) 回读 last_result.json（base64 回传，剥离桥接噪声行） ----------
echo "----- last_result.json -----"
RES_B64="$("$CALL" exec "$VM" cmd /c \
  "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('C:/rpa/last_result.json'))" \
  2>/dev/null | LC_ALL=C tr -cd '0-9A-Za-z+/=')"
if [ -n "$RES_B64" ]; then
  printf '%s' "$RES_B64" | base64 -d; echo
else
  echo "[x] 读取 last_result.json 失败（脚本可能未产出）" >&2
fi
