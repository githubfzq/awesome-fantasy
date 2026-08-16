---
name: tax-withholding-vm
description: >-
  操作 Parallels Windows 11 虚拟机（"Windows 11"，10.211.55.5）中的「自然人电子税务局（扣缴端）」的端到端技能。
  涵盖：通过 cua computer_server 驱动 VM（截图/点击/输入/运行命令）、确定性启动扣缴端、
  程序化读取并关闭系统错误弹窗（ProcDataDeal.exe - 系统错误 / MSVCR100.dll 缺失）、
  修复 VC++ 2010 运行库（Mac 中转下载 + 静默安装 + 重启 VM + 重注 CUA 服务）。
  当用户要做扣缴端申报、报税、登录、或遇到"找不到 MSVCR100.dll""系统错误"弹窗、
  需要重启/重连 VM 的 computer_server 时使用。
agent_created: true
---

# 自然人电子税务局（扣缴端）VM 操作

## 何时用

- 在 Parallels Windows VM 里启动 / 操作「自然人电子税务局（扣缴端）」
- 扣缴端弹「ProcDataDeal.exe - 系统错误」「找不到 MSVCR100.dll」等报错
- VM 重启后 CUA computer_server 失联，需要重新注入会话
- 需要不靠坐标、不靠肉眼看截图地驱动 Windows 桌面

## 关键事实（环境）

- VM：`Windows 11`，IP `10.211.55.5`；Mac 侧网桥 `bridge100` = `10.211.55.1`
- CUA endpoint：`http://10.211.55.5:8000/mcp`（由 `cua-computer-use` 技能提供）
- 扣缴端：`C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe`（拉起 `EPPortalITS2.exe`）
- 故障子进程：`...\AppModules\ITSKHD\Common\Base\ProcDataDeal\ProcDataDeal.exe`（x86）
- 脚本目录：`scripts/`（`cua_ps.py` 封装 PowerShell 执行；`close_popup.ps1` 关弹窗；
  `detect_dialog.ps1` 检测弹窗；`install_runtime.ps1` 装运行库；`list_all.ps1`）

## 工作流

### 1) 连通性自检
```bash
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status
```
返回 `{"status":"ok",...}` 即可。失败 → 见 §「CUA 服务重注」。

### 2) 确定性启动扣缴端（不要用桌面坐标盲点）
```bash
cd <skill>/scripts
python3 cua_ps.py <<'PS'
Start-Process 'C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe' -WorkingDirectory 'C:\ITSKHD\EPPortal_DS3.0'
"launched"
PS
```
启动后等 6–8 秒再截图（截图存**工作区** `screenshots/`，勿存 `/tmp`）。

### 3) 关闭系统错误弹窗（不靠坐标）
```bash
python3 cua_ps.py close_popup.ps1 "ProcDataDeal" "确定"
```
（UI Automation 对 `#32770` 对话框枚举不到控件，脚本走 Win32 `FindWindow` + `SendMessage BM_CLICK`。）

### 4) 检测是否还有弹窗（不看截图）
```bash
python3 cua_ps.py detect_dialog.ps1
# 无 → NO_ERROR_DIALOG_FOUND
```

### 5) 修复 MSVCR100.dll（VC++ 2010 运行库）
VM 无外网，走 Mac 中转（详见 `references/runbook.md` §4）：
1. Mac 下载 `vcredist_x86.exe`；
2. Mac 起 `python3 -m http.server 8000 --bind 10.211.55.1 --directory <dir>`；
3. VM 内 `python3 cua_ps.py install_runtime.ps1`（拉取 + `/q /norestart` 安装）。
4. **装完必须重启 VM**（安装会留挂起文件操作）。装完停掉 Mac HTTP 服务。

### 6) 重启 VM + 重注 CUA 服务
```bash
CALL=~/.prlctl-bridge/call.sh
$CALL exec "Windows 11" cmd /c "shutdown /r /t 3 /f"   # 走 prlctl 桥，别用裸 prlctl
# 轮询 ping 10.211.55.5 直到恢复（~60s）
PY="C:\\Program Files\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\\python3.13.exe"
CMD="C:\\pstools\\psexec.exe -i 1 -d -accepteula \"$PY\" -m computer_server --host 0.0.0.0 --port 8000 --detect-resolution >> C:\\cua_server.log 2>&1"
$CALL exec "Windows 11" cmd /c "$CMD"
curl -s --noproxy '*' --max-time 8 http://10.211.55.5:8000/status   # 期望 ok
```
> `-i 1` 必须（注入 console 会话 1）；`psexec -d` detached 避免随 exec 结束被杀。
> Mac 上裸 `prlctl` 在非 GUI shell 会报 `/bin/ps: Operation not permitted`，一律走 `~/.prlctl-bridge/call.sh`。

## 常见坑（速查）

| 现象 | 处理 |
|---|---|
| 截图 `image_data` 空 | CUA 服务在 session 0 → 用 `psexec -i 1` 重注 |
| curl 内网超时 | 加 `--noproxy '*'`；`cua_ps.py` 已禁用代理 |
| 找不到运行库弹窗 | §5 装 VC++ 2010 后**必须重启 VM** |
| 命令"命令行太长" | 用 `cua_ps.py script.ps1`（先落盘再 `-File`） |
| PowerShell `$pid` 只读报错 | 避免使用 `$pid` 作变量名 |

完整细节见 `references/runbook.md`。
