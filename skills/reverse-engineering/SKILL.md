---
name: reverse-engineering
description: Use for REA/Ghidra reverse engineering of binaries/APKs.
---

# Reverse Engineering (REA + Ghidra) — machine toolchain & workflows

Complements the upstream-installed skill `reverse-engineer-anything` (REA's own tool-routing docs; do NOT edit it — `rea setup` overwrites it). This skill holds THIS machine's toolchain state, install fixes, and case workflows.

## Toolchain on this machine
- `rea` CLI v6.8.0: `~/.npm-global/bin/rea`. REQUIRES node@24: `export PATH="/opt/homebrew/opt/node@24/bin:$PATH"` (system /usr/local node 24.14.0 and brew node 25.6.0 both fall outside REA's engines `^22.23.4 || ^24.22.1 || >=26.12.1`).
- Ghidra 12.1.4: `~/Tools/ghidra_12.1.4_PUBLIC`. Needs `JAVA_HOME=/opt/homebrew/opt/openjdk@21` (system java 11 rejected).
- Hermes MCP: `~/.hermes/config.yaml` → `mcp_servers.rea` with `env: {GHIDRA_INSTALL_DIR: ~/Tools/ghidra_12.1.4_PUBLIC, JAVA_HOME: /opt/homebrew/opt/openjdk@21}`. Registered via `rea setup --client hermes --skill-client hermes --yes` (auto-backup at `config.yaml.rea.backup`). Restart the Hermes session to mount the `mcp__rea__*` tools.
- Engineless tools (usable immediately): JS/ASAR analysis, APK package & signature inspection, PE/ELF notes, pyc/BEAM/SQLite/GGUF/HAR/pcap. Native decompilation = Ghidra only (Hopper 商业未装; IDA/Kuna/jadx 未配).

## Pitfalls (learned the hard way)
- Ghidra 12.1+ official zips ship NO macOS native decompiler (upstream ghidra#9536, REA#1994): doctor reports `native_decompiler` missing and decompile fails with `architecture_unsupported` on thin binaries. Build it (~15 s, needs Xcode CLT + bison/flex):
  ```
  cd ~/Tools/ghidra_12.1.4_PUBLIC/Ghidra/Features/Decompiler/src/decompile/cpp
  make ghidra_opt ARCH_TYPE="-arch arm64" OSDIR=mac_arm_64 \
    decompiler_dir="$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/os/mac_arm_64"
  mkdir -p "$decompiler_dir" && install -m 755 ghidra_opt "$decompiler_dir/decompile"
  ```
  Verify: `rea doctor --client hermes --provider ghidra` → `native_decompiler` healthy.
- Universal (fat) Mach-O rejected by Ghidra: `lipo <bin> -thin x86_64 -out thin` first. Newer system binaries may be x86_64+arm64e with NO arm64 slice — thin to x86_64 instead.
- Stripped smoke-test targets (e.g. /bin/echo) expose no `main` symbol → "Unknown Ghidra procedure name". Compile an unstripped test binary instead of blaming the toolchain.
- After setup, `rea doctor` still lists ok:false for hopper/ida/jadx/kuna + unregistered clients — those are optional engines/clients, expected, not errors.
- GitHub downloads need proxy: `export https_proxy=http://127.0.0.1:7899`.

## Android APK workflow
1. Unknown package name: official site HTML → store links → app-store landing page embeds `"packageName":"..."` plus a direct imtt.dd.qq.com APK URL. The .apk-looking URL may return HTML — parse the page, fetch the real URL, then verify with `aapt2 dump badging` (`~/Library/Android/sdk/build-tools/34.0.0/aapt2`).
2. Analyze: REA `inspect_android_package` (manifest/classes/refs), `inspect_apk_signature` (v1–v3, repack detection). Java-layer pseudocode needs jadx (`REA_JADX_MCP_JAR` = jadx-headless-mcp 0.7.1, not yet installed; plain `brew install jadx` works for manual digging). Native `.so` → Ghidra arm64.
3. Engineless quick CLI: `npx -y rea-agents@latest analyze-javascript-application <dir-or-asar> --json`.

## Pull APK from LAN Android via Termux SSH (XiaoMi 192.168.1.8:8022)
- `pm` must use `--user 0` (default routes to user 10 → SecurityException).
- Termux `adb` binary can be broken (`CANNOT LINK EXECUTABLE`); `pkg reinstall android-tools` does NOT fix it. Don't depend on adb — APKs are world-readable:
  `path=$(ssh -p 8022 host "pm path --user 0 <pkg> | sed 's/package://'")` then `ssh -p 8022 host "cat '$path'" > app.apk`.
- Verify the app still exists first: `pm list packages --user 0 | grep <kw>` — if uninstalled, get the APK from the store (workflow above) instead of hunting the device.
- List 3rd-party apps by filtering vendor noise: grep -viE 'com.android|com.google|com.miui|com.xiaomi|com.tencent|com.qualcomm|vendor.qti|com.qihoo|org.telegram'.

## References
- `references/rea-install.md` — full install/verify recipe with exact commands
- `references/case-1diary.md` — 一本日记 (com.chenupt.day) 备份解密进行中：包名发现链、备份密文格式、下一步计划
