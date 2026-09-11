---
name: wage-withholding-rpa
description: 在 Parallels Windows 11 VM 中端到端自动完成「自然人电子税务局（扣缴端）」月度工资薪金申报：declare_month.sh 一条命令串起 关闭→登录→复制上月→计税→发送→终态复核，硬门全过自动发送（用户已事先授权），失败即停、全程留痕。当用户要自动化个税扣缴端月度申报、或要求"把申报流程走完"时使用。
---

# 工资薪金申报 RPA（VM · 端到端月度流水线）

## Overview

把「申报当月工资薪金」月度操作封装为**端到端流水线**：Mac 侧驱动 `scripts/declare_month.sh`，
VM 侧内核 `scripts/declare_month_pipeline.py`（经 run_vm.sh + PsExec session 1 执行），运行于
Parallels Desktop 的 Windows 11 VM 交互式桌面。

- **标准入口**：`declare_month.sh auto` —— 关闭→登录→复制→计税→发送→复核，硬门全过自动发送。
- **适用**：每月在「自然人电子税务局（扣缴端）」做综合所得申报（复制上月数据 → 计税 → 发送申报）。
- **不适用**：非 VM 环境、或非扣缴端的其他系统。
- 早期 `wage_rpa.py` 5 步交互流程保留作单步调试参考（见 §legacy）。

## 端到端流水线（标准入口）

### 运行位置（关键）

真实运行副本必须放在 **`~/Documents/rpa/`**（VM 经 `\\Mac\Home\Documents\rpa` 可见；隐藏目录 VM 不可见）。
本技能 `scripts/` 里的是维护真源，更新后同步过去再跑。

### 用法（declare_month.sh）

```bash
bash declare_month.sh auto        # close→login→preflow(dry)→preflow(real)，在验证码/视觉门处自动停
# 退出码 90：需验证码 → Read ~/Documents/rpa/captcha.png 识 4 位码 →
bash declare_month.sh login --captcha <码>
# 退出码 80：复制/草稿就绪，需视觉判读（pipeline/*.png）确认后继续 →
bash declare_month.sh auto-resume finish    # 计税→双门→发送→终态（硬门全过自动发送）
bash declare_month.sh recheck                # 退出模块重进，第二次独立读数
# 发送后中断（如确认框干扰）：declare_month.sh terminal-resume —— 只收尾取证，绝不重发
```

分阶段手动：`close` / `login [--captcha XXXX] [--dry]` / `preflow 1|0`（1=dry 0 点击）/
`finish` / `terminal-resume` / `recheck`。

### 门模型（每道不过即停机，绝不猜）

| 门 | 断言 |
|---|---|
| 门1 通道新鲜度 | 每次 VM 调用前后 `C:\rpa\last_result.json` 的 `run_id` 严格更新；未更新=本次未执行→自动重试一次，仍失败 `GATE1_FAIL`（防桥接陈旧回读假成功） |
| 月份门 | 税款所属期实测=`N-1月`（N 月申报 N-1 月，如 2026-09 期→`2026年08月`）；不符停机，**绝不改月份** |
| 复制证据门 | 【复制结果】「成功复制【1】条，失败【0】条」∧ 网格「填写人数==1」（李关珍）；复制 0 条/人数≠1 停机。草稿已在（幂等分支）则不重复制，防止复制出第 2 条 |
| 发送前双门 | 步骤4 校验 memo **无负态文案**（计税前「未计算税款」计税后应翻转消失，空=无错误）∧ 发送钮 `enabled∧visible`（rect 钉死 [1138,343,1226,375]） |
| 终态门 | 只认正向白名单「申报成功」类文案（memo 机器读 + 截图判读），且**退出模块重进两次独立读数**一致；绝不用代理信号猜"已申报" |
| 铁律 | 发送**仅点 1 次**，负态/未知态**绝不重发**；无缴款步骤；不带专项附加扣除；登录被拒（非验证码类）绝不重试 |

### 确认模型（2026-09-12 起生效）

用户显式事先授权：**硬门全部通过即直接发送申报，不再逐次人工确认**（授权记录写入发送 run 的
JSONL `send_authorization` 事件；见 `declare_month.sh` `stage_finish` 的
`send_authorized=True` + `auth_note`）。若要恢复"发送前停下等确认"，把 `send_authorized`
改为 `False` 并在退出码 80/81 处转人工。验证码、未知模态、门失败仍会停机交人——"少确认"
不等于"无安全阀"。

### 证据与留痕

- `~/Documents/rpa/pipeline/`：关键步截图（draft/pre_send/after_send/recheck）+ gates/summary/recheck JSON + 关键 run 的 JSONL 回拉。
- VM 侧 `C:\rpa\logs\<run_id>.jsonl`：每步 action/verify/timeout 全量日志。
- 陷阱清单 T1–T9（复制向导选项①、按钮空文本几何钉死、明细页数字只能截图判读、离开明细页只能点「返回」、z-order 页判据、锚唯一性、忽略 IME 候选窗等）见
  `~/WorkBuddy/2026-09-11-00-14-31/plan/run_protocol.md`；状态机 S0–S14 与全部裁决见同目录 `design/`、`plan/constraints_and_rulings.md`。

