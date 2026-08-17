# 扣缴端登录 · 详细 Runbook

本文件补充 `SKILL.md` 的驱动机制、窗口定位器坐标、以及全部坑点的修复细节。
（坐标来自 3024×1890 屏幕、Delphi VCL 控件树实测；窗口重开后坐标体系可能整体平移，
优先用 `enum_windows.py` / dump 子控件**运行时重新求坐标**，下列坐标仅作首猜。）

## 1. Mac ↔ VM 桥接（prlctl-bridge）

- 调用：`~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "<command>"`
- 单槽串行：同一时刻只能有一条 `call.sh` 在执行；长命令挂起会占槽导致后续 90s 超时。
- zsh 元字符：桥接命令经 zsh 传递，`$`（含 PowerShell 的 `$_`）会被 zsh 展开 → 含 `$` 的命令用单引号或转义。
- 桥接恢复（卡死时）：
  ```bash
  pkill -9 -f 'prlctl exec'
  rm -f ~/.prlctl-bridge/req ~/.prlctl-bridge/res
  sleep 2
  ~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "echo bridge_ok"
  ```

## 2. session 模型与 PsExec

- `prlctl exec` 落点 = **session 0（SYSTEM，无桌面）**：pywinauto/pyautogui 看不到 session 1 窗口。
- 切 session 1：`C:\rpa\pstools\PsExec64.exe -i 1 -accepteula <cmd>`。
- 跑 Python：`... -accepteula C:\venv\Scripts\pythonw.exe C:\rpa\x.py`（静默）/ `python.exe`（看异常）。
- 启动外部 exe（扣缴端）：`PsExec64.exe -i 1 -d -accepteula -w C:\ITSKHD\EPPortal_DS3.0 C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe`
  （`-d` detached，避免随 exec 结束被杀；`-w` 设工作目录）。**别**用 pythonw 去 `subprocess` 拉 exe（会 exit 137）。
- 结果回读：脚本把 JSON 写 `C:\rpa\last_result.json`；编排端用 base64 读回（`[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:/rpa/last_result.json'))` 经桥接回传 + `LC_ALL=C tr -cd '0-9A-Za-z+/='` 过滤噪声 → 本地 `base64 -d`，见 §11）。**绝不用 `Get-Content` / `type` 明文回读**（会被桥接噪声行与 locale 破坏）。

## 3. 运行脚本（run_vm.sh + 共享文件夹，已取代 push_run.sh）

关健点：代码固定在 Mac Home 下的 `~/Documents/rpa`（VM 侧即 `\\Mac\Home\Documents\rpa`，Parallels 共享文件夹），
**VM 用 `PsExec -i 1` 在交互会话里直接 `pythonw` 跑共享路径上的源码**。不再 base64 推送、不再 `Remove-Item`、
不再 `certutil` 解码——因此**彻底没有批量删除告警**。改完 Mac 上的代码，VM 下次运行即时生效。

- 扁平目录：`~/Documents/rpa` 下所有 `.py` 平铺（无 `core`/`tax` 子目录）。Python 自动把脚本目录加入 `sys.path[0]`，
  跨文件 `import rpa_core` / `import flow_lib` 零配置，无需 `PYTHONPATH`。
- 路径翻译：Mac 路径 `~/Documents/rpa/foo.py` → VM 内 UNC `\\Mac\Home\Documents\rpa\foo.py`（`run_vm.sh` 的 `to_unc()`）。
- session 1 执行：`C:\rpa\pstools\PsExec64.exe -i 1 -accepteula C:\venv\Scripts\pythonw.exe \\Mac\Home\Documents\rpa\foo.py`。
- 桥接自愈：卡死时清孤儿 `prlctl exec` + `req/res`，无需手动干预（`run_vm.sh` 每次运行前自检，失败时自动 pkill 自愈）。
- 结果回读：脚本写 `C:\rpa\last_result.json`；`run_vm.sh` 用 base64 回传 + `tr -cd` 过滤噪声读回（见 §11）。
- 旧 `push_run.sh` 的反面教训：它曾在**每次运行前遍历脚本目录里全部 `*.py`**，先 `Remove-Item *.py + *.b64` 再
  `certutil -decode` 推送。数十次运行累计触发 VM 文件监控 telemetry 的"检测到批量删除操作"告警（累计 193 项），
  这正是被共享文件夹方案根除的问题——现在零文件传输、零删除。

