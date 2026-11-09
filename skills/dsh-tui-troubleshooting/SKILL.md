---
name: dsh-tui-troubleshooting
description: Use when `dsh tui` / `dsh --profile dsh-tui` / `dsh-tui` errors on WSL — profile-not-found, startup plugin failures, TUI blank or hanging.
---

# dsh TUI troubleshooting (WSL)

## Symptom → cause → fix

### `Error: dsh: profile "tui" does not exist`
`dsh` has NO shipped `tui` profile. Shipped templates are only:
`acp`, `web`, `headless`, `sdk`, `sdk-minimal` (see `PROFILE_TEMPLATES` in
`node_modules/@deepseek-ai/dsh-app-boot/lib/index.js`).

The TUI is a **third-party plugin**, `@deepseek-harness-tui/dsh-tui`, installed
into a profile named **`dsh-tui`** (not `tui`).

Fix:
```sh
dsh plugin --profile dsh-tui add @deepseek-harness-tui/dsh-tui@<version>
```
Then either run `dsh --profile dsh-tui`, or symlink an alias profile:
```sh
ln -sfn dsh-tui ~/.dsh/profiles/tui   # makes `dsh tui` work
```

### `dsh: installation rejected: Plugin ... is incompatible with dsh <ver>`
dsh's plugin manager checks `peerDependencies` against the installed dsh runtime.
Version matrix that matters (`@deepseek-harness-tui/dsh-tui`):
- `0.15.0+` → requires dsh `0.2.0-rc.2+`
- `0.12.0–0.14.1` → require `dsh-host-webserver`/`dsh-deepseek-account` at `0.2.x`
- **`≤0.11.2` → compatible with dsh `0.1.7-rc.x`** ← use this with dsh 0.1.7-rc.2

Alternative if a newer TUI is required: upgrade dsh itself
(`npm install -g @deepseek-ai/dsh@latest`), which also needs the matching TUI peer range.

### `credentials-local: ... .credentials.yaml is readable beyond its owner (mode 644)`
dsh's credential provider refuses world-readable credential files.
```sh
chmod 600 ~/.dsh/.credentials.yaml ~/.dsh/.env
```

### `dsh-tui requires an interactive terminal (stdout must be a TTY)`
Not an error — `dst run` in 0.11.x still goes through the TUI. Use
`script -qec "dst run --json '<prompt>'" /tmp/out.txt` to force a PTY.

## Verifying a TUI run without a human at the keyboard
```sh
cd ~/.dsh/profiles/dsh-tui
timeout 120 script -qec "./node_modules/.bin/dst run --json 'reply with exactly: OK'" /tmp/out.txt
# then read the session log:
zstd -dc ~/.dsh/sessions/*/*/session.v4.jsonl.zstd | tail -c 1500
```
The `replayState.response` field shows `provider` / `model` actually used.

## Provider: point the TUI at the magpie gateway
`~/.dsh/profiles/dsh-tui/cordis.patch.yml` — copy the `llm-pi-ai`,
`agent-default-model` and `web-search-deepseek` blocks from the `web` profile,
and override the TUI app row:
```yaml
- id: dsh-tui
  config:
    provider: magpie
    model: "auto/GLM-5.3-Flash"
    fullscreen: true
    terminalImages: true
    effort: max
    preset: !!js process.env.DSH_TUI_PRESET ?? undefined
    workspace: !!js process.env.DSH_TUI_WORKSPACE_TARGET ?? undefined
    sessionId: !!js process.env.DSH_TUI_RESUME_SESSION ?? undefined
```
**Pitfall:** a dsh patch REPLACES the targeted row's whole `config`. Restating
only `provider` wipes `fullscreen`/`effort`/etc. Always restate every key the
row owns (copy from the bundle's own `cordis.patch.yml`).

## Useful commands
- `dsh --profile dsh-tui --dump-config` — show the composed profile tree (no mount)
- `dsh-tui doctor` — env checks (dsh/pnpm/profile version/key/config files)
- `dsh-tui safe` — read-only diagnostics + repair guidance
- `dsh-tui version` — launcher vs profile version alignment
- dsh startup failures are logged to `~/.dsh/logs/startup-*.log`
