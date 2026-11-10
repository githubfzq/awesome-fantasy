# Android APK Reversing Workflow (jadx + Termux extraction)

Class workflow for "extract an Android app's APK and reverse its logic". Verified end-to-end 2026-11 on the 一本日记 (com.chenupt.day) backup-crypto break.

## 1. Get the APK

**From a LAN phone over SSH (Termux)** — no root needed for base.apk:
```bash
# list packages: plain `pm list packages` fails with INTERACT_ACROSS_USERS_FULL on MIUI; add --user 0
ssh -p 8022 <phone> "pm list packages --user 0 | grep -iE '<keyword>'"
# resolve path then pull: APKs are world-readable, plain cat over ssh works even when Termux adb is broken
ssh -p 8022 <phone> "pm path --user 0 <pkg> | sed 's/package://'"
ssh -p 8022 <phone> "cat '/data/app/~~.../base.apk'" > app.apk
```

**Package name unknown / obfuscated (e.g. com.ZQOnW.YTGJj):**
1. Pull candidate APKs, identify with aapt2 (no brew formula; use local SDK build-tools):
   `~/Library/Android/sdk/build-tools/34.0.0/aapt2 dump badging app.apk | grep -E '^package|application-label:'`
2. If the app is uninstalled or label is useless, find the official download page. Store landing pages leak both the real package name and a direct APK URL in their HTML: `grep -aoE '"packageName":"[^"]+"|https?://[^" ]+\.apk' page.html`. App-store fallback chains (official site → vendor store page → direct APK) resolved a renamed app in minutes.
3. Beware vendor pages that return HTML instead of APK (应用宝 wraps downloads); the landing HTML itself contains the direct `imtt.dd.qq.com` APK link.

## 2. Decompile (Java layer)

`brew install jadx` then `jadx -d out/ --no-res --threads-count 6 app.apk` (never pass both `-j` and `--threads-count`; single-threaded fallback with `-j 1 --no-res` is enough for a first pass). Do NOT bother with REA's jadx provider (REA_JADX_MCP_JAR) unless you need MCP integration — plain jadx CLI + grep covers static Java-layer work.

## 3. Find the crypto

```bash
grep -rln 'javax.crypto|SecretKeySpec' jadx-out/sources/   # ignore alipay/tencent SDK noise
grep -rn 'UtilClass\.(a|c|encrypt|decrypt)(' jadx-out/sources/  # find callers → hardcoded passwords live here
```
Typical Chinese-app pattern: a small AESCrypt util (key=SHA-256(password), fixed or zero IV, AES/CBC/PKCS7, Base64 NO_WRAP) with per-file literal passwords at each call site. Grep the string literals out of the caller — the app's "password-protected export" is usually just these constants, NOT the user's login credentials.

## 4. Reproduce in Python

System python has no Crypto/Cryptography. User denies system pip — use uv:
```bash
uv venv .venv && uv pip install --python .venv/bin/python pycryptodome
.venv/bin/python decrypt.py
```
- **uv "tcp connect error: Connection refused"**: uv inherits `http_proxy/https_proxy/all_proxy` from the shell; if that proxy port is dead, even `--index-url` overrides fail. Fix: strip them per-invocation — `env -u http_proxy -u https_proxy -u all_proxy uv pip install ...`. Verify the network is actually fine first (`curl -sI https://pypi.org`); if direct TLS works, the proxy env is the culprit, not PyPI.
Reusable template: scripts/aes_b64_decrypt.py in this skill.

## Worked example: 一本日记 v3 backup (2026-11)

- key = SHA-256(password).digest(), IV = 16 zero bytes, AES/CBC/PKCS7, output Base64
- passwords (from m3/C1501.java): source.json=wxaj19sd, category.json=usdfi8op, tag.json=91knu3nj, model.json=ssd00dsd, version=uqwjhd0l
- Durable scripts + outputs live in the user's project: ~/Public/Projects/obsidian-1dairy/ (scripts/decrypt_1diary.py, scripts/export_md.py, decrypted/ = 523 diary markdown 2019-2025 + images). Do NOT keep working scripts only under /tmp — macOS purges it between sessions and references rot.
- **Exporter idempotency pitfall**: if the export script names same-day files by appending suffixes (_2, _3) but never clears old output, reruns accumulate duplicates (523 → 1569 files). Fix: `shutil.rmtree(out_md_dir)` + rebuild at the start of main(). Verify export scripts by running twice and asserting the file count is unchanged.
- zip attachment coverage: source.json referenced 83 image UUIDs, zip contained 44 — exporter itself drops attachments; don't chase the missing ones as a decryption bug.