## 4. 文件回传（pull_file.sh 原理）

`prlctl copyfrom` 在沙箱被拒（unattended 模式）。改用 VM 内 base64 输出、Mac 解码：

```bash
B64=$(~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "powershell -NoProfile -Command [Convert]::ToBase64String([IO.File]::ReadAllBytes('C:/rpa/captcha.png'))" 2>/dev/null | tail -1)
echo "$B64" | base64 -d > /Users/fanzuquan/Downloads/captcha.png
```

> 注：Parallels 共享盘 `\\Mac\Home`（VM 内即 Mac Home）**可被 session 1 的 `pythonw` 直接读写**（已验证：
> `PsExec -i 1 pythonw \\Mac\Home\Documents\rpa\_smoke.py` 成功运行并完成 cross-import）。早期"pythonw 看不到
> 共享盘"的说法是把 session 0（prlctl exec 落点，非交互、无桌面）与 session 1 混为一谈所致——本方案恰恰让
> session 1 直接读共享路径。结果文件约定写 VM 本地 `C:\rpa`（而非共享盘），仅为避开 UNC 写入的边角开销；
> 脚本**源码**则一律从 `\\Mac\Home\Documents\rpa` 读取，Mac 侧编辑即时在 VM 侧生效。

## 5. 窗口 / 控件定位器（Delphi VCL）

| 用途 | 类 / 标题 | 备注 |
|---|---|---|
| 登录主窗 | `Tfrm_LoginViewer` | `enabled:false` = 被弹窗挡 |
| 申报密码登录页 | `spDeclare`（内层页） | 切 tab 后 `vis:true` |
| 账号密码登录页 | `spAccount` | 默认首页，**禁止**用；强制申报密码登录，禁用「实名登录」(扫码/手机号/CA 证书等) |
| 单位选择框 | `TIntelligentSearch` | 点开弹 `Tfrm_IntelligentSearchPop` |
| 单位列表弹窗 | `Tfrm_IntelligentSearchPop` | 含搜索框 `TXPFamerEditW.W` + 列表 `TListBox.W` |
| 纳税人识别号框 | 占位符"纳税人识别号" | 选单位后**自动带出**，勿手填 |
| 密码框 | `TXPFamerEditEx` | `WM_SETTEXT` 填；`get_value()` 返回 None |
| 验证码框 | `TXPFamerEditEx`，占位"请输入验证码" | **仅失败时出现**；图片无 HWND |
| 登录按钮 | 坐标 ~(1192,1170) | 运行时重求 |
| 隐形错误弹窗 | `Tfrm_MsgDlgRich`，标题"提示信息" | owner-drawn 文字读不出；单 `TITSSpeedButton` 确定钮；模态挡窗 |
| 虚拟键盘 | `TvirKeyboardForm` | 点密码框弹出，点"关闭"二字关闭 |
| 进度窗 | `TfrmBase`，标题"进度" | 登录中短暂出现 |
| 主界面 | `Tfrm_MainFrame`（易税门户）/ `frm_ITSHomePage` | `vis:true` = 登录成功 |

左侧功能菜单是树形/自绘控件，文本读不出，靠坐标或 dump 子控件定位（填报阶段待补）。

## 6. 隐形模态弹窗（最阴间的坑）

