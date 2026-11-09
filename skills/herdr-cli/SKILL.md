---
name: herdr-cli
description: 操作 herdr 终端的 pane（分屏/发命令/读输出）；herdr tab 非 iTerm2。
agent_created: true
---

# herdr CLI pane 操作（herdr-cli）

herdr（/opt/homebrew/bin/herdr）是独立的终端 workspace 管理器，有自己的 server（socket `~/.config/herdr/herdr.sock`）。用户的工作流以 herdr 为主；`herdr tab` 指 herdr 自身的 workspace/tab，**不是 iTerm2 的 tab**。收到「在当前 herdr tab 里新建 pane」类请求时，直接走本技能，不要碰 iTerm2。

## 核心 workflow

1. **确认目标 pane**：
   ```bash
   herdr pane list      # 全部 pane，含 pane_id (w1:p3)、tab_id、cwd、focused
   herdr pane current   # 当前会话所在 pane
   ```
2. **分屏**（right = 左右分屏，down = 上下）：
   ```bash
   herdr pane split w1:p3 --direction right --cwd /path/to/project --no-focus
   ```
   返回新 pane_id。`--no-focus` 避免抢走用户当前焦点。
3. **在新 pane 里启动服务**：`send-text` 文本末尾带换行符即回车：
   ```bash
   herdr pane send-text w1:p4 'source .venv/bin/activate && exec openbiliclaw start
   '
   ```
4. **验证**：`herdr pane read w1:p4` 看输出（输出可能滞后，sleep 几秒再读）；对 Web 服务再用端口探活（`lsof -nP -iTCP:<port> -sTCP:LISTEN` + curl）做独立确认——pane read 拿不到内容时端口证据更可靠。

## 坑（Pitfalls）

1. **`send-text` 的选项参数无效**：`--text <txt> --press-enter` 和 `pane run <id> -- <cmd>` 在 0.9.1 都会把参数字面打进终端（报 `command not found: --text` 之类）。正确用法只有位置参数 `send-text <PANE_ID> <TEXT>` + 文本自带换行。如果 pane 里已打进错误命令，先 send 一条 `true` 类无害命令或按用户情况处理。
2. **herdr ≠ iTerm2**：两套系统并存。误在 iTerm2 里操作后要清理：关闭误建 session，并确认随 pane 启动的子进程（服务）已退出。iTerm2 AppleScript 分屏的正确语法是对 session 调 `split vertically <session> with profile "Default"`（vertical=左右），`create session with default profile` 不是合法调用。
3. **herdr 的 AppleScript 不可用**（它不是常规 macOS 自动化目标），一律走 CLI 子命令；`herdr <subcommand> --help` 有详尽用法。
4. `pane read` 返回 JSON，`result.text` 是终端内容；直接管道 tail 也行。

## 相关技能

- `herdr-nvim`（用户自有，勿改）：herdr 的 nvim 侧栏插件排错。
