# Local REA install state — this Mac (2026-11-01)

## Installed paths

| Component | Path | Version |
|---|---|---|
| rea CLI | ~/.npm-global/bin/rea | 6.8.0 |
| node@24 (REA runtime) | /opt/homebrew/opt/node@24/bin/node | 24.22.2 (keg-only) |
| Ghidra | ~/Tools/ghidra_12.1.4_PUBLIC | 12.1.4 |
| JDK | /opt/homebrew/opt/openjdk@21 | 21.0.13 |
| Hermes skill copy | ~/.hermes/skills/reverse-engineer-anything/ | v59 |

## Hermes MCP registration (config.yaml)

```yaml
mcp_servers:
  rea:
    command: ~/.npm-global/bin/rea
    args:
      - mcp
    enabled: true
    env:
      GHIDRA_INSTALL_DIR: ~/Tools/ghidra_12.1.4_PUBLIC
      JAVA_HOME: /opt/homebrew/opt/openjdk@21
```

Backup of pre-setup config: ~/.hermes/config.yaml.rea.backup

## Environment quirks on this machine

- System node is 24.14.0 at /usr/local/bin/node (TOO OLD for REA). Brew node is 25.6.0 (also outside REA's supported range). Always prefix PATH with /opt/homebrew/opt/node@24/bin when running `rea` from a shell.
- Shell proxy needed for outbound: `export https_proxy=http://127.0.0.1:7899`.
- /bin/echo is a universal binary with x86_64 + arm64e slices (no plain arm64); thin with `lipo -thin x86_64`. It is also fully stripped (no local symbols) — bad smoke-test target.
- Native decompile binary was built locally: Ghidra/Features/Decompiler/os/mac_arm_64/decompile (Mach-O arm64, from `make ghidra_opt ARCH_TYPE="-arch arm64"`).

## Remaining optional engines (not installed)

- Hopper: `rea setup --install-hopper` handles it (paid, $129).
- IDA: set REA_IDA_MCP_CONFIG (mrexodia/ida-pro-mcp).
- jadx (APK): REA_JADX_MCP_JAR must point to jadx-headless-mcp 0.7.1 JAR.
- Kuna: REA_KUNA_COMMAND (verified 1.833).

## Smoke-test status

Decompilation path verified up to Ghidra analysis (provider_version 12.1.4 returned, target imported, unix-socket transport). Final pseudocode output untested — test target (/bin/echo slice) was stripped. Next verification: compile a small hello binary with symbols and run `rea decompile <bin> --procedure main --format md`.

## Later additions (2026-11-07 session)

- `brew install jadx` (1.5.6) — used directly for APK Java-layer decompile, bypassing REA's jadx provider entirely. See references/android-apk-reversing.md for the workflow.
- Project venv at ~/Public/Projects/obsidian-1dairy/.venv has pycryptodome (for backup-crypto repro scripts).
