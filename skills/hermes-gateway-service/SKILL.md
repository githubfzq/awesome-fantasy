---
name: hermes-gateway-service
description: Use when gateway fails to start or stay running as service.
---

# Hermes Gateway Service Management

## Trigger
Use when:
- Setting up Hermes gateway as a launchd/systemd service
- Gateway fails to start or stay running
- Troubleshooting "another instance running" errors
- Cleaning up a conflicting old gateway (OpenClaw, etc.)
- Feishu/Lark messages not arriving despite WebSocket connected
- Investigating `LastExitStatus` or `spawn scheduled` state

## 1. Install as Service

```bash
# Install as user-level launchd service (auto-start at login, auto-restart on crash)
hermes gateway install

# Verify
hermes gateway status
```

Creates `~/Library/LaunchAgents/ai.hermes.gateway.plist` with:
- `RunAtLoad: true` — starts at login
- `KeepAlive: true` — restarts on crash
- `ThrottleInterval: 30` — 30s minimum respawn delay
- `ExitTimeOut: 25` — graceful drain window

### Manual start/stop via launchctl
```bash
# Bootstrap (load + start)
launchctl bootstrap gui/501 ~/Library/LaunchAgents/ai.hermes.gateway.plist

# Bootout (unload + stop)
launchctl bootout gui/501/ai.hermes.gateway

# Inspect state
launchctl print gui/501/ai.hermes.gateway
```

## 2. Check Gateway Status

```bash
hermes gateway status
```

| Status Output | Meaning |
|---|---|
| `✓ Gateway is running (PID: N)` | Manual/foreground run |
| `✓ Gateway is supervised by launchd (PID: N)` | Running as launchd service |
| `state = spawn scheduled` | Launchd trying to start but process keeps dying |
| `LastExitStatus = 19968` | Previous run exited with error |
| `✗ Gateway is not running` | No gateway process |

## 3. Troubleshooting Launchd Service Failures

### 3.1 Root-owned gateway.error.log
**Symptom:** `launchctl print` shows `state = spawn scheduled`, `LastExitStatus` is non-zero. Process never appears in `ps`.

**Cause:** `~/.hermes/logs/gateway.error.log` was created by a previous `sudo` or system-wide launchd run and is owned by `root`. The user-level launchd (gui/501) cannot write to it.

**Fix:**
```bash
sudo rm ~/.hermes/logs/gateway.error.log
launchctl bootout gui/501/ai.hermes.gateway
launchctl bootstrap gui/501 ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

### 3.2 Deprecated .env settings
**Symptom:** Gateway starts but logs show deprecated env warnings.

**Fix:** Remove from `~/.hermes/.env`:
```bash
sed -i '' '/^MESSAGING_CWD=/d' ~/.hermes/.env
sed -i '' '/^TERMINAL_CWD=/d' ~/.hermes/.env
```

### 3.3 "Another instance running"
**Symptom:** `hermes gateway run` says another instance is already running.

**Fix:**
```bash
pkill -f "hermes gateway run"
sleep 2
hermes gateway run --replace
```

## 4. OpenClaw Gateway Conflict

### Detection
The old OpenClaw gateway may still be running and intercepting Feishu messages even though Hermes gateway is connected.

```bash
# Check for OpenClaw process
ps aux | grep openclaw

# Check for OpenClaw launchd service
launchctl list | grep openclaw
ls ~/Library/LaunchAgents/ | grep -i claw
```

### Cleanup
```bash
# 1. Stop the launchd service
launchctl bootout gui/501/ai.openclaw.gateway

# 2. Remove the plist so it doesn't restart on reboot
rm ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 3. Kill any remaining process
pkill -f openclaw

# 4. Verify no OpenClaw gateway is listening on its port
lsof -i :18789
```

### Verification
After cleanup, restart Hermes gateway and test:
```bash
hermes gateway run --replace
# Monitor for incoming messages
tail -f ~/.hermes/logs/gateway.log
```

## 5. Feishu DNS Issues

**Symptom:** WebSocket connects (`wss://msg-frontier.feishu.cn/ws/v2?...`) but REST API calls fail with:
```
Failed to resolve 'open.feishu.cn' ([Errno 8] nodename nor servname provided, or not known)
```

**Diagnostics:**
```bash
nslookup open.feishu.cn
ping -c 1 -t 3 open.feishu.cn
```

## Pitfalls
- `hermes gateway install` creates a plist with `--replace` flag — this is fine
- If you manually ran `hermes gateway run` first, kill it before starting the service
- Root-owned error log files silently prevent launchd from starting the gateway
- An old OpenClaw gateway will intercept Feishu messages even when Hermes gateway is connected — always check for it