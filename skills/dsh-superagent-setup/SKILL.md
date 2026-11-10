---
name: dsh-superagent-setup
description: Use when installing, running, upgrading or configuring dsh-superagent (DeepSeek's router-worker proactive GitHub coding agent) on a DSH profile.
---

# dsh-superagent

A proactive agent for **one** GitHub repository, packaged as a DeepSeek Harness
bundle. It listens to GitHub (optionally Feishu), turns allowed requests into
Tickets, and runs each Ticket in its own isolated agent session and directory.
Results come back in the original conversation, often as a pull request.

Repo: https://github.com/deepseek-ai/dsh-superagent (MIT research prototype)
Docs live in the checkout under `docs/000-philosophy.md` … `008-cookbook.md`,
read in order. `SETUP.md` is the operator-facing setup checklist.

## Architecture
- **Router** (`dsh-superagent-router` preset) — long-running main session, small tool set, dispatches.
- **Worker** (`dsh-superagent-worker` preset) — one Executor Session per Ticket, own directory, own branch.
- Presets move foreground shell commands to the background after 5 s so workers stay responsive.
- Acceptance modes: `off` / `observe` (default — records only) / `auto`.

## Install (official commands)
```sh
npm install -g @deepseek-ai/dsh@0.2.1-rc.3     # engines.dsh requires ^0.2.1-alpha.2
git clone <repo> dsh-superagent && cd dsh-superagent
pnpm install && pnpm build
dsh superagent --from-default-profile web --dump-config > /dev/null
dsh plugin --profile superagent add "link:$PWD"
```
Then copy `examples/profile.cordis.patch.yml` to
`~/.dsh/profiles/superagent/cordis.patch.yml`, replacing every placeholder
(`stateDir` absolute path, `webserver` host/port).

**Do not** re-run the `--from-default-profile` command on an existing profile —
it replaces the profile and deletes `cordis.patch.yml` (machine config).

## Operate
```sh
scripts/dsh-superagent start | status | stop | restart
scripts/dsh-superagent --profile superagent --respect-stop restart   # preserves an intentional stop
```
Exit codes: 0 healthy · 1 not running / runtime error · 2 a component errored
(restart won't fix) · 3 waiting for setup (needs a person).

## Management API (agents can call it)
`http://127.0.0.1:<port>/orchestrator/api/` with header `x-orchestrator-request: 1`.
Key routes: `GET state`, `GET settings`, `PUT settings/<block>` (body
`{"value":…, "revision":n}`), `POST setup/check`, `GET/PUT prompts`,
`POST executor/pause`, `POST policy-sync/<source id>`.
Blocks: `source:github`, `source:feishu`, `policy`, `eval`, `executor`.

## Isolation
Runs with `danger-full-access` as the operator's OS user. A worker can read the
operator's home dir. The plugin rewrites process-wide PATH and git config, so it
must live in a **separate DSH profile** from the one you work in.

## Pitfalls
- `dsh` resolves a bundle from the **global dsh installation first**, then the
  profile. A stale global copy of the same plugin shadows the profile's newer
  one → "skipping profile bundle … incompatible with dsh X". Fix: upgrade the
  global copy too.
- `dsh plugin add` validates the *currently installed* plugin's peer
  requirements, not the one being installed. To move a profile across a dsh
  major line, run `pnpm add` directly in the profile dir, then upgrade the
  global copy.
- dsh patches REPLACE a row's whole `config` — restate every key the row owns.
