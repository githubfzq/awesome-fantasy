# Case: 一本日记 backup decryption (IN PROGRESS, 2026-11-01)

## Goal
Decrypt the app's exported backup to recover diary entries for import into the
user's Obsidian vault. Backup zip on local Mac:
`~/Public/Projects/obsidian-1dairy/data/diary_backup_all_20251108_222248_v3.zip`
(same file also at `/sdcard/日记备份/` on the phone).

## Package name discovery chain (reusable pattern)
1. Termux `pm list packages --user 0` — 480 packages, NO diary app → **app was uninstalled** from the XiaoMi phone
2. `pm path` guesses all failed. Install-source hints on device: none.
3. Official site 1diary.me → Huawei store link exposed `com.xf.day` (Huawei listing id; NOT the real Android package)
4. Yingyongbao (Tencent myapp) landing page HTML for the app contains BOTH:
   - `"packageName":"com.chenupt.day"` ← real package
   - direct URL `http://imtt.dd.qq.com/sjy.00022/.../<HASH>.apk?fsname=com.chenupt.day_1.96.65.apk`
5. Downloaded & verified with `aapt2 dump badging`:
   `package: name='com.chenupt.day' versionCode='4694' versionName='1.96.65'`, label "One Diary"

Lesson: `.apk`-looking URLs from app stores may serve HTML pages; parse the page for
`packageName` + `microdown.myapp.com` / `imtt.dd.qq.com` URLs, then re-fetch and verify with aapt2.

## Local artifacts (this session)
- APK: `/tmp/diary-apk/1diary_direct.apk` (99MB, com.chenupt.day 1.96.65) — /tmp may be wiped; re-download via the chain above if gone
- Decoy APKs pulled from the phone that were NOT the diary app (labels: Simple / 得到大脑; two obfuscated-pkg adult apps, deleted)
- Extracted cipher files: `/tmp/diary-data/` (source.json 1,045,784 b64 chars, model.json, category.json, tag.json, version)

## Cipher format (analyzed)
- All json/`version` files: whole-content Base64 → binary, length always multiple of 16
- 16-byte blocks with zero repeats across 49,021 blocks → CBC/CTR/GCM, NOT ECB
- Each of version/category.json/tag.json is exactly ONE 16-byte block (24 b64 chars) —
  usable as decryption oracles (plaintext is probably `1` or `[]` or similar short JSON)
- source.json = 784,336 bytes ciphertext; images/audio in the zip are NOT encrypted (plain jpg)

## Backup naming clue
`diary_auto_backup_e3eb6c5243_e741c141-5614-49d3-a80c-c50a393d97b6.zip` — the hex segment
`e3eb6c5243` (5 bytes) appears in every backup filename; possibly a key-salt or account hash.

## Next steps (when resumed)
1. jadx the APK (com.chenupt.day): `brew install jadx` then `jadx -d out 1diary_direct.apk`
   - or REA route: set `REA_JADX_MCP_JAR` (jadx-headless-mcp 0.7.1) for MCP workflow
2. Search decompiled source for backup/export code: keywords Cipher, AES, SecretKeySpec,
   PBKDF2, "source.json", "diary_backup", "v3", MD5/SHA of password
3. Expect password-based KDF (user must supply the backup password they set in-app)
4. Verify round-trip on the one-block `version` file first (fast oracle), then source.json
5. Convert decrypted JSON → Markdown into the Obsidian vault; map UUID attachments in the zip to entries

## Re-download APK if /tmp cleared
```
# fetch landing page of 一本日记 on a17.app.qq.com / sj.qq.com search, grep for
# "packageName" and imtt.dd.qq.com URL (they rotate hashes), then:
curl -sL -e "https://a17.app.qq.com/" -o 1diary.apk "<imtt URL>"
~/Library/Android/sdk/build-tools/34.0.0/aapt2 dump badging 1diary.apk | grep '^package'
```
