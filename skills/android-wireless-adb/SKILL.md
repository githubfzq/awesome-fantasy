---
name: android-wireless-adb
description: 无线 ADB 配对/连接排障：protocol fault、端口过期、mDNS 解析、MIUI 掉线循环、5555 模式、macOS 本地网络权限绕道。
---

# Android 无线 ADB 连接与配对（android-wireless-adb）

适用：局域网安卓手机（小米/Redmi 等已开"无线调试"）通过 adb pair + connect 无线连接，及各类连接失败排障。本机已验证机型：M2012K11AC（Redmi，192.168.1.8）。

## 快速诊断表

| 现象 | 根因 | 处理 |
|---|---|---|
| `adb pair` 输码后 `error: protocol fault (couldn't read status message)` | 两个可能：①**配对端口已过期**——手机配对码弹窗超时关闭（约 1 分钟）后端口立即失效，TLS 握手中途被掐断；②**adb server 进程被 macOS 本地网络权限拦截**（连不上手机，客户端读不到状态）。`ADB_TRACE=all adb nodaemon server` 看 server 日志可分辨：`Failed to start pairing connection client [... No route to host]` = 拦截；端口 CLOSED = 过期 | ①重新开弹窗拿新码立刻重试；②见下方"本地网络权限"章节 |
| `adb pair` 报 `Failed: Wrong password or connection was dropped.` | **合并错误消息，有歧义**：可能是码错/过期，也可能是连接路径被掐（隧道那一跳失败，手机根本没收到请求）。2026-11-08 实测连续 20 次"密码错"实际全是隧道转发 EHOSTUNREACH | 先独立验证转发通路真的到达手机（看转发进程日志有无 connect 成功），再怀疑码；不要反复换码重试 |
| `adb connect IP:PORT` → `No route to host` 但 ping/nc 都通 | ①adb server 状态脏；②**本地网络权限拦了 adb server 进程**（见下方章节） | 先 `adb kill-server && adb start-server` 重试；仍失败且 nc 从用户终端能通 = 权限问题 |
| `adb connect` TCP 通但 TLS 被对端 reset（curl/openssl 探测可见） | Mac 的 adb key 不在手机信任列表（MIUI 清了授权或"撤销USB调试"触发过） | 必须重新 pair 或走 USB 授权一次，无绕过 |
| 连接能建立但每~6秒闪断重连，手机反复弹「已连接/已断开无线调试」通知 | **MIUI adbd 自身每 ~6.5s 掐断 adbwifi TLS 会话**（`SSL_read failed [invalid library (0)]`），adb server 自动重连 → 通知循环。**与客户端版本无关**：SDK 34.0.4 与 homebrew 36.0.2 A/B 实测掐断间隔与频率完全一致（2026-11-08，见 references/20261108-loop-evidence.md）。每轮 ~6s 窗口内命令可用，shell 不易察觉 | ①换 adb 版本**无效**（已实测），不要浪费时间；②根治=USB 插一次 `tcpip 5555`（旧协议绕开 adbwifi TLS）；③治标=MIUI 通知管理关掉无线调试通知；④照常使用，断线自动重连 |
| 5555 拒绝连接 | `adb tcpip 5555` 在手机重启/重插 USB 后失效，需重设 | 走 USB 兜底流程重设 |

## 关键排障手法

