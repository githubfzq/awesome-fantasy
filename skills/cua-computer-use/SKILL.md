---
name: parallels-cua-server-setup
description: "Install and run the cua Computer Server (cua-computer-server[mcp]) inside a Parallels Windows 11 VM so it can be driven remotely over the LAN from the Mac host via MCP over HTTP. Use when setting up computer-use or UI automation against a Windows machine in Parallels, operating a Windows VM headlessly, exposing computer_screenshot / computer_click / computer_type / computer_run_command over the network, or troubleshooting a cua-computer-server that returns image_data or screenshot errors. Captures the non-obvious must-run-in-the-interactive-session (session 1) not session-0-service fix plus the Mac bridge100 routing workaround."
agent_created: true
---

# Parallels cua Computer Server Setup

## Overview

This skill turns a Parallels Windows 11 VM into a remotely drivable "computer"
exposed through cua's `computer_server` MCP endpoint (e.g. `http://VM_IP:8000/mcp`).
The Mac host reaches it over the LAN and can screenshot, click, type, read the
accessibility tree, run commands, and read/write files on the Windows desktop —
all from outside the VM.

The hard-won lessons baked into this skill:

1. **Session isolation is the #1 failure mode.** `computer_server` must run in the
   *interactive logon session* (Windows **session 1 / "Console"**) to capture the
   desktop. Launching it with `Start-Process` / as a service lands it in
   **session 0 (Services)**, which has no desktop — `computer_screenshot` then
   fails with `Error calling tool 'computer_screenshot': 'image_data'`. Inject it
   into session 1 with `psexec -i 1 -d`.
2. **Mac → VM routing needs `bridge100` to have an IPv4.** Parallels shared
   networking often leaves `bridge100` without an IP; the Mac cannot route to the
   VM until `sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0`.
3. **Bypass the Mac HTTP proxy** when testing (`curl --noproxy '*'`), otherwise
   requests to `10.211.55.5` time out through the local proxy.

## When to use

- "在虚拟机里装 Computer Server" / "set up cua computer server in the Windows VM"
- "远程操作 Windows 虚拟机" / drive a Parallels Windows VM over the LAN
- Screenshot/click/type against a Windows desktop from the Mac via MCP
- Debugging `computer_screenshot` returning `'image_data'` or empty results
- Reconnecting after the Mac reboots (bridge100 IP is lost on reboot)

## Prerequisites

- Parallels Desktop installed on the Mac; a Windows 11 VM exists and is running.
- The VM uses Parallels **Shared Network** (default) → VM gets `10.211.55.x`,
  Mac side is `10.211.55.1` on `bridge100`.
- The user is logged into the Windows VM interactively (so a real desktop exists
  in session 1).
- Mac has `osascript` admin rights available (for the one-time `bridge100` IP and
  the prlctl bridge bootstrap, which pop a password dialog).

## Workflow

### Step 1 — Establish a headless command channel into the VM

`prlctl exec` from a non-GUI session returns exit code 253. Use the file-IPC
bridge defined in `scripts/setup_prlctl_bridge.sh`, which:

- Writes `~/.prlctl-bridge/agent.sh` (a `launchd` KeepAlive LaunchAgent that runs
  `prlctl` inside the GUI session namespace via `launchctl bsexec GUI_PID
  chroot -u UID -g GID / ...`) and `~/.prlctl-bridge/call.sh` (a client that
  drops a request file and polls for the result).
- Bootstraps once with `osascript ... with administrator privileges` (password
  dialog), then every later `call.sh exec "Windows 11" cmd /c "..."` is
  passwordless.

After setup, all VM commands use:

```bash
CALL=~/.prlctl-bridge/call.sh
$CALL exec "Windows 11" cmd /c "ipconfig | findstr IPv4"
```

### Step 2 — Verify VM identity, Python, and network

```bash
$CALL exec "Windows 11" cmd /c "ver"
$CALL exec "Windows 11" cmd /c "ipconfig | findstr IPv4"   # expect 10.211.55.5
```

Python notes for this VM:

- Windows here ships **Python 3.13 via Microsoft Store**. The `python` /
  `python3.13` command is NOT on PATH inside a headless `prlctl exec` session
  (App Execution Aliases are not inherited). Use the full path:
  `C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_VERSION_x64__qbz5n2kfra8p0\python3.13.exe`
  (read the exact folder with `reg query HKCU\Software\Python\PythonCore /s` or
  `dir "%LOCALAPPDATA%\Microsoft\WindowsApps\python*.exe"`).
