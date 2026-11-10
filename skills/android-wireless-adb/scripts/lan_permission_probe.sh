#!/usr/bin/env bash
# macOS 15 本地网络权限探测：判别当前进程上下文能否访问局域网目标
# 用法: bash lan_permission_probe.sh <LAN_IP> <PORT>
# 依据: 前台终端/launchd 派生进程应 OK；daemon/后台化进程被拦时 errno=65 且耗时 ~0.000s
# 详见 skill: devops/android-wireless-adb references/macos-local-network-permission.md
IP=${1:-192.168.1.8}
PORT=${2:-8022}
python3 - "$IP" "$PORT" <<'EOF'
import socket, sys, time
ip, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(); s.settimeout(5)
t0 = time.time()
try:
    s.connect((ip, port))
    print(f"ALLOWED  {ip}:{port} (elapsed {time.time()-t0:.3f}s)")
except OSError as e:
    dt = time.time() - t0
    print(f"BLOCKED  {ip}:{port}  errno={e.errno} {e.strerror} (elapsed {dt:.3f}s)")
    if e.errno == 65 and dt < 0.05:
        print("  -> 内核权限层瞬时拒绝 = macOS 本地网络隐私拦截（此进程上下文无权限）")
    elif dt > 2:
        print("  -> 慢速失败 = 真网络问题（ARP/无应答/端口关闭），不是权限拦截")
    else:
        print("  -> 其他 OSError，检查端口与网络")
finally:
    s.close()
EOF
