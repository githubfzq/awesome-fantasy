---
name: docjev-local
description: Run docjev locally with the magpie gateway's Jev model.
version: 1.0.0
author: Hermes Agent
license: Apache-2.0
metadata:
  hermes:
    tags: [docjev, jev, magpie, ocr, demo]
---

# Running docjev locally

Repo: /data/workspace/reese/projects/docjev (uv project, CLI `docjev` / `jev-docs`).
Migrated there on 2026-11-04 from /home/data/projects/reese/docjev to save root-disk
space; `/data/workspace` is a separate 15T xfs volume with 12T free.

## When to Use

- Start, configure, or troubleshoot the docjev CLI, its local OCR, or its demo web app.
- Point docjev's Jev decisions at the local magpie gateway instead of api.typesafe.ai.
- Fix LiteParse OCR failures caused by missing tesseract language data.

## Environment

```sh
cd /data/workspace/reese/projects/docjev
uv sync --all-extras
export TYPESAFE_API_KEY=magpie
export TYPESAFE_BASE_URL=http://127.0.0.1:3425   # magpie gateway, serves /v1/systemone
export TYPESAFE_DEFAULT_MODEL=typesafe/jev-latest # -> jev-1.14.0
```

`typesafe/jev-latest` is the magpie model id for System One; `auto/jev-router` and
bare `jev-*` names are rejected there. The CLI equivalent of the model env var is
`--model typesafe/jev-latest`.

## OCR readiness (one-time)

LiteParse's Rust OCR needs `~/.tesseract-rs/tessdata/eng.traineddata`. Direct
raw.githubusercontent.com downloads stall; fetch it through the gh-proxy mirror
(~380 KB/s) and copy it to `eng.traineddata` in that directory. Verify with
`docjev doctor --smoke` — `local_ocr.status` must be `passed`.

DOCX/PPTX conversion makes fontconfig write a `.uuid` file into
`src/jev_docs/web/static/assets/brand/fonts/`. It is gitignored, so an
untracked `.uuid` there means that gitignore entry was lost.

## Checks

```sh
uv sync --all-extras        # dev + datasets extras: pytest needs reportlab/python-docx/python-pptx
docjev classify examples/real/originals/r04.pdf --rules examples/real/classify/rules.yaml
docjev split examples/real/public-finance-packet.pdf --rules examples/real/split/rules.yaml \
  --export-dir output/real-segments --output output/real-split.json
pytest -q                    # ~190 tests, no paid provider calls
ruff check . && mypy src/jev_docs
```

Expected split of the 15-page packet: tax_form 1-3, financial_report 4,
financial_report 5, press_release 6-15.

## Demo app

`docjev demo` serves http://127.0.0.1:8765. Per user preference, run it in a
herdr pane split to the right of the agent's pane, not as an agent background
process:

```sh
herdr pane list --workspace "$HERDR_WORKSPACE_ID"        # find the agent pane
herdr pane split <agent-pane-id> --direction right --cwd "$PWD" --no-focus
herdr pane run <new-pane-id> "cd <repo> && TYPESAFE_API_KEY=magpie TYPESAFE_BASE_URL=http://127.0.0.1:3425 TYPESAFE_DEFAULT_MODEL=typesafe/jev-latest .venv/bin/docjev demo"
```

The web UI posts no model name, so the engine default must come from
`TYPESAFE_DEFAULT_MODEL` (src/jev_docs/engines/__init__.py `default_jev_model()`).
The `/race` page additionally needs an OpenAI key.

## LAN access

`docjev demo --host 0.0.0.0 --port 8765` binds all interfaces. The app middleware
rejects non-local Host headers unless `create_app(allow_remote=True)`, which the
CLI passes automatically for a non-local host. Same-origin and security headers
still apply. Restart by sending ctrl+c to the pane and re-running the command
there, never as a second instance elsewhere.

Binding to 0.0.0.0 is not enough on its own: the app's own Host check rejects
LAN requests with 403 unless the allow-remote path is enabled. Verify from the
LAN address (`curl http://<host-ip>:<port>/`), not just from loopback — loopback
passes the localhost-only guard either way.

## Related skills

- `openmaic-magpie-deployment` — magpie gateway facts; its System One
  reference file covers the `/v1/systemone` endpoint, the working Jev model
  ids and the rejected ones, and it ships `scripts/capture_systemone.py` to
  print the exact request a client sends without spending tokens.
- `blocked-page-recovery` — its mirror reference file has the gh-proxy
  mirror and the safe download/stop rules used for the tessdata file.

## Reference files

- `references/decision-pipeline.md` — where docjev's Jev request is built
  (`src/jev_docs/engines/jev.py`), how state and questions are constructed,
  how answers become categories and segments, and the context-budget, retry
  and metrics rules.
