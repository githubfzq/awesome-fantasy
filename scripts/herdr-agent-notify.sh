#!/usr/bin/env bash
set -euo pipefail

# Listen to remote herdr agent status changes and notify Windows via notify-send-wsl.
#
# Environment overrides:
#   HERDR_SSH_HOST        SSH host alias (default: herdr)
#   HERDR_SESSION         Named herdr session
#   HERDR_SOCKET_PATH     Explicit socket path on the remote/local host
#   HERDR_NOTIFY_CMD      Notification command (default: notify-send-wsl)
#   HERDR_NOTIFY_ON       Comma-separated statuses to notify on
#   HERDR_RECONNECT_DELAY Reconnect delay in seconds
#
# Examples:
#   ./scripts/herdr-agent-notify.sh
#   HERDR_SSH_HOST=herdr ./scripts/herdr-agent-notify.sh --notify-on blocked,done
#   HERDR_SESSION=work ./scripts/herdr-agent-notify.sh --dry-run

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/herdr-agent-notify.py" "$@"
