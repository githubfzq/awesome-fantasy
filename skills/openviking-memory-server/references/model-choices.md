# OV model configuration — evaluation and working combination

OV requires two distinct model capabilities:

| Role | Purpose | Must be |
|---|---|---|
| embedding | retrieval / indexing | OpenAI-embeddings-shaped or a provider-native shape OV supports |
| VLM | memory extraction, content understanding | chat-completions-shaped |

## Working combination

- **embedding** — provider `minimax`, model `embo-01` (1536 dims), `api_base=https://api.minimaxi.com/v1/embeddings`
- **VLM** — an OpenAI-compatible chat endpoint (a local gateway holding several vendor keys), model `auto/<model>` so the router can fail over between vendors

Why this pairing: the Pi hosting the server had no vendor credentials of its own for the VLM but could reach a LAN gateway that held them; for embeddings it could reach a vendor directly. No extra container image and no local inference on the small host.

## Rejected paths (each verified, not assumed)

### magpie as an embedding relay — rejected

magpie's `/v1/embeddings` does **not** translate OpenAI request shape into the vendor-native shape. A request in OpenAI form (`{"model":..., "input":[...]}`) was passed through and the vendor rejected it for a missing `texts` parameter. A relay that passes the body through unchanged cannot serve two different vendor shapes.

### OV's native `local` embedder — rejected on this host

`provider: "local"` with a GGUF model (e.g. `bge-small-zh-v1.5-f16`, 512 dims) is officially supported and needs no API key, but it needs `llama-cpp-python` inside the container. The published container does not ship it, and pip could not install it on the target architecture (no matching wheel).

### ollama + nomic-embed-text — viable but worse

Works, but costs an extra large image pull and puts model inference on the small host. Use it only when there is genuinely no reachable embedding API.

## Practical notes

- MiniMax's native embedding request shape is `{"model":..., "type":"db", "texts":[...]}` — `texts`, not `input`. OV's minimax provider sends exactly this, which is why it works against the vendor directly.
- Confirm the dimension the provider actually returns before writing `dimension` into the config; a wrong value only surfaces later as a collection-dimension conflict.
- The VLM endpoint must be reachable **from inside the container**, not just from the host — verify with an in-container request.
