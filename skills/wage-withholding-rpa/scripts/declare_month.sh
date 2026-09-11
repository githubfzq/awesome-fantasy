#!/usr/bin/env bash
# declare_month.sh — 2026-09 申报期（税款所属期 2026年08月）综合所得（工资薪金）
#   端到端申报 Mac 侧驱动。VM 侧内核 = declare_month_pipeline.py。
#
# 用法:
#   declare_month.sh close              # 干净关闭扣缴端（含托盘进程收尾）
#   declare_month.sh login [--captcha XXXX] [--dry]   # 取密(仅内存)→全新启动→登录
#   declare_month.sh preflow 1|0        # 1=dry-run(0点击) / 0=实跑（月份门→模块→复制→视觉门停）
#   declare_month.sh finish             # （视觉通过后）计税→双门→发送(用户已显式授权)→终态
#   declare_month.sh recheck            # 退出模块重进复核（第二次独立读数）
#   declare_month.sh auto               # 串起 close→login→preflow(1)→preflow(0)，
#                                       # 在验证码(退出码90)/视觉门(退出码80)处停下等编排端
#   declare_month.sh auto-resume finish|recheck   # 视觉门通过后继续
#
# 门1（通道新鲜度）：每次 VM 流水线调用前记录 C:\rpa\last_result.json 的 run_id，
#   运行后断言严格更新；未更新=本次未执行 → 自动重试一次，仍失败 GATE1_FAIL。
# 凭据：仅运行时经 keepass-lookup 取出并放进进程环境（WITHHOLDING_PASSWORD），
#   绝不 echo、绝不落盘；auto_login 日志只记长度。
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
VM="Windows 11"
BR="$HOME/.prlctl-bridge/call.sh"
KP="$HOME/.zcode/skills/keepass-lookup/scripts/kp_get.py"
KP_DB="/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agents.kdbx"
KP_KEY="/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agent_main_pass"

# ---------------------------------------------------------------- 门1 工具
old_run_id() {
  local b64
  b64=$("$BR" exec "$VM" cmd /c \
    "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('C:/rpa/last_result.json'))" \
    2>/dev/null | LC_ALL=C tr -cd '0-9A-Za-z+/=')
  [ -z "$b64" ] && { echo ""; return; }
  printf '%s' "$b64" | base64 -d 2>/dev/null | python3 -c '
import json,sys
try: print(json.load(sys.stdin).get("run_id","") or "")
except Exception: print("")' 2>/dev/null || echo ""
}

extract_json() {  # stdin=JSON, $1=status|run_id|detail_status|failed_step
  python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: print("parse_error"); raise SystemExit
k=sys.argv[1]
if k=="status": print(d.get("status",""))
elif k=="run_id": print(d.get("run_id",""))
elif k=="failed_step": print(d.get("failed_step",""))
elif k=="detail_status": print((d.get("detail") or {}).get("status",""))
' "$1"
}

pipeline_run() {  # $1=args-json；stdout=last_result.json 正文；门1 内建
  local args="$1" old new out body
  old=$(old_run_id)
  out=$(bash "$DIR/run_vm.sh" --args-json "$args" "$DIR/declare_month_pipeline.py" 2>&1)
  body=$(printf '%s' "$out" | tr -d '\r' | sed -n '/----- last_result\.json -----/,$p' | sed '1d')
  new=$(printf '%s' "$body" | extract_json run_id)
  if [ -z "$new" ] || [ "$new" = "$old" ]; then
    echo "[gate1] run_id 未更新(old=$old new=$new) → 判定本次未执行，重试一次" >&2
    old="$new"
    sleep 2
    out=$(bash "$DIR/run_vm.sh" --args-json "$args" "$DIR/declare_month_pipeline.py" 2>&1)
    body=$(printf '%s' "$out" | tr -d '\r' | sed -n '/----- last_result\.json -----/,$p' | sed '1d')
    new=$(printf '%s' "$body" | extract_json run_id)
    if [ -z "$new" ] || [ "$new" = "$old" ]; then
      echo "GATE1_FAIL run_id 仍未更新（通道完整性门不过，绝不采信结果）"
      return 9
    fi
  fi
  printf '%s\n' "$body"
}

# ---------------------------------------------------------------- 阶段
stage_close() {
  local out st
  out=$(bash "$DIR/close_app.sh" 2>&1)
  echo "$out"
  st=$(printf '%s' "$out" | tr -d '\r' | sed -n 's/^STATUS=//p' | tail -1)
  echo "PIPELINE_STATUS=${st:-unknown}"
  [ "$st" = "closed" ] && return 0
  return 1
}

