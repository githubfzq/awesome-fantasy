---
name: macos-system-settings
description: Use when configuring macOS System Settings programmatically.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macos, settings, system-settings, handoff, continuity, applescript]
    category: apple
---

# macOS System Settings automation

Change and verify macOS settings without hijacking the user's screen.
Prefer CLI/AppleScript over GUI clicking; use the GUI only to *verify*.

## Navigating System Settings (the reliable way)

`x-apple.systempreferences:<id>` deep links are UNRELIABLE on macOS 14/15 —
most extension IDs silently fail or land on the wrong pane. Do not guess IDs.

Instead use AppleScript with the pane's **localized display name**:

```applescript
tell application "System Settings"
  activate
  reveal pane "隔空投送与接力"   -- localized name, e.g. "AirDrop & Handoff"
end tell
```

To discover available pane names (they follow the system language):

```bash
osascript -e 'tell application "System Settings" to get name of every pane'
```

Note: `reveal pane id "com.apple.X-Settings.extension"` often errors with
-1728 ("can't get pane id") even for valid extension IDs — use the name form.

## Enabling Handoff / Universal Clipboard via CLI

Universal Clipboard is part of Handoff (useractivityd). Toggle it without
opening System Settings:

```bash
defaults write com.apple.coreservices.useractivityd ActivityAdvertisingAllowed -bool true
defaults write com.apple.coreservices.useractivityd ActivityReceivingAllowed -bool true
launchctl kickstart -k gui/$(id -u)/com.apple.coreservices.useractivityd
# verify
defaults read com.apple.coreservices.useractivityd ActivityAdvertisingAllowed   # expect 1
```

This makes the underlying feature active; the System Settings UI toggle
("允许在这台 Mac 和 iCloud 设备之间使用接力") reflects it.

Handoff requirements to check for the user: same Apple ID on both devices,
Bluetooth on both, same Wi-Fi, devices within a few meters. iPhone side:
设置 → 通用 → 隔空投送与接力 → 接力. Clipboard copy is valid ~1 min;
iPhone copy → Mac ⌘V and Mac copy → iPhone long-press paste, both directions.

## Verifying a settings pane without stealing the screen

The Settings window may be on another Space or hidden behind a full-screen
app; `computer_use(capture, app="System Settings")` can then return 0x0
window-not-found even though the app is running. Robust fallback:

```bash
osascript -e 'tell application "System Settings" to reveal pane "<name>"'
sleep 1.5
screencapture -x /tmp/ss.png     # full-screen capture works regardless of Space
```

then analyze /tmp/ss.png with `vision_analyze` to read toggle states.
`osascript` needs Accessibility permission for System Events UI queries
(error -1728 "不允许辅助访问" means the calling terminal lacks it) — plain
`tell application "System Settings"` commands do NOT need that permission,
so prefer them over System Events scripting.

## Pitfalls

- Don't click around System Settings via element indices when a `defaults`
  write or `reveal pane` does the same job — GUI navigation of the sidebar
  wastes many round-trips, and pixel clicks on AXStaticText sidebar rows
  come back as `suspected_noop` (they only advertise AXShowMenu, not AXPress).
- `defaults read ~/Library/Preferences/ByHost/...` by exact path fails when
  the plist filename suffix differs; read the domain instead
  (`defaults read com.apple.coreservices.useractivityd`).
- When the user is actively working in a full-screen terminal Space, do NOT
  `activate`/raise Settings repeatedly — reveal once, verify via
  screencapture, and tell the user where to look.
