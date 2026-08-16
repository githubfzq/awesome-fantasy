#!/bin/bash
#
# setup_prlctl_bridge.sh — one-shot Mac-side setup of a passwordless file-IPC
# bridge into a Parallels VM, so `prlctl exec` works from a non-GUI session.
#
# Why: `prlctl` from a headless shell returns exit 253 because it needs the GUI
# session namespace. We run a tiny agent inside the GUI session (via a
# launchd LaunchAgent in the gui/<uid> domain) that executes prlctl on demand
# and returns the result through request/response files. The first bootstrap
# pops a macOS password dialog; afterwards every call is passwordless.
#
# Usage:
#   bash setup_prlctl_bridge.sh
# Then:
#   ~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "ipconfig"
#
set -euo pipefail

BRIDGE="$HOME/.prlctl-bridge"
PRLCTL="/Applications/Parallels Desktop.app/Contents/MacOS/prlctl"
LABEL="com.user.prlctl-bridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
UIDN="$(id -u)"

mkdir -p "$BRIDGE"

# ---- agent.sh (runs prlctl on request, inside the GUI session) ----
cat > "$BRIDGE/agent.sh" <<'AGENT'
#!/bin/bash
BRIDGE_DIR="$HOME/.prlctl-bridge"
REQ="$BRIDGE_DIR/req"; RES="$BRIDGE_DIR/res"
PRLCTL="/Applications/Parallels Desktop.app/Contents/MacOS/prlctl"
mkdir -p "$BRIDGE_DIR"; rm -f "$REQ" "$RES"
while true; do
  if [ -f "$REQ" ]; then
    args=()
    while IFS= read -r line; do [ -n "$line" ] && args+=("$line"); done < "$REQ"
    rm -f "$REQ"
    if [ ${#args[@]} -gt 0 ]; then output=$("$PRLCTL" "${args[@]}" 2>&1); code=$?; else output="(no args)"; code=1; fi
    tmp="$RES.tmp.$$"; printf '%d\n%s' "$code" "$output" > "$tmp"; mv -f "$tmp" "$RES"
  fi
  sleep 0.3
done
AGENT

# ---- call.sh (client: drop request, poll for response) ----
cat > "$BRIDGE/call.sh" <<'CALL'
#!/bin/bash
BRIDGE_DIR="$HOME/.prlctl-bridge"; REQ="$BRIDGE_DIR/req"; RES="$BRIDGE_DIR/res"
[ $# -eq 0 ] && { echo "Usage: $0 <prlctl args...>" >&2; exit 2; }
rm -f "$RES"; printf '%s\n' "$@" > "$REQ"
for i in $(seq 1 3000); do [ -f "$RES" ] && break; sleep 0.2; done
[ ! -f "$RES" ] && { echo "ERROR: timeout (is LaunchAgent running? check ~/.prlctl-bridge/agent.err)" >&2; exit 1; }
code=$(head -1 "$RES"); output=$(tail -n +2 "$RES"); rm -f "$RES"
printf '%s' "$output"; exit "${code:-0}"
CALL

chmod +x "$BRIDGE/agent.sh" "$BRIDGE/call.sh"

# ---- LaunchAgent plist (loaded into the gui/<uid> domain) ----
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${BRIDGE}/agent.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${BRIDGE}/agent.log</string>
  <key>StandardErrorPath</key>
  <string>${BRIDGE}/agent.err</string>
</dict>
</plist>
PLIST

# ---- bootstrap into the GUI session (one password dialog) ----
echo "Bootstrapping LaunchAgent (macOS will ask for your login password)..."
osascript -e "do shell script \"launchctl bootstrap gui/${UIDN} ${PLIST}\" with administrator privileges"

# give it a moment, then smoke-test
sleep 2
if "$BRIDGE/call.sh" list -a >/dev/null 2>&1; then
  echo "OK: bridge is live. Try: $BRIDGE/call.sh exec \"Windows 11\" cmd /c \"ipconfig\""
else
  echo "WARN: bridge did not respond. Check $BRIDGE/agent.err and ensure the password dialog was approved."
fi
