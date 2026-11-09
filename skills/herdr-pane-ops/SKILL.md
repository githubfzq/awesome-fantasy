---
name: herdr-pane-ops
description: 在 herdr 终端工作区分屏/启动服务/操作 pane 时使用；勿混 iTerm2。
agent_created: true
---

# herdr pane 操作（herdr-pane-ops）

herdr（`/opt/homebrew/bin/herdr`）是独立于 iTerm2 的终端 workspace 管理器。**用户说"herdr tab"、"当前 herdr 会话"时指的是 herdr 自己的 pane 树，不要去操作 iTerm2**（两者同时运行且 iTerm2 里也有叫 herdr 的 tab，极易混淆——2026-10-29 实际误操作过一次：在 iTerm2 里 split 并启动了服务，用户纠正后全部回滚重来）。

## 判别：目标在哪个多路复用器

1. `herdr status` — server running 说明 herdr 活跃；`herdr pane list` 能看到带 `agent: hermes`、`cwd` 与当前会话匹配的 pane，即为目标环境。
2. **只认 herdr 的 pane id（形如 `w1:p3`）**，不要用 iTerm2 AppleScript。
3. 如果上一轮误在 iTerm2 操作过，先回滚：关闭误建 session（`close session N of tab`）、确认其拉起的进程已退出，再在 herdr 里重做。

## 常用命令（herdr 0.9.1 实测语法）

```bash
herdr pane list                      # 全部 pane（JSON），看 pane_id / tab_id / focused / cwd
herdr pane current                   # 当前会话所在 pane
herdr pane split <PANE_ID> --direction right --cwd <path> --no-focus   # 右侧分屏
herdr pane send-text <PANE_ID> '<command>
'                                   # 发命令；文本末尾带换行即回车
herdr pane read <PANE_ID>            # 读 pane 当前输出（JSON）
herdr pane send-keys <PANE_ID> enter # 补发回车
```

## 坑

0. **herdr pane 进程被 macOS「本地网络」权限拦**（2026-11-08 实测）：pane 里跑的进程连局域网设备报 `No route to host`，同一时刻用户前台终端同代码全通——herdr 不在前台终端派生链上，pane 进程拿不到本地网络授权。需要连局域网服务（adb、SSH 到 LAN 设备、自定义端口探测）时：让用户在自己终端跑，或由前台 python 起回环隧道让目标工具只碰 127.0.0.1。详见技能 android-wireless-adb。

1. **`herdr pane run <ID> -- 'cmd'` 和 `send-text --text ... --press-enter` 都不对**（该版本）：run 的 `--` 会被当作 shell 命令字面执行（`zsh: command not found: --`）；send-text 只接受位置参数 `<PANE_ID> <TEXT>`，换行符即回车。
2. send-text 发长命令可能被终端 readline 折行显示，但内容完整到达；验证以 `pane read` 输出和端口/进程探活为准，别只看渲染。
3. `pane read` 返回 JSON（`result.text`）；日志刷得快时 content 可能短暂为空，稍等再读。
4. 启动服务后不要只看 pane 输出确认——用 `lsof -iTCP:<port>` + curl 探活拿硬证据（本会话验证：服务日志正常滚动但 read 抓不全）。
5. venv 项目在 pane 里启动：`source .venv/bin/activate && exec <cmd>`，`exec` 让服务成为 pane 主进程，Ctrl+C 即停、不留孤儿。
6. **send-text 嵌套引号会被两层 shell 吃掉**：向 pane 传 `adb shell "cmd | grep -E \"x\""` 这类双层转义，内层引号到达时已破碎——命令执行了但输出恒为空，极易误判成"手机没日志"。正确姿势：把管道放到 Mac 侧执行，如 `adb shell logcat -d -t 80 2>&1 | grep adbd | tail -10`（`shell` 后不跟引号包整体）；ssh 远程命令同理。判别：同一命令不经 pane 直接跑一次对比输出。
7. **pane read 输出形态不稳定**：有时直接返回 pane 纯文本，有时是 JSON 包络（`result.text`）；重定向到文件后用 grep/tail 解析，不要硬依赖 json.load。

## 停止服务与 pane 生命周期

1. **Ctrl+C 用 send-keys，不是 send-text**：`herdr pane send-keys <PANE_ID> ctrl+c`。send-text 发 `C\n` 只是字面字符，不会被解释为中断信号。
2. **pane id 会失效**：服务进程退出后 pane 可能随之消失（`pane_not_found`），且下次 split 的 id 会变（如 w1:p4 → w1:p5）。重操作前**必须重新 `herdr pane list`**，不要复用记忆里的旧 id。
3. 停止确认：`lsof -nP -iTCP:<port> -sTCP:LISTEN` 无输出即端口已释放。

## 0.9.5 新能力（2026-11-01 实测）

- **agent 子命令是自动化正道**：`herdr agent list`（JSON，含每个 agent 的 `agent_session.value` 会话 ID 和 resume 终端标题）、`herdr agent prompt <TARGET> <TEXT> --wait --until idle|done`（提交 prompt 并等状态）、`herdr agent wait/read/send-keys/attach`。比裸 pane send-text + read 更可靠——prompt 有 blocked 检测（agent_blocked 时拒绝提交，防止打进权限弹窗）。
- **integration**：`herdr integration install <agent>` 装 18+ agent 的状态上报/原生会话恢复钩子；`herdr integration status` 看安装/过期。本机现状：hermes current v5；claude/codex/cursor outdated（要 `herdr integration install` 重装升级）。
- **会话 ID 直接可读**：`agent list` 的 `agent_session`（source 如 herdr:hermes）+ 终端标题就是 resume 命令（如 `hermes --resume 20261030_014934_67cf12`）。这是跨工具复用对话的关键接口——Paseo 等其他环境接力时从此取 ID。
- **worktree**：`herdr worktree create/open/remove` 管 git worktree 工作区。
- **状态机**：idle/working/blocked/done/unknown；blocked 判定刻意保守（只认已知批准 UI），误判 idle 时不要盲发输入。
- **更新**：brew 装的 herdr 不能用 `herdr update --handoff`（走 brew upgrade）。

## 验证清单

- [ ] `herdr pane list` 确认新 pane 在正确的 tab、cwd 正确
- [ ] send-text 后 `pane read` 看到命令被执行（或报错）
- [ ] 服务端口 lsof + curl 探活通过
- [ ] 若之前误操作过 iTerm2：确认已回滚干净