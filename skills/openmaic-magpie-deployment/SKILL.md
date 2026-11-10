---
name: openmaic-magpie-deployment
description: Run OpenMAIC locally on the magpie gateway.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [openmaic, magpie, llm, deployment]
---

# OpenMAIC on the magpie gateway

## When to Use
Use when configuring or running the OpenMAIC checkout at
`/data/workspace/reese/projects/OpenMAIC` (migrated 2026-11-04; the old
`/home/data/projects/reese/OpenMAIC` is a symlink to it) against the local
magpie gateway: writing `openmaic.yml`, choosing models, starting the database
or the server, or debugging a failed generation run.

Also use it to diagnose a classroom scene that misbehaves in the browser
(a runtime-error banner, a blank interactive widget). `references/classroom-scene-debugging.md`
has where classroom content lives in postgres, how to extract the exact
document the browser ran, how the runtime-error banner is wired, and the
third-party CDN dependencies that generated interactive pages carry.

`scripts/scan-interactive-katex.cjs` dumps every stored interactive page and
prints, per page, whether it still carries a legacy CDN KaTeX block and how
its math delimiters split between the rendered body and `<script>` bodies.
Run it before changing the KaTeX injection policy — the real pages decide
whether a detector is right, and a synthetic sample does not.

## Facts
- The magpie gateway is an OpenAI-compatible server on `http://127.0.0.1:3425/v1`
  (`magpie serve --web=0.0.0.0:3430`); key is `magpie`. Model ids look like
  `remote-magpie/<group>/<model>`; `<group>` is `auto` (routing group) or a
  pinned upstream (`codex`, `zcode`, `minimax-cn`, `deepseek`, `workbuddy-ai`).
- The account is `personal_free_user`: the `workbuddy-ai` upstream rejects the
  gpt-6 family with `model [...] is not allowed for user type
  [personal_free_user]`. `auto` routing groups sometimes land there and return
  HTTP 400, which OpenMAIC treats as non-retryable and pauses the run. Always
  pin a working upstream (`codex/gpt-6.1-sol`, `zcode/GLM-5.3`,
  `minimax-cn/MiniMax-M3.1-Flash`).
- `minimax-cn/*` returns reasoning inside `content` (`<think>` tags); prefer
  `codex/*` or `zcode/*` for stages that must emit clean JSON.

- magpie also serves `POST /v1/systemone` (TypeSafe System One) for **decision**
  models: use `typesafe/jev-latest` (resolves to `jev-1.14.0`). Routing groups
  such as `auto/jev-router` and bare `jev-*` names are rejected there.
  `references/systemone-jev.md` has the request/response shape, the rejected
  ids with their errors, and the `TYPESAFE_*` client env vars.

## Steps
1. Database: `pnpm db:up` (docker postgres on 127.0.0.1:5432, user/password
   `openmaic`/`openmaic-dev`, db `openmaic`).
2. `.env.local` needs (uncommented): `DATABASE_URL`,
   `MAGPIE_API_KEY=magpie`, `ALLOW_LOCAL_NETWORKS=true`,
   `OPENMAIC_SECRET_KEY=<random>`, `OWNER_SINGLE_USER=true`.
3. `openmaic.yml` (read once at startup): a `magpie` provider with
   `preset: openai-compatible`, `baseUrl: http://127.0.0.1:3425/v1`,
   `apiKey: ${MAGPIE_API_KEY}`, and a `models` list. Assign the slots
   (`llm`, `course.*`, `classroom`, `agent`) to `magpie:<pinned model id>`.
   Media/search slots (`image`, `video`, `tts`, `asr`, `webSearch`) get `null`
   when no provider is declared. An unset `${VAR}` or an unknown slot stops the
   server at boot with the exact path.
4. Comment out providers whose key env vars are empty (e.g. `openai`,
   `mimo`) — an unset variable is a boot error.
5. Build and run: `pnpm build`, then `pnpm start` (port 3000). Run the server
   **in a herdr pane to the right of the agent's pane**, not as an agent
   background process (this user's preference); its logs are read with
   `herdr pane read <pane-id> --source recent-unwrapped --lines N`, so a
   redirected log file goes stale. See the `herdr` skill for the pane commands.

## Speech (TTS)
The `tts` slot decides whether narration exists. `tts: null` (no provider
declared) resolves to `disabled`: scenes still contain `speech` actions, but
no audio was generated and playback only dwells silently — the engine falls
back to the browser's Web Speech API **only** when the slot names
`browser-native-tts`.

Server-side narration (pre-generated MP3s, downloadable, needed for video
export) needs a provider under `providers` with its `preset:` and a key in
`.env.local`, then the slot assigned to it. MiniMax (verified here):

```yaml
providers:
  minimax-tts:
    preset: minimax-tts
    apiKey: ${MINIMAX_TTS_API_KEY}
slots:
  tts: minimax-tts:speech-2.8-hd
```

- Both `https://api.minimaxi.com` and `https://api.minimax.chat` accept the
  key; the preset default (`api.minimaxi.com`) is used.
- The workspace may hold its own `tts` assignment, which **overrides** the
  server default. Clear it (`PUT /api/model-config` with
  `{"kind":"slots","clear":["tts"]}`) so the deployment default applies.
- Courses generated while `tts` was off have no audio at all. To give them
  sound in place: classroom page → **专业模式** → bottom bar → **全部配音**.
  The button regenerates the **current scene's** speech lines only, so repeat
  it per scene. It needs the build-time flag
  `NEXT_PUBLIC_MAIC_EDITOR_ENABLED=true` (rebuild required).
- `references/tts-and-audio.md` has the MiniMax request shape, the voice ids
  and the SQL to verify what is stored.

## Test suite gotchas
- The suite is hermetic: `tests/setup-env.ts` does NOT load `.env.local`
  (opt in with `TEST_LOAD_LOCAL_ENV=1`). But `openmaic.yml` — a gitignored
  local deployment file — IS read from `process.cwd()`, and its `${MAGPIE_API_KEY}`
  / `${MINIMAX_TTS_API_KEY}` refs then fail to resolve, so ~200-300 tests fail
  with "Invalid model configuration". Move `openmaic.yml` aside for a test run.
- Run the suite under the project's pinned Node 22
  (`export PATH="$HOME/.nvm/versions/node/v22.22.2/bin:$PATH"`). The Hermes
  agent shell defaults to the bundled Node 26, whose jsdom `localStorage`
  handling breaks ~100 workbench/slide-renderer tests
  ("Cannot read properties of undefined (reading 'setItem')").
- With Node 22 and `openmaic.yml` moved aside, ~4 files still flake on the
  5s default timeout under full parallel load (CI notes the same). They all
  pass when rerun in isolation.

## Verification
- `GET /api/health`; `GET /api/model-config` shows the deployment provider and
  the resolved slots.
- `POST /api/verify-model` with `{"provider":"magpie","model":"<id>"}`.
- End to end: `POST /api/generation-runs` with `{"requirement":"..."}`, then
  `POST /api/generation-runs/<id>/confirm-outline` with
  `{"commandId":"c1","outlineRevision":1}` (the revision comes from the run
  snapshot) and poll the run until `state == "completed"`.
- Gateway-side call log: `/home/data/.config/magpie/routing/<date>.jsonl`
  (one record per call, with `tries[].error`).
