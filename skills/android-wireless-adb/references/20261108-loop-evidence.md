# 无线调试通知循环证据（2026-11-08）

## 现象
手机（M2012K11AC，MIUI/Android 13）每几秒弹「已连接无线调试」/「已断开」通知，连续轰炸。ADB 连接本身可用（shell 命令全部成功执行）。

## 逐格证据（手机侧 adbd logcat）
```
17:04:33.871  ADB wifi device disconnected
17:04:40.661  ADB wifi device disconnected
17:04:49.526  ADB wifi device disconnected
17:04:56.231  ADB wifi device disconnected
17:05:22.641  ADB wifi device disconnected
```
每轮：`SSL_read failed [invalid library (0)]` → `ADB wifi device disconnected` → 0.3-0.6s 后 `New TLS connection` → `Handshake succeeded` → `adbd_wifi_secure_connect: connected host-28` → 系统弹通知。累计 187 次 TLS 连接。间隔 ~6.5-6.7s，极规律。

握手日志每次都出现 `Invalid base64 key`（E 级），连接仍成功——装饰性噪音，不要追查。

## 版本 A/B 测试（推翻 homebrew 36 TLS 缺陷的单一归因）
| 客户端 | 掐断间隔 | secure_connect 每分钟 |
|---|---|---|
| SDK adb 34.0.4 | ~6.5s | ~9 |
| homebrew adb 36.0.2（server 在 herdr pane 启动） | ~6.7s | ~8 |

结论：`invalid library (0)` 与客户端版本无关，是 MIUI adbd 对 adbwifi TLS 会话的自身处理缺陷（建连 ~6s 后必掐）。换客户端版本（含 SDK/homebrew 互切）不能修复。

注意区分两个 TLS 缺陷：
- **配对握手失败**（pairing 阶段 `Handshake failed in SSL_accept`）：homebrew 36 有此问题，SDK 34 正常 → 配对用 SDK 版
- **连接后 ~6s 会话被掐**（`SSL_read failed`）：与客户端版本无关 → 只能绕（USB tcpip 5555）

## 误判教训
17:06:30 起出现 40s 窗口无 SSL_read 失败，当场误判「循环已停」；17:09 恢复循环。
**验证必须用 60s 间隔 `grep -c secure_connect` 的 delta 指标、观察 ≥2 分钟**——单刻安静不算数。

## 已排除假设
- WiFi 抖动/省电：同周期 SSH(8022) 连接全程稳定、RSSI -46、链路 286Mbps、屏幕亮屏中——网络层干净
- mDNS 自动重连：设 `ADB_MDNS_AUTO_CONNECT=0` 后循环依旧——重连是 adb server 对已登记设备的标准 reconnect，非 mDNS 触发
- Tailscale/防火墙：连接路径已走 launchd 转发器回环（127.0.0.1:39920→手机 CONN 口），macOS 本地网络权限已绕开

## 转发器侧旁证
循环期间 launchd 转发器日志（fwd.log）每分钟 14-18 次 `connected 192.168.1.8:<conn_port>`；lsof 采样 39920 口可见 adb 客户端源端口每轮更换。循环停止时 lsof 稳定为 2 条 ESTABLISHED。

## 修复排序
1. **USB 插一次 + `adb tcpip 5555`**：旧式协议完全绕开 adbwifi TLS 层，5555 端口固定（手机重启后需重设）——唯一根治
2. MIUI 通知管理关闭无线调试通知：治标，循环继续但不再打扰
3. 照常使用：6s 窗口内命令执行正常，偶发断线重试即可

## 后续会话补充（同日晚）
- **方案 A（换 adb 36 经转发器连）已实测无效**：36 版 server 下掐断间隔 ~6.7s、每分钟 ~8 次，与 34 版完全一致。版本路线正式关闭，不要再试任何客户端版本组合。
- **重开无线调试开关会清除配对**：用户当晚重开开关后 connect 报 `Post-handshake SSL_peek failed [SSLV3_ALERT_CERTIFICATE_UNKNOWN]`（adb server trace 实锤：TCP 通、TLS 被服务端拒）→ 必须重新 pair，且连接端口变为 39313（mDNS 重解析）。详见 SKILL.md「MIUI 开关清配对」节。
- **上网调研定调**：6 秒掐断属 AOSP 一代 adbwifi 系统性问题（Android 17 Rust 重写 ADB Wi-Fi 2.0 的官方动机，小米点名重灾区）；`invalid library (0)` = BoringSSL 错误队列空时的兜底输出，真实含义是 TCP 已被对端掐断——定位方向是「谁掐 TCP」（MIUI 网络/电源策略）而非 TLS 参数。调研摘要已并入 SKILL.md「MIUI 调研结论」节。