**现象**：登录界面所有组件点不动、点哪都"嘀"警告声。
**根因**：某个 `Tfrm_MsgDlgRich` 弹窗（owner-drawn 文字渲染不出 → 肉眼像"没弹窗"）模态地挡在登录窗前，
`IsWindowEnabled(登录窗)=false`。所有点击被它吃掉的。
**诊断**：`enum_windows.py` → 找 `Tfrm_LoginViewer` 是否 `enabled:false`、是否有 `Tfrm_MsgDlgRich` `visible:true`。
**关闭**：pywinauto 给 owner-drawn 控件的坐标是错的（打到屏幕外）。用 ctypes `EnumChildWindows` 求 OK 钮
**真实 rect**，再 `SetCursorPos` + `mouse_event(LEFTDOWN/UP)` 点真实中心。`scripts/close_modal.py` 已实现。
（之前 rpa.py 的 `uia_click --title 提示信息 --class_name TITSSpeedButton` 在 `top_window()` 没误命中时可关，
但易误命中僵尸窗 → 优先用按 hwnd 的真实坐标点击。）

## 7. 输入法（IME）

`type_keys` 发的英文字母被中文输入法组词 → 识别号只进 6 位、密码多出乱字符。
**一律用 `WM_SETTEXT`**：`user32.SendMessageW(hwnd, 0x0C, 0, ctypes.c_wchar_p(text))`。
填后 `WM_GETTEXTLENGTH`(0x0E) 校验真实长度。也可 `ImmAssociateContext(hwnd, NULL)` 关该框 IME 后再 keys。

## 8. 验证码（失败场景）

- 登录**失败**才出现：框 `TXPFamerEditEx`(占位"请输入验证码") + 右侧验证码**位图**（画在面板，无 HWND、无类名）。
- **刷新**：点图片区域（输入框右边、同高、仅一小段间隙、无边框）。点中才换图，不点不自动刷新、也不清空已填文本框。
- **读取**：`captcha.py` 在 VM 内 `ImageGrab` 截验证码区域 → 存 `C:/rpa/captcha.png` → Mac 用 `pull_file.sh` 回传 → Read 识别。
  `ImageGrab` 在 session 1 的 pythonw 下可用（偶发 exit 137 可重试）。
- **时效**：验证码极短（数秒~十几秒）。"用户看到→发我→我填"的往返必超时作废。验证过填充方式本身正确，
  失败全因超时，不是密码错/填充错。理想方案是 VM 内截图即时回传、Mac 识别后即时 `WM_SETTEXT` 填回。

## 9. 凭据

- KeePass 条目"自然人电子税务局扣缴端"：username=纳税人识别号（选单位后自动带出，无需手填）、password=申报密码。
- 取密：`~/.workbuddy/skills/keepass-lookup/scripts/kp_get.py --search 自然人电子税务局`（主密码走 `KEEPASS_MASTER` 或交互，**绝不落盘/不写记忆**）。
- 单位名实测为"**修文县关珍养殖场**"（场，非"厂"；`login_declare.py` 已内置末字容错匹配）。

## 10. 执行内核 rpa_core.py（写新步骤必读）

后续扩展填报流程（人员采集 → 工资薪金 → 计税 → 报送）时，**照下面模板写**，不要另起一套。

```python
import rpa_core as R

def main(r):
    # 动作步骤：必须给 verify，且 verify 是"可观测的状态判据"，不是 sleep
    r.step("open_salary_form",
           action=lambda: R.click_at(*R.center(some_rect)),
           verify=lambda: {"grid": g["rect"]} if (g := find_grid()) else None,
           verify_desc="工资明细表格已出现",
           timeout=15)
    return {"done": True}

if __name__ == "__main__":
    R.Runner("salary_fill", expected_windows={"Tfrm_MainFrame"}).run(main)
```

**verify 判据的选取原则**（按可靠性排序）：

1. **新窗口出现/消失** —— `R.find_window(cls)`，最可靠。
2. **控件文本长度/内容** —— `R.wm_get_len(hwnd)` / `R.wm_get_text(hwnd)`，用于输入类。
3. **控件出现/可见性** —— `enum_children` 过滤 class + visible，用于切页类。
4. **列表项数 > 0** —— `R.listbox_items()`，用于异步加载的数据。
5. **像素差异** —— `captcha.py` 里的 `mean_diff`，仅用于无 HWND 的位图（最后手段）。

