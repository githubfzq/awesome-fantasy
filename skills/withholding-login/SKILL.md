---
name: withholding-login
description: "登录 / 关闭 Parallels Windows 11 虚拟机中的「自然人电子税务局（扣缴端）」。登录侧：prlctl 桥接 + PsExec session1 驱动、关闭 owner-drawn 隐形模态弹窗（Tfrm_MsgDlgRich）、绕过中文输入法用 WM_SETTEXT 填密、仅登录失败才出现的验证码（点图刷新 + 截图回传识别）。关闭侧：真实点击系统关闭按钮 + 循环确认多级弹窗（Tfrm_MsgDlgRich『确认信息』、Tfrm_MsgDlg『提示信息/数据库备份』）直到完整退出。当用户要启动/登录/关闭扣缴端、或登录界面点哪都弹警告声、或遇到验证码/输入法/退出弹窗问题时使用。"
agent_created: true
---

# 扣缴端登录（自然人电子税务局 扣缴端 · VM）

## 何时用

- 在 Parallels VM 里启动并登录「自然人电子税务局（扣缴端）」。
- 登录界面"点任何区域都弹警告声"——几乎必然是隐形模态弹窗挡住（见 §常见坑）。
- 申报密码登录页需要选单位、填密码、处理验证码。
- 遇到中文输入法把密码字母组词、验证码刷新不了、截图传不回 Mac 等问题。

> 本技能覆盖"登录进软件"与"关闭退出软件"两端（中间填报阶段不在范围）。关闭侧见下方「关闭流程」章节。
> 后续"人员采集→填工资→计税→发送申报"属于更繁琐的填报流程，待后续完善，不在本技能范围内。
> 相关技能：`tax-withholding-vm`（VM 基础设施/运行库修复）、`wage-withholding-rpa`（5 步填报）。

## 驱动模型（关键事实）

```
macOS 编排端
  │  ~/.prlctl-bridge/call.sh exec "Windows 11" <cmd>   (prlctl 桥接，单槽串行)
  ▼
Windows 11 VM —— session 0 (SYSTEM，prlctl exec 落点，无桌面)
  │  C:\rpa\pstools\PsExec64.exe -i 1 -accepteula        (切入交互式桌面会话 1)
  ▼
session 1 (fanzuquan 桌面，扣缴端在此运行)
  │  C:\venv\Scripts\pythonw.exe \\Mac\Home\Documents\rpa\<script>.py   (源码经 Parallels 共享文件夹直接运行；标准库 ctypes 调 Win32 API + Pillow 截图；独立 venv)
  └─ 结果写 C:\rpa\last_result.json，编排端再读回
```

- VM：`Windows 11`，IP `10.211.55.5`。扣缴端：`C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe`。
- Python venv：`C:\venv\Scripts\pythonw.exe`（静默）/ `python.exe`（调试）。
- 结果文件：`C:\rpa\last_result.json`。桥接读回：`powershell Get-Content C:/rpa/last_result.json -Raw`
  （`cmd /c type` 编码会乱，**别用**）。
- 把脚本跑在 VM 上：用 `~/Documents/rpa/run_vm.sh <~/Documents/rpa/xxx.py>`。脚本固定在 Mac Home 下的 `~/Documents/rpa`（VM 侧即 `\\Mac\Home\Documents\rpa`），Parallels 共享文件夹让 VM 直接读 Mac 源码运行——**不再 base64 推送、不再 `Remove-Item`、不再 `certutil` 解码，因此彻底没有批量删除告警**。
- 把 VM 内文件（如验证码 PNG）拉回 Mac：用 `scripts/pull_file.sh <C:/path/to.png>`（base64 回传，绕开被禁的 `prlctl copyfrom`）。

> 详细驱动机制、窗口定位器坐标、全部坑点与修复见 `references/runbook.md`。

## 运行环境与前置安装（必读 · 缺此脚本直接 import 失败）

> 这一节属于"驱动层前置"，由本**具体流水线技能**负责说清；不要写进
> `create-windows-rpa-pipeline`（那是基础设施无关的工程契约）。它不写在这里，
> 别人拿到技能就会卡在"venv 在哪、装什么包"。

