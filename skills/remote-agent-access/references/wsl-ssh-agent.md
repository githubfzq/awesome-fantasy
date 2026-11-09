# Recovering the Windows→WSL SSH agent

Symptom: from WSL, `ssh <remote-host>` returns `Permission denied
(publickey,password)` for hosts that worked earlier, and `ssh-add -l` reports
`The agent has no identities`.

Two independent things can be broken. Diagnose them in order.

## 1. The Windows ssh-agent service is stopped or disabled

WSL's `~/.ssh/agent.sock` is a `socat` bridge to the Windows OpenSSH agent's
named pipe (`//./pipe/openssh-ssh-agent`). If that service is stopped, the
socket still exists and connects, but every identity query returns empty —
which looks exactly like "no keys loaded".

Check the service from WSL:

```sh
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
"$PS" -NoProfile -Command "Get-Service ssh-agent | Select-Object Name,Status,StartType | Format-Table -AutoSize"
```

`Stopped` + `Disabled` is the diagnosis. `Start-Service` from a non-admin
session fails with error 1058 ("service is disabled") — the StartType must be
changed first, and that needs elevation.

Elevate from WSL without asking the user to open a terminal:

```sh
"$PS" -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList \
  '-NoProfile','-Command','Set-Service ssh-agent -StartupType Manual; Start-Service ssh-agent' -Wait"
```

`-Verb RunAs` triggers a UAC prompt the user accepts; the elevated window
closes on its own. If the session is not an administrator at all, check
membership with
`[Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()`.

A restarted agent starts EMPTY. Reload the identities:

```sh
"$PS" -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList \
  '-NoProfile','-Command','& \"$env:WINDIR\System32\OpenSSH\ssh-add.exe\" \"$env:USERPROFILE\.ssh\id_rsa\"' -Wait"
```

Verify on the Windows side: `ssh-add.exe -l` must list the keys, and the WSL
side must see the same list.

## 2. The WSL-side bridge is stale

The `socat` bridge holds a connection to the Windows pipe from the moment it
started. After the Windows agent restarts, the bridge can keep serving an
empty agent until it is restarted.

The user's own helper does this correctly — use it rather than hand-rolling:

```sh
fish -c '. ~/.local/bin/wsl-ssh-agent-forwarder -r'
```

It is a **fish** script (`set -g`, command substitution `(...)`), so `bash -lc`
fails with `set: -g: invalid option`. Run it with `fish`, not bash.

Verify afterwards:

```sh
ssh-add -l          # must list identities
ssh <host> 'echo ok'
```

## Distinguishing this from "the key is wrong"

If `ssh-add -l` lists identities and the remote still refuses, the problem is
the KEY, not the agent: the remote does not accept that key for that user.
Check the remote's `authorized_keys` for the specific public key, and confirm
the login user matches (`ssh user@host` vs the alias's `User` directive).
An alias can carry a `User` that differs from your default, which makes a
working key look broken.

## When the remote needs a dedicated key for a service

An SSH tunnel run by a systemd unit cannot use the agent described above: a
unit's environment has no `SSH_AUTH_SOCK`, and even where it does, the
socket is a per-session temp path. Give the unit its own key pair instead:

```sh
# on the tunnel host
ssh-keygen -t ed25519 -N "" -C "user@purpose" -f ~/.ssh/id_ed25519_<purpose>
# add the .pub to the FAR side's authorized_keys
```

Then in the unit: `IdentityFile=%h/.ssh/id_ed25519_<purpose>` together with
`IdentitiesOnly=yes` so the agent (if present) is not consulted first.
