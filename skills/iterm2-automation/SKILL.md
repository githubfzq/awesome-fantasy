---
name: iterm2-automation
description: Drive iTerm2 panes/tabs via AppleScript. Use for new panes.
---

# iTerm2 AppleScript automation

macOS user's main terminal is iTerm2. Common ask: "open X in a new pane/tab". All of this works over `osascript`; no accessibility permission issues observed (unlike GUI RPA).

Session-verified commands and exact error transcripts live in `references/verified-snippets.md`.

## Discovery: find the right tab/window first

Never assume `current window`/`current tab` is the target — enumerate:

```applescript
tell application "iTerm2"
  repeat with w in windows
    repeat with t in tabs of w
      -- tab identity = name of its current session
      if (name of current session of t) contains "herdr" then ...
    end repeat
  end repeat
end tell
```

Pitfall: `get index of every tab` fails with error -1728 ("cannot get index"). Iterate objects directly instead of asking for index properties in bulk. Similarly `count tabs of window 1` works but `get name of every tab of window 1` may fail — always go through `name of current session of t`.

## Splitting panes (the hard-won syntax)

`create session with default profile` is INVALID — AppleScript parse error -2741/-2740 ("expected , but found class name"). The correct calls, issued against a **session**:

```applescript
-- left/right split (vertical divider):
tell application "iTerm2" to split vertically current session of current tab of current window with profile "Default"
-- top/bottom split:
tell application "iTerm2" to split horizontally current session of current tab of current window with profile "Default"
```

Note the inverted naming: `split vertically` = new pane to the LEFT/RIGHT. Returns the new session's specifier (`session id ... of tab N of window id M`). Profile name must match an existing profile ("Default" works on stock installs).

The sdef (`sdef /Applications/iTerm.app`) also exposes `split vertically with default profile` as a tab-level command, but it errors -1708 in practice ("doesn't understand") — use the session-direct form above.

## Run a command in a specific pane

```applescript
tell application "iTerm2"
  -- after locating session s:
  tell s
    write text "cd /path && some-command"
  end tell
end tell
```

`write text` sends the line + Enter. New session inherits cwd of the split source, so prefix `cd` when needed.

## Read pane output

```applescript
tell application "iTerm2" to get contents of session S
```

Caveats:
- `contents` can return empty while a command is starting up or output is refreshing — sleep a few seconds and retry, and don't conclude failure from one empty read.
- For services, more reliable verification than screen scraping: probe the listen port (`lsof -nP -iTCP:PORT -sTCP:LISTEN`, curl health check) and `ps` for the process start time.

## Shell-tool pitfalls when calling osascript

- Inline `osascript -e` multi-line heredocs can be misdetected by the shell tool guard as backgrounding (`&` in applescript strings like `set out to out & ...` triggers "Foreground command uses '&' backgrounding"). **Workaround: write the script to a file** (`write_file` to /tmp/*.applescript) and run `osascript /tmp/script.applescript`.
- Windows-terminal/SSH remote osascript does not help here; this is local macOS only.
- Bundle/app name: both `"iTerm2"` and `"iTerm"` appear in error messages; `"iTerm2"` is the app's scripting name and works.

## Verification checklist

1. After split: re-enumerate sessions of the target tab — new session name appears (typically `~ (-zsh)`).
2. After write text + a few seconds: check service port listening / process running rather than relying on `contents`.
3. `computer_use` capture with app="iTerm2" can fail to match an on-screen window (returns 0x0). Don't block on screenshots; use port/process evidence.
