# Hermes Gateway runit Service Template

Copy this template to create a new runit service for Hermes Gateway on Termux.

## File: `/data/data/com.termux/files/usr/var/service/hermes-gateway/run`

```sh
#!/bin/sh
#
# runit service script for Hermes Gateway on Termux
# Must use exec so runit tracks the child PID directly.
#

HERMES_HOME="${HOME}/.hermes"
LOG_DIR="$HERMES_HOME/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Run gateway in foreground; runit will supervise and restart on crash.
exec hermes gateway run >> "$LOG_DIR/gateway.log" 2>&1
```

## Installation Steps

```bash
# 1. Create service directory
mkdir -p /data/data/com.termux/files/usr/var/service/hermes-gateway/log

# 2. Write the run script (use the template above)
# 3. Make executable
chmod +x /data/data/com.termux/files/usr/var/service/hermes-gateway/run

# 4. Verify
sv status hermes-gateway
tail -f ~/.hermes/logs/gateway.log
```

## Managing the Service

```bash
sv start hermes-gateway
sv stop hermes-gateway
sv restart hermes-gateway
sv status hermes-gateway
```

## Notes

- The `exec` prefix is critical — without it, runit cannot track the process.
- Logs append to `~/.hermes/logs/gateway.log`; consider a log rotation strategy for long-running deployments.
- Android may kill background processes when Termux is suspended — restarting Termux re-launches runsvdir and all registered services.
