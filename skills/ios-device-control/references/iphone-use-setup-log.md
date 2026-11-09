# iPhone-use 安装实录（2026-10-29 会话）

本次会话的逐步执行记录，供排障对照。

## 环境快照

- macOS 15.7.7, Xcode 26.2 (17C52), Node 24.14.0, npm 11.9.0
- iPhone 16, iOS 26.6.2, 开发者模式已开启
- 设备: udid `00008140-0002759C3443801C`, core_device_id `08268F04-C72B-5552-BD81-212767E2B471`（注意两者不同，configure 用 udid）
- Apple Team: 证书 `Apple Development: u201312526@alumni.hust.edu.cn (ARNHN3RZNS)`，证书 OU 实为 `2N697H3F5J`
- 选定配置: team_id=ARNHN3RZNS, bundle_id=com.fanzuquan.wda.runner, local_port=18100, device_port=8100

## 已完成

1. 克隆 iPhone-use → `~/Public/Projects/iPhone-use`
2. MCP 服务验证: py3.10 手工 JSON-RPC initialize + tools/list 成功，20 个工具
   （pua_observe/find/tap/swipe/type_text/press_button/screenshot/launch_app/wait/scroll_find/collect_list/apps/doctor/ready/metrics/setup/batch/screen/screen_frame/screen_action）
3. 写入 `~/.hermes/config.yaml` mcp_servers.iphone_use（backup: config.yaml.bak-iphoneuse）
4. `pua_setup configure` 成功写入 `~/.local/share/iphone-use/config.json`
5. WDA 16.14.0 (commit d17782422d55ff1e5e0ceb74eb1fd509cc0c35b6) 已 SSH 克隆到
   `~/.local/share/iphone-use/runtime/WebDriverAgent`

## 失败与原因

- fetch job 03d7a90d: HTTPS git clone GitHub 443 超时 → 改手动 SSH 克隆（成功）
- build job 3cdf7f1d: `No Accounts: Add a new account in Accounts settings` +
  `No profiles for 'com.fanzuquan.wda.runner.xctrunner'` → **Xcode 未登录 Apple ID，等用户手动登录后重跑 build**
- 系统 python3.9（Xcode 自带）无 `mcp` 包且 pip 无源可用；pyenv python3.10 已有 mcp 包，统一用 python3.10

## 下次继续（用户登录 Xcode 后）

```
pua_setup action=build   → 轮询 status
pua_setup action=start   → 轮询直到服务 ready
pua_ready                → ready=true
pua_apps                 → 列 APP 验证
# 原始终端验证方式: python3.10 server/iphone_use.py --doctor
```

提醒用户: 退出 iPhone Mirroring、保持手机解锁、可能需在手机上信任开发者证书
（Settings → General → VPN & Device Management）。