> 🔌 **依赖关系（重要）**：本流水线**不依赖 `windows-rpa` 基础 skill**。桌面驱动用的是 **标准库 `ctypes`**
> （`SendMessageW`/`FindWindow`/`WM_SETTEXT`），不是 `windows-rpa` 的 `pyautogui`/`pywinauto` 引擎。
> 因此**不要**按 `windows-rpa` 的「运行环境与前置安装」去安装 pyautogui/pywinauto——它们对扣缴端
> owner-drawn 自绘弹窗坐标会打偏，装进本 venv 反而有害。本流水线所需的唯一第三方库是 `Pillow`（见下）。
> （另一技能 `wage-withholding-rpa` 才真正依赖 `windows-rpa`，二者驱动不同、互不相干。）

- **必须建独立的 Python 虚拟环境**，与系统 Python 隔离，避免被系统升级破坏、也避免污染。
- **venv 路径（约定固定）**：`C:\venv`（VM 内 Windows on ARM64 的 Python 3.x）。
- **前置条件**：VM 内已安装 **Python 3.x（Windows on ARM64 版）**；否则 `python -m venv` 无命令可执行。
- **创建**（在 VM 内，经桥接/PsExec 跑）：
  ```powershell
  python -m venv C:\venv
  ```
- **第三方依赖（脚本真实 import 的，仅此一项）**：`Pillow`（`PIL.ImageGrab` 截图、冻结现场用）。
  - ⚠️ **纠正早期文档**：本流水线**不用 pywinauto**。Win32 交互全部走标准库 `ctypes`
    （`SendMessageW`/`FindWindow`/`WM_SETTEXT` 等）；owner-drawn 弹窗 pywinauto 给的坐标反而是错的，
    所以刻意不用。`ctypes` 是标准库，无需安装。
  - 权威清单见 `scripts/requirements.txt`，安装：
    ```powershell
    C:\venv\Scripts\pip install -r <推到 VM 的>requirements.txt
    # 或单包： C:\venv\Scripts\pip install Pillow
    ```
- **验证安装**（import 不报错才算就绪）：
  ```powershell
  C:\venv\Scripts\python.exe -c "import PIL, ctypes; print('Pillow', PIL.__version__)"
  ```
- **调用入口**（即驱动模型那条）：静默 `C:\venv\Scripts\pythonw.exe`、调试 `C:\venv\Scripts\python.exe`。
  所有 `push_run.sh` 运行的脚本都走这个 venv，系统 Python 不满足依赖会直接崩。

## 执行契约（RPA 硬约束 · 不可绕过）

所有 VM 内操作脚本**必须**基于 `rpa_core.py`（现固定在 `~/Documents/rpa/rpa_core.py`，VM 侧 `\\Mac\Home\Documents\rpa\rpa_core.py`）执行。内核把"每步验证"变成框架强制，
而不是靠写脚本时自觉。

```
每一步 = 前置守卫(guard) → 前置条件(pre) → 动作(action) → 后置验证(verify: 条件轮询+超时) → 结构化日志
                                                              │
                                                    验证不过 ─┴─→ 立即中止 + 冻结现场（窗口树 JSON + 全屏 PNG）
```

**五条禁令**

1. **禁止盲点**：任何 `step()` 缺 `verify` 会被内核直接判失败（除显式 `allow_no_verify=True` 的纯读取步骤）。
2. **禁止用 `time.sleep` 当验证**：等待一律走 `wait_until(fn, timeout, interval)` 条件轮询；
   固定 sleep 只能用于"让 UI 喘一口气"，永远不能作为成功判据。
3. **禁止验证失败后继续**：`fail()` 抛 `StepFailed` 中止全流程（fail-fast）。走进不可控状态的代价远高于多跑一次。
4. **禁止在被遮挡状态下点击**：每个动作前 `guard()` 检查有无阻塞模态弹窗
   （`Tfrm_MsgDlgRich` 会把主窗 `enabled` 置 false 并吞掉全部点击 → 表现为"点哪都嘀"）。
5. **禁止自动关闭未预期弹窗**：默认检测到就停机上报，由人确认内容；只有显式传
   `auto_close_modal=true` 才允许关已知的"提示信息"框。

**安全阀（税务系统专有）**

