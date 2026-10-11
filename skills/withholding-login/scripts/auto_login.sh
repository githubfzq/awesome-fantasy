#!/usr/bin/env bash
# auto_login.sh — 扣缴端「一键登录」Mac 侧入口（Agent 最小交互版）
#
# 整条登录流程 = 1 次 VM 调用（验证码路径 = 2 次：截码 → 填码提交）。
# 只读体检用 --dry-run；登录用 --password（或环境变量 WITHHOLDING_PASSWORD）。
#
# 用法:
#   auto_login.sh [--unit U] [--password P] [--captcha C] [--dry-run]
#                 [--auto-close-modal] [--no-start-app] [--login-timeout S]
#
# 输出: last_result.json 全文 + 最后一行 STATUS=<status>（Agent 只按 STATUS 分支）。
#
# 密码优先级: --password > 环境变量 WITHHOLDING_PASSWORD（都不给 → VM 侧 preflight 失败，
# 绝不落盘明文；日志只记长度）。

set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

UNIT=""; PASSWORD=""; CAPTCHA=""; DRY=0; AUTO_CLOSE=0; NO_START=0; TIMEOUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --unit)          UNIT="$2"; shift 2 ;;
    --password)      PASSWORD="$2"; shift 2 ;;
    --captcha)       CAPTCHA="$2"; shift 2 ;;
    --dry-run)       DRY=1; shift ;;
    --auto-close-modal) AUTO_CLOSE=1; shift ;;
    --no-start-app)  NO_START=1; shift ;;
    --login-timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "[x] 未知参数: $1" >&2; exit 2 ;;
  esac
done

[ -n "$PASSWORD" ] || PASSWORD="${WITHHOLDING_PASSWORD:-}"
JSON=$(python3 - "$UNIT" "$PASSWORD" "$CAPTCHA" "$DRY" "$AUTO_CLOSE" "$NO_START" "$TIMEOUT" <<'PY'
import json, sys
unit, pwd, cap = sys.argv[1], sys.argv[2], sys.argv[3]
dry, aclose, nostart = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
to = sys.argv[7]
d = {"unit": unit, "password": pwd}
if cap:      d["captcha"] = cap
if dry:      d["dry_run"] = True
if aclose:   d["auto_close_modal"] = True
if nostart:  d["start_app"] = False
if to:       d["login_timeout"] = float(to)
print(json.dumps(d, ensure_ascii=False))
PY
)

OUT="$("$DIR/run_vm.sh" --args-json "$JSON" "$DIR/auto_login.py" 2>&1)"
# 剥离 run_vm.sh 的 stderr 进度行，保留 JSON 与 STATUS
echo "$OUT" | grep -vE '^\* |^\[!\]|^\[ok\]|^\[x\]' | sed '/^$/d'

# 提取 status 字段（无 status 时回退 failed_step/ok；PsExec 输出带 \r，marker 常拼在行尾）
STATUS="$(printf '%s' "$OUT" | tr -d '\r' | sed -n '/last_result\.json/,$p' | sed '1s/.*----- last_result\.json -----//' | tail -n +2 | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("parse_error"); raise SystemExit
st = d.get("status")
if st:
    print(st)
elif d.get("failed_step"):
    print("error:" + d["failed_step"])
elif d.get("ok"):
    print("ok")
else:
    print("error")
')"
echo "STATUS=$STATUS"
