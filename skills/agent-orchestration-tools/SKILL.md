---
name: agent-orchestration-tools
description: Use when user asks about Paseo or agent orchestration tools.
---

# 多编码 Agent 编排工具（agent-orchestration-tools）

调研结论（2026-11-01，来源：GitHub README、HN Show HN、codeagentswarm 横评）。

## 工具格局

同类工具都是"多 agent 并行工作台"的变体：
- **Paseo**（getpaseo/paseo）— 自托管 + 全端覆盖（desktop/mobile/web/CLI），差异化最强
- CodeAgentSwarm — 桌面工作区
- T3 Code — "open-source control plane for coding agents"
- Superset — "code editor for the AI agents era"

## Paseo 要点

- Apache-2.0（README 最新标注；早期为 AGPL-3.0），~15.5k stars（2026-08），单人开发（boudra），无遥测/无跟踪/无强制登录
- 架构：本机 daemon（TypeScript）管理 agent 进程，客户端经 WebSocket 连接；**直接包装第一方 agent CLI 原样运行，不碰 OAuth token**
- Provider：Claude Code / Codex / Copilot / OpenCode / Pi / Antigravity / Muse Code；前置条件 = 至少装好一个 agent CLI
- 核心：并行 agent 各自独立 git worktree；内置编排（agent 可拉起/对话其他 agent）；编辑器/diff/终端/PR/浏览器分屏；手机端是完整原生 App（iOS/Android）
- 语音：本地 Parakeet + Kokoro + Sherpa ONNX，不上云

## 常用命令

```bash
paseo run --provider claude/opus-4.6 "task"       # 启动 agent
paseo ls / attach <id> / send <id> "follow-up"    # 列出/跟随/追加
paseo daemon pair                                  # 生成手机配对二维码（E2EE relay）
paseo --host ssh://user@host ls                    # 经 SSH 管理远程 daemon
```

## 本机状态（fanzuquan 的 Mac）

- v0.14.0 arm64 已装 /Applications/Paseo.app（2026-11-01，SHA512 校验通过），daemon 监听 127.0.0.1:6767
- 手机配对：App 内 Settings → 主机 → Pair Device（relay 或 Tailscale 直连）
- headless/远程机器：`npm install -g @getpaseo/cli`
- 配置：~/.paseo/config.json（daemon.listen 等启动项，改后 `paseo daemon restart`）

## 安装套路（Electron DMG 类应用通用）

见技能 software-install-guide §二 macOS 本机"DMG 图形应用标准套路"与"Electron 应用的官方校验和"（latest-mac.yml 的 sha512 是 base64 非 hex）。
