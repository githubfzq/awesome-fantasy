---
name: software-install-guide
description: 软件安装与 GitHub 资源下载通用指南。当需要在本机（macOS）、远程 Linux 服务器或云服务器上安装或升级软件、从 GitHub 下载 release 资源、配置二进制到 PATH、创建 systemd/LaunchAgent 常驻服务时使用。核心规范：GitHub 下载永远优先走 ghproxy 前缀代理加速（国内云服务器直连最快），下载后先校验再解压安装，安装幂等可重入。
agent_created: true
---

# 软件安装通用指南（software-install-guide）

规范"在用户的 Mac 本机与远程服务器上安装软件"的完整流程：选源 → 下载 → 校验 → 安装 → 常驻 → 验证。核心纪律是 **GitHub 资源必走代理加速** 与 **安装幂等**。

## 何时使用

- 从 GitHub 下载 release 二进制/源码包（最常见场景）
- 在 macOS / Ubuntu 服务器上安装命令行软件并配置 PATH
- 把软件配置为常驻服务（Linux systemd / macOS LaunchAgent）
- 既有软件升级到新版本

## 一、GitHub 资源下载（铁律：必走 ghproxy 前缀代理）

**链接格式为 URL 前缀代理**（不是改域名）：

```
https://<镜像域名>/https://github.com/<owner>/<repo>/releases/download/<tag>/<文件名>
https://<镜像域名>/https://github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz
```

**镜像优先级**（2026-08-21 实测，详见 `references/mirrors.md`）：

1. `gh-proxy.com`（首选，国内云服务器直连秒下）
2. `ghproxy.net`
3. `ghfast.top`
4. `gh.llkk.cc` / `github.akams.cn`（备用）

**执行策略（按下载目标机器选路）**：

| 目标机器 | 策略 |
|---|---|
| **国内云服务器**（如腾讯云 Lighthouse） | 直接在服务器上 `curl -L https://gh-proxy.com/<github-url>`，速度最快 |
| **本机 Mac** | 本机环境代理（127.0.0.1，系统代理 7890）访问这些镜像**很慢且易 502/中断**；最快路径是**先在国内云服务器上下载，再 `scp` 回本地**。小文件可直接试本地代理 + 镜像 |
| **公司内网服务器** | 若可直连公网，走镜像；否则"云服务器中转 → scp"链路 |

**下载辅助脚本**：`scripts/ghdl.sh <github-url> [输出文件]` 自动按镜像优先级轮询下载并校验 tarball 完整性，优先使用它。

**下载纪律**：
- 下载后先 `tar tzf <file> >/dev/null`（或对应格式校验）再解压，**禁止直接解压未校验的包**（半截文件会解出残缺二进制）
- 有官方 checksums 时必须校验：`sha256sum -c`（Linux）/ `shasum -a 256 -c`（Mac）
- 查最新版本：`curl -s https://api.github.com/repos/<owner>/<repo>/releases/latest | grep tag_name`（本机走环境代理通常可达；国内服务器访问 api.github.com 可能超时，此时直接去镜像站已知版本号）

## 二、安装规范（分平台）

### Linux 服务器（有 sudo）

- 二进制：`/usr/local/bin/<tool>`；配置：`/etc/<tool>/`
- 常驻服务：systemd 单元写入 `/etc/systemd/system/<tool>.service`，`systemctl daemon-reload && systemctl enable --now <tool>`
- systemd 单元模板（`Restart=on-failure` + `RestartSec=5s` + `LimitNOFILE=1048576`），参考 `references/install-patterns.md`

### Linux 服务器（无 sudo，用户级）

- 二进制：`~/.local/bin/<tool>`（确认在 PATH）；配置：`~/.config/<tool>/`
- 常驻：用户级 systemd `~/.config/systemd/user/<tool>.service` + `systemctl --user enable --now`（需 lingering：`sudo loginctl enable-linger <user>`，无 sudo 时用 `nohup`/`tmux` 兜底并告知局限）
- 需要提权执行安装脚本时，**先把脚本 scp 到远端 `/tmp/`，再 `echo <pass> | sudo -S bash /tmp/xx.sh`**——不要在 ssh 命令里拼 heredoc（会抢占 stdin 导致密码读失败）

### macOS 本机

- 优先 Homebrew：`brew install <formula>`（自带依赖管理和服务管理 `brew services`）
- 无 formula 的二进制：放 `~/.local/bin/`，确认 PATH 包含该目录
- 常驻：`~/Library/LaunchAgents/com.<vendor>.<tool>.plist`（`RunAtLoad` + `KeepAlive`），加载 `launchctl load -w <plist>`
- 注意：WorkBuddy 会话内 launchctl 用户域可能不可用（bootstrap 报 5: I/O error），此时让用户在自己的终端执行 `launchctl load`

## 三、安装幂等与验证

1. **先查现状再装**：`<tool> --version`、`systemctl status <tool>`、`which <tool>`——重复安装时报 `Text file busy`（运行中二进制被占用）或 `enable` 非零退出**不代表失败**，按现状判断
2. **安装后验证三步**：二进制可执行（`--version`）→ 服务 active（`systemctl is-active` / `launchctl print`）→ 功能实测（端口监听 `ss -tlnp` / `lsof -iTCP:<port>`、实际请求一次）
3. **防火墙**：云服务器新开端口必须去控制台层放行（腾讯云 Lighthouse 用 lighthouse-ops MCP `create_firewall_rules`），系统内无 iptables 可改；开完端口要实际连通性测试
4. 升级流程：停服务 → 覆盖二进制 → 起服务 → 验证；配置文件格式注意大版本变更（如 frp v0.52+ 从 ini 换 TOML）

## 资源

- `references/mirrors.md` — ghproxy 镜像详细对照表（可用性、适用场景、测试方法）
- `references/install-patterns.md` — systemd/LaunchAgent 单元模板、scp 中转完整命令模板
- `scripts/ghdl.sh` — GitHub 资源多镜像轮询下载脚本（自动校验）