**绝不能用**："点击返回 exit 0"、"sleep 若干秒后假定成功"、"日志打印了就算成功"。

**API 速查**

| 用途 | 调用 |
|---|---|
| 找顶层窗 | `R.find_window("Tfrm_MainFrame", visible_only=True)` |
| 枚举后代控件 | `R.enum_children(hwnd)` → `[{hwnd,class,title,visible,enabled,rect}]` |
| 条件等待 | `R.wait_until(fn, timeout=10, interval=0.3)` → `(value, elapsed)` |
| 真实点击 | `R.click_at(x, y)` / `R.center(rect)` |
| 绕 IME 写文本 | `R.wm_set_text(hwnd, s)` + `R.wm_get_len(hwnd)` 校验 |
| 列表读/真实点项 | `R.listbox_items(hwnd)` / `R.listbox_click_item(hwnd, idx)` |
| 主动停机 | `r.fail("step", "原因", {...})`（自动 snapshot + 写日志） |
| 记录中间观测 | `r.emit("probe", step="x", **kv)` |
| 脱敏 | `R.mask(secret)` |

**排障顺序**（脚本报失败时）：
1. `fetch_log.sh --brief` → 看是哪一步 `step_fail`、reason 是什么、等了多久。
2. `fetch_log.sh --list` → 找到该 `run_id`。
3. `fetch_log.sh --snap <run_id>` → 取回失败瞬间截图，人眼确认界面真实状态。
4. 对照 `<run_id>-fail-<step>-windows.json` 看当时窗口树（是否有意外弹窗、目标控件是否存在）。

## 11. 桥接回读的中文编码 + 管道坑（已修复，改脚本前必读）

**坑 1：base64 回读被桥接噪声行 / 默认 locale 破坏。**
- 现象：`tr: Illegal byte sequence` + `base64: stdin: (null): error decoding base64 input stream`，导致读不到 `last_result.json` / 日志。
- 根因：桥接层（`.prlctl-bridge/agent.sh`）是**纯透传**——它只执行 `"$PRLCTL" "${args[@]}" 2>&1` 并把原始 stdout 写入 `res`，**不会注入任何噪声**。混入输出的是 VM 侧的文件监控/审计 telemetry（如「检测到批量删除操作：累计删除数量 N 项」这类安全告警，以及其它中文诊断行），它们与命令真实输出共用同一条 stdout 通道，被桥接一并 relay 回 Mac。Mac 侧默认 locale 下 `tr` 遇到多字节中文直接报「Illegal byte sequence」，且 `grep -v '^$' | tail -1` 在噪声行排在 base64 之后时会把真正的 base64 吞掉。
- 修复（已在 `run_vm.sh` / `fetch_log.sh` 落地）：回读管道统一用
  ```bash
  ... | LC_ALL=C tr -cd '0-9A-Za-z+/='
  ```
  只保留 base64 字母表字符，无论噪声行在前后都会被剥离；再 `printf '%s' "$B64" | base64 -d` 本地解码。
- **铁律**：凡经桥接回读文本（含中文的 JSON / JSONL / 截图），一律走 base64 回传（`[Convert]::ToBase64String([IO.File]::ReadAllBytes(...))`）+ 本地 `base64 -d`，绝不用 `Get-Content` / `type` 明文回读。

**坑 2：`cmd /c` 把 PowerShell 内部管道符 `|` 当成自己的管道。**
- 现象：`'Sort-Object' 不是内部或外部命令`（cmd 把 PowerShell 脚本里的 `|` 当成 cmd 管道，把 `Sort-Object` 当独立命令执行）。
- 修复：`fetch_log.sh --list` / `--snap` 等带 PowerShell 内部管道的命令，管道符必须写成 `^|`（cmd 转义，原样传给 PowerShell）。
- 易错点：`^|` 只在桥接 `cmd /c "..."` 包装里需要；Mac 侧 bash 管道（`| grep` / `| tr`）是正常的，不要加 `^`。
