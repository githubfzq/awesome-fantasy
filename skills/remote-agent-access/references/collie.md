# Collie: private mobile access and multi-session diagnosis

Validated with Collie 1.25.1 and Herdr 0.9.x. These are version-scoped observations; use the installed help and embedded docs as the operational reference.

Sources:
- https://colliepwa.dev/zh/install
- https://colliepwa.dev/zh/docs/crew
- https://colliepwa.dev/zh/docs/configure
- https://colliepwa.dev/zh/docs/voice-and-push
- https://colliepwa.dev/zh/docs/security

## Installation and runtime topology

A standalone release binary can mirror Herdr; it need not be installed as a Herdr plugin. The plugin and standalone routes can have different configuration directories. `collie doctor` identifies the active configuration. Common standalone configuration is `~/.config/collie/.env`, state is `~/.local/state/collie/`.

Typical lead configuration:

```dotenv
COLLIE_MUX=herdr
COLLIE_MULTI_SESSION=on
COLLIE_TRUSTED_USER=<actual-tailnet-login>
```

Discover the login from current Tailscale status rather than guessing an email address. On Linux, configure `sudo tailscale set --operator=<user>` if needed. `collie start` writes a user service and publishes Tailscale Serve; inspect the existing mappings before changing them. Verify HTTPS `/api/health`, `tailscale serve status`, and `systemctl --user is-active collie`. Check `loginctl show-user <user> -p Linger` for operation after SSH logout.

Herdr's saved machine list and Collie's crew are independent. `collie crew add <ssh-host>` provisions and enrolls members over SSH. Where downloads must be staged separately, install first, then use the manual enrollment path rather than racing an automatic installer against manual writes:

```sh
collie crew invite | ssh <member> '<absolute-collie> crew join https://<lead-name> - --address <member-overlay-ip>:8787 --label <label>'
collie restart
collie crew status --json
```

`invite` and enrollment change the roster; follow the printed restart instructions. Never put raw enrollment tokens on command lines. Member mode uses pinned mutual TLS and publishes no browser front door. Verify the member actually listens on the advertised endpoint. A member still bound to 127.0.0.1 cannot be reached through its overlay IP. For a deliberate overlay bind, the validated configuration required both `COLLIE_HOST=<member-overlay-ip>` and `COLLIE_ALLOW_NON_LOOPBACK_BIND=1`; restrict it to that private IP and verify the crew TLS boundary. Do not use a wildcard bind as a generic repair.

## Member reachable only over SSH

A validated fallback used two loopback forwards maintained by a user systemd service:

```ini
[Unit]
Description=SSH transport for a terminal bridge member
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=SSH_AUTH_SOCK=<actual-stable-agent-socket>
ExecStart=/usr/bin/ssh -N -T -o BatchMode=yes -o ForwardAgent=no -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -L 127.0.0.1:18789:127.0.0.1:8787 -R 127.0.0.1:18787:127.0.0.1:8787 <member-ssh-alias>
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

Choose unused ports. The member joins lead `http://127.0.0.1:18787` using `--insecure` only because this HTTP hop is confined to the authenticated SSH tunnel; advertise member `127.0.0.1:18789` as seen by the lead. The member itself stays on loopback, and its crew listener still uses pinned TLS. Verify both tunnel directions and the crew roster. Explicitly document dependence on the unlocked SSH agent after host reboot. Member-side allowlist configuration may be needed without Tailscale; use current docs and allow only required hosts, never disable the Host gate globally.

## Named session missing from the phone

Reproduction pattern: a remote machine has both `default` and a named session. The default has no agents, while the named session has the user's development panes. The dashboard initially shows only primary-session panes from that member even though discovery has found the named session.

1. On the intended host, run `herdr session list` and `herdr --session <name> status`. Confirm the exact socket and inspect a known workspace/pane without restarting it.
2. Confirm Collie's active config enables `COLLIE_MULTI_SESSION=on`.
3. `collie sessions --all --json` can enumerate panes from a non-primary remote session even when the default dashboard omits them. Its `session` field can mean whether an agent journal session is known (`yes`/`no`), not the Herdr session name. Do not use that field as proof of the selected multiplexer session.
4. Read `/api/snapshot` and inspect the `sessions` registry: `{name,isPrimary,reachable,agents,host}`. A reachable named entry proves discovery, not display. `crew status` pane counts may cover a different scope than all-session enumeration; do not force them to match.
5. Browser page URLs use `?h=<crew-member-id>&s=<herdr-session-name>`. API calls use `?host=<crew-member-id>&session=<herdr-session-name>`. These parameter names are deliberately different.
6. In the UI select the machine in the header, then its session selector. The session menu offers `All sessions`, `default`, and discovered named sessions. Validate a known pane label after selection. A direct URL is `https://<lead>/?h=<member>&s=<session>` with values URL encoded.

A validated browser check compared the normal dashboard and this explicit URL, asserted the desired pane text, and opened the session menu. No Herdr restart or upgrade was necessary. A stale Herdr binary is not itself evidence that it caused the missing view.

### Authorized local snapshot read

In this version the bridge's owner-only `local-secret` file supplies a read-only Bearer credential. With a configured trusted Tailscale user, a loopback request also needed that identity header or returned `403 identity required`. Distinguish this from `device not paired`.

```python
from pathlib import Path
from urllib.request import Request, urlopen
import json
secret = <REDACTED> / '.local/state/collie/local-secret').read_text().strip()
request = Request(
    'http://127.0.0.1:8787/api/snapshot?host=<member>&session=<name>',
    headers={
        'Authorization': 'Bearer ' + secret,
        'Tailscale-User-Login': '<configured-trusted-login>',
    },
)
with urlopen(request, timeout=15) as response:
    snapshot = json.load(response)
print(snapshot['sessions'])
```

Use this only on the authorized local bridge host. Never expose the local secret, copy it to a phone, or use it as a write credential. Read exact HTTP error bodies rather than guessing the authorization scheme. For browser diagnosis, a temporary request interceptor can attach these headers only to same-origin API requests, without pairing a diagnostic browser or using an existing phone's token.

## iPhone pairing and push verification

iOS Web Push requires iOS 16.4+, trusted HTTPS, Home Screen installation, launch through its icon, pairing in that app's own storage, and notification permission. Pairing in a Safari tab does not automatically pair the installed app.

```sh
collie pair --json
collie devices list
collie push-keys
collie restart
collie push list
collie push-test 'Connection test' 'Check the phone and open the relevant agent.'
```

Generate VAPID keys before the phone subscribes and do not rotate them casually. `Needs input` is normally on; `Finished` is normally off. State-transition completion includes interrupted agents. A successful push-test reports submission, while phone receipt still needs user confirmation.

For duplicate pairing records, revoke the exact unwanted label with `collie devices revoke <label>`, then list devices and push subscriptions again. Do not clear all push subscriptions or revoke the retained phone as a cleanup shortcut.

## Boot splash

`Connecting to the herd…` is literal HTML in the initial boot splash. If it persists, inspect module/CSS requests and JavaScript console errors before investigating agent detection. The original loading report resolved before a browser cause was established; no particular Safari incompatibility was proven. Stop that investigation when the user reports entering the pairing screen.