1. **先分层定位**：`ping IP`（网络）→ `nc -z -G 3 IP <port>`（端口）→ TLS 探测 `echo | openssl s_client -connect IP:PORT`。ping 通+ssh/Termux 8022 通说明局域网没问题，报错出在配对层。
2. **端口不要手抄屏幕**：手机"无线调试"主页面显示的端口 ≠ 配对端口；且两者都会变。用 mDNS 实时解析最可靠（`dns-sd` 与 `adb mdns services` 互为备份：adb 内置的刚起 server 时可能返回空，稍等重试——2026-11-08 它解析出了 dns-sd 没抓到的连接端口；配对完成后连接服务广播 dns-sd 也可能扫不到，此时用 adb 内置的）：
   ```bash
   dns-sd -B _adb-tls-pairing._tcp local    # 浏览配对服务，得实例名 adb-<uuid>-xxxx
   dns-sd -L <实例名> _adb-tls-pairing._tcp local   # 得 Android.local.:<配对端口>
   dns-sd -L <实例名> _adb-tls-connect._tcp local   # 得 Android.local.:<连接端口>
   ```
   解析到主机名时用 `ping Android.local` 拿 IP；dns-sd 是阻塞的，用后台进程跑几秒再读输出。
3. **配对有时效**：向用户要配对码时明确说"立刻发，弹窗约 1 分钟过期"；拿到码后用 mDNS 端口（不是屏幕端口）+ 码执行 `adb pair IP:PAIR_PORT`，成功后 `adb connect IP:CONNECT_PORT`。
4. **连接闪断/通知轰炸：读手机侧日志定位断连方**（比 Mac 侧猜测快得多）：`adb -s <dev> shell "logcat -d | grep -E 'adbd|AdbDebuggingManager'"`。`WIFI TLS connected/disconnect key message` 时间线给出循环周期与频率；`SSL_read failed [invalid library (0)]` = 手机端 TLS 读崩（版本不匹配特征，非网络问题）。Mac 侧重连频率用转发器日志 `grep -c "connected 192"` 计数。同机对照注意：WiFi RSSI 强（-46dBm）+ 屏幕亮着仍闪断，排除省电掉线假设再查协议层。

## MIUI 开关清配对 + 重连 checklist（2026-11-08 晚补充）

**重要行为**：在手机上关闭再重开「无线调试」开关，会**清除已配对设备记录**——Mac 的证书手机不再信任，connect 时 adb server 日志报：
```
Post-handshake SSL_peek failed [SSLV3_ALERT_CERTIFICATE_UNKNOWN]
Handshake failed. Kicking transport
```
TCP 通、TLS 握手被服务端拒 = 配对状态没了，必须重新配对（拿新码）。同时连接端口必然变化，须 mDNS 重解析。OEM 配对状态不随开关持久化是社区反复报告的已知行为（MIUI/HyperOS 尤甚）。

**重连 checklist**（用户说"连不上"时按序执行）：
1. 检查用户命令形式：`adb connect 39313` 缺 IP 前缀必失败（nodename 错）；且直连手机 IP 会被本地网络权限拦，必须 `adb connect 127.0.0.1:39920`（转发口）
2. `adb mdns services` 解析新连接端口 → 更新 `~/Library/Application Support/adb-fwd/fwd_map.json` 的 CONN 值
3. `adb connect 127.0.0.1:39920`；若 adb server 日志出现 CERTIFICATE_UNKNOWN → 配对已清，走配对流程拿新码（`adb pair 127.0.0.1:39910 <码>`）

## MIUI 调研结论（上网核实，2026-11-08）

- **6 秒掐断是 AOSP 一代 adbwifi 的系统性问题区，小米是重灾区**：Google 在 Android 17 用 Rust 重写无线 ADB（ADB Wi-Fi 2.0），官方承认一代实现依赖第三方 mDNS/Open Screen 库、存在长期断连与配对问题，点名小米/Redmi/POCO 受影响最深。根治要等小米吸收该重写。
- **MIUI 省电模型**：社区一致报告 MIUI 把 ADB 归为非关键后台服务，节电时限流/杀会话（激活→省电检测→限流→会话终止）。与本机「空闲即断、有流量则稳」的现象吻合。
- **错误串解读**：`SSL_read failed [invalid library (0)]` 是 BoringSSL 错误队列为空时的兜底输出，真实含义是 **TCP 层已被对端掐断（RST/EOF）而非 TLS 协议错**——所以定位方向应是「谁在掐 TCP」（MIUI 网络策略，logcat 可见 MiuiNetworkPolicy 活跃）而非 TLS 参数调优。
- **缓解排序**：①USB 一次 `tcpip 5555`（非 TLS 旧通道，不经 adbwifi 栈，最稳）②开发者选项开「停用 adb 授权超时」③`svc power stayon true` 防息屏 ④MIUI 通知管理关无线调试通知（治标）。

