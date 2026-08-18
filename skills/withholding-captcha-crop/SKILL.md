---
name: withholding-captcha-crop
description: "扣缴端（及同类 Delphi VCL / Win32 应用）登录时出现的验证码是 owner-drawn 位图、无 HWND，无法用枚举子控件直接拿到矩形。本技能提供『稳定截取验证码图片区域』的可复用方法：用 ImageGrab.grab() 抓真整屏（物理像素），结合 enum 得到的登录窗逻辑 rect 与 DPI scale，按『验证码输入框右侧同一行』的相对位置推算验证码位图区域并裁剪，供后续 OCR / 视觉识别。规避 PowerShell CopyFromScreen 只截半屏、PIL ImageGrab 黑屏、DPI 跨空间乱乘系数等全部已知坑。当用户要在 RPA 流程里自动读取验证码图片、或截图总被裁歪/截到壁纸/坐标对不上时使用。"
agent_created: true
---

# 扣缴端验证码图片区域截取（owner-drawn captcha crop）

## 何时用

- RPA 登录扣缴端时验证码出现，需要**把验证码图片本身截成一张干净的小图**交给 OCR / 视觉识别。
- 截图总是出问题：截到桌面壁纸、整屏被裁掉一半、坐标对不上、黑屏。
- 需要知道"怎么在 VM 里稳定拿到验证码图片的矩形框"。

> 本技能只负责"**截出验证码图片区域**"这一件事。读出字符后的"填码点登录"由 `withholding-login` 的 `login_declare.py`（带 `captcha` 参数）或本技能的 `submit_only.py` 完成。

## 核心结论（先讲答案）

登录窗里那个验证码**不是独立窗口控件**——它是直接画在窗体画布上的位图（owner-drawn，无 HWND）。

- ❌ **路径 B（直接暴露）走不通**：`enum_children` 枚举不出它的矩形，因为压根没有这个窗口。
- ✅ **路径 A（相对定位）是唯一可靠的**：登录窗本身是顶层窗口，`enum_top_windows` 能拿到它的 `rect`（逻辑像素）；验证码位图就画在**验证码输入框右侧、同一行**——用输入框的矩形 + 窗体右边界推出它的位置，再从"真整屏"里裁出来。

实测（扣缴端申报密码登录页，单位=修文县关珍养殖场）：

| 要素 | 逻辑像素 rect | 备注 |
|---|---|---|
| 登录窗 `Tfrm_LoginViewer` | `[535, 227, 977, 718]` | 顶层窗口，可靠 |
| 验证码输入框 `TXPFamerEditEx`(第3个) | `[597, 520, 794, 557]` | 右侧 x=794 之后是图片 |
| **验证码位图(推算)** | **`[795, 512, 976, 562]`** | **输入框右 + 同排；已截图验证可读** |
| DPI scale | `2.0` | `物理整屏宽 / GetSystemMetrics(SM_CXSCREEN)` |

> 别硬编码上面的绝对数字。脚本应**动态**从 enum 推出验证码输入框矩形，再按"右侧同排"推位图矩形——绝对数字会随分辨率/窗体缩放漂移，相对关系才稳定。

## 截图方式选型（最关键的坑）

| 方式 | 结果 | 结论 |
|---|---|---|
| `powershell CopyFromScreen`（`snap_fullscreen.py` 早期用） | 只拿到 `1512×945`（逻辑分辨率，**半屏/被裁**） | ❌ 禁用。这就是"截图被裁剪过"的根因 |
| 独立 `PIL.ImageGrab.grab()`（session1 内裸跑） | 黑屏 / 壁纸 | ❌ 独立脚本语境下抓错桌面表面 |
| **`rpa_core.snapshot()` 内的 `ImageGrab.grab()`**（经由 `run_vm.sh` + `pythonw` 在 session1 跑） | `3024×1890`（**真·整屏物理像素**） | ✅ 唯一可靠 |

**铁律**：截整屏只用 `ImageGrab.grab()`（全屏无参数），且必须在 `run_vm.sh` 运行的脚本里、经 `pythonw` 在交互桌面会话 1 中执行。返回的是**物理像素**整屏。

## 坐标映射公式（DPI 不踩坑）

整屏是**物理像素**，而 `enum_*` 返回的 `rect` 是**逻辑像素**（DPI 缩放后）。二者差一个 `scale`：

```
scale = 整屏图像.width / ctypes.windll.user32.GetSystemMetrics(0)   # SM_CXSCREEN=0
# 本 VM：3024 / 1512 = 2.0
物理_rect = [int(v * scale) for v in 逻辑_rect]
```

裁剪：`ImageGrab.grab(bbox=物理_rect)` 直接从整屏裁出目标控件。

> ⚠️ 不要猜 scale（不要写死 2.0）。每次运行都用上面的公式现算——换显示器/改缩放比，硬编码就会裁歪。

