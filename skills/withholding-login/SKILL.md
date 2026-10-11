---
name: withholding-login
description: "在 Parallels Windows 11 VM 中一键登录/关闭「自然人电子税务局（扣缴端）」。单入口 auto_login.sh 自动启动应用、填申报密码表、截验证码（PNG 落到 Mac 共享盘）、点登录，返回结构化 STATUS 供决策表分支；close_app.sh 处理多级退出弹窗并兜底退出进程。当用户要登录/关闭扣缴端、或登录界面点哪都嘀、或遇到验证码/输入法/隐形弹窗问题时使用。"
agent_created: true
---

# 扣缴端登录/关闭（自然人电子税务局 扣缴端 · VM）

## 何时用

- 登录 / 关闭 Parallels VM（"Windows 11"）里的「自然人电子税务局（扣缴端）」。
- 登录界面"点哪都嘀"、验证码刷新不了、密码被输入法组词等问题（多半已被状态机自动处理，见下）。
- 相关技能：`tax-withholding-vm`（VM 基础设施/运行库修复/系统错误框）、`keepass-lookup`（取申报密码）、`withholding-captcha-crop`（验证码截取原理）。

## Agent 快速路径（推荐 · 全程 1~2 次调用）

登录 = 调一次 `auto_login.sh`（自动：启动应用 → 填表 → 截验证码 / 点登录），按 `STATUS` 决策表分支；
关闭 = 调一次 `close_app.sh`。**不要**再逐个跑 `login_declare.py` / `capture_captcha.py` / `pull_file.sh`（已内聚）。

```bash
# 1) 取申报密码（keepass-lookup；库与主密码不确定时问用户；绝不落盘/写记忆）
CRED="$(python3 ~/.workbuddy/skills/keepass-lookup/scripts/kp_get.py \
          --db <agents.kdbx 路径> --master-file <主密码文件路径> --search 自然人电子税务局)"
PASS="$(printf '%s' "$CRED" | python3 -c 'import sys,json;print(json.load(sys.stdin)["password"])')"
#   坑：keepassxc-cli 用「show -s -a UserName -a Password」只返回两行纯值且空字段会错位，
#   kp_get.py 已改为全量 show -s + 行首字段名解析；库仅主密码保护，不要传 --key-file（会 HMAC 失败）

# 2) 登录（密码也可经环境变量 WITHHOLDING_PASSWORD 传入，避免出现在命令行）
WITHHOLDING_PASSWORD="$PASS" ~/Documents/rpa/auto_login.sh --unit "修文县关珍养殖场"
#    （--unit 可省，默认内置该单位；--dry-run 只体检不点击）

# 3) 关闭
~/Documents/rpa/close_app.sh
```

## STATUS 决策表（Agent 只看最后一行 STATUS=… 分支）

| STATUS | 含义 | Agent 动作 |
|---|---|---|
| `already_logged_in` | 主界面已可见（幂等） | ✅ 完成，无需操作 |
| `dry_run` | 只读体检+定位，未点击（`located` 含控件矩形） | 正常；按需进入正式登录 |
| `captcha_required` | 表单已填好、验证码图已截好 | 读 `captcha_mac`（默认 `~/Documents/rpa/captcha.png`）识别 4 位码 → 带 `--captcha` 重跑（见下） |
| `success` | 登录成功（`main_rect`） | ✅ 完成 |
| `rejected` | 登录被拒（**非验证码类**：密码错/账号异常） | 🛑 停机，看 `modal_text`/`screen` 人工处理；**绝不自动重试** |
| `modal_blocked` | 有阻塞模态弹窗且未授权自动关闭 | 看 `modal_text`/`screen`；确认无害后可加 `--auto-close-modal` 重跑 |
| `timeout` | 点登录后超时未进主界面、无弹窗 | 看 `screen`；重跑一次或人工检查 |
| `start_timeout` | 自动启动后等待登录窗超时 | 可能弹「系统错误」框，转 `tax-withholding-vm` 排查 |
| `not_started` | `--no-start-app` 且登录窗不可见 | 正常；去掉 `--no-start-app` 即可自动启动 |
| `error:<step>` / `parse_error` | 脚本失败（如 `error:preflight`=缺密码） | 按 `failed_step` 修参数后重跑 |

### 验证码路径（仅登录失败后出现 · 每轮 2 次调用）