### 依赖技能

`withholding-login`（auto_login.sh / close_app.sh 与 STATUS 决策表）、`keepass-lookup`
（申报密码：`kp_get.py --db agents.kdbx --master-file agent_main_pass --search 自然人电子税务局`）、
`tax-withholding-vm`（系统错误框/运行库）、`parallels-desktop`（VM 生命周期）、
`withholding-captcha-crop`（验证码原理）。

## 架构（关键事实）

```
macOS 编排端 (declare_month.sh)
   │  ~/.prlctl-bridge/call.sh exec "Windows 11" <cmd>   (prlctl 桥接)
   ▼
Windows 11 VM —— session 0 (SYSTEM / prlctl exec 落点，无桌面)
   │  C:\rpa\pstools\PsExec64.exe -i 1 -s   (切入交互式会话)
   ▼
session 1 (fanzuquan 登录的桌面，扣缴端在此运行)
   │  C:\venv\Scripts\python.exe <脚本>（pyautogui + pywinauto UIA 优先）
   └─ 结果 JSON 写回 C:\rpa\last_result.json，编排端解析并断言门1
```

- 为什么走 psexec：`prlctl exec` 落在 session 0（无桌面），GUI 自动化必须在 session 1。
- VM 操作**串行化**：并发探针会触发 PsExec 255 虚警。
- 桥接命令禁止 shell 元字符 `& | < >`；含 `$` 的命令用单引号包裹（zsh 会展开）。

## 环境事实（目标 VM 已验证）

- VM：`Windows 11`，ARM64（Apple Silicon）。Python 3.11 装于系统，**全局 venv `C:\venv`**（Tsinghua pip 镜像已配）。
- 依赖：`pyautogui pillow pywinauto pyperclip`。ARM64 坑：pywin32 无 `win32ui.pyd`，已给
  pywinauto `base_wrapper.py` 打 `try/except ImportError` 补丁（UIA 后端不受影响）。
- psexec：`C:\rpa\pstools\PsExec64.exe`。session 1 屏幕实测 3024×1890。
- 扣缴端：`C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe`，主窗 `Tfrm_MainFrame`（Delphi VCL）。

## 文件结构

```
scripts/
  declare_month.sh            # Mac 侧端到端驱动：门1 内建、取密仅内存、分阶段/auto
  declare_month_pipeline.py   # VM 侧内核：stage=preflow/finish/terminal_resume/recheck，dry_run 内建
  wage_rpa.py                 # [legacy] 早期 5 步交互流程，单步调试参考
  rpa.py                      # [legacy] 早期 VM 内 RPA 引擎（uia_* 子命令）
references/
  tax_app_locators.md         # 扣缴端 UI 定位器记录模板
```

## 安全边界（强制）

- **发送申报是唯一不可逆对外动作**：现行模型 = 用户事先授权 + 硬门自动放行（见上"确认模型"）；
  无论何种模型，**发送只允许 1 次真实点击**，发送后任何负态/未知态一律停机取证，**绝不重发**。
- 凭据：仅运行时经 keepass-lookup 取出放进进程环境（`WITHHOLDING_PASSWORD`），绝不 echo、
  绝不落盘、日志只记长度；执行脚本不得硬编码凭据。
- 月份不符、复制 0 条、未知模态、验证码多轮失败（>3 轮）、登录被拒 → 停机交人，不自动猜。
- 任何动作失败不自动重试发送；流程在中止点停下并报告，由人介入。

## legacy：早期 5 步交互流程（wage_rpa.py，调试参考）

登录→人员采集→填工资（复制上月）→计税→发送（默认停下等 `yes`）。单步：
`python wage_rpa.py --step 3`；dump UIA 树补定位器：`--discover "自然人电子税务局"`；
`--dry-run` 只打印。环境变量覆盖：`BRIDGE_CALL` `RPA_VM` `RPA_PSEXEC` `RPA_VENV_PY` `RPA_PY`
`RPA_RESULT_FILE` `KEEPASS_GET` `KEEPASS_ENTRY` `RPA_TAX_APP`。
定位策略：`uia_click/uia_type` 控件 name 中文文本优先 → 子串 → 图像模板回退。

## 调试 / 排错

- 自检：`call.sh exec "Windows 11" ... psexec -i 1 -s C:\venv\Scripts\python.exe C:\rpa\rpa.py check`
- 看不到桌面/尺寸为 0：确认脚本经 `psexec -i 1` 在 session 1 运行，而非 session 0。
- `import win32ui` 失败：确认已应用 pywinauto `base_wrapper.py` 的 try/except 补丁（ARM64）。
- 桥接无响应/退出 137：agent 被旧 `prlctl exec` 卡住，清理 `~/.prlctl-bridge/req`、`res` 并杀残留进程后重试。
- `GATE1_FAIL`：门1 重试仍陈旧 → 通道未真正执行，检查 `run_vm.sh` 与共享盘挂载，**绝不采信旧结果**。
- 登录超时弹窗（`Tfrm_MsgDlgRich`「登录超时」）随时可能出现：出现即会话已死 → 关弹窗 → 重登录 → 重新断言草稿（填写人数==1 则直接计税）→ 继续。