## 可靠截取四步法（脚本固化于 `~/Documents/rpa/capture_captcha.py`）

1. **填表让验证码出现**：切到「申报密码登录」，选单位（识别号联动带出），`WM_SETTEXT` 填密码。此时验证码框 + 右侧位图出现。（填表逻辑复用 `withholding-login`，见脚注）
2. **抓真整屏**：`full = ImageGrab.grab()` → 存 `full_real.png`（物理像素）。
3. **算 scale + 拿登录窗 rect**：`scale = full.width / GetSystemMetrics(0)`；`lw = find_window("Tfrm_LoginViewer")`，取 `lw["rect"]`（逻辑）。
4. **推验证码位图矩形并裁剪**：
   - 先尝试**路径 B**：在子控件里找"位于验证码输入框右侧、垂直重叠、非编辑/按钮类"的控件（如 `TImage`）——抓到就用它的 rect。
   - 否则**路径 A**（扣缴端走这条）：以验证码输入框 `rect=[cx1,cy1,cx2,cy2]`、窗体 `rect=[wx1,wy1,wx2,wy2]` 推：
     ```
     pad_x = max(3, int((cx2-cx1)*0.02))
     pad_y = max(7, int((cy2-cy1)*0.2))
     位图逻辑 = [cx2+pad_x, cy1-pad_y, wx2-2, cy2+pad_y]
     ```
   - `bbox = [int(v*scale) for v in 位图逻辑]` → `ImageGrab.grab(bbox=bbox)` → 存 `captcha_only.png`。

`capture_captcha.py` 还会落 `children.json`（登录窗全部子控件明细 + scale + login_rect）作为**双保险**：万一相对定位偏了，人可用这份清单在 Mac 侧按同一坐标系重新裁。

## 已知坑速查

| 现象 | 根因 / 处理 |
|---|---|
| 截图是桌面壁纸 / 黑屏 | 没在 session1 的 `pythonw` 语境下跑 `ImageGrab`，或用了 `CopyFromScreen`。改用 `run_vm.sh` 运行 + `ImageGrab.grab()`。 |
| 整屏只有一半（1512×945） | 用了 PowerShell `CopyFromScreen`（逻辑分辨率）。换 `ImageGrab.grab()`（物理）。 |
| 坐标裁出来是空白/错位 | scale 用错或没乘。务必 `整屏宽 / GetSystemMetrics(SM_CXSCREEN)` 现算；逻辑 rect × scale = 物理 bbox。 |
| `enum_children` 里找不到验证码图片控件 | 正常！它就是 owner-drawn 无 HWND。**不要**试图枚举它，改用"输入框右侧同排"相对定位（路径 A）。 |
| 验证码总报过期 | 验证码时效极短。流程必须：截屏→即时回传→读出→立即 `submit_only` 填码点登录，**不要重填表单**（重填会刷新验证码，使刚读出的码失效）。 |
| 重跑 `login_declare` 后验证码变了 | `login_declare` 会重填单位+密码，触发验证码刷新。读码与提交必须用 `submit_only.py`（只填验证码+点登录，不重填表单）。 |

## 一键用法

```bash
# 1) 填表 + 截验证码区域（VM 内抓真整屏 + 相对定位裁出 captcha_only.png）
~/Documents/rpa/run_vm.sh \
  --args-json '{"unit":"修文县关珍养殖场","password":"<KeePass取>"}' ~/Documents/rpa/capture_captcha.py
# 2) 回传（pull_file.sh 仍在 withholding-login 技能 scripts/ 目录）
~/.workbuddy/skills/withholding-login/scripts/pull_file.sh C:/rpa/screenshots/captcha_only.png ./captcha_only.png
# 3) 视觉/OCR 读出 4 位字符后，立即 submit（只填码+点登录，不重填表单）
~/Documents/rpa/run_vm.sh --args-json '{"captcha":"<读出的4位>"}' ~/Documents/rpa/submit_only.py
```

密码经 `--args-json` 走 base64(JSON)，绝不硬编码/落明文；日志里只记长度（`mask()`）。

## 资源

- `~/Documents/rpa/capture_captcha.py` — VM：填表 → `ImageGrab.grab()` 真整屏 → 算 scale → 相对定位裁验证码图（`captcha_only.png`）+ 落 `children.json` 双保险。
- `~/Documents/rpa/submit_only.py` — VM：在已填好表单的登录窗上**只填验证码 + 点登录**（不重填，避免刷新）。
- 配套：`withholding-login` 技能（登录状态机 / KeePass 取密 / 桥接驱动）。

> 脚注：填表逻辑（切 tab / 选单位 / `WM_SETTEXT` 填密）与本技能解耦——`capture_captcha.py` 内联了一份独立副本，不依赖 `withholding-login` 的其它脚本，便于单独经 `run_vm.sh` 运行。
