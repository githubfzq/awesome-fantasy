# runit Service Reference

Quick reference for all services currently running under runit on this Termux instance.

## Service Directories

All services live under `/data/data/com.termux/files/usr/var/service/<name>/`

Each service directory contains:
- `run` — executable script that starts the daemon (must use `exec`)
- `log/` — optional log subprocess
- `supervise/` — created automatically by runit when the service starts

## Current Services

| Service | PID | Status | run script |
|---------|-----|--------|------------|
| `sshd` | 15606 | running | `/data/data/com.termux/files/usr/var/service/sshd/run` |
| `ssh-agent` | — | running | `/data/data/com.termux/files/usr/var/service/ssh-agent/run` |
| `hermes-gateway` | 32514 | running | `/data/data/com.termux/files/usr/var/service/hermes-gateway/run` |

## Checking Service Status

```bash
# Check all services at once
sv status sshd
sv status ssh-agent
sv status hermes-gateway

# Verify runsvdir supervisor is alive
ps aux | grep runsvdir
```

Expected runsvdir line:
```
/data/data/com.termux/files/usr/bin/runsvdir /data/data/com.termux/files/usr/var/service
```

## Adding a New Service

```bash
# 1. Create directory structure
mkdir -p /data/data/com.termux/files/usr/var/service/<service-name>/log

# 2. Write the run script (MUST use exec)
cat > /data/data/com.termux/files/usr/var/service/<service-name>/run <<'EOF'
#!/bin/sh
exec <your-command-here>
EOF
chmod +x /data/data/com.termux/files/usr/var/service/<service-name>/run

# 3. runsvdir picks it up immediately — no reload needed
sv status <service-name>
```

## Managing Services

```bash
sv start <service>      # Start a stopped service
sv stop <service>       # Stop a running service
sv restart <service>    # Stop then start
sv once <service>       # Run once and exit (one-shot)
sv cad <service>        # Cancel a one-shot service
```

## Log Files

- Gateway log: `~/.hermes/logs/gateway.log`
- SSH log: typically `/var/log/auth.log` (if configured)
- runit internal logs: visible via `sv status` output

## Useful Paths

```
/data/data/com.termux/files/usr/var/service/       # runit service directory
/data/data/com.termux/files/usr/bin/runsvdir       # runit supervisor binary
/data/data/com.termux/files/usr/bin/sv             # service control command
/data/data/com.termux/files/usr/bin/runit          # runit package
```
