# cua Computer Server on Parallels Windows 11 — Full Setup Guide

Deep-reference narrative for the `parallels-cua-server-setup` skill. Covers every
command run during the initial build, the exact outputs that signal success or
failure, and *why* each workaround exists. Keep SKILL.md lean; load this when
actually executing the workflow or debugging.

## Environment that this was validated against

| Item | Value |
|------|-------|
| Host | macOS (Apple Silicon), Parallels Desktop installed |
| VM | Parallels "Windows 11", running, user `fanzuquan` logged in |
| VM IP (shared net) | `10.211.55.5` (gateway `10.211.55.1` on Mac `bridge100`) |
| Windows build | 10.0.26200.x (Windows 11) |
| Python in VM | Microsoft Store **3.13** (no `python` on PATH inside `prlctl exec`) |
| cua-computer-server | 0.3.42 (`mcp` extra; requires `>=3.12,<3.14`) |
| Server endpoint | `http://10.211.55.5:8000/mcp` (streamable HTTP) |

## Step 1 — Headless command channel (prlctl bridge)

`prlctl exec` from a non-GUI shell returns exit 253 (no GUI session namespace).
The fix is a file-IPC bridge: a LaunchAgent (`com.user.prlctl-bridge`) running
`agent.sh` inside the `gui/<uid>` domain executes `prlctl` on demand; `call.sh`
drops a request file and polls for the response file. The bridge files live in
`~/.prlctl-bridge/`. Bootstrap pops one macOS password dialog; thereafter
`call.sh` is passwordless.

```bash
CALL=~/.prlctl-bridge/call.sh
$CALL exec "Windows 11" cmd /c "ver"
$CALL exec "Windows 11" cmd /c "ipconfig | findstr IPv4"   # 10.211.55.5
```

If `call.sh list -a` returns nothing useful, the LaunchAgent may not have the GUI
session; check `~/.prlctl-bridge/agent.err`. The agent auto-respawns via
`KeepAlive`.

## Step 2 — Environment probe (what to expect)

```text
ver            -> Microsoft Windows [Version 10.0.26200.x]
ipconfig       -> IPv4 Address . . . . . . . . : 10.211.55.5
python --version -> 'python' is not recognized   (Store alias not inherited)
```

Read the real Python path:

```bash
$CALL exec "Windows 11" cmd /c "reg query HKCU\Software\Python\PythonCore /s"
# path like:
# C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\
```

Use that full path for every `python3.13.exe` invocation.

> If no Python at all: `winget` is absent on this image. Download the installer
> with `curl` and install **per-user** to avoid a headless UAC hang:
> `"%TEMP%\python312.exe" /quiet PrependPath=1 InstallAllUsers=0`
> (3.12 also satisfies cua's `>=3.12,<3.14`; but 3.13 Store edition already
> present is preferred — no reinstall needed).

## Step 3 — Install cua-computer-server

```bash
PY="C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\python3.13.exe"
$CALL exec "Windows 11" cmd /c "\"$PY\" -m pip install cua-computer-server[mcp]"
```

Verify the CLI and its flags:

```bash
$CALL exec "Windows 11" cmd /c "\"$PY\" -m computer_server --help"
# shows: --host (default 127.0.0.1)  --port (default 8000)  --detect-resolution
```

> `--host 0.0.0.0` is mandatory for LAN access; the default binds localhost only.

## Step 4 — Firewall

```bash
$CALL exec "Windows 11" cmd /c "netsh advfirewall firewall add rule name=cua-computer-server dir=in action=allow protocol=TCP localport=8000"
```

## Step 5 — Start in the INTERACTIVE session (the critical fix)

**Do NOT** use `Start-Process -WindowStyle Hidden` or run via a bare `prlctl exec`
foreground — both land the process in **session 0 (Services)**, which has no
desktop, and `computer_screenshot` fails with:

```text
{"content":[{"type":"text","text":"Error calling tool 'computer_screenshot': 'image_data'"}],"isError":true}
```

