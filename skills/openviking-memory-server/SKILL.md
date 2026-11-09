---
name: openviking-memory-server
description: Use when deploying a self-hosted OpenViking memory server.
---

# Self-Hosted OpenViking Memory Server

Use when deploying or wiring OpenViking memory servers.

Deploy an OpenViking memory backend for one or more agent harnesses (Hermes, Codex, OpenCode, DSH, …), and decide how those harnesses share or isolate memory. Also covers reaching the server from other hosts.

## Topology decision

Default to **one self-hosted server + multi-tenant namespaces**, not one server per agent.

- **Account** — tenant/team boundary
- **User** — data owner; give each harness its own user key for isolation
- **Peer** — `viking://user/<id>/peers/<peer_id>/`, derived from git origin; the same repo on different machines/harnesses lands in one peer space
- **Shared library** — same user key across harnesses, different peers
- **Isolated library** — separate user key per harness (separate account for a hard tenant boundary)

Server-side namespaces are the only real isolation. Pointing clients at different URLs on one instance does not create boundaries.

## Deploy sequence

1. Clone the official repo (`volcengine/OpenViking`) and pin the commit you reviewed.
2. Keep a `ov.conf` **template** with `${VAR}` placeholders and render it with a script — secrets never land in the repo. Server config and client config (`ovcli.conf`) are different files; `ovcli.conf` is what you distribute to agents.
3. Put the data dir on a large disk, not the OS disk.
4. Run it under podman + podman-compose, and wire it into the host's **existing** boot-time container script rather than inventing a second boot mechanism.
5. Create the account, then one user per harness; record returned keys in a 0600 file.
6. Verify: `/health`, then a full session → commit → recall round trip.

## Model dependencies

OV needs an embedding model (retrieval) and a VLM (memory extraction). `references/model-choices.md` records the evaluation that produced the working combination and the two rejected paths — read it before re-litigating the choice.

## Changing the embedding model

The vectordb collection freezes provider/model/dimension. A dimension change requires moving the collection aside before restart, and the backup must live **outside** the data dir or OV will rescan it and fail again. Rename rather than delete so the step is reversible.

## Reachability from other hosts

Agents on other machines need a network path in. Tailscale is the reliable one. Give the device a **generic** name (`raspberry`) rather than a service-specific one (`raspberry-ov`) so later services reuse the same node.

Tailscale is not automatically fast: a peer behind NAT may land on a **relay** instead of a direct connection, and relay hops carry ~800ms RTT plus packet loss. Check `tailscale status` for `direct` vs `relay` on each peer before blaming the server.

When one client is stuck on a relay, put the hop on a machine that has a direct path to BOTH ends (an intermediate host with direct links to the server and to the client) and forward the port there. Two direct legs beat one relay leg by an order of magnitude. If the client itself cannot reach any host directly, tunnel through a host it CAN reach (e.g. SSH `-L` to a jump host), and make that tunnel a systemd user service so it survives reboots — with a dedicated key pair, because an interactive shell's ephemeral agent socket is not available to a service unit.

## Isolation and credential placement

One `ovcli.conf` serves every harness on a host, and the installer rewrites its top-level credentials on each run. Give each harness its own user via the `plugin.<harness>` sections — see `references/multi-harness-credentials.md`.

## Connecting harnesses

`references/harness-integration.md` covers the Hermes plugin install (including GitHub-unreachable hosts), the Codex/OpenCode/DSH installers, and the env-var contract.

`references/multi-harness-credentials.md` covers giving several harnesses on ONE host different memory users (the `plugin.<harness>` sections in `ovcli.conf`), the per-agent config-root env vars for a shared multi-user Linux box, and the isolation check. `scripts/ov_cli_sections.py` writes those sections idempotently.

**Hermes integrates as a native plugin, not MCP** — it calls the OV REST API directly over httpx and registers `viking_*` tools. Every other harness (Codex, Claude Code, OpenCode, pi, dsh) gets a plugin plus a stdio MCP proxy. This matters when a client asks "is this MCP?" — the answer differs by harness, and Hermes has no MCP server in the chain.

## Verification

`references/pi-deployment.md` holds the exact commands and the working values for a live instance.

## Pitfalls

- Do **not** add memory limits to a rootless podman container on a host without a cgroup v2 memory controller — the container refuses to start.
- podman-compose does not expand nested `${VAR:-${OTHER}}`; write absolute paths.
- Point `TMPDIR` at the large disk for podman/buildah — their scratch space defaults to the OS disk and can fill it during image pulls.
- Under disk pressure, prune dangling images and orphaned `/var/tmp/storage*` dirs, but confirm no live process holds each one first.

## Codex reports "Hook failed: plugin contents changed; hook approval required"

Not a connectivity problem — the server can be perfectly healthy while every hook fails.

Codex records a trust hash for each plugin hook. When the marketplace auto-updates the
plugin, `hooks.json` changes, the recorded hash no longer matches, and the *running*
Codex refuses to run the hook until it is re-approved. The plugin cache directory
mtime is when it was re-fetched; the recorded hash lives in `~/.codex/config.toml`
(`[hooks.state."<plugin>:<event>:0:0"].trusted_content_hash`) and in
`~/.codex/.hook-trust/<hash>`.

Fix: add to `~/.codex/config.toml`

```toml
[hooks]
bypass_hook_trust = true
```

The plugin must then be re-approved once (accept the prompt in a new Codex session);
the setting keeps later auto-updates from breaking hooks again.

Diagnose it with `herdr pane read <pane>` — the TUI prints the exact reason
(`Hook failed` + the cause line). `ov-memory-doctor` reports "no problems found"
here because it only checks that a trust *record exists*, not that its hash still
matches. `codex exec` does not apply the trust gate, so a fresh exec session
succeeds while the long-running TUI session keeps failing.

Other Codex hook failure kinds (from the binary): `timeout` (hook exceeded its
per-hook timeout), `stdin_error`, `wait_error`, `spawn_error` (usually `node` not
on PATH for the launcher), `trust_error`.