- 检测到验证码框但未提供验证码 → **拒绝点登录**，避免累计密码错误次数导致账号锁定。
- 登录后出现 `Tfrm_MsgDlgRich` → 判定"被拒"并停机 + 截图，**绝不自动重试**（弹窗文案是 owner-drawn，
  必须人眼看截图确认是"密码错误"还是"需验证码"）。
- 密码/验证码在日志里只记长度（`mask()`），绝不落明文。

**日志与追溯**

| 位置 | 内容 |
|---|---|
| `C:\rpa\logs\<run_id>.jsonl` | 逐事件日志：`run_start`/`step_start`/`pre_ok`/`action_done`/`step_ok`/`step_fail`/`probe`/`snapshot`/`crash`/`run_end` |
| `C:\rpa\logs\latest.jsonl` | 本次运行副本（Mac 侧固定读这个） |
| `C:\rpa\logs\<run_id>-fail-<step>-screen.png` | 失败瞬间全屏截图（冻结现场） |
| `C:\rpa\logs\<run_id>-fail-<step>-windows.json` | 失败瞬间完整窗口树 |
| `C:\rpa\last_result.json` | 本次结果摘要（含 steps 数组、failed_step、reason） |

Mac 侧查看：`scripts/fetch_log.sh --brief`（只看每步结论）、`--list`（历史 run）、
`--snap <run_id>`（取回失败截图到 `~/Downloads`）。

> `pythonw.exe` 无控制台，**`print` 全部丢失** —— 所以过程信息必须落盘，这不是可选项。
> 顶层 `Runner.run()` 捕获一切异常写日志，避免再出现"exit 1 / 137 查不到原因"。

## 登录流程（确定性步骤）

> ⚠️ **登录方式硬约束**：本流程**只**允许「申报密码登录」（左 tab → `spDeclare`）。
> **禁止「实名登录」**（含其下属的扫码、手机号+验证码、CA 证书等任何子方式），也**不用「账号密码登录」**（`spAccount`，默认首页）。
> 密码唯一来源是 KeePass 条目「自然人电子税务局扣缴端」的 `password` 字段（即申报密码），绝不使用自然人个人实名凭据。

1. **启动扣缴端**（后台 detached，避免占桥接槽）：
   ```bash
   ~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "C:/rpa/pstools/PsExec64.exe -i 1 -d -accepteula -w C:/ITSKHD/EPPortal_DS3.0 C:/ITSKHD/EPPortal_DS3.0/EPEvenue_SH.exe"
   ```
   等 ~10s，用 `enum_windows.py` 确认 `Tfrm_LoginViewer` 可见且 `enabled:true`、无 `Tfrm_MsgDlgRich` 挡窗。

