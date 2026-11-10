# Multi-harness credential routing and shared-host isolation

Covers how to give several harnesses on ONE host different OpenViking users,
and how to keep a multi-user Linux box's per-person configs separate.

## The credential file is shared; the plugin sections are not

Every official OV plugin resolves credentials from the SAME file —
`~/.openviking/ovcli.conf` — or from `OPENVIKING_*` env vars. The installer
**rewrites the top-level `api_key`/`user` on every run**, so installing
harnesses in sequence leaves all of them pointing at the LAST one installed.

The fix is the `plugin` section of the same file. The plugin resolves
`ovcli.conf` → `plugin[<harness_key>]` → env override, where `harness_key`
comes from `HARNESS_KEYS` in the plugin's `lib/shared/config-schema.mjs`:

```
claude_code  codex  opencode  dsh  pi  cursor  trae  trae_cn
zcode  kimicode  codebuddy  openclaw
```

Both `claude_code` and `claude-code` spellings resolve to the same section.

Write the sections with a script rather than by hand — one call per host,
idempotent, and it keeps the key out of shell history:

```sh
python3 ov_cli_sections.py ~/.openviking/ovcli.conf ~/.openviking/keys.txt \
  http://<host>:1933 <account> \
  codex=codex claude-code=claude opencode=opencode pi=pi dsh=dsh
```

`ov_cli_sections.py` (see `scripts/ov_cli_sections.py`) reads a
`name=key` file, keeps the top-level values as a fallback for clients that
don't use sections, and writes each section with `url`/`api_key`/`account`/
`user`.

## Verify the split actually took effect

Do not trust the file — query each user and confirm the memory spaces differ:

```sh
for u in codex claude opencode pi dsh shared; do
  curl -s -X POST "$OV/api/v1/search/search" \
    -H "X-API-Key: <REDACTED> "^$u=" keys.txt|cut -d= -f2-)" \
    -H "Content-Type: application/json" \
    -d '{"query":"<something written to one space>","mode":"context"}'
done
```

A user whose space was never written returns `hits=0` — that is the proof of
isolation, not a failure.

## Installer flags and env vars

The unified installer takes `--harness` as a comma list:
`claude, codex, cursor, trae, trae-cn, trae-cli, zcode, kimicode, codebuddy,
opencode, pi, dsh, dsh-desktop, cli`.

Per-harness config roots are honoured through the agents' own env vars, so a
shared Linux account can give each person a private config tree:

| Harness | Env var | Effect |
|---|---|---|
| Codex | `CODEX_HOME` | config, skills, agent home |
| Claude Code | `CLAUDE_CONFIG_DIR` | config + plugin install root |
| DSH | `DSH_HOME` | profiles + global patch (also `--dsh-profile`) |
| pi | `PI_CODING_AGENT_DIR` | extensions + session dir |
| OpenCode | `OPENCODE_CONFIG_DIR` | config dir |

**Set the env var BEFORE running the installer** — it decides where the
plugin lands. Verify after: the plugin must live under the private tree,
not the shared default.

The installer also rewrites `~/.openviking/ovcli.conf` top-level values, so
re-run the section writer after ANY installer run.

## Pitfalls

- **The installer ignores per-user config roots for some harnesses.** pi's
  installer wrote to `~/.pi/agent/extensions/openviking` even with
  `PI_CODING_AGENT_DIR` set to a private path. After installing, move the
  plugin tree into the private dir and leave a symlink at the shared path so
  both launch styles resolve.
- **A shared account means a shared `ovcli.conf`.** Every person on the box
  reads the same file. If isolation matters, each person needs their own
  `OPENVIKING_HOME` (installer env var) rather than relying on sections.
- **A harness without its own section silently falls back to the top-level
  user.** That is the failure mode when you install 5 harnesses and forget
  the sections — they all end up writing to one memory space without any
  error. Count the sections after writing.
- **`claude` is the OV user, `claude-code` is the config section.** They are
  different names; conflating them writes the section under the wrong key
  and the client silently falls back.
