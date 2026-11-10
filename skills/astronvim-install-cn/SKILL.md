---
name: astronvim-install-cn
description: Use when installing AstroNvim in a China-network environment
version: 1.0.0
license: MIT
author: hermes
metadata:
  hermes:
    tags: [astronvim, neovim, china, mirrors, installation]
---

## When to Use
Use when the user asks to install AstroNvim on Linux from the official AstroNvim docs
(docs.astronvim.com, repo AstroNvim/AstroNvim, template AstroNvim/template), and the machine
has a China-region network where GitHub release assets are slow or blocked.

Note on naming: the project is **AstroNvim**; the official docs' isolated-install alias is
`astronvim="NVIM_APPNAME=astronvim nvim"`. "AstroVim" (without the n) was the pre-rename name
of the project and is not a current official identifier — the old github.com/astrovim org and
AstroNvim/astrovim repo no longer exist.

# Installing AstroNvim with China mirrors (official flow)

## Steps that work
1. Read the official docs first: `https://docs.astronvim.com/` (Getting Started) and
   `https://docs.astronvim.com/reference/alt_install/` (headless + isolated install).
   Requirements listed by AstroNvim: Neovim >= 0.11 stable, tree-sitter CLI, C compiler,
   clipboard tool, truecolor terminal; optional ripgrep, lazygit, gdu, bottom, Python, Node.
2. GitHub acceleration (direct github.com release assets and objects.githubusercontent.com
   time out): use `https://v6.gh-proxy.org/https://github.com/<path>`.
   For git clones, set globally:
   `git config --global url."https://v6.gh-proxy.org/https://github.com/".insteadOf "https://github.com/"`
   This makes lazy.nvim's `git clone` of lazy.nvim and plugin clones work unmodified.
   `api.github.com` and `codeload.github.com` are reachable directly; only release
   assets need the proxy.
3. Official install = clone template into `~/.config/nvim`, `rm -rf ~/.config/nvim/.git`,
   then start nvim once (or `nvim --headless +q`) to install plugins.
4. Dependencies without root access: `apt-get download <pkg>` + `dpkg-deb -x pkg dir`,
   then copy the binary into `~/.local/bin` (works for xclip, fd-find -> fd).
5. tree-sitter CLI: release binary `tree-sitter-linux-x64.gz` needs GLIBC >= 2.39.
   On Ubuntu 22.04 (GLIBC 2.35) use v0.25.10, not the latest release.
   Mason's `tree-sitter-cli` package ships the same too-new binary — overwrite
   `~/.local/share/nvim/mason/packages/tree-sitter-cli/tree-sitter-linux-x64` with the
   working 0.25.10 binary.
6. Mason downloads go through `require("mason.settings").current.github.download_url_template`;
   override it in `~/.config/nvim/lua/plugins/mason.lua` with the proxied template, and set
   pip/npm mirrors via `mason.settings` `pip.install_args` / `npm.install_args`.
7. Mason packages install headlessly with:
   `nvim --headless "+lua require('mason-registry').get_package('X'):install(); vim.wait(N, ...)" +q`
   (mason-tool-installer's `run_on_start` only fires on a real VimEnter, so headless
   `+q` never triggers it).
8. Verify with `nvim --headless "+checkhealth astronvim" +q` and
   `nvim --headless "+lua print(vim.inspect(require('lazy.core.config').plugins))" +q`
   (filter `p.err`).

## Pitfalls
- `TSInstall`/`TSInstallSync` are not commands in current nvim-treesitter (main branch);
  use `require('nvim-treesitter.install').install({'lua'})`.
- `+AstroVersion` fails with E481 because the command takes no range; run it without `+`.
- Headless nvim exits while Mason is still installing; must `vim.wait` for completion.
