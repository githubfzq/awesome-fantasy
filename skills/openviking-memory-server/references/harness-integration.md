# Connecting agent harnesses

## Hermes

### Official catalog plugin

The catalog entry `openviking` (community tier, maintained by volcengine) lives in `plugin-catalog/openviking.yaml` and points at `examples/hermes-plugin` in the OV repo at a pinned SHA. `hermes plugins install openviking --enable` handles it when GitHub is reachable.

The plugin declares `hooks: [on_session_end]` and provides `viking_*` tools (including `viking_remember`), commits pending tokens in the background, and produces a recall digest.

### When the host cannot reach GitHub

The installer uses libgit2, which ignores git's `url.<mirror>.insteadOf` config — setting that alone does **not** help. Two working routes:

**Route A — mirror URL + pinned SHA** (works when the plugin source scan passes):

```sh
hermes plugins install "https://<mirror>/https://github.com/volcengine/OpenViking.git" \
  --ref <full-40-char-sha> --yes-deps --enable
```

`--ref` requires the full 40-character SHA; a short SHA is rejected.

**Route B — clone by hand and adopt** (bypasses the installer's source scan, which blocks community-tier sources):

```sh
mkdir -p ~/.hermes/plugins/openviking && cd ~/.hermes/plugins/openviking
git init -q .
git remote add origin https://github.com/volcengine/OpenViking.git
# copy the plugin subdir's files in, then commit
hermes plugins adopt openviking
hermes plugins enable openviking
```

`adopt` needs Hermes ≥ 0.22 (it does not exist in 0.20.x). Route A also needs the plugin's `requires_hermes` satisfied — the catalog entry requires ≥ 0.21.4.

### Credential contract

Provider env vars live in the **active profile's** `.env` (`~/.hermes/.env` for the default profile, `~/.hermes/profiles/<name>/.env` otherwise):

```
OPENVIKING_ENDPOINT=http://<host>:1933
OPENVIKING_API_KEY=<user_key>
OPENVIKING_ACCOUNT=<account>
OPENVIKING_USER=<user>
OPENVIKING_AGENT=<peer id>
```

With `OPENVIKING_API_KEY` set, OV derives account/user identity from the key itself. Also distribute `~/.openviking/ovcli.conf` (url + api_key + account + user) for the unified installers and any plugin that reads it.

Select the provider:

```sh
hermes config set memory.provider openviking
hermes memory status        # verify: Provider: openviking, Status: available
```

Only one external provider can be active at a time; the built-in MEMORY.md/USER.md store stays active alongside it.

### Verifying the capture path

Run a real oneshot turn and confirm the model actually calls `viking_remember`:

```sh
hermes chat --oneshot -q "请记住这条信息：…"
```

Look for a `Viking_remember` tool call in the output. A session that only *recalls* proves nothing about writing.

## Codex / OpenCode / Claude Code / DSH / pi

Official OpenViking provides a unified installer and per-harness adapters:

```sh
curl -fsSL https://openviking.ai/install | bash -s -- --url http://<host>:1933 --api-key <user_key>
```

`--harness` takes a comma list:
`claude, codex, cursor, trae, trae-cn, trae-cli, zcode, kimicode, codebuddy,
opencode, pi, dsh, dsh-desktop, cli`.

The installer's real script also lives at
`https://docs.openviking.net/dl/memory-plugin-shared/install.sh` — use that
URL directly when the `openviking.ai/install` wrapper is unreachable. It
verifies a release checksum and prints the publish version.

- **Codex** — hook-based (UserPromptSubmit recalls, Stop captures) plus a stdio MCP proxy
- **OpenCode** — npm package registered in `opencode.json`'s plugin array; behavior toggles live in `~/.openviking/ovcli.conf`
- **Claude Code** — `claude plugin marketplace add` + `claude plugin install`
- **pi** — a native extension under the pi extensions dir
- **DSH** — official bundle, installed into a specific dsh profile (`--dsh-profile`, default `web`)
- **MCP-only clients** — get `openviking_*` tools but no automatic recall or capture

Peer id defaults to being derived from the git origin, so the same repo maps to the same peer space across machines.

**The installer rewrites `~/.openviking/ovcli.conf`'s top-level credentials on every run** — installing several harnesses in sequence leaves them all on the last user. Re-run the section writer afterwards: see `references/multi-harness-credentials.md`.

For a shared multi-user Linux account, set the agent's own config-root env var BEFORE installing so the plugin lands in that person's tree (`CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `DSH_HOME`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). Verify the install path afterwards — some installers ignore the root and write to the shared default.

## Shared vs isolated recall

- Harnesses that should **share** experience → same user key, different peers
- Harnesses that should **not** see each other → separate user key each
- Same repo across harnesses → same peer (derived from git origin), which is where cross-harness project knowledge lands

## Detecting duplicate injection

OV's gateway and native plugins coordinate via context markers. If the same harness has two paths injecting memory, one of them yields. Check the injected envelope names when recall looks doubled:
- Hermes native → `<memory-context>`
- OV plugin → `<openviking-context>`
- Gateway header → `X-OpenViking-Plugin`
