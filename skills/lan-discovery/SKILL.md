---
name: lan-discovery
description: "Discover LAN devices via nmap, ARP, and MAC vendor lookups."
category: devops
---

# LAN Device Discovery

Use when the user asks "what devices are on my network", "who is on my LAN", "find devices on my network", or similar network reconnaissance.

## Workflow

### 1. Determine the local subnet

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Look for the main LAN interface (typically `en0` on macOS). The subnet is usually `192.168.x.0/24` or `10.x.x.0/24`.

### 2. Check cached ARP entries

```bash
arp -a | grep -v incomplete | grep "<your subnet prefix>"
```

This shows devices that have recently communicated with this machine. Entries with `(incomplete)` are stale ARP probes — ignore them.

### 3. Ping-scan the subnet

```bash
nmap -sn <subnet>/24 --send-ip
```

This finds all live hosts. `-sn` is a ping scan only (no port scan), so it doesn't need root. The `--send-ip` flag avoids DNS resolution delays.

### 4. Identify devices by MAC vendor

```bash
# Look up the OUI (first 3 bytes) of each MAC address
curl -s "https://api.macvendors.com/<oui>"
```

Key OUI prefixes to know:
- `54:69:90` → **HUAWEI** (routers)
- `f4:fc:49` → **ZTE** (ONT/IPTV/CPE)
- `a4:f9:21` → **Apple, Inc.**
- `36:d0:02` → **Apple** (often MacBooks)
- `56:27:07` or `56:27:7e` → often virtual/randomized (privacy MAC)

Note: `api.macvendors.com` has rate limits (~1 req/sec). Space lookups out with `sleep 1` between calls.

### 5. Identify devices by open ports

```bash
nmap -sT -p 22,80,443,8080,5000,548,139,445,5900 <ip> --send-ip
```

Common port-to-device mappings:
| Ports | Likely device |
|-------|---------------|
| 80, 443 | Router, web interface |
| 22 (SSH) + 5900 (VNC) | Server, Raspberry Pi, NAS |
| 22 (SSH) only | Linux server, dev board |
| 548 (AFP) | Mac file sharing |
| 80, 443, 8080 | Router/AP management interface |
| 139, 445 (SMB) | NAS, Windows file share |
| No open ports | Mobile device (iPhone/Android) in standby |

### 6. Cross-reference with SSH config

```bash
cat ~/.ssh/config
```

SSH Host entries often have `HostName` matching discovered IPs, plus the `User` and `Port` for direct access.

## Pitfalls

- **Privacy MAC addresses** — Apple devices (iOS 14+, macOS 15+) use randomized MACs per network. The OUI lookup may return "Apple, Inc." but won't identify the specific device model.
- **nmap needs root for OS detection** — `nmap -O` returns "TCP/IP fingerprinting requires root privileges" without sudo. Use port scanning as a proxy instead.
- **ARP cache is incomplete** — `arp -a` only shows devices that recently talked to this machine. Always pair with `nmap -sn` for a full scan.
- **Rate-limited MAC APIs** — `api.macvendors.com` is free but rate-limited. Use `sleep 1` between calls for more than 3 lookups, or batch via `sudo arp-scan --local` (which includes vendor strings in its output).
- **`arp-scan` needs root on macOS** — it opens a BPF device. Falls back to `nmap -sn` + `arp -a` without sudo.