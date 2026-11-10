---
name: obsidian-copilot-opencode-permissions
description: Use when Obsidian Copilot's OpenCode agent keeps asking for permission confirmations, or when Copilot's Auto/Safe permission picker is missing or broken.
---

# Obsidian Copilot + OpenCode 权限确认无法关闭的排查

## 症状
- Copilot（Agent Chat）里用 OpenCode 后端做 bash / 写文件，每一步都弹 "Permission required" 卡片。
- 权限选择器里没有 **Auto**（只有 Safe），或者切 Auto 无效。

## 根因（已实测确认）
Copilot 的 OpenCode 后端把权限选择器映射到 OpenCode 的 **ACP `mode` configOption**：

```
default (Safe) -> agent "copilot-build"   （Copilot 注入，bash/edit = "ask"）
auto           -> agent "build"           （OpenCode 原生全权限代理）
```

源码位置（反编译 `main.js`）：`bFt = { default: "copilot-build", auto: "build" }`，
OpenCode 后端 `getModeMapping()` 返回 `{kind:"configOption", configId:"mode", canonical:{default:"copilot-build", auto:"build"}}`。
UI 用 `Lqn()` 取 canonical 与 OpenCode `session/new` 返回的 `mode` 选项的交集，
所以 **`build` 不在 OpenCode 的 mode 列表里 → Auto 选项直接消失**。

`oh-my-openagent` (OMO) 插件会在配置加载时把 `build` 强制改写为
`{ mode: "subagent", hidden: true }`（源码 `assembleSisyphusEnabledConfig()`）。
于是 Auto 永远无法生效，会话停在 `copilot-build`（ask 规则）上 → 每次都弹权限。

## 关键陷阱
- **仅在 opencode.jsonc 里写 `"agent": {"build": {"mode": "primary"}}` 无效**：OMO 每次加载配置都会把它重置为 subagent+hidden。必须同时阻止 OMO 改写（禁用 Sisyphus 或移除插件）。
- OMO 启用时 `plan` 也会被 hidden。
- Copilot 启动 opencode 时用 `OPENCODE_CONFIG_CONTENT` 注入配置；**该变量一旦被用户自定义，Copilot 会完全用你的内容替换它注入的安全配置**（包括 copilot-build 的 ask 规则）——这是最后手段，会废掉 Safe/Auto 分层。

## 验证手法（无需打开 Obsidian）
在宿主机上直接驱动 ACP 复刻 Copilot 的行为：

```bat
@echo off
set "OPENCODE_CONFIG_CONTENT=C:\path\to\copilot-cfg.json"
cd /d D:\obsidian\tech
"%USERPROFILE%\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe" acp --cwd D:\obsidian\tech
```

`copilot-cfg.json` 内容（Copilot 实际注入的形状）：
```json
{"agent":{"build":{"permission":{"external_directory":{"D:/obsidian/tech/**":"allow"}}},
"copilot-build":{"mode":"primary","permission":{"bash":"ask","edit":"ask",
"external_directory":{"D:/obsidian/tech/**":"allow"}}}},"default_agent":"copilot-build"}
```

然后用 Node 走 JSON-RPC：`initialize` → `session/new`（看返回的 `configOptions` 里 id="mode" 的 options）→
`session/set_config_option {configId:"mode", value:"build"}` → `session/prompt`。

判定：
- `mode` 选项含 `build` 且 `set mode=build` 成功 → Auto 可用。
- 切到 `build` 后 bash/写文件 **0 次 `session/request_permission`** → 修复成功。
- 对照：留在 `copilot-build` 应仍会弹权限（证明 Safe 分层没被破坏）。

## 排查时的环境陷阱（WSL）
- WSL 里跑 Windows 二进制时，**环境变量不会传给 Windows 进程**，除非设 `WSLENV=VAR/u`。用 `OPENCODE_CONFIG_CONTENT` 做实验时，用 `/mnt/c/Windows/System32/cmd.exe /c` 包一层 bat 文件来设变量才可靠。
- `HOME` / `XDG_CONFIG_HOME` 覆盖对 Windows 版 opencode **无效**（它用 Windows 的 HOME/APPDATA）。要隔离测试只能改真实的 `%USERPROFILE%\.config\opencode\opencode.jsonc`。
- 判定配置是否生效用 `opencode debug config`，不要靠 `debug config --pure`。

## 修复方案
- **方案 A（推荐）**：从 `%USERPROFILE%\.config\opencode\opencode.jsonc` 移除 `"plugin": ["oh-my-openagent@latest"]`。
  代价：Obsidian 内也失去 OMO 的 Sisyphus 编排。
- **方案 B（保留 OMO）**：在 `~\.omo\omo.jsonc` 设 `sisyphus_agent.disabled: true`（写在 `[opencode]` 包装层内），
  并在 opencode.jsonc 设 `"agent": {"build": {"mode": "primary"}}` 让 build 保持可见。
- **方案 C（不推荐）**：自定义 `OPENCODE_CONFIG_CONTENT` 覆盖 Copilot 注入。

## 注意
- "Auto" 对 OpenCode 实际等于 `build` 全权限，会绕过所有细粒度限制，只在可信 vault 用。
- 版本错位常见：插件记录的 opencode 版本可能与实际二进制不同，以 `opencode --version` 为准。