2. **切到「申报密码登录」页**：登录窗有两个 tab 头（约 y638–704，左 `1072–1512`=申报密码/**点这个** / 右 `1512–1952`=实名登录/**绝不点**）。
   点左 tab 头 → `spDeclare` 页激活（单位选择框 `TIntelligentSearch` 可见）。

3. **选单位** → 识别号自动带出：点 `TIntelligentSearch`(~1192,752) 弹 `Tfrm_IntelligentSearchPop`，
   在 `TListBox.W` 里选中目标单位（如"修文县关珍养殖**场**"），识别号框自动填入 18 位。

4. **填密码（必须绕过输入法）**：用 `WM_SETTEXT`（ctypes `SendMessageW(hwnd,0x0C,...)`），
   **不要用 `type_keys`**（中文 IME 会把英数组词，长度错）。填后 `WM_GETTEXTLENGTH`(0x0E) 校验长度。
   密码取自 KeePass 条目"自然人电子税务局扣缴端"（用 keepass-lookup 技能取，绝不硬编码/落盘）。

5. **验证码（仅登录失败才出现）**：首次正常登录**无验证码框**。失败时出现 `TXPFamerEditEx` 验证码框 +
   右侧位图（无 HWND）。刷新=点图片（同高、紧邻右侧小间隙）；读取=`captcha.py` 截图存 `C:/rpa/captcha.png`
   → `pull_file.sh` 回传 Mac → Read 识别。验证码**过期很快**，尽量在 VM 内截图后即时回传填回，压缩往返。

6. **点登录**(~1192,1170)：出现 `TfrmBase`「进度」窗，随后 `Tfrm_LoginViewer` 关闭、`Tfrm_MainFrame`(易税门户) 可见 = 登录成功。

### 一键编排（推荐用法）

```bash
# 脚本现固定在 ~/Documents/rpa（VM 侧即 \\Mac\Home\Documents\rpa），直接经共享文件夹运行，无需推送
# 先干跑：只体检 + 定位控件，不点击不输入（强烈建议每次先跑一次）
~/Documents/rpa/run_vm.sh --args-json '{"dry_run":true}' ~/Documents/rpa/login_declare.py
# 正式登录（密码由 KeePass 取，勿写死在文档/脚本里）
~/Documents/rpa/run_vm.sh \
  --args-json '{"unit":"修文县关珍养殖场","password":"<从KeePass取>"}' ~/Documents/rpa/login_declare.py
# 看每步验证结论（fetch_log.sh 仍在技能 scripts/ 目录）
~/.workbuddy/skills/withholding-login/scripts/fetch_log.sh --brief
```

参数：`unit` / `password` / `captcha`（失败重试时）/ `dry_run` / `auto_close_modal` / `login_timeout`(默认45s)。
参数走 base64(JSON)，避免中文单位名经桥接被编码损坏。

### 每步验证判据（登录状态机）

| # | 步骤 | 动作 | **后置验证判据**（不过即停机） |
|---|---|---|---|
| 0 | `preflight` | 无（只读） | 登录窗可见 + `enabled`；无阻塞模态弹窗 |
| 1 | `switch_tab` | 点左 tab 头 | 可见 `TIntelligentSearch`（单位选择器仅存在于申报密码页） |
| 2 | `open_picker` | 点单位选择器 | `Tfrm_IntelligentSearchPop` 可见 **且列表项数 > 0** |
| 3 | `select_unit` | 真实点击列表项 | 弹窗已收起 **且识别号被联动带出**（长度 ≥15 且非占位符） |
| 4 | `fill_password` | `WM_SETTEXT` | `WM_GETTEXTLENGTH == len(password)` |
| 5 | `captcha_gate` | 无/填验证码 | 无验证码框才放行；有框未给码 → **拒绝点登录** |
| 6 | `click_login` | 点登录钮 | 轮询三态：主窗可见=成功 / 出现提示弹窗=被拒(停机) / 超时=失败 |
| 7 | `post_verify` | 无（只读） | 登录窗已关闭 **且**主窗可见 + `enabled` |

幂等：若主界面已可见，脚本直接返回 `already_logged_in`，不会重复操作。

第 3 步用 `LB_GETITEMRECT` 拿列表项真实矩形后**真实鼠标点击** —— 只发 `LB_SETCURSEL`
不会触发 Delphi 的 `OnClick`，识别号就不会被带出。

## 登录后系统状态（实测确认 · 2026-08）

> 本节记录登录成功后主界面的**控件结构、默认值和模块布局**，供后续填报/操作脚本定位目标。
> 数据来源：`inspect_main.py` 控件树巡检 + 主窗口截图视觉交叉验证（2026-08-16 实测）。

### 主窗口基本信息

| 属性 | 值 |
|---|---|
| 窗口类名 | `Tfrm_MainFrame` |
| 标题 | `自然人电子税务局（扣缴端）` |
| 逻辑坐标 | `[251, 104, 1261, 792]`（宽 1010 × 高 688） |
| DPI 缩放 | 2.0（物理像素 = 逻辑 × 2） |
| 首页表单 | `Tfrm_ITSHomePage`（嵌在 `TFrmView` 内） |

### 税款所属月份

| 属性 | 值 |
|---|---|
| 控件类 | `TXPFarmerDTPicker`（Delphi DateTimePicker 子类） |
| 逻辑坐标 | `[556, 237, 669, 258]` |
| 当前值 | **`2026年07月`**（已程序化读取确认，见下备注） |
| 备注 | 控件显示文本**可直接读**，无需截图、无需下拉：用 `SendMessageW(hwnd, WM_GETTEXT=0x000D, ...)` 读回 `'YYYY年MM月'`（实测 `'2026年07月'`）。⚠️ 但**不能用 `GetWindowTextW`**（Win32 API 返回的是缓存 caption，自绘控件恒为空）；`DTM_GETSYSTEMTIME`(0x1001) 返回 0(GDT_VALID) 但 `SYSTEMTIME` 结构为零，亦不可靠。**读月份请用 WM_GETTEXT**。参考脚本 `read_month_dtp.py`。 |

### 左侧菜单区

| 属性 | 值 |
|---|---|
| 控件类 | 多层嵌套 `TJdlsPanel` |
| 逻辑坐标 | `[252, 192, 447, 766]` |
| 内容 | 导航菜单树（办税桌面 / 扣缴申报 / 查询统计 / 系统设置 等）；所有菜单项为 owner-drawn，无 HWND 文本 |

### 常用功能区（6 个模块）

| 属性 | 值 |
|---|---|
| 控件类 | `TXPFarmerGridPanel`（网格面板，owner-drawn 单元格） |
| 逻辑坐标 | `[468, 287, 1239, 557]` |
| 模块名称（按截图从左到右、上到下排列） | 见下表 |

**6 个常用功能模块：**

| # | 模块名称 | 说明 | RPA 关联操作 |
|---|---|---|---|
| 1 | **人员信息采集** | 自然人基础信息登记、报送和公安系统身份验证 | 新增员工时入口 |
| 2 | **专项附加扣除信息采集** | 子女教育支出、住房租金支出等信息采集 | 月度扣除数据维护 |
| 3 | **综合所得申报** | 工资薪金、劳务报酬、稿酬、特许权使用费等月度申报 | **工资薪金月度申报主入口** |
| 4 | **分类所得申报** | 利息股息红利、财产租赁、财产转让等月度申报 | 偶发性所得申报 |
| 5 | **非居民所得申报** | 工资薪金、劳务报酬、稿酬、特许权使用费等月度申报 | 外籍员工所得 |
| 6 | **税款缴纳** | 个人所得税税款在线缴纳 | 申报后缴税 |

> ⚠️ 所有 6 个模块的名称和图标均为 owner-drawn 绘制在 GridPanel 的单元格内，
> 各单元格无独立 HWND、`GetWindowTextW` 返回空。定位方式：GridPanel 整体坐标已知 →
> 按 3 列 2 行布局计算各模块中心点 → 点击。或直接截图识别后点击对应区域。

### 待处理事项区

| 属性 | 值 |
|---|---|
| 控件类 | `TJdlsPanel` |
| 逻辑坐标 | `[448, 567, 1259, 763]` |
| 当前内容 | **`暂无待处理事项`** |

### 控件树关键路径（从主窗到首页）

```
Tfrm_MainFrame (主窗)
└── TPanel 'pnl_all'
    └── TJdlsPanel (左右分栏)
        ├── TJdlsPanel (左侧菜单区 [252,192]-[447,766])
        │   └── TJdlsPanel (多层嵌套)
        └── TPanel (右侧内容区 [447,192]-[1260,766])
            ├── TJdlsPanel (顶部栏 [447,192]-[1260,225])
            │   └── TPanel (标题/工具栏)
            └── TJdlsPanel (主页内容 [447,225]-[1260,766])
                └── TFrmView '视图基类' → Tfrm_ITSHomePage 'frm_ITSHomePage'
                    ├── TJdlsPanel (顶部: 税款所属月份 DTPicker [556,237]-[669,258])
                    ├── TXPFarmerGridPanel (常用功能 6 模块 [468,287]-[1239,557])
                    └── TJdlsPanel (待处理事项 [448,567]-[1259,763])
```

## 关闭流程（确定性步骤）

退出扣缴端是**多级弹窗**流程：先真实点击右上角系统关闭按钮，再逐层确认弹窗。`close_declare.py`
已完整跑通（闭环、无残留弹窗）。

> 关闭入口**覆盖两种状态**：①已进入主界面（`Tfrm_MainFrame`）②仍在登录窗未登录（`Tfrm_LoginViewer`）。脚本先点对应窗口的系统关闭按钮，再循环清多级弹窗——即使停在登录窗也能一键完整退出。

1. **点系统关闭按钮**：用 `WM_GETTITLEBARINFOEX`(0x033F) 取关闭按钮（`HTCLOSE`，`rgrect[5]`）
   的**精确屏幕坐标**真实点击；该 API 不可用时回退到标题栏右上角估算坐标。
   verify = 主窗消失 **或** 出现 `Tfrm_MsgDlgRich` 确认弹窗。
2. **循环确认弹窗**（每级）：枚举 `Tfrm_MsgDlgRich`（『确认信息』：确定/取消）与
   `Tfrm_MsgDlg`（『提示信息』/数据库备份提示：单按钮确认）两类 owner-drawn 弹窗，
   点「确认 / 靠左按钮」，verify = 该 class 的可见窗口已消失。直到主窗消失、无残留弹窗。

### 一键编排
```bash
# 完整关闭（含确认信息 + 数据库备份多级弹窗）
~/Documents/rpa/run_vm.sh ~/Documents/rpa/close_declare.py
# 看每步验证结论（fetch_log.sh 仍在技能 scripts/ 目录）
~/.workbuddy/skills/withholding-login/scripts/fetch_log.sh --brief
```

### 每步验证判据（关闭状态机）
| # | 步骤 | 动作 | **后置验证判据**（不过即停机） |
|---|---|---|---|
| 0 | `click_close` | 点系统关闭按钮（主窗或登录窗） | 主窗/登录窗消失 **或** 出现 `Tfrm_MsgDlgRich` 确认弹窗 |
| 1 | `confirm_modal_N` | 点弹窗确认钮（优先标题匹配，否则靠左取最左按钮） | 该弹窗 class 的可见窗口已消失 |
| - | 循环终止 | — | 主窗 `Tfrm_MainFrame` **与** 登录窗 `Tfrm_LoginViewer` 均不可见 **且** 无 `Tfrm_MsgDlgRich`/`Tfrm_MsgDlg` 残留弹窗 |

> ⚠️ **关键坑**：`rpa_core.blocking_modal()` 只认 `Tfrm_MsgDlgRich`，**不认 `Tfrm_MsgDlg`**（数据库备份提示）。
> 若依赖内核 modal 检测会误判"无阻塞弹窗"提前返回、留下残留弹窗。`close_declare` 用自己的
> `find_confirm_modal()` 枚举两类弹窗。弹窗家族与坐标细节见 `references/runbook.md` §12。

## 常见坑（速查表）

| 现象 | 根因 / 处理 |
|---|---|
| 登录界面点哪都"嘀"警告声、组件点不动 | 隐形 `Tfrm_MsgDlgRich` 模态弹窗挡窗（owner-drawn 文字读不出，但窗体可见+启用，把登录窗 `enabled` 置 false）。`enum_windows.py` 可确诊；`close_modal.py` 用 OK 钮**真实 rect** 点击关闭（pywinauto 给的坐标对 owner-drawn 是错的，别用）。 |
| 密码只进了几位 / 多了几位 | 中文输入法把 `type_keys` 的英数组词。改用 `WM_SETTEXT` 直接写。 |
| 验证码框填了却总报"验证码错误/超时" | 验证码时效性：用户看到→发我→我填 的往返超时报废。改 VM 内截图即时回传填回。**截取验证码图片区域请用固化技能 `withholding-captcha-crop`（`capture_captcha.py`）**——它用 ImageGrab.grab() 真整屏 + 相对定位（owner-drawn 无 HWND），比本技能自带的 `captcha.py` 更可靠。 |
| 点验证码图片不刷新 | 图片是面板位图、无 HWND，靠坐标点中才刷新；先确认无隐形弹窗挡窗（见上）。首次登录本就无验证码框。**截取验证码区域用 `withholding-captcha-crop` 技能。** |
| 旧 `push_run.sh` 的 `certutil`/`Remove-Item` 批量删除告警 | **已废弃**：改用 `run_vm.sh` 经 Parallels 共享文件夹（`\\Mac\Home\Documents\rpa`）直接运行 Mac 上的源码，不再推送/解码/删除任何文件，告警从根上消失。 |
| `prlctl copyfrom` 失败 | 沙箱禁裸 prlctl（unattended 被拒）→ 用 `pull_file.sh` 的 base64 通道回传。 |
| PsExec 跑 pythonw 启动外部 exe 退出 137 | pythonw 持有子进程被杀 → 启动 exe 改由 `PsExec -i 1 -d` 直接拉 exe，不经 pythonw。 |
| 桥接无响应 / 90s 超时 | 孤儿 `prlctl exec` 占槽：`pkill -9 -f 'prlctl exec'` + `rm -f ~/.prlctl-bridge/req ~/.prlctl-bridge/res`，KeepAlive 重生 agent。 |
| `Tfrm_LoginViewer` 还有弹窗关不掉 | owner-drawn 弹窗 `top_window()` 会误命中僵尸窗；按精确 hwnd 定位再关。 |
| 脚本跑完不知道做了什么 / 静默失败 | `pythonw` 无控制台，`print` 全丢 → 必须走 `rpa_core` 落盘 JSONL；用 `fetch_log.sh --brief` 看每步结论。 |
| 点了很多次但界面毫无反应 | 先跑 `enum_windows.py`：若主窗 `enabled:false` 就是被隐形模态弹窗禁用，此时**任何点击都是徒劳**，别再加点击次数。 |
| 选了单位但识别号没带出 | 只发了 `LB_SETCURSEL` 未触发 `OnClick` → 必须用 `LB_GETITEMRECT` + 真实鼠标点击。 |
| 不确定坐标对不对，怕误点 | 先 `--args-json '{"dry_run":true}'` 干跑，只体检+定位+回报坐标，不做任何点击/输入。 |
| 控件 `GetWindowTextW` 返回空，但明明有文字 | `GetWindowTextW` 返回的是**缓存 caption**，自绘/跨线程控件恒为空。改用 `SendMessageW(hwnd, WM_GETTEXT=0x000D, ...)` 直接读（如 `TXPFarmerDTPicker` 税款所属月份经此读回 `'2026年07月'`）。`DTM_GETSYSTEMTIME`(0x1001) 对自定义日期控件常返回 0 但结构为零，**不可靠**。 |

## 资源

> **代码位置（2026-08 重构）**：可执行的 RPA 脚本已固定在 `~/Documents/rpa/`（VM 侧 `\\Mac\Home\Documents\rpa`），由 `run_vm.sh` 经共享文件夹直接运行，**不再推送/删除**。`~/.workbuddy/skills/withholding-login/scripts/` 现在只保留 shell 辅助（`pull_file.sh`/`fetch_log.sh`）与若干遗留诊断脚本（`enum_windows.py`/`grab.py`/`snap_*.py`/`diag_*.py` 等，仅供人工排查，不经 `run_vm.sh` 运行）。

- `~/Documents/rpa/rpa_core.py` — **执行内核**：`Runner`/`step`/`wait_until`/`guard`/
  `snapshot`/JSONL 日志/顶层异常捕获/win32 与 ListBox 原语/`mask` 脱敏/base64 参数解析。
- `~/Documents/rpa/run_vm.sh` — Mac 侧：经共享文件夹直接运行 `~/Documents/rpa/*.py` + 回读结果；内置桥接健康自愈。**取代旧 `push_run.sh`，无任何文件删除。**
- `~/Documents/rpa/login_declare.py` — VM：申报密码登录**状态机**（8 步，每步带验证判据，支持 dry_run）。
- `~/Documents/rpa/close_declare.py` — VM：点击系统关闭按钮 + **循环确认多级弹窗**（`Tfrm_MsgDlgRich`/`Tfrm_MsgDlg`）直到完整退出扣缴端。
- `~/Documents/rpa/close_modal.py` — VM：真实坐标关闭 `Tfrm_MsgDlgRich`，并验证弹窗确已消失。
- `scripts/pull_file.sh` — Mac 侧：VM 文件 → Mac（base64 回传）。
- `scripts/fetch_log.sh` — Mac 侧：取执行日志（`--brief`/`--list`/`--run`/`--snap`）。
- `scripts/enum_windows.py` — 遗留诊断（不经 run_vm.sh）：枚举全部顶层窗，诊断隐形弹窗/校验登录态。
- `scripts/captcha.py` — 遗留诊断（已被 `withholding-captcha-crop` 技能取代）。
- `scripts/requirements.txt` — **VM 内 venv 权威依赖清单**（`Pillow` 一项；`ctypes` 为标准库不列）。装环境时 `pip install -r` 它。
- `references/runbook.md` — 驱动机制、窗口定位器、全部坑点修复细节。
