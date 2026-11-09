---
name: lazygit-headless-clipboard
description: Use when LazyGit (or another TUI) fails to copy to the clipboard with "exit status 1", "No clipboard utilities available", or an OSC52/tmux copy recipe breaks. Covers diagnosing the clipboard backend over SSH and shipping a working copyToClipboardCmd.
---

# LazyGit clipboard failures on headless/SSH hosts

## The one fact that explains most of it

LazyGit's copy path is two separate steps, and they fail independently:

1. **compute the string** (relative path, diff lines, commit hash)
2. **write it to the clipboard** — this is the only step that runs an external command

`pkg/commands/oscommands/os.go` → `OSCommand.CopyToClipboard()`:

```go
if c.UserConfig().OS.CopyToClipboardCmd != "" {
    cmdStr := utils.ResolvePlaceholderString(c.UserConfig().OS.CopyToClipboardCmd,
        map[string]string{"text": c.Cmd.Quote(str)})
    return c.Cmd.NewShell(cmdStr, c.UserConfig().OS.ShellFunctionsFile).Run()
}
return clipboard.WriteAll(str)   // default path
```

So `exit status 1` is **always** a failed subprocess, never a bad path. The
default path calls `github.com/atotto/clipboard` (v0.1.4), whose
`clipboard_unix.go` `init()` picks a helper by **LookPath only** — it never
checks `$DISPLAY` / `$WAYLAND_DISPLAY`:

```go
if os.Getenv("WAYLAND_DISPLAY") != "" { ...wl-copy... }
if _, err := exec.LookPath("xclip"); err == nil { return }   // existence only
if _, err := exec.LookPath("xsel");  err == nil { return }
```

`writeAll` ends with `return copyCmd.Wait()`, so a non-zero exit from the
helper becomes the literal string `exit status 1`.

Consequence: on a headless box where `xclip`/`xsel` are *installed but no
display server is reachable*, LazyGit picks xclip, xclip fails with
`Can't open display: (null)`, and you get a bare `exit status 1`. If **no**
helper were installed you'd instead get the friendlier
`No clipboard utilities available...` — so seeing the bare `exit status 1`
specifically tells you a helper exists but is failing.

Note `exit status 1` is Go's `exec.ExitError` format, so a Go binary is the
likely culprit.

## Diagnose

```bash
echo "DISPLAY=[$DISPLAY] WAYLAND_DISPLAY=[$WAYLAND_DISPLAY] TMUX=[$TMUX]"
printf 'hello' | xclip -selection clipboard; echo "xclip exit=$?"
printf 'hello' | xsel -b -i;           echo "xsel  exit=$?"
printf 'hello' | wl-copy;              echo "wl-copy exit=$?"
grep -A3 copyToClipboardCmd ~/.config/lazygit/config.yml
```

## Keybindings (upstream `docs/keybindings/Keybindings_en.md`)

| pane | ctrl+o | source |
|---|---|---|
| Files | Copy path to clipboard | `pkg/gui/keybindings.go` |
| Commit files | Copy path to clipboard | same |
| Branches / Tags | Copy branch/tag name | same |
| Commits | Copy abbreviated commit hash | same |
| **Main (diff) pane** | **Copy selected diff lines** | `Keybindings_en.md:233,317` |

So "ctrl+o in the diff pane to copy the relative path" does not exist upstream.
For an explicit *relative path*, use the Files panel's `y` copy menu → `p`
(`CopyRelativeFilePath`, `pkg/gui/controllers/files_controller.go:1490`).
`P` = absolute path, `n` = file name. All of them funnel through the same
`CopyToClipboard`, so they all fail together.

## Landmines in the OSC52 recipe from `docs/Config.md`

The documented recipe is:

```
printf "\033]52;c;$(printf {{text}} | base64 -w 0)\a" > /dev/tty
```

Three real defects, all verified:

1. **`printf {{text}}` treats the text as a format string.** A path with `%`
   is corrupted or rejected. `printf "weird/a%q.txt"` under fish →
   `%q: invalid conversion specification`; under bash the tail is silently
   dropped (`weird/a%q.txt` → `weird/a`). Use **`printf %s {{text}}`** so the
   text is an argument, never a format.
2. **`base64 -w 0` is GNU-only.** BSD/macOS `base64` rejects `-w`. Use
   `base64 | tr -d '\n'`.