stage_login() {
  local out st pwd
  pwd=$(python3 "$KP" --db "$KP_DB" --master-file "$KP_KEY" --search 自然人电子税务局 \
        | python3 -c 'import json,sys;sys.stdout.write(json.load(sys.stdin)["password"])')
  [ -n "$pwd" ] || { echo "[x] 取密失败"; echo "PIPELINE_STATUS=kp_failed"; return 2; }
  if [ "${1:-}" = "--dry" ]; then
    out=$(WITHHOLDING_PASSWORD="$pwd" bash "$DIR/auto_login.sh" --dry-run 2>&1)
  else
    out=$(WITHHOLDING_PASSWORD="$pwd" bash "$DIR/auto_login.sh" "$@" 2>&1)
  fi
  unset pwd
  echo "$out" | grep -v '^WITHHOLDING'
  st=$(printf '%s' "$out" | tr -d '\r' | sed -n 's/^STATUS=//p' | tail -1)
  echo "PIPELINE_STATUS=${st:-unknown}"
  if [ "$st" = "captcha_required" ]; then
    echo "CAPTCHA_IMAGE=$HOME/Documents/rpa/captcha.png"
    return 90
  fi
  [ "$st" = "success" ] || [ "$st" = "already_logged_in" ]
}

stage_preflow() {  # $1=1 dry / 0 real
  local dry="${1:-0}" body st dst fst
  body=$(pipeline_run "$(python3 -c '
import json,sys
print(json.dumps({"stage":"preflow","dry_run":sys.argv[1]=="1"}))' "$dry")") || return $?
  echo "$body"
  st=$(printf '%s' "$body" | extract_json status)
  dst=$(printf '%s' "$body" | extract_json detail_status)
  fst=$(printf '%s' "$body" | extract_json failed_step)
  local eff="${st:-$dst}"
  echo "PIPELINE_STATUS=${eff:-$fst}"
  case "$eff" in
    dry_ok) return 0 ;;
    copy_done_need_visual|draft_present_need_visual) return 80 ;;
    *) return 1 ;;
  esac
}

stage_finish() {
  local body st dst fst
  body=$(pipeline_run "$(python3 -c '
import json
print(json.dumps({"stage":"finish","visual_ok":True,"send_authorized":True,
 "auth_note":"用户 2026-09-12 显式事先授权：硬门全部通过即直接发送申报，不再等待逐次确认",
 "calc_timeout":60,"terminal_timeout":240}, ensure_ascii=False))')") || return $?
  echo "$body"
  st=$(printf '%s' "$body" | extract_json status)
  dst=$(printf '%s' "$body" | extract_json detail_status)
  fst=$(printf '%s' "$body" | extract_json failed_step)
  local eff="${st:-$dst}"
  echo "PIPELINE_STATUS=${eff:-$fst}"
  case "$eff" in
    sent_need_visual) return 81 ;;
    *) return 1 ;;
  esac
}

stage_recheck() {
  local body st dst fst
  body=$(pipeline_run '{"stage":"recheck"}') || return $?
  echo "$body"
  st=$(printf '%s' "$body" | extract_json status)
  dst=$(printf '%s' "$body" | extract_json detail_status)
  fst=$(printf '%s' "$body" | extract_json failed_step)
  local eff="${st:-$dst}"
  echo "PIPELINE_STATUS=${eff:-$fst}"
  [ "$eff" = "recheck_captured" ]
}

stage_terminal_resume() {
  local body st dst fst
  body=$(pipeline_run '{"stage":"terminal_resume"}') || return $?
  echo "$body"
  st=$(printf '%s' "$body" | extract_json status)
  dst=$(printf '%s' "$body" | extract_json detail_status)
  fst=$(printf '%s' "$body" | extract_json failed_step)
  local eff="${st:-$dst}"
  echo "PIPELINE_STATUS=${eff:-$fst}"
  case "$eff" in
    sent_need_visual) return 81 ;;
    *) return 1 ;;
  esac
}

cmd_auto() {
  echo "=== [1/5] close ==="
  stage_close || { echo "AUTO_STOP: close 未成功"; return 1; }
  echo "=== [2/5] login ==="
  stage_login; rc=$?
  [ $rc -eq 0 ] || { [ $rc -eq 90 ] && echo "AUTO_STOP(90): 需识验证码后: declare_month.sh login --captcha <码> 再 auto-resume"; return $rc; }
  echo "=== [3/5] preflow dry ==="
  stage_preflow 1 || { echo "AUTO_STOP: dry-run 未过"; return 1; }
  echo "=== [4/5] preflow real ==="
  stage_preflow 0; rc=$?
  [ $rc -eq 80 ] && echo "AUTO_STOP(80): 复制完成，需视觉确认后: declare_month.sh auto-resume finish"
  return $rc
}

case "${1:-}" in
  close)    stage_close ;;
  login)    shift; stage_login "$@" ;;
  preflow)  stage_preflow "${2:-0}" ;;
  finish)   stage_finish ;;
  terminal-resume) stage_terminal_resume ;;
  recheck)  stage_recheck ;;
  auto)     shift; cmd_auto "$@" ;;
  auto-resume)
    case "${2:-}" in
      finish)  stage_finish ;;
      recheck) stage_recheck ;;
      *) echo "用法: declare_month.sh auto-resume finish|recheck"; exit 2 ;;
    esac ;;
  *) sed -n '2,20p' "$0"; exit 2 ;;
esac