1. 第 1 次 `auto_login.sh --password …` → `STATUS=captcha_required`，`captcha_mac` 即 Mac 侧 PNG（脚本已自动刷新+截好，**无需** pull_file 回传）。
2. Read 识别 4 位码（看不清/超时 → 直接重跑第 1 步换新码，不要硬猜）。
3. 第 2 次 `auto_login.sh --password … --captcha <4位码>` → 按决策表分支：
   - 码错/超时：脚本自动关弹窗并截**新**码 → 又回 `captcha_required`，回到第 2 步（每轮 2 次调用，最多建议 3 轮）。
   - 密码错误等非验证码类：`rejected`，停机。

### 关闭

```bash
~/Documents/rpa/close_app.sh
# STATUS=closed  主窗/登录窗均不可见且扣缴端进程已退出
# STATUS=partial 有残留（看 JSON 的 final_modal/process）
# STATUS=error:* 脚本失败
```
关闭 = 真实点击系统关闭按钮 → 循环处理退出确认弹窗（`Tfrm_MsgDlgRich`『确认信息』/`Tfrm_MsgDlg`『提示信息』）→
窗口隐藏（托盘化）后自动对 `TApplication` 发 WM_CLOSE，仍不退则 taskkill 兜底。

## 硬约束（不可绕过）

- **只用「申报密码登录」**（`spDeclare`）；禁实名登录（扫码/手机号/CA 证书）与账号密码登录。
- 密码唯一来源 KeePass 条目「自然人电子税务局扣缴端」的 password 字段（申报密码）。
- 有验证码框但未提供验证码 → **拒绝点登录**（防密码错误累计锁定账号）。
- 被拒弹窗只有确认是「验证码/超时」类才自动关闭并换码；非验证码类**停机交人工**。
- 密码/验证码日志只记长度（mask），绝不落明文；凭据不写记忆/不落盘。
- 状态机已内置幂等：主界面可见直接 `already_logged_in`；登录窗不可见自动启动应用（`start_app=false` 可关）。

## 常见坑（速查）

| 现象 | 处理 |
|---|---|
| `STATUS=error:preflight` | 没给密码；用 `--password` 或环境变量 `WITHHOLDING_PASSWORD` |
| 验证码总超时 | 直接重跑截新码（验证码极短命）；不要拿旧图硬猜 |
| 登录界面点哪都嘀 | 隐形 `Tfrm_MsgDlgRich` 挡窗——`modal_blocked` 时看截图确认，无害则 `--auto-close-modal` |
| 密码被输入法组词 | 已内置 `WM_SETTEXT` 绕过 IME，勿改 |
| 应用启动后无登录窗 | `start_timeout` → 可能弹「系统错误」框，转 `tax-withholding-vm`（装运行库/重启 VM） |
| 关闭后 STATUS=partial | 看 JSON `process`/`final_modal`；手动检查托盘/进程后重跑 close_app.sh |
| 取到的密码为空/串成用户名 | 用了多 `-a`（输出纯值、空字段错位）；改用 kp_get.py（全量 `show -s` 解析），或 `-a Password` 单取 |
| 取密报 `HMAC 不匹配` | 主密码错，或误传了 `--key-file`（agents.kdbx 仅主密码保护） |
| 搜索命中 `/回收站/…` 同名条目 | 搜索词加精确（kp_get.py 已自动跳过回收站条目） |

## 资源

> 可执行脚本固定在 `~/Documents/rpa/`（VM 侧 `\\Mac\Home\Documents\rpa`，共享文件夹直接运行，改完即生效）。
> 技能 `scripts/` 为同源副本；`~/.workbuddy/skills/withholding-login` 是指向本仓库的符号链接。

- `~/Documents/rpa/auto_login.sh` — **登录入口**（Mac 侧；包装 auto_login.py，输出 JSON + `STATUS=` 行）。
- `~/Documents/rpa/auto_login.py` — **登录状态机**（VM 侧：自动启动应用/填表/截验证码/点登录/被拒分流）。
- `~/Documents/rpa/close_app.sh` + `close_declare.py` — **关闭入口**（多级退出弹窗 + 进程兜底）。
- `~/Documents/rpa/run_vm.sh` — 运行器：经共享文件夹在 session 1 跑 `*.py` 并回读 `last_result.json`（内置桥接自愈）。
- `~/Documents/rpa/rpa_core.py` / `flow_lib.py` — 执行内核 / 验证码闭环逻辑单元。
- `~/Documents/rpa/capture_captcha.py`、`submit_only.py`、`status_probe.py` 等 — 底层单步脚本（一般不需要直接调）。
- `references/runbook.md` — 驱动机制、窗口定位器坐标、全部坑点与修复细节（§Agent 快速路径/§验证码/§凭据）。
