---
name: termux-setup
description: "Termux runit services, gh install, gateway auto-start."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [termux, android]
metadata:
  hermes:
    tags: [termux, android, runit, gateway, setup, sshd, service-management]
---

# Termux Setup Guide

Hermes Agent runs on Termux (Android) with a few quirks compared to desktop Linux. This skill covers installation, service management, and environment gotchas unique to the platform.

## Package Management

Use `pkg` or `apt-get` (Termux mirrors apt syntax):

```bash
# Install gh CLI for GitHub auth (DO NOT use pip — it won't have the binary)
pkg install gh
# or equivalently:
apt-get install gh

# Other useful packages
pkg install ffmpeg        # for voice features
pkg install python        # Python 3.11 is pre-installed in modern Termux
```

`gh` is the recommended GitHub auth tool — see `github-auth` skill for login flow.

## Service Management: runit (not systemd)

Termux ships **runit** via the `runit` package. `runsvdir` watches `/data/data/com.termux/files/usr/var/service/` and manages services exactly like systemd manages unit files — but without init.

### Checking runit status

```bash
# See all managed services
sv status sshd
sv status ssh-agent
sv status hermes-gateway   # once configured (see below)

# The runsvdir supervisor process
ps aux | grep runsvdir
# Expected: /data/data/com.termux/files/usr/bin/runsvdir /data/data/com.termux/files/usr/var/service
```

### Adding a new service (e.g. Hermes Gateway)

Create the service directory and a `run` script. The script **must** use `exec` so runit tracks the child PID directly.

```bash
# 1. Create the service directory structure
mkdir -p /data/data/com.termux/files/usr/var/service/hermes-gateway/log

# 2. Write the run script
cat > /data/data/com.termux/files/usr/var/service/hermes-gateway/run <<'EOF'
#!/bin/sh
HERMES_HOME="/data/data/com.termux/files/home/.hermes"
LOG_DIR="$HERMES_HOME/logs"
mkdir -p "$LOG_DIR"
exec hermes gateway run >> "$LOG_DIR/gateway.log" 2>&1
EOF
chmod +x /data/data/com.termux/files/usr/var/service/hermes-gateway/run

# 3. runsvdir picks it up automatically — no daemon reload needed
sv status hermes-gateway
```

### Managing services

```bash
sv start hermes-gateway    # start
sv stop hermes-gateway     # stop
sv restart hermes-gateway  # restart
sv status hermes-gateway   # check status
```

**Critical:** Do NOT mix `nohup … &` or `systemctl` with runit. Use only `sv` commands or let the agent start gateway via `hermes gateway run` (foreground/background tool).

## Gateway on Termux

```bash
# Check status
hermes gateway status

# Start in foreground (for manual testing)
hermes gateway run

# The runit service handles auto-restart on crash — preferred for production
```

Termux-specific notes:
- `hermes gateway install` prints: *"Gateway service installation is not supported on Termux. Run manually: hermes gateway"*
- Android may kill background processes when Termux is suspended in the background. Restarting Termux re-launches `runsvdir` and all registered services.
- The gateway log accumulates at `~/.hermes/logs/gateway.log`; rotate manually if needed.

## Environment Notes

| Quirk | Detail |
|-------|--------|
| No systemd | Use runit instead (see above) |
| `pip` may use Python 3.11, `python3` may use 3.14 | Hermes venv is independent; don't mix `pip install` with the Hermes venv |
| `$HOME` = `/data/data/com.termux/files/home` | All `~/.hermes` paths resolve here |
| No `sudo` | All packages are user-installed via `pkg`/`apt-get` |
| Background jobs survive only while Termux is active | Use runit for services that need auto-restart |
| `TERMINAL_CWD` env var is deprecated | Move to `config.yaml` → `terminal.cwd` |

## Quick Reference: Common Commands

```bash
# Package management
pkg list-installed
pkg search <name>
pkg install <name>

# runit service management
sv status <service>
sv start <service>
sv stop <service>
ls /data/data/com.termux/files/usr/var/service/

# Hermes
hermes gateway status
hermes skills tap add owner/repo
hermes doctor
```

## ADB / Root / su

For ADB remote-debugging detection, enabling tcpip 5555 with root, and the "Magisk installed but `su` says not found" DenyList trap, see `references/adb-root-debugging.md`. MIUI gotcha: `pm list packages` is unreliable (can return empty or hide installed apps) — verify app presence with `pm path <pkg>` instead.

## Related Files

- `references/runit-reference.md` — full runit service management reference with current services and commands
- `references/adb-root-debugging.md` — ADB state detection, root 5555 enablement, Magisk DenyList/su troubleshooting
- `templates/gateway-service-run.sh` — ready-to-copy run script template for adding a new service
