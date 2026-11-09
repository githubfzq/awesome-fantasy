# WeKnora compose notes

Repo: /home/data/LY/WeKnora_0.6_test/weknora (branch dev). Main compose file:
`docker-compose.yml`; a `docker-compose.dev.yml` exists for the local
go-run + air dev loop and does NOT declare `KGENV`.

## Deployment tiers and the KGENV build arg

`docker-compose.yml` declares, under `app.build.args`:

    KGENV=${KGENV:?KGENV_must_be_set_dev_beta_release}

`docker/Dockerfile.app` consumes it as:

    ARG KGENV
    COPY --from=builder /app/.env.${KGENV} /app/.env

So KGENV selects which env file is baked into the image and sourced by
`scripts/docker-entrypoint.sh` (`source /app/.env`). Tiers:

| KGENV     | baked file       | use                                |
|-----------|------------------|------------------------------------|
| `dev`     | `.env.dev`       | local dev; this checkout's default |
| `beta`    | `.env.beta`      | beta / K8s ai namespace deployment |
| `release` | `.env.production`| production                         |

If `KGENV` is missing from the shell and from `.env`, EVERY compose command
in the repo dir fails at interpolation — including `ps`.

Env file inventory in this checkout:

- `.env`            — local, gitignored, content identical to `.env.dev`
- `.env.dev`        — local, gitignored (`.gitignore` line 13)
- `.env.beta`       — tracked in git, K8s beta deployment env
- `.env.production` — tracked in git
- `.env.example`    — tracked in git, the template fresh clones copy to `.env`

`KGENV=dev` is set in `.env` and `.env.dev`, and documented in `.env.example`.

## Profiles in docker-compose.yml

Default profile (covered by a bare `docker compose stop`):
frontend, app, docreader, postgres, redis.

Profile-gated services:
- `docling` → docling, full
- `sandbox` → full
- `minio` → minio, full
- `jaeger` → jaeger, full
- `neo4j` → neo4j, full
- `qdrant` → qdrant, full
- `milvus` → milvus
- `weaviate` → weaviate
- `doris-fe` / `doris-be` → doris
- `dex` → dex, full
- `searxng-init` / `searxng` → searxng, full
- `langfuse-db-init`, `langfuse-clickhouse`, `langfuse-minio`,
  `langfuse-worker`, `langfuse-web` → langfuse, full
- `mcp` → full

To stop a profile-gated service:
`docker compose --profile neo4j --profile full stop neo4j`.

## Other things worth knowing

- `app` has `env_file: [.env]` AND bind-mounts `./config/config.yaml`,
  `./scripts/precheck.sh`, `./skills/preloaded`, `./config/builtin_models.yaml`
  and `./config/builtin_mcp.yaml` from the working tree, so those files must
  exist for the container to start.
- The compose file currently hardcodes `REDIS_ADDR=redis:6379` (it was
  changed from `${REDIS_ADDR:-redis:6379}`).
- `scripts/start_all.sh` is the repo's own start/stop wrapper
  (`-d` docker, `-s` stop, `-l` list, `-c` check) and does `down
  --remove-orphans` for stop — prefer explicit `docker compose stop` when
  the user only wants the services paused, so containers and volumes stay.
- Named volumes hold all state (postgres-data, data-files, minio_data,
  neo4j-data, ...). `stop` preserves them; `down` keeps named volumes but
  removes containers and the project network.
