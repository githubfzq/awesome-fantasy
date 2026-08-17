# 自然人电子税务局（扣缴端）VM 操作手册

本文档是 `tax-withholding-vm` 技能的执行细节。所有命令假设从 Mac 运行，目标为
Parallels Windows 11 VM（"Windows 11"，IP `10.211.55.5`），CUA computer_server 在
`http://10.211.55.5:8000/mcp`。

## 0. 环境常量（先确认）

| 项目 | 值 |
|---|---|
| VM 名称 | `Windows 11` |
| VM IP | `10.211.55.5` |
| Mac 侧网桥 IP | `10.211.55.1`（接口 `bridge100`） |
| CUA endpoint | `http://10.211.55.5:8000/mcp` |
| mcp_call.py | `/Users/fanzuquan/.workbuddy/skills/cua-computer-use/scripts/mcp_call.py` |
| prlctl 桥客户端 | `~/.prlctl-bridge/call.sh` |
| VM Python | `C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\python3.13.exe`（版本号会变，见下） |
| psexec | `C:\pstools\psexec.exe` |
| 扣缴端安装目录 | `C:\ITSKHD\EPPortal_DS3.0\` |
| 启动器 | `C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe`（拉起 `EPPortalITS2.exe`） |
| 故障子进程 | `C:\ITSKHD\EPPortal_DS3.0\AppModules\ITSKHD\Common\Base\ProcDataDeal\ProcDataDeal.exe`（x86） |
| 截图保存目录 | 工作区内的 `screenshots/`（**不要用 /tmp，预览打不开**） |

### 获取 VM 内 Python 精确路径（版本会变）

```powershell
(Get-ChildItem 'C:\Program Files\WindowsApps' -Filter 'python3.13.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
```
用 `~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "..."` 执行，或技能脚本 `cua_ps.py`。

### 健康检查

```bash
# Mac 侧（绕过代理）
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status
# → {"status":"ok","os_type":"windows","features":["mcp"]}
```

若返回空 / 超时 → CUA 服务没在跑（见 §6 重注）。

---

## 1. 确定性启动扣缴端（不要靠桌面坐标盲点）

```bash
cd /Users/fanzuquan/.workbuddy/skills/tax-withholding-vm/scripts
python3 cua_ps.py <<'PS'
Start-Process 'C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe' -WorkingDirectory 'C:\ITSKHD\EPPortal_DS3.0'
"launched"
PS
```

启动后等 6–8 秒再截图。

---

## 2. 程序化关闭系统错误弹窗（不靠坐标）

扣缴端常见 `ProcDataDeal.exe - 系统错误` 对话框（类 `#32770`）。UI Automation 对这类
对话框枚举不到控件，必须用 Win32 API。技能自带脚本：

```bash
python3 cua_ps.py close_popup.ps1 "ProcDataDeal" "确定"
```

- 第 1 个参数 = 标题关键字（空串 = 匹配所有对话框）
- 第 2 个参数 = 要点击的按钮文字（空串 = 只读取不点击）

输出示例：
```
DIALOG: ProcDataDeal.exe - 系统错误 [hwnd=263224]
--- controls ---
Button | 确定 [hwnd=197694]
Static | 由于找不到 MSVCR100.dll，无法继续执行代码...
CLICKED hwnd=197694 (确定)
```
无弹窗时输出 `NO_DIALOG_FOUND titleKw='...'`。

---

## 3. 不靠看截图判断是否有弹窗（自动检测）

```bash
python3 cua_ps.py detect_dialog.ps1
```
（脚本见同目录 `detect_dialog.ps1`，枚举可见顶层窗口标题，命中 `ProcDataDeal`/`
系统错误`/`MSVCR` 即报告，否则 `NO_ERROR_DIALOG_FOUND`。）

---

## 4. 修复 MSVCR100.dll 缺失（VC++ 2010 运行库）

**前置：VM 无外网**。走 Mac 中转：

### 4.1 Mac 下载运行库
```bash
mkdir -p ~/tax_redist && cd ~/tax_redist
curl -L --max-time 120 -o vcredist_x86.exe \
  "https://download.microsoft.com/download/5/B/C/5BC5DBB3-652D-4DCE-B14A-475AB85EEF6E/vcredist_x86.exe"
```
（x64 备选 URL 常年变，扣缴端是 32 位，x86 通常足够；如需 x64 自行搜索
`vcredist_x64.exe` 2010。）

### 4.2 Mac 起本地 HTTP 服务（Parallels 子网）
```bash
# 确认 bridge100 有 IP（无则 sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0）
sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0 2>/dev/null
cd ~/tax_redist
python3 -m http.server 8000 --bind 10.211.55.1 --directory ~/tax_redist
```

### 4.3 VM 内拉取并静默安装（前台，长超时）
```bash
python3 cua_ps.py install_runtime.ps1
```
`install_runtime.ps1` 内容（脚本同目录已有）：
```powershell
New-Item -ItemType Directory -Force -Path C:\vc | Out-Null
Invoke-WebRequest -Proxy $null -Uri http://10.211.55.1:8000/vcredist_x86.exe -OutFile C:\vc\vcredist_x86.exe
Start-Process C:\vc\vcredist_x86.exe -ArgumentList '/q','/norestart' -Wait
"install exit: $LASTEXITCODE"
Get-Item 'C:\Windows\SysWOW64\MSVCR100.dll','C:\Windows\System32\MSVCR100.dll' | Select FullName,Length
```
> 注意：`computer_run_command` 默认 30s 超时，安装要加长客户端超时——直接用
> `cua_ps.py` 即可（其底层 `_post` 用 120s；若仍不够，临时改 `mcp_call.py` 里
> `timeout=30`）。安装后通常 `REBOOT PENDING`（见 §5）。

安装完成后**务必停止 Mac 的 HTTP 服务**：`pkill -f "http.server 8000 --bind 10.211.55.1"`。

---

## 5. 重启 VM 并重新注入 CUA 服务

VC++ 2010 安装后会留挂起文件操作，**必须重启 VM** 才能让子进程识别运行库。

### 5.1 重启（走独立 prlctl 桥，不依赖即将退出的 CUA 服务）
```bash
CALL=~/.prlctl-bridge/call.sh
$CALL exec "Windows 11" cmd /c "shutdown /r /t 3 /f"
```
轮询直到 `ping 10.211.55.5` 重新通（通常 ~60s）。

> 不要用 Mac 上的裸 `prlctl` 命令：非 GUI shell 下会报 `/bin/ps: Operation not
> permitted`、初始化失败。一律走 `~/.prlctl-bridge/call.sh`。

### 5.2 重注 CUA 服务到交互会话 1
```bash
CALL=~/.prlctl-bridge/call.sh
PY="C:\\Program Files\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\\python3.13.exe"
CMD="C:\\pstools\\psexec.exe -i 1 -d -accepteula \"$PY\" -m computer_server --host 0.0.0.0 --port 8000 --detect-resolution >> C:\\cua_server.log 2>&1"
$CALL exec "Windows 11" cmd /c "$CMD"
sleep 8
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status   # 期望 ok
```
要点：
- **必须 `-i 1`** 注入到 console 会话 1，否则截图得到空 `image_data`（落在 session 0）。
- 用 `psexec -d`  detached，服务不会随 exec 结束被杀。

### 5.3 验证运行库修复
重注后启动扣缴端，再跑 `detect_dialog.ps1` 应返回 `NO_ERROR_DIALOG_FOUND`，且
`ProcDataDeal` 进程 `Responding=True`。

---

## 6. 故障排查表

| 现象 | 原因 | 处理 |
|---|---|---|
| `computer_screenshot` 返回 `image_data` 空 | CUA 服务在 session 0 | `psexec -i 1 -d` 重注服务 |
| curl 到 VM 超时 | 本地 http_proxy 拦截内网 | `curl --noproxy '*'`；或用 `cua_ps.py`（已禁用代理） |
| 找不到 VM IP | bridge100 无 IPv4 | `sudo ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0` |
| 启动扣缴端弹 `找不到 MSVCR100.dll` | 缺 VC++ 2010 运行库 | 见 §4 安装；**装完必须重启 VM（§5）** |
| 安装/命令超时 | `computer_run_command` 默认 30s | 用 `cua_ps.py`（120s）；长任务改 `mcp_call.py` 超时 |
| 命令 "命令行太长" | inline 脚本过长（含 Add-Type） | 用 `cua_ps.py script.ps1`（先落盘 `-File` 执行） |
| PowerShell 报 `$PID` 只读 | 脚本里用了 `$pid` 变量名 | 改名（如 `$pidv`） |
| 截图预览打不开 | 存到 /tmp（home 之外） | 存到工作区 `screenshots/` |

---

## 7. 常用片段

```bash
# 截图（存工作区）
python3 /Users/fanzuquan/.workbuddy/skills/cua-computer-use/scripts/mcp_call.py \
  http://10.211.55.5:8000/mcp computer_screenshot \
  --save /Users/fanzuquan/WorkBuddy/2026-08-12-11-27-44/screenshots/xxx.png --noproxy

# 看全部进程（避免 zsh 转义：用文件 + cua_ps.py）
python3 cua_ps.py list_all.ps1

# 杀掉扣缴端相关进程
python3 cua_ps.py <<'PS'
Get-Process | Where-Object {$_.Name -like '*EPPortal*' -or $_.Name -like '*EPEvenue*' -or $_.Name -like '*ProcDataDeal*'} | Stop-Process -Force -ErrorAction SilentlyContinue
"killed"
PS
```