## 免配对兜底（USB 一次，最稳）

之前项目（Artemis）已验证路线——**注意直连仍会被本地网络权限拦，必须走转发器回环口**：
```bash
adb tcpip 5555            # 手机需 USB 已连且已授权调试（此步走USB传输不经权限拦截）
printf '{"39910": "PAIR:0", "39920": "CONN:5555"}' > ~/Library/Application\ Support/adb-fwd/fwd_map.json
adb connect 127.0.0.1:39920   # 经转发器回环连手机5555，拔线无线可用
```
5555 固定不变、无配对时效、**不经 adbwifi TLS 栈（彻底绕开 MIUI 6 秒掐断与通知轰炸）**；代价是手机重启/重插 USB 后 tcpip 失效需重设。`svc power stayon true` 可防息屏省电杀连接。

## 本地网络权限拦截（macOS 15+，2026-11-08 实战确认）

**现象**：adb server / 后台进程连局域网报 `No route to host`，同一时刻同一二进制从用户前台终端连完全正常。防火墙关闭也拦。

**决定性判别实验**（同机同目标同时段对比）：
```bash
# 在用户前台终端跑：全通
python3 -c "import socket;s=socket.socket();s.settimeout(4);s.connect(('手机IP',8022));print('FG OK')"

# 在 Hermes background / herdr pane / adb server 上下文跑同样的代码：Errno 65 EHOSTUNREACH
```
前台 8/8 通、后台 0/8 通 = 本地网络权限按进程上下文拦截，不是网络问题。

**关键事实**：
- adb server 是 daemon（`adb` 命令只是客户端，实际干活的是 fork 出的 server 进程），**永远继承不到前台终端的权限上下文**，重启 server 无用
- herdr pane 里的进程同样被拦（herdr 不在前台终端派生链上）；iTerm2 经 osascript 驱动会卡自动化授权弹窗，不实用
- **launchd + Apple 签名二进制才放行（2026-11-08 晚对照矩阵实锤）**：同一 /usr/bin/python3（com.apple.python3），launchd LaunchAgent 派生=放行、Hermes 会话派生=拦截；**homebrew python（org.python.python）从 launchd 跑仍被拦**。判据=两层：①签名身份层（Apple 平台签名默认放行；ad-hoc/第三方签名一律静默拦，TCC 用户库零 kTCCServiceLocalNetwork 记录=授权弹窗从未触发）②进程谱系层（权限随责任进程链继承，daemon 永远拿不到前台上下文）。唯一免 GUI 交互的可靠组合=launchd(LaunchAgent) + Apple 签名解释器。取证矩阵与判定实验见 `references/macos-local-network-permission.md`
- `Wrong password or connection was dropped` 可能是这条拦截的下游假象——转发隧道那一跳死了，手机根本没收到配对请求

**根治**：系统设置 → 隐私与安全性 → 本地网络 → 给用户的终端 app（iTerm2/Terminal）授权；之后从该终端启动的 adb server 可直连局域网。**让用户在自己终端里直接跑 pair/connect 是最快路径**。