- `cua-computer-server` requires `>=3.12,<3.14`, so 3.13 is fine — no need to
  install 3.12.
- If no Python at all: download the installer with `curl` (winget is absent on
  this image) and install with `InstallAllUsers=0 PrependPath=1` to avoid a UAC
  prompt that hangs headless (`/quiet` alone defaults to AllUsers and silently
  fails with no file on disk).

### Step 3 — Install the server

```bash
PY="C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\python3.13.exe"
$CALL exec "Windows 11" cmd /c "\"$PY\" -m pip install cua-computer-server[mcp]"
```

Confirm: `"$PY" -m computer_server --help` shows `--host` / `--port`
(defaults bind to `127.0.0.1`, so `--host 0.0.0.0` is required for LAN).

### Step 4 — Open the firewall

```bash
$CALL exec "Windows 11" cmd /c "netsh advfirewall firewall add rule name=cua-computer-server dir=in action=allow protocol=TCP localport=8000"
```

### Step 5 — Start the server in the INTERACTIVE session (critical)

Do **not** use `Start-Process` (lands in session 0). Use PsExec to inject into
session 1:

```bash
# first time only: download PsTools (download.sysinternals.com is reachable; retry if curl silently drops the file)
$CALL exec "Windows 11" cmd /c "curl -sL --max-time 120 -o C:\pstools.zip https://download.sysinternals.com/files/PSTools.zip && powershell -NoProfile -Command \"Expand-Archive -Path C:\pstools.zip -DestinationPath C:\pstools -Force\""

# kill any session-0 instance if present
$CALL exec "Windows 11" cmd /c "taskkill /f /im python3.13.exe"

# launch into console session 1, detached, logging to a file
$CALL exec "Windows 11" cmd /c "C:\pstools\psexec.exe -i 1 -d -accepteula \"$PY\" -m computer_server --host 0.0.0.0 --port 8000 --detect-resolution >> C:\cua_server.log 2>&1"
```

Verify it is in session 1 (not Services):

```bash
$CALL exec "Windows 11" cmd /c "tasklist /fi \"IMAGENAME eq python3.13.exe\" /v"   # Session# = 1, Console
$CALL exec "Windows 11" cmd /c "netstat -ano | findstr :8000"
```

### Step 6 — Route the Mac to the VM and verify

```bash
# one-time (lost on reboot): give bridge100 an IPv4
sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0

# health check (bypass proxy!)
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status
# → {"status":"ok","os_type":"windows","features":["mcp"]}
```

Use `scripts/mcp_call.py` to exercise a tool end-to-end (e.g. a screenshot):

```bash
python3 scripts/mcp_call.py http://10.211.55.5:8000/mcp computer_screenshot
```

### Step 7 — Register as a remote MCP tool on the Mac (optional)

```bash
claude mcp add cua-win11 --transport http http://10.211.55.5:8000/mcp
```

## Gotchas (read before debugging)

- **`'image_data'` screenshot error** → server is in session 0. Re-launch with
  `psexec -i 1 -d`. Confirm via `tasklist /v` that Session# = 1 and "Console".
- **Mac cannot reach 10.211.55.5** → `bridge100` has no IPv4. Run the `ifconfig`
  command in Step 6 (needs sudo / password dialog).
- **curl to VM times out** → local `http_proxy` is intercepting LAN traffic. Add
  `--noproxy '*'`.
- **`python` not found in VM** → use the full WindowsApps path (Step 2).
- **Server dies when the exec that started it ends** → always launch via
  `psexec -i 1 -d` (detached), never a bare `prlctl exec` foreground command.
- **No auth** → `computer_server` exposes screenshots, keystrokes, file read/write
  and shell to the whole subnet. Restrict the firewall rule to the Mac's IP, stop
  the server when idle, and never expose `0.0.0.0:8000` to the public internet.

## Resources

- `scripts/setup_prlctl_bridge.sh` — one-shot Mac-side setup of the passwordless
  `prlctl` file-IPC bridge into the VM (creates agent + call client + LaunchAgent).
- `scripts/mcp_call.py` — minimal MCP-over-HTTP client to `initialize` and call any
  tool on the cua `/mcp` endpoint; defaults to `computer_screenshot` for a quick
  smoke test and can decode/save returned images.
- `references/setup-guide.md` — full narrative with every command, exact outputs,
  and the rationale behind each workaround, for deep-reference while working.
