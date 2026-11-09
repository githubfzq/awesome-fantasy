# magpie System One (TypeSafe-style) and the Jev models

magpie is not only OpenAI-compatible. It also serves
`POST /v1/systemone` — the TypeSafe "System One" endpoint that decision
models (Jev) answer. Any client that speaks the TypeSafe SDK
(`typesafe-sdk` for Python) can point its base URL at magpie:

```sh
export TYPESAFE_API_KEY=magpie
export TYPESAFE_BASE_URL=http://127.0.0.1:3425   # SDK appends /v1/systemone
```

## Model naming on /v1/systemone

System One asks a **decision model**, not a routing group. Verified working
ids:

| Model id | Resolves to |
|---|---|
| `typesafe/jev-latest` | `jev-1.14.0` |
| `remote-magpie/openrouter/~typesafe/jev-latest` | `typesafe/jev-1.14-20261014` |

Rejected ids and their errors:

- `auto/jev-router` (routing group) → 400 "holds models that hold
  conversations; System One asks a group of decision models, or a decision
  model as `provider/model`".
- `jev-latest`, `jev-1.13.0` (bare, no provider prefix) → 404 "magpie knows
  no Jev model ...; name the provider before it".
- `openrouter/typesafe/...` → 400 "OpenRouter is switched off in magpie".

## Request shape

`{"model": ..., "state": "<text>", "questions": {"<key>": {...}}}` — the
question object is a tagged union: a choice question needs
`{"type": "choice", "instructions": ..., "criteria": {<id>: <description>}}`
(criteria is a **dict**, not a list) and a boundary question needs
`{"type": "noul", ...}`. Hand-writing the JSON without the discriminator
returns `union_tag_not_found`; the typesafe SDK builds it for you
(`Choice(instructions=..., criteria={...})`, `Noul(instructions=...)`).

The response carries `answers`/`choices` (with `choice`, `confidence`,
`probabilities`) and `nouls` (with `noul`), plus `usage` and the resolved
`model`. Verified: `typesafe/jev-latest` answers a 3-way classification with
`choice` plus one probability per criterion.

## Capture the wire request

To see exactly what a client sends — and to exercise the client's own response
validation — point its base URL at a local echo server instead of magpie:

```bash
python3 scripts/capture_systemone.py 8899
export TYPESAFE_BASE_URL=http://127.0.0.1:8899
export TYPESAFE_API_KEY=dummy
```

The server prints the request path, selected headers, body keys, model, state
and every question, then answers each choice question with its first criterion
and each noul question with 0.5. It answers the question **types** it sees, so
a client whose answer parsing expects `probabilities` on a choice or `noul` on
a boundary keeps working and you can confirm the whole loop locally, for
free, before spending tokens on magpie.

Use this when you need the concrete request shape for a client you did not
write, or to prove which model id and base URL a wrapper actually sends.

## Client configuration

The SDK's own env vars apply: `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`,
`TYPESAFE_DEFAULT_MODEL`. A client that always passes its own model string
ignores `TYPESAFE_DEFAULT_MODEL`, so wire the default through the app's own
config layer when the UI never sends a model name.
