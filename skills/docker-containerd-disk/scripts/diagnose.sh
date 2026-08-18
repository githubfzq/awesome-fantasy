#!/usr/bin/env bash
# Diagnose Docker data-root vs /var/lib/containerd disk usage.
# Read-only: does not delete anything.
set -euo pipefail

echo "=== docker topology ==="
docker info 2>/dev/null | rg -i 'Storage Driver|Docker Root Dir|Runtimes|Server Version' || {
  echo "docker info failed"
  exit 1
}
echo
if [[ -f /etc/docker/daemon.json ]]; then
  echo "=== /etc/docker/daemon.json ==="
  cat /etc/docker/daemon.json
  echo
fi

echo "=== containerd root hint ==="
if [[ -f /etc/containerd/config.toml ]]; then
  rg -n '^\s*#?\s*root\s*=' /etc/containerd/config.toml || echo "(no root= line; default /var/lib/containerd)"
else
  echo "(no /etc/containerd/config.toml)"
fi
echo

CTR_ROOT="${CONTAINERD_ROOT:-/var/lib/containerd}"
echo "=== sizes under ${CTR_ROOT} ==="
if [[ -d "$CTR_ROOT" ]]; then
  sudo du -sh "$CTR_ROOT" 2>/dev/null || du -sh "$CTR_ROOT" 2>/dev/null || true
  sudo du -sh \
    "$CTR_ROOT/io.containerd.content.v1.content" \
    "$CTR_ROOT/io.containerd.snapshotter.v1.overlayfs" \
    2>/dev/null || true
else
  echo "missing $CTR_ROOT"
fi
echo

echo "=== docker system df ==="
docker system df 2>/dev/null || true
echo

echo "=== ctr namespaces / images (moby) ==="
if command -v ctr >/dev/null 2>&1; then
  sudo ctr namespaces ls 2>/dev/null || true
  echo "--- named (non-dangling) ---"
  sudo ctr -n moby images ls 2>/dev/null | awk 'NR==1 || $1 !~ /moby-dangling/' || true
  echo "dangling count: $(sudo ctr -n moby images ls -q 2>/dev/null | grep -c moby-dangling || true)"
  echo "--- snapshot kinds ---"
  sudo ctr -n moby snapshots ls 2>/dev/null | awk 'NR>1{k[$3]++} END{for (i in k) print i, k[i]}' || true
else
  echo "ctr not found"
fi
echo

echo "=== container GraphDriver roots ==="
docker ps -aq 2>/dev/null | while read -r id; do
  docker inspect "$id" --format '{{.GraphDriver.Name}} {{index .GraphDriver.Data "UpperDir"}}' 2>/dev/null
done | awk '{
  drv=$1
  split($2,a,"/")
  root="/" a[2] "/" a[3] "/" a[4] "/" a[5]
  key=drv " " root
  c[key]++
} END{for (k in c) print c[k], k}'
echo

echo "=== mounts referencing containerd snapshotter ==="
if mount 2>/dev/null | rg -q 'io.containerd.snapshotter'; then
  mount | rg 'io.containerd.snapshotter' | head -20
else
  echo "none"
fi
echo

echo "=== Active snapshots vs docker IDs (heuristic) ==="
if command -v ctr >/dev/null 2>&1; then
  mapfile -t DOCKER_IDS < <(docker ps -aq 2>/dev/null || true)
  sudo ctr -n moby snapshots ls 2>/dev/null | awk 'NR>1 && $3=="Active"{print $1}' | while read -r key; do
    short="${key:0:12}"
    hit=0
    for id in "${DOCKER_IDS[@]:-}"; do
      if [[ "$id" == "$short"* ]] || [[ "$short" == "$id"* ]]; then
        echo "MATCH $key -> $id"
        hit=1
        break
      fi
    done
    if [[ "$hit" -eq 0 ]]; then
      echo "ORPHAN_ACTIVE $key"
    fi
  done
fi

echo
echo "Done (read-only)."
