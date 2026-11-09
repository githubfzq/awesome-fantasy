# Xcode Team ID 歧义：证书 CN 括号 vs OU（2026-10-29 会话）

## 现象

xcodebuild 报错：

```
error: No signing certificate "iOS Development" found: No "iOS Development" signing
certificate matching team ID "ARNHN3RZNS" with a private key was found.
```

同时 keychain 里确实存在有效证书：

```
security find-certificate -c "Apple Development" -p login.keychain-db | openssl x509 -noout -subject
# subject= /UID=4W45WZZZB8/CN=Apple Development: u201312526@alumni.hust.edu.cn (ARNHN3RZNS)/OU=2N697H3F5J/...
```

CN 括号里的 ID 是 `ARNHN3RZNS`，但证书的实际 OU（= 真实 Team ID）是 `2N697H3F5J`。两者不一致时 xcodebuild 按 DEVELOPMENT_TEAM 配置值匹配证书 OU，找不到就报上面的错。

## 排障步骤

1. 读证书 OU 确认真实 Team ID：
   ```sh
   security find-certificate -c "Apple Development" -p ~/Library/Keychains/login.keychain-db \
     | openssl x509 -noout -subject
   ```
   OU 字段才是 xcodebuild 实际匹配的 Team ID；CN 括号里那个只是显示名的一部分，可能是别的 team 的。
2. 让用户打开 Xcode → Settings → Accounts，看登录账号下显示的 Team ID 是哪个。
3. 以 Xcode Accounts 面板 / 证书 OU 为准重新 configure：
   ```
   pua_setup action=configure udid=<udid> team_id=<真实ID> bundle_id=<bundle>
   ```
   然后重跑 build。

## 关联坑

- "No Accounts: Add a new account in Accounts settings" = Xcode 从未登录过 Apple ID，证书再全也没用，登录是硬前提。
- keychain 有证书 ≠ Xcode 账号已登录（证书可能来自另一台机器同步/旧安装）。
- 登录后个人免费 Team 的 profile 需要设备 UDID 注册，`-allowProvisioningUpdates` 由 iPhone-use 的 build 命令自动带上，无需手动加。