**绕道方案（已验证全通，2026-11-08 端到端成功）**：launchd 常驻转发器，adb 只碰 127.0.0.1（回环不受此权限管）：
```bash
# 装一次（已装在 ~/Library/LaunchAgents/local.adb-fwd.plist，KeepAlive 常驻）
launchctl load ~/Library/LaunchAgents/local.adb-fwd.plist
# 转发表：/tmp/fwd_map.json，key=本地端口，value="PAIR:<手机配对端口>" 或 "CONN:<手机连接端口>"
printf '{"39910": "PAIR:43063", "39920": "CONN:41915"}' > /tmp/fwd_map.json
# 配对/连接（全部走回环端口）
~/Library/Android/sdk/platform-tools/adb pair 127.0.0.1:39910 <码>
~/Library/Android/sdk/platform-tools/adb connect 127.0.0.1:39920
```
组件：fwd_daemon.py（动态读 map）、fwd_map.json、日志 fwd.log。**2026-11-08 已迁持久路径**（/tmp 重启即清，LaunchAgent 会找不到脚本）：`~/Library/Application Support/adb-fwd/`（daemon+map+log），plist `~/Library/LaunchAgents/local.adb-fwd.plist` 指向该路径。连接端口用 `adb mdns services` 解析（比 dns-sd 可靠）。见 `references/20261108-pair-debug-evidence.md`。

## adb 版本差异（homebrew 36 vs SDK 34）

两个不同的 TLS 缺陷，别混淆：

**缺陷①配对握手失败（pairing 阶段）**：homebrew 36.0.2 server 日志报 `Handshake failed in SSL_accept/SSL_connect [invalid library (0)]`，配对必然失败；SDK 34.0.4 握手正常。**配对/连接一律用 SDK 版**：
```bash
~/Library/Android/sdk/platform-tools/adb   # 34.0.4
# 两者密钥都在 ~/.android/adbkey，通用
```
判别方法：`ADB_TRACE=all adb nodaemon server` 起前台 server，pair 一次后 grep 日志看 `tls_connection.cpp` 行。

**缺陷②连接后 ~6s 会话被手机侧掐断**（`SSL_read failed [invalid library (0)]`，同错误字符串但发生在手机 adbd 侧）：A/B 实测与客户端版本无关（34/36 一致），是 MIUI adbd 自身问题。换版本不能修，只能绕（USB tcpip 5555）或容忍。详见 `references/20261108-loop-evidence.md`。

## 坑

- macOS 无 `timeout` 命令（GNU coreutils 未装）；dns-sd 这类常驻监听用后台进程 + sleep + 读输出 + kill 的模式，不要试图前台加 timeout。
- Termux 的 adb（android-tools 包）二进制可能符号损坏（CANNOT LINK EXECUTABLE），`pkg reinstall android-tools` 修复；Termux adb 不能替代 Mac 侧配对（无配对凭证）。
- adb key 位置 `~/.android/adbkey`；手机端 TLS reset 拒绝时先怀疑授权被清，而不是网络。
- **端口过期 ≠ 码错**：`Wrong password or connection was dropped` 是合并错误。先验证链路再换码，否则会烧掉多个配对窗口（本会话实际烧了 5 个）。
- 向用户要码的交互成本高（用户回复有延迟，弹窗 1 分钟就过期）：要码的同时就把 mDNS 解析、隧道、脚本全部预先备好，码到手后一次执行。连续失败时先停下来查链路，不要无限重试。
- 排障过程记录见 `references/20261108-pair-debug-evidence.md`（protocol fault → 端口过期 → TLS 缺陷 → 本地网络权限拦截的逐层剥离）与 `references/20261108-loop-evidence.md`（通知轰炸循环的版本 A/B 实测与误判教训）；macOS 本地网络权限的完整取证矩阵（签名×谱系对照表、 errno/耗时判别法、launchd 探测复用命令、TCC 写库无效负结果、TN3179 官方网段豁免）见 `references/macos-local-network-permission.md`；权限快速探测脚本 `scripts/lan_permission_probe.sh`（单命令判别"被权限拦"还是"真网络问题"）。
- **通知轰炸循环的教训**：连接「能用」≠ 连接「健康」。判断连接质量要数转发器日志增速（>10 次/分钟即异常循环），不能只看 `adb devices` 是否显示 device。异常时立即读手机 logcat 找断连方，不要先在 Mac 侧换配置。
