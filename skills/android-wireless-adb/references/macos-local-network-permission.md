# macOS 15 本地网络权限拦截：取证矩阵（2026-11-08 晚）

## 问题
探究「后台进程连局域网 EHOSTUNREACH」到底是 App 干扰还是系统机制。结论：**macOS 15 内核级「本地网络」隐私权限，非第三方 App 干扰**。

## 排除清单（全查过）
| 嫌疑 | 证据 | 结论 |
|---|---|---|
| 系统防火墙 | socketfilterfw disabled, block-all/stealth off | 排除 |
| pf 过滤器 | /dev/pf 无规则 | 排除 |
| 第三方网络扩展 | 仅 Tailscale 一个；昨天退出后拦截依旧 | 排除 |
| VPN/代理劫持 | en0 直连路由正常，ARP 有手机 MAC | 排除 |
| 路由/ARP 故障 | 前台进程同目标秒连成功 | 排除 |
| TCC 用户库 | 268 条记录无一条 kTCCServiceLocalNetwork | 授权弹窗从未触发 |

## 拦截的行为特征
- `connect()` 立即返回 `errno=65 EHOSTUNREACH`，**耗时 0.000s**（内核 socket 层直接拒绝，SYN 都没发）
- 防火墙类拦截通常 EPERM/EACCES；本地网络权限故意伪造「路由不可达」假象，静默无提示
- 目的地无关：网关/手机任意端口全拦；127.0.0.1 回环全放行

## 决定性对照矩阵（同一台 Mac，2026-11-08）
| 进程 | 二进制签名 | 派生者 | 结果 |
|---|---|---|---|
| 转发器 fwd_daemon.py | com.apple.python3 (Apple, 59GAB85EFG) | launchd LaunchAgent | **放行** |
| 同 /usr/bin/python3 | com.apple.python3（同一二进制） | launchctl submit 临时任务 | **放行** |
| 同 /usr/bin/python3 | com.apple.python3（同一二进制） | Hermes 会话 | **拦截** |
| homebrew python 3.11 | org.python.python（Homebrew 自签） | launchd | **拦截** |
| homebrew socat / adb 36 | ad-hoc 签名 | 任意 | **拦截** |
| /usr/bin/nc | com.apple.nc（Apple） | 前台终端 | 放行 |
| SDK adb 34 | Apple notarized (59GAB85EFG) | fork-server daemon | **拦截**（daemon 谱系问题） |

## 判定模型：两层判据，缺一不可
1. **签名身份层**：Apple 平台签名（com.apple.*）默认放行；未知/ad-hoc/第三方签名默认静默拒。
2. **进程谱系层**（responsible process）：权限随责任进程链继承。launchd 会话派生=可信；GUI 终端前台链=可信；daemon（adb fork-server）/非终端后台链（Hermes/herdr）=继承不到授权。

唯一免 GUI 交互的可靠组合：**launchd（LaunchAgent 或 launchctl submit）+ Apple 签名解释器**（/usr/bin/python3、/usr/bin/nc 等）。

## 正规出口
系统设置 → 隐私与安全性 → 本地网络 → 手动「+」添加 App 授予签名身份。用户面板为空时说明从未触发过弹窗，须手动添加。授权后该签名身份的进程（含 daemon？未验证）可直连 LAN。

## 手动写 TCC 库无效（2026-11-08 实测，重要负结果）
试图给 org.python.python 手写 TCC 用户库（kTCCServiceLocalNetwork + csreq 签名需求 + auth_value=2），插入成功但拦截依旧。**tccd 日志给出答案**：
```
tccd: Failed to find a service object for kTCCServiceLocalNetwork
```
**本地网络权限根本不走 TCC**（苹果官方 TN3179 + Quinn/Howard Oakley 社区确认）。它是 macOS 15 新增的独立隐私系统：独立状态存储、无 CLI 管理、tccutil 不适用。苹果还承认 bug FB16131937：短命进程的授权弹窗根本不会弹出，只会无限静默失败——这正是 homebrew CLI 工具的处境。
**官方全局豁免（TN3179，macOS 15.5+，最彻底出口）**：
```bash
sudo defaults write com.apple.network.local-network AllowedWiFiLocalNetworkAddresses -array "192.168.1.0/24"
# 同域还有 AllowedEthernetLocalNetworkAddresses（有线网段）
```
把整个网段声明为「非本地网络」，**所有程序免授权访问**，苹果给 CI/开发机的正规开关。写库实验残留的 TCC 行无害（tccd 不识别该 service），清理用 DELETE 即可。
**TCC 与本地网络权限的关系（科普要点）**：TCC（Transparency, Consent & Control）管敏感数据类——通讯录/照片/麦克风/摄像头/屏幕录制/完全磁盘访问，存 TCC.db，tccutil 可重置。本地网络权限长得像 TCC（同一设置面板、per-app 开关）但不是 TCC——独立系统、无工具链，这是 macOS 15 新增的并行隐私系统。误写 TCC.db 不会被读，也不会报错，纯无效功。

## 复用探测方法
```bash
# 签名查询
codesign -dv <binary> | grep -E "Identifier=|TeamIdentifier"
# 快速/慢速失败判别（0.000s=内核权限层；>2s=真网络问题）
python3 -c "import socket,time;s=socket.socket();s.settimeout(5);t=time.time();\ntry: s.connect(('IP',port))\nexcept OSError as e: print(e.errno, time.time()-t)"
# launchd 对照
launchctl submit -l t1 -o /tmp/o -e /tmp/e -- /usr/bin/python3 probe.py; sleep 5; cat /tmp/o; launchctl remove t1
```
