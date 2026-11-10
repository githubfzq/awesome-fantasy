---
name: repo-dev-server-bootstrap
description: Clone a GitHub repo and run its dev server in a herdr pane.
version: 1.0.0
metadata:
  hermes:
    tags: [git, clone, dev-server, vitepress, herdr, npm]
    related_skills: [herdr, github]
---

# Clone a repo and serve it

## When to Use

- The user names a GitHub repository and asks to clone it and start its
  documentation or dev server locally (often: “克隆 X 到某目录并启动文档服务”).
- The user then asks to change how that service is exposed (LAN binding,
  different port) — apply the change in the same running pane.
- The repository is already present in the workspace and the user only asks to
  (re)start or re-bind its service — skip step 1 entirely.

Class of task: user names a GitHub repo and asks to clone it into a working
directory, start the project's documentation/dev service per the repo's own
startup instructions, and expose it for them to open.

Order of operations is fixed: clone -> read startup docs -> install -> serve in
a herdr pane -> verify -> report the real URL.

## 0. Is the repo already here?

`ls` / `git -C <dir> status` the candidate directory first. If the project is
already cloned (a common case: the user returns to a repo they worked on
yesterday and asks to “re-run the docs service”), do not re-clone and do not
touch git state — go straight to serving it in a pane.

## 1. Clone (do not assume GitHub is blocked)

Before reaching for SSH or a mirror, check whether one is already configured:

```bash
git config --global --get-regexp 'insteadof|url\..*\.insteadof'
```

A global `url.<mirror>/https://github.com/.insteadof=https://github.com/` rule
means plain `git clone https://github.com/<owner>/<repo>.git` already routes
through the mirror. If it works, stop — do not add more fallbacks.

If the direct clone hangs or fails, escalate in this order: HTTPS -> SSH
(`git@github.com:owner/repo.git`) -> explicit mirror URL (see
`references/git-mirror-fallbacks.md`). Always clone into the directory the
user named, not the cwd.

Find the correct owner/repo from the web when the user gives only a project
name; do not guess an owner.

## 2. Read the project's startup requirements

The repo states its own requirements — read them before running anything:

- `README.md` (and `README.zh.md`) — Quick Start section: install command,
  dev command, expected port, base path.
- `AGENTS.md` — maintained command list and any repo-specific rules.
- `package.json` — `scripts` and `engines` (node version).

Check the runtime version against `engines` (`node -v`, `npm -v`).

## 3. Install dependencies

Run the repo's own install command (`npm install` / `pip install -r ...`).
Audit/vulnerability output is informational — do not run `npm audit fix`, which
mutates the lockfile and is out of scope unless asked.

## 4. Serve it in a herdr pane, to the right

This user wants long-running services visible in a herdr pane, split to the
**right** of the agent's pane, not as agent background processes. See the
`herdr` skill for the full pane workflow; the short form:

```bash
herdr pane list --workspace "$HERDR_WORKSPACE_ID"   # find the pane to split from
herdr pane split <pane-id> --direction right --cwd "<repo-dir>" --no-focus
herdr pane run <new-pane-id> "cd <repo-dir> && npm run dev"
```

Pitfall: `herdr pane focus` takes a direction, not a pane id. To show the
service pane, call `herdr pane focus --direction right --pane <agent-pane-id>`
with the **agent's** pane id — the direction is resolved relative to that
source pane, so passing the service pane id focuses the wrong side.

Pitfall: the startup script may chain a preparation step
(`"dev": "npm run assets:optimize && vitepress dev docs"`), and the preparation
step can take minutes. It is fine to leave it running in the pane; read the
pane output to see when the server itself binds. If you need a specific host
or port, run the underlying binary directly
(`npx vitepress dev docs --host 0.0.0.0 --port 5173`) after the preparation
step instead of fighting npm argument forwarding.

Run the server in the **foreground** of that pane so its output and its
lifetime live in the pane. Read output with
`herdr pane read <pane-id> --source recent-unwrapped --lines N`.

Restart in the same pane (`herdr pane send-keys <pane-id> ctrl+c`, then re-run)
rather than starting a second instance.

## 5. Expose on the LAN when asked

Dev servers bind to 127.0.0.1 by default. To make them reachable from other
machines, restart the same command with the host flag:

- VitePress / Vite: `npm run dev -- --host`
- Next.js: `npm run dev -- --hostname 0.0.0.0` or `next dev -H 0.0.0.0`
- Generic node servers: set `HOST=0.0.0.0`.

Pitfall: npm appends `--` args to the **last** command of the script chain, so
a script like `"dev": "npm run assets:optimize && vitepress dev docs"` receives
`--host` on `vitepress dev docs` only. Confirm the flag actually landed by
reading the pane output — the server prints extra `Network:` lines only when
it is bound to non-loopback interfaces.

Pitfall: an app-level Host allowlist defeats the binding. Frameworks and
hand-written middleware often reject any request whose Host header is not
localhost (403 "serves localhost only"), so a correctly bound server still
refuses LAN clients. Grep the app for `Host`, `hostname`, `127.0.0.1` checks
and middleware that returns 403 before claiming LAN access works; the fix is
usually an explicit allow-remote flag rather than a bind-address change.

Verify from the LAN address, not loopback: `curl http://<host-ip>:<port>/`.
A loopback request passes a localhost-only guard whether or not LAN access
actually works.

## 6. Verify, then report

Do not claim a URL you have not confirmed.

```bash
ss -ltnp | grep <port>                 # bound address: 127.0.0.1 vs *:PORT
curl -s -o /dev/null -w "%{http_code}\n" http://<host>:<port><base-path>/
```

Then read the pane output once more and report:

- the exact base path (VitePress sites under a repo base often serve at
  `/<repo-name>/`, not `/`),
- the loopback URL and the LAN URL,
- the pane id where the service runs.

## Pitfalls

- Check `git config --global --get-regexp insteadof` before declaring GitHub
  unreachable — a mirror is often already wired up, and reporting "GitHub is
  blocked" when it is not wastes the user's time.
- Never report the root URL for a VitePress site with a non-empty base: the
  root returns 404 while the real page works.
- `npm run dev -- --host` on a chained script only forwards to the final
  command; verify via the server's own `Network:` output, not by assumption.
- The agent's own `HERDR_PANE_ID` may be stale (`pane_not_found` from
  `--current`); resolve the pane id from `herdr pane list` and split from an
  explicit id.
