---
name: hermes-memory-provider
description: 配置 Hermes 外部记忆库（OpenViking 等_provider）到局域网/远程时使用。
agent_created: true
---

# Hermes 外部记忆库 Provider 接入

## 一、机制（与 MCP 无关，别混）

Hermes 外部记忆走 **memory provider 插件**，不是 MCP server。可用 provider：openviking, mem0, honcho, hindsight, holographic, retaindb, byterover；同时只能激活一个；内置 MEMORY.md/USER.md 始终生效。

```bash
hermes memory status                              # 查当前 provider 与插件清单
hermes config set memory.provider openviking      # 启用
hermes memory off                                 # 回退到内置 only
```

- OpenViking 插件本体：`~/.hermes/hermes-agent/plugins/memory/openviking/`（README.md 有完整 env 表和 viking_* 工具说明）。
- 连接配置写在 **profile 的 .env**（默认 `~/.hermes/.env`），不是 config.yaml：

```text
OPENVIKING_ENDPOINT=http://<host>:1933   # 默认 127.0.0.1:1933
OPENVIKING_API_KEY=<key>                 # API-key 模式必填
OPENVIKING_ACCOUNT=default               # 无 key 的信任模式才用
OPENVIKING_USER=default
OPENVIKING_AGENT=hermes                  # peer ID；多机共享同一库时各设不同值（hermes-mac / xiaomi）
```

## 二、服务器侧取 key

OpenViking 服务器的凭据通常在：
- `~/.openviking/keys/users.txt` — 每行 `name=<key>`
- `~/.openviking/ovcli.conf` — 服务器自己的 CLI 配置，含 api_key

直接 ssh 上服务器读。

## 三、验证清单（config 写入 ≠ 链路通）

1. `curl http://<host>:1933/health -H "Authorization: Bearer <key>"` → `{"healthy":true,...}`
2. MCP 端点握手：POST `/mcp` 带 initialize JSONRPC，应返回 serverInfo
3. `hermes memory status` 显示 `Provider: openviking / available`
4. **端到端**：`hermes chat -q "调用 viking_browse 列出 viking:// 根目录"` 拿到真实目录列表才算通

## 四、坑

### 1. IPv6/mDNS：getaddrinfo 把公网 IPv6 排前面

树莓派等设备 mDNS 会通告公网 IPv6（运营商前缀 2409:...）。Python `getaddrinfo` 把 IPv6 排在 IPv4 前，httpx 按序连接 → `No route to host` 或请求被系统代理劫持成 502。**curl 有 Happy Eyeballs 回退所以"看起来通"，完全掩盖问题**。诊断：对比 `dscacheutil -q host -a name <host>` 与 Python getaddrinfo 的地址顺序。

修复：**ENDPOINT 直接写 IPv4 字面量**（如 `http://192.168.1.28:1933`），不要用 .local 域名。

### 2. macOS TCC 本地网络权限拦 Homebrew Python（2026-11-07 实测）

Homebrew 的 python3.11（Hermes 运行时）若未获"本地网络"隐私授权，连接**任何**局域网 IP 均报 `[Errno 65] No route to host`，而系统 /usr/bin/python3、curl、nc 全部正常。ad-hoc 签名身份变化可致既有授权失效。

- 修复：系统设置 → 隐私与安全性 → 本地网络 → 打开 Python；或 `tccutil` 重置后重新触发授权弹窗。
- **识别模式**：这会让"用 Hermes 本身连局域网服务"的验证全部失败，看起来像服务器挂了——用 nc / 系统 python / curl 三方对照，若只有 Homebrew Python 失败即是 TCC。
- 系统代理叠加干扰：`scutil --proxy` 若显示 http 代理（如 127.0.0.1:7899），内网请求可能被劫持返回 502，与 TCC 症状混杂。

## 五、环境事实（2026-11-07）

- OpenViking 服务：raspberryfzq.local（192.168.1.28）:1933，openviking v1.27.0（server v0.5.3），auth_mode=api_key，账户 fanzuquan。hermes 专用 key 在 raspberry `~/.openviking/keys/users.txt`。
- 本机 Mac Hermes 已配置：config.yaml `memory.provider=openviking` + ~/.hermes/.env 三个变量（端点用 IPv4）。待 TCC 授权后生效。
- XiaoMi（Termux，ssh XiaoMi）待配置：同样三变量 + `hermes config set memory.provider openviking` + `sv restart $PREFIX/var/service/hermes-gateway`。
