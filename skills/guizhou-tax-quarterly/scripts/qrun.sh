#!/bin/bash
# qrun.sh — 贵州电子税务局季度申报一键入口
# 用法：
#   bash qrun.sh list          # 确保登录 + 列出待办（不动状态）
#   bash qrun.sh vat           # 增值税+工会经费
#   bash qrun.sh biz_a         # 经营所得 A 表 ×2
#   bash qrun.sh fin           # 财务报表季报
#   bash qrun.sh all [--yes]   # 全部（--yes = 事先授权，提交不再逐项确认）
set -e
PY=/Users/fanzuquan/.workbuddy/binaries/python/envs/default/bin/python
DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[qrun $(date +%H:%M:%S)] $*"; }

# 1) 确保登录（CDP 模式：必要时拉起 Chrome，等你人工登录）
log "step1: 确保登录态…"
if ! "$PY" "$DIR/login_cdp.py"; then
  log "登录未完成，终止。请重跑 bash qrun.sh $*"
  exit 1
fi

# 2) 执行申报
MODE="${1:-list}"; shift || true
case "$MODE" in
  list) log "列出待办…"; "$PY" "$DIR/declare.py" --list ;;
  vat|biz_a|fin) log "办理 $MODE …"; "$PY" "$DIR/declare.py" --only "$MODE" "$@" ;;
  all)  log "全部办理…"; "$PY" "$DIR/declare.py" --all "$@" ;;
  *) echo "用法: bash qrun.sh [list|vat|biz_a|fin|all] [--yes]"; exit 1 ;;
esac
