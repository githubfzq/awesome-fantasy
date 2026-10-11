---
name: withholding-captcha-crop
description: "截取 Delphi VCL / Win32 应用（如扣缴端）里 owner-drawn 验证码位图（无 HWND）：用 ImageGrab.grab() 抓真整屏物理像素 + DPI scale + 相对定位裁出干净小图，供 OCR / 视觉识别。扣缴端登录的验证码截取已内置在 withholding-login 的 auto_login.py；本技能保留独立脚本 capture_captcha.py 与原理，供单独截取、排查"截图被裁/黑屏/坐标偏"时使用。"
agent_created: true
---

# 扣缴端验证码图片区域截取（owner-drawn captcha crop）

## 何时用

- RPA 流程里需要把验证码图片本身截成干净小图交给 OCR / 视觉识别。
- 截图出问题：截到壁纸、整屏裁半、坐标对不上、黑屏。
- 排查/复现验证码截取逻辑（扣缴端正常登录走 `withholding-login` 的 `auto_login.sh`，已内置截码，见下）。

## 核心结论

登录窗的验证码**不是独立窗口控件**——是画在窗体画布上的位图（owner-drawn，无 HWND）。

- ❌ `enum_children` 枚举不出它（压根没有这个窗口）。
- ✅ **相对定位（路径 A）**：登录窗 `Tfrm_LoginViewer` 是顶层窗口，`enum_top_windows` 拿 `rect`（逻辑像素）；
  验证码位图画在**验证码输入框右侧同一行** → 输入框矩形 + 窗体右边界推出，再从"真整屏"裁出。
- 实测参考（3024×1890 屏、scale=2.0）：登录窗 `[535,227,977,718]`，验证码输入框 `[597,520,794,557]`，
  位图 ≈ `[795,512,976,562]`。**别硬编码**——运行时动态从 enum 推，相对关系才稳定。

## 截图方式选型（最关键的坑）

| 方式 | 结果 | 结论 |
|---|---|---|
| `powershell CopyFromScreen` | 1512×945（逻辑分辨率，半屏/被裁） | ❌ 禁用 |
| 独立 `PIL.ImageGrab.grab()`（非 session1 语境） | 黑屏 / 壁纸 | ❌ |
| **`rpa_core.snapshot()` 内 `ImageGrab.grab()`**（`run_vm.sh` + pythonw 在 session 1） | 3024×1890 真·整屏物理像素 | ✅ 唯一可靠 |

**铁律**：截整屏只用 `ImageGrab.grab()`（全屏无参数），且必须经 `run_vm.sh` 在交互桌面会话 1 执行。

## 坐标映射（DPI 不踩坑）

```
scale = 整屏图像.width / GetSystemMetrics(SM_CXSCREEN=0)   # 本 VM：3024/1512 = 2.0，每次现算别写死
物理_rect = [int(v * scale) for v in 逻辑_rect]
ImageGrab.grab(bbox=物理_rect)   # 从整屏裁出目标
```

## 脚本

- `~/Documents/rpa/capture_captcha.py` — 独立单步：填表让验证码出现 → `ImageGrab.grab()` 真整屏 → 算 scale →
  相对定位裁出 `captcha_only.png`（VM 内 `C:/rpa/screenshots/`），并落 `children.json` 双保险（万一偏了可按同坐标系重裁）。
- `~/Documents/rpa/submit_only.py` — 在已填好表单的登录窗上**只填验证码 + 点登录**（不重填表单，避免刷新验证码使刚读出的码失效）。
- **扣缴端登录已内置**：`withholding-login` 的 `auto_login.sh` 自动完成 刷新→截码→共享盘 `~/Documents/rpa/captcha.png`（`captcha_mac`），
  无需单独调本技能脚本；仅当要手动截码或排查时才用 `capture_captcha.py`。

## 已知坑速查

| 现象 | 根因 / 处理 |
|---|---|
| 壁纸 / 黑屏 | 没在 session1 pythonw 语境跑 `ImageGrab`，或用了 `CopyFromScreen` |
| 整屏只有一半 | `CopyFromScreen` 给逻辑分辨率；换 `ImageGrab.grab()` |
| 裁出来空白/错位 | scale 没乘或猜错；务必 `整屏宽/GetSystemMetrics(0)` 现算 |
| enum 找不到验证码控件 | 正常，owner-drawn 无 HWND；用"输入框右侧同排"相对定位 |
| 验证码总过期 | 时效极短：截屏→回传→读出→立即填码提交，**不要重填表单**（会刷新验证码） |

## 一键用法（独立截码）

```bash
# 填表 + 截验证码区域（输出在 VM 内 C:/rpa/screenshots/captcha_only.png）
~/Documents/rpa/run_vm.sh \
  --args-json '{"unit":"修文县关珍养殖场","password":"<KeePass取>"}' ~/Documents/rpa/capture_captcha.py
# 回传（需手动时）：
~/.workbuddy/skills/withholding-login/scripts/pull_file.sh C:/rpa/screenshots/captcha_only.png ./captcha_only.png
# 读出 4 位后立即提交（不重填表单）：
~/Documents/rpa/run_vm.sh --args-json '{"captcha":"<4位>"}' ~/Documents/rpa/submit_only.py
```

密码经 base64(JSON) 传递，日志只记长度（`mask()`），绝不落明文。
