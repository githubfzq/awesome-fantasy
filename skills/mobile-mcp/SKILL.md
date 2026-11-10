---
name: mobile-mcp
description: "Set up Mobile MCP for iPhone/Android control in Hermes."
version: 0.1.0
metadata:
  hermes:
    tags: [MCP, mobile, ios, setup]
---

# Mobile Device Control via Mobile MCP

Use when the user asks to control their iPhone/Android from the Mac (list apps, tap, screenshot, read chat lists via UI automation).

## Status check first

Before promising anything, check whether a mobile MCP server is already configured:

```bash
grep -A 5 -i 'mcp_servers' ~/.hermes/config.yaml
```

If no mobile server is listed, the agent has NO phone-control tools — say so and offer setup. Do not search the deferred-tool catalog for phone tools as a workaround; unconfigured MCP servers do not appear there.

## Setup: register mobile-mcp in Hermes

Hermes uses the native MCP client (see bundled `native-mcp` skill for full config reference). Add under `mcp_servers` in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  mobile:
    command: "npx"
    args: ["-y", "mobile-mcp"]
```

Restart Hermes after editing config (no hot-reload). Tools register as `mcp_mobile_<tool>`.

## iOS prerequisites (user-side, one-time)

1. iPhone connected to Mac via USB (Wi-Fi later, USB first).
2. Xcode Command Line Tools installed: `xcode-select --install`.
3. On the phone: enable Developer Mode (Settings → Privacy & Security → Developer Mode) — requires restarting the device.
4. WebDriverAgent must be built/installed to the phone once (Xcode or mobile-mcp's setup flow); trust the developer certificate on the phone.
5. First connection: tap "Trust" on the phone prompt.

Android instead: USB debugging enabled, `adb` on PATH — usually simpler.

## Pitfalls

- Config edits need an agent restart; mid-session the tools stay absent.
- iOS first-run requires manual phone interaction (Developer Mode toggle, trust prompt, WDA install) — the user must be present.
- Confirm WHICH app the user means before driving the UI; this session had a mid-task correction (千牛 → 牵手 → clarify).