Confirm the bad state with `tasklist /v` (Session# = 0, "Services"). Fix: inject
into **session 1 (Console)** with PsExec.

```bash
# PsTools (retry the curl if the zip silently fails to land; ~5.2 MB)
$CALL exec "Windows 11" cmd /c "curl -sL --max-time 120 -o C:\pstools.zip https://download.sysinternals.com/files/PSTools.zip && powershell -NoProfile -Command \"Expand-Archive -Path C:\pstools.zip -DestinationPath C:\pstools -Force\""

# stop any session-0 instance
$CALL exec "Windows 11" cmd /c "taskkill /f /im python3.13.exe"

# launch detached into console session 1, logging to file
$CALL exec "Windows 11" cmd /c "C:\pstools\psexec.exe -i 1 -d -accepteula \"$PY\" -m computer_server --host 0.0.0.0 --port 8000 --detect-resolution >> C:\cua_server.log 2>&1"
```

Verify the good state:

```text
tasklist /fi "IMAGENAME eq python3.13.exe" /v
  python3.13.exe  1972  Console  1   ...  NT AUTHORITY\SYSTEM   ...
netstat -ano | findstr :8000
  TCP  0.0.0.0:8000  0.0.0.0:0  LISTENING  1972
```

Session# = **1** and "Console" = correct. (SYSTEM ownership in session 1 is fine;
SYSTEM in session 1 can access the interactive desktop.)

## Step 6 — Mac routing + health check

`bridge100` frequently has **no IPv4** under Parallels shared networking, so the
Mac cannot route to the VM. Assign one (needs sudo / password dialog; lost on
reboot):

```bash
sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0
```

Then (note `--noproxy '*'` — the Mac's `http_proxy` otherwise intercepts LAN IPs):

```bash
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status
# {"status":"ok","os_type":"windows","features":["mcp"]}
```

Smoke-test the MCP screenshot end-to-end:

```bash
python3 scripts/mcp_call.py http://10.211.55.5:8000/mcp computer_screenshot --save win_shot.png --noproxy
# prints: [saved image -> win_shot.png (192297 bytes)]
```

## Step 7 — Register as a remote MCP tool (Mac side)

```bash
claude mcp add cua-win11 --transport http http://10.211.55.5:8000/mcp
```

Available tool families (40+): `computer_screenshot`, `computer_click`,
`computer_type`, `computer_hotkey`, `computer_scroll`,
`computer_get_accessibility_tree`, `computer_run_command`,
`computer_file_read` / `computer_file_write`, etc.

## Reconnect after a Mac reboot

1. `sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0` (bridge100
   IP does not persist).
2. Verify the VM server is still up (`tasklist` shows it in session 1). If the VM
   was restarted, the `psexec -i 1 -d` launch must be repeated (or add a
   logon-time autostart — see "Hardening" below).
3. `curl --noproxy '*' http://10.211.55.5:8000/status`.

## Hardening / production notes

- **No authentication.** `computer_server` exposes screenshots, keystrokes, file
  read/write and a shell to whoever reaches the port. Never bind `0.0.0.0:8000`
  to a public interface. Restrict the Windows firewall rule to the Mac's IP:
  `netsh advfirenet ... remoteip=10.211.55.1`; stop the server when idle.
- **Autostart in session 1:** add a Scheduled Task (`schtasks /create /sc onlogon
  /ru <user> /rl highest`) or a `HKCU\...\Run` entry that runs
  `C:\pstools\psexec.exe -i 1 -d -accepteula <py> -m computer_server ...` so it
  comes up in the interactive session after a VM reboot. (Plain `Start-Process`
  autostart still lands in session 0 — only psexec -i 1 is correct.)
- **Bridged vs Shared networking:** if the VM is switched to Parallels *Bridged*
  mode it gets a real LAN IP (e.g. 192.168.x.x) and the `bridge100` workaround is
  unnecessary, but the session-1 requirement remains unchanged.
