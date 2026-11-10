---
name: docker-compose-service-ops
description: Fix docker compose errors and manage service lifecycle.
version: 1.0.0
metadata:
  hermes:
    tags: [docker, docker-compose, deployment, troubleshooting, services]
    related_skills: [repo-dev-server-bootstrap, systematic-debugging]
---

# Docker Compose ops in an existing repo

## When to Use

- The user reports a `docker compose` command error (`ps`, `config`, `up`,
  `build`) in a repo that already has a compose file.
- The user asks to start, stop, or inspect "the service(s)" of a repo that is
  deployed via compose.

Class of task: make the compose file parse and behave correctly in the user's
checkout, then run the requested lifecycle operation (usually stop), and
report the real container state.

## 1. Read the error before touching anything

Run the failing command verbatim; the parse error names the offending
variable or syntax. Then confirm the file the user means — repos often ship
several compose files (`docker-compose.yml`, `docker-compose.dev.yml`, plus
`.bak.*` copies). Use the one the user invoked; check `docker compose ls` to
see which config file the running project actually came from.

`docker compose config --services` is a cheap way to re-trigger a parse
error without starting anything.

## 2. Missing required variables (`:?` interpolation)

A message like `required variable X is missing: X_must_be_set_...` means the
compose file declares `X=${X:?...}` — compose refuses to parse the project at
all until `X` is defined in the environment or in the project's `.env`.

Derive the correct value from the repo, never guess it:

1. Find every consumer of the variable (`grep -rn '<VAR>' --include='*.yml'
   --include='Dockerfile*' --include='*.sh'`). A build arg usually has a
   matching `ARG` in the Dockerfile and a file-naming convention such as
   `COPY /app/.env.${VAR}`.
2. List the candidate files that exist in the repo (`.env.dev`, `.env.beta`,
   `.env.production`, ...) and pick the tier the user's deployment actually
   is — infer it from which env file the running containers were built from,
   the values in the user's `.env`, or the tier documented in the Dockerfile
   comment.
3. Define it in BOTH places:
   - the local `.env` (what compose actually reads), and
   - the tracked template `.env.example` (so the next clone does not hit the
     same error).

Pitfall: the local `.env` is often gitignored while `.env.example` is
tracked. Editing only the template leaves the running checkout broken;
editing only `.env` leaves every fresh clone broken.

Pitfall: `read_file` refuses `.env`-style files as secret-bearing. Use
`terminal` (grep/sed) for those, and never echo secret values into your
reply.

## 3. Verify the parse, then the state

```bash
docker compose config --services   # parses; still errors if interpolation is broken
docker compose ps -a                # -a shows exited containers too
```

`docker compose ps` alone shows only running containers and will silently
hide the exited ones you are trying to diagnose — use `-a` when the question
is "what state is each container in".

## 4. Stopping services: profiles matter

`docker compose stop` only touches services in the **default profile**.
Services behind a profile (`profiles: [neo4j]`, `[full]`, …) keep running and
will still show up as Up in `docker compose ps`.

```bash
docker compose stop                                     # default-profile services
docker compose --profile neo4j --profile full stop neo4j   # profile-gated service
```

Read the `profiles:` keys in the compose file before assuming `stop` covered
everything; then confirm with `docker compose ps -a` and `docker compose ls`
that the project no longer reports as running.

Prefer `stop` over `down` when the user says "停掉 / 停一下": `down` removes
containers, networks, and can remove volumes, which is destructive and
harder to undo. Only `down` when the user explicitly asks to tear down.

## 5. Report actual state

State plainly what was fixed, what was verified (with the command output),
and what was left running or untouched. If a container was already exited
before you started, say so — do not imply you started or fixed it.

## Pitfalls

- A parse error in one compose file makes EVERY compose command in that
  directory fail, including read-only ones like `ps`; fix the variable
  before diagnosing container health.
- `.bak.*` and `.bak.tidy.*` copies of the compose file and Dockerfile are
  common leftovers — grep them too when tracing a variable's history, but
  never edit them as the fix.
- `docker compose ls` counts running containers per project; a project
  showing `running(2)` means two containers are still up even if the
  default-profile `stop` appeared to succeed.

## Repo notes

Per-repo details (env tiers, profile lists) live in
`references/weknora-compose.md` for the WeKnora checkout.
