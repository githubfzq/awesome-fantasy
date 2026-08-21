#!/usr/bin/env bash
# ghdl.sh - GitHub 资源多镜像轮询下载（ghproxy 前缀代理）
# 用法: ghdl.sh <github-url> [输出文件名]
# 环境变量: GHDL_MIRRORS 逗号分隔镜像列表（默认 gh-proxy.com,ghproxy.net,ghfast.top）
set -uo pipefail

URL="${1:?用法: ghdl.sh <github-url> [输出文件名]}"
OUT="${2:-$(basename "$URL")}"
MIRRORS="${GHDL_MIRRORS:-gh-proxy.com,ghproxy.net,ghfast.top}"

[ -f "$OUT" ] && echo "已存在 $OUT（如需重下请先删除）" && exit 0

verify() {
  local f="$1"
  [ -s "$f" ] || return 1
  case "$f" in
    *.tar.gz|*.tgz) tar tzf "$f" >/dev/null 2>&1 ;;
    *.tar.xz)       tar tJf "$f" >/dev/null 2>&1 ;;
    *.zip)          unzip -tq "$f" >/dev/null 2>&1 ;;
    *)              file "$f" | grep -qiE 'executable|archive|data' ;;
  esac
}

IFS=',' read -ra MIRROR_ARR <<< "$MIRRORS"
for m in "${MIRROR_ARR[@]}"; do
  m="${m%/}"
  echo ">> 尝试镜像: $m"
  if curl -fL --connect-timeout 10 --retry 2 -o "$OUT" "${m}/${URL}"; then
    if verify "$OUT"; then
      echo ">> 下载成功并校验通过: $OUT ($(du -h "$OUT" | cut -f1)) <- $m"
      exit 0
    fi
    echo "!! 校验失败（文件不完整），换下一镜像"
    rm -f "$OUT"
  else
    echo "!! 下载失败 (exit=$?)，换下一镜像"
    rm -f "$OUT"
  fi
done

echo "!! 所有镜像均失败。建议：在国内云服务器上直连 gh-proxy.com 下载后 scp 回来。" >&2
exit 1