3. **`> /dev/tty` needs a controlling terminal.** LazyGit runs the command
   without a pty (`UsePty()` is only set for credential prompts), so `tty`
   inside the command reports "not a tty" — see upstream issue
   [#3595](https://github.com/jesseduffield/lazygit/issues/3595). The redirect
   to `/dev/tty` itself still works when a tty exists; it is `tty(1)` that
   complains.

Also: `{{text}}` is substituted with `Cmd.Quote()` (double-quoted, escapes
`\ " $ \``), so the text arrives as one shell word — but `%` is *not*
escaped, which is exactly why defect 1 bites.

## tmux: raw OSC52 works; DCS-wrapped does not (by default)

tmux implements OSC 52 itself when `set-clipboard` is on. Verified on tmux 3.4:

- `set -g set-clipboard on` + **raw** `ESC]52;c;<b64>BEL` → captured into the
  tmux buffer.
- the DCS passthrough form `ESC Ptmux; ESC ESC]52;...` only reaches the outer
  terminal with `set -g allow-passthrough on`; it does **not** populate the
  tmux buffer.

So inside tmux, prefer `tmux load-buffer -w -` (sets the buffer *and*
relays to the outer terminal).

## Gotcha: `tmux load-buffer` needs `$TMUX`

`tmux load-buffer` finds the server via `$TMUX` (socket path, pid, session).
If `$TMUX` is unset — e.g. LazyGit was launched outside tmux, or through a
wrapper that strips the env — tmux falls back to the **default** socket
`/tmp/tmux-$UID/default` and fails with:

```
error connecting to tmp/tmux-1000/default (No such file or directory)
```

That is an environment problem, not a LazyGit bug. Fixes: run inside tmux,
or export `$TMUX` to match the running server, or use a backend that does not
need tmux at all.

## The Neovim :terminal buffer trap (silent no-op)

If LazyGit is launched **inside a Neovim `:terminal` buffer** — LunarVim's
`<leader>gg` does exactly this via toggleterm, see
`lvim/lua/lvim/core/terminal.lua` → `M.lazygit_toggle` — then `/dev/tty`
inside that buffer is the **embedded pty owned by Neovim's terminal
emulator**, not the outer terminal.

So an OSC 52 sequence written to `/dev/tty` is consumed by Neovim and never
reaches the real terminal. Symptom: **no error at all**, but the clipboard
never changes. Verified: a child in a Neovim `:terminal` buffer that writes
OSC 52 to `/dev/tty` produces **zero** OSC 52 sequences on the outer pty.

Neovim's own clipboard provider avoids this by writing to **channel 2**
(nvim's stdout) rather than to a terminal:

```lua
-- /opt/nvim-linux64/share/nvim/runtime/lua/vim/ui/clipboard/osc52.lua
vim.api.nvim_chan_send(2, osc52(clipboard, vim.base64.encode(s)))
```

### The fix: ask Neovim over RPC

Neovim sets `$NVIM` to its server socket for processes it spawns, so a child
can hand the text back to Neovim and let Neovim's provider emit the OSC 52:

```sh
if [ -n "$NVIM" ] && command -v nvim >/dev/null 2>&1; then
	tmp=$(mktemp "${TMPDIR:-/tmp}/lazygit-copy.XXXXXX")
	printf '%s' "$text" > "$tmp"
	if nvim --server "$NVIM" --remote-expr \
		"setreg(\"+\", join(readfile(\"$tmp\"), \"\\n\"))" >/dev/null 2>&1; then
		rm -f "$tmp"; exit 0
	fi
	rm -f "$tmp"
fi
```

The payload goes through a temp file because the text may contain quotes,
newlines, `%`, etc. that would break a command-line argument. `--remote-expr`
evaluates **Vimscript**, not Lua — a `lua ...` prefix raises
`E121: Undefined variable: lua`; use `setreg(...)` with Vimscript functions
(`readfile`, `join`) instead.

Verified end to end: with this route, an OSC 52 sequence carrying the exact
path (`percent%q.txt` included) reaches the outer pty.

## Recommended: a small helper script

Put a script on `$PATH` and point LazyGit at it, so one config works in every
environment. Ordered backends: **Neovim RPC → native display helper → tmux →
OSC 52**. The Neovim branch must come first, because inside a Neovim
terminal buffer the later branches either do nothing (OSC 52 swallowed) or
target the wrong place.

```sh
#!/bin/sh
text="$1"
[ -n "$text" ] || exit 1

# 1. Neovim: we are inside a Neovim :terminal buffer. /dev/tty here is the
#    EMBEDDED pty, so OSC 52 written to it never leaves Neovim. Ask Neovim
#    to set the '+' register instead; its provider writes to nvim's stdout
#    (channel 2) = the real outer terminal.
if [ -n "$NVIM" ] && command -v nvim >/dev/null 2>&1; then
	tmp=$(mktemp "${TMPDIR:-/tmp}/lazygit-copy.XXXXXX") || tmp=""
	if [ -n "$tmp" ]; then
		printf '%s' "$text" > "$tmp"
		if nvim --server "$NVIM" --remote-expr \
			"setreg(\"+\", join(readfile(\"$tmp\"), \"\\n\"))" >/dev/null 2>&1; then
			rm -f "$tmp"; exit 0
		fi
		rm -f "$tmp"
	fi
fi

# 2. native helpers, only when a display is actually reachable
if [ -n "$WAYLAND_DISPLAY" ] && command -v wl-copy >/dev/null 2>&1; then
	printf '%s' "$text" | wl-copy 2>/dev/null && exit 0
fi
if [ -n "$DISPLAY" ]; then
	command -v xclip >/dev/null 2>&1 && { printf '%s' "$text" | xclip -selection clipboard 2>/dev/null && exit 0; }
	command -v xsel  >/dev/null 2>&1 && { printf '%s' "$text" | xsel -b -i 2>/dev/null && exit 0; }
fi

# 3. tmux (needs $TMUX to locate the server)
if [ -n "$TMUX" ] && command -v tmux >/dev/null 2>&1; then
	printf '%s' "$text" | tmux load-buffer -w - 2>/dev/null && exit 0
fi

# 4. OSC 52 straight to the controlling terminal.
#    Probe in a subshell: in POSIX sh a failed redirection is fatal.
if ( : > /dev/tty ) 2>/dev/null; then
	b64=$(printf '%s' "$text" | base64 | tr -d '\n')
	[ -n "$b64" ] && printf '\033]52;c;%s\007' "$b64" > /dev/tty 2>/dev/null && exit 0
fi

echo "no usable clipboard backend" >&2
exit 1
```

Then:

```yaml
os:
  copyToClipboardCmd: '/path/to/lazygit-copy.sh {{text}}'
```

Notes on the script:
- `printf '%s'` (not `printf %s` on the format) keeps `%` in filenames intact.
- `base64 | tr -d '\n'` is portable across GNU/BSD.
- The `/dev/tty` probe must be in a subshell — otherwise a failed
  redirection kills the whole script with exit 2 and you get no error
  message at all.

## Verifying a fix

Run LazyGit in a tmux session and check the tmux buffer, which proves the
bytes actually reached the terminal:

```bash
tmux new-session -d -s t; tmux set -g set-clipboard on
tmux send-keys -t t 'lazygit' Enter
# select a file, press ctrl+o
tmux show-buffer      # should print the relative path
```

To confirm what LazyGit hands the command, wrap it:

```sh
#!/bin/sh
printf '%s' "$1" > /tmp/probe.txt
exec /path/to/lazygit-copy.sh "$1"
```

To test the Neovim branch specifically, run the helper from a script inside a
`:terminal` buffer and watch the **outer** pty for an OSC 52 sequence — the
one inside the buffer is invisible from outside, which is exactly the bug.
Note that a `%` in the `:terminal` **command line** is a Vim file-name
expansion (`E499`), so pass tricky names through a script file instead of
typing them into `:terminal`.

## Upstream

- [#5724](https://github.com/jesseduffield/lazygit/issues/5724) — feature request: built-in tmux/OSC 52 fallback for headless SSH hosts (open)
- [#5816](https://github.com/jesseduffield/lazygit/pull/5816) — tmux and OSC 52 fallbacks (open)
- [#3595](https://github.com/jesseduffield/lazygit/issues/3595) / [#3597](https://github.com/jesseduffield/lazygit/pull/3597) — OSC 52 recipe, `base64 -w 0`, tmux passthrough
- [#1055](https://github.com/jesseduffield/lazygit/issues/1055) — same `exit status 1` over SSH
- [atotto/clipboard v0.1.4](https://raw.githubusercontent.com/atotto/clipboard/v0.1.4/clipboard_unix.go) — the LookPath-only probe
