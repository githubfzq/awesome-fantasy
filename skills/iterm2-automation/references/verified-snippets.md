# Verified AppleScript snippets (2026-10-29 session)

Working commands, in invocation order:

```bash
# 1. Enumerate tabs by session name (herdr tab target)
osascript -e 'tell application "iTerm2"
set out to ""
repeat with w in windows
  set out to out & "window: " & (name of w) & linefeed
  repeat with t in tabs of w
    set out to out & "  tab: " & (name of current session of t) & linefeed
  end repeat
end repeat
return out
end tell'
# Result: tab names like "fantasyMac-2.local: awesome-fantasy (herdr)", "[1data-gpu-] ~ (ssh)"

# 2. Create right-side pane in the current tab (vertical divider = left/right)
osascript -e 'tell application "iTerm2" to split vertically current session of current tab of current window with profile "Default"'
# Returns: session id 86EFBE3C-... of tab 1 of window id 422

# 3. Confirm the new pane exists
osascript -e 'tell application "iTerm2" to get name of every session of current tab of current window'
# Result: "fantasyMac-2.local: awesome-fantasy (herdr), ~ (-zsh)"

# 4. Write launch command into the new pane
osascript -e 'tell application "iTerm2" to tell session "~ (-zsh)" of current tab of current window to write text "cd ~/Public/Projects/OpenBiliClaw && uv run openbiliclaw start"'
```

# Failed attempts (do not retry these forms)

| Attempt | Error |
|---|---|
| `create session with default profile` (tab tell-block) | -2741/-2740 parse: 预期是","，却找到类名称 |
| `split vertically with default profile` on tab | -1708: doesn't understand |
| `get index of every tab` | -1728: 不能获得 index |
| `get name of every tab of window 1` | -1728 |
| `get contents of current session` right after `write text` | returns empty while command starts; retry after sleep |

# Service verification evidence pattern

Instead of scraping pane contents:

```bash
lsof -nP -iTCP:8420 -sTCP:LISTEN        # port up (IPv4+IPv6)
ps -p <pid> -o pid,lstart,command        # process started at expected time
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8420/   # 302 = web UI redirect
```

All three confirmed within ~10s of `write text` firing the launch command.
