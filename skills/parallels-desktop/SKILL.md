---
name: parallels-desktop
description: >-
  Parallels Desktop 虚拟机运维管理技能。用于管理和排查 macOS 上 Parallels Desktop
  虚拟机问题，包括启动/停止虚拟机、Secure Boot 安全启动问题修复、虚拟机卡死强制关闭、
  查看和修改虚拟机硬件配置等。当用户提到 Parallels、PD、虚拟机无法启动、安全启动报错、
  Secure Boot、prlctl、Windows 虚拟机等关键词时触发。
agent_created: true
---

# Parallels Desktop 虚拟机运维管理

## Overview

通过 `prlctl` 命令行工具管理和排查 macOS 上 Parallels Desktop 虚拟机问题。涵盖虚拟机生命周期管理、Secure Boot 修复、强制关闭、权限提升、服务初始化、网络修复等常见运维场景。

## 前置条件

- macOS 上已安装 Parallels Desktop
- `prlctl` 命令行工具位于 `/Applications/Parallels Desktop.app/Contents/MacOS/prlctl`
- **prlctl 连接 Parallels Service 的上下文要求**：只有在「用户 GUI 登录会话（如 Terminal.app）」或「osascript administrator privileges（root）」两种上下文下 `prlctl` 才能连上服务。在 WorkBuddy 这类**非 GUI 会话、非提权**的执行上下文里，即使**关闭沙箱、赋予完全权限**，直接跑 `prlctl` 也会报 `Unable to connect to Parallels Service`（exit 253）——这不是沙箱/权限问题，而是 `prlctl` 只能从上述两种上下文连上服务。

## 核心原则：优先用户身份，禁止提权启动 VM（最高优先级）

> 🚨 **铁律：以 root 身份（osascript 提权）启动的 VM，和以用户身份启动的 VM 是两套完全独立的实例。用户要的是「用户身份的 VM」——只有这样用户才能在 Parallels 界面实时看到、操作它。**

**提权的弊端（实战血泪）**：用 `osascript ... with administrator privileges`（root 上下文）执行 `prlctl start`，VM 会挂在 root 上下文里：
- 用户的 GUI 会话**看不到、也用不了**这个 VM，Parallels 窗口里不显示；
- 即便 `pgrep` 能看到 `prl_vm_app` 进程在跑，用户那边依然显示未启动；
- root 上下文与用户 GUI 会话是**两套独立的 VM 状态视图**，`prlctl list` 在两个上下文下结果对不上（root 上下文还可能返回假的 `stopped`）。

**正确做法**：
- **启动 / 恢复 / 重启 VM（`start` / `resume` / `restart`）→ 必须由用户在本机 Terminal.app 里不加 sudo 执行**，VM 才挂在用户上下文、用户可见可用。在 WorkBuddy / SSH 等非 GUI 会话里无法以用户身份启动 VM（prlctl 报 exit 253），此时**只能把启动命令交给用户在 Terminal 执行，绝不要用提权代启动**。
- **查看状态（`list`）、修改配置（`set`）、VM 内执行（`exec`）等 → 同样优先用户身份**（在 Terminal.app 里），让结果对应用户的 VM 视图。
- **提权（`osascript administrator privileges`）仅用于少数系统级操作**：初始化服务（`inittool2 init`）、加载 LaunchDaemon、分配 `bridge100` IP、清理被 root 误启动的 VM 进程等。这些操作不涉及「VM 归属哪个上下文」。
- **在 WorkBuddy 等非 GUI 会话上下文里**：能直接做的只有 `pgrep` 进程核查、`ifconfig`/`nc` 网络探测等不依赖 prl_disp_service 的命令；凡是要 `prlctl` 的，要么提权（仅限系统级操作），要么交给用户在 Terminal 跑（涉及 VM 生命周期的，一律交给用户）。

## 权限提升（仅限系统级操作，勿用于启动 VM）

> ⚠️ 再次强调：本节提权手段**只用于 inittool2 / LaunchDaemon / bridge100 / 清理 root 残留 VM 等系统级操作**。**启动、恢复、查看、配置 VM 一律用用户身份在 Terminal.app 执行，禁止提权**——否则 VM 挂在 root 上下文，用户看不到（详见上方「核心原则」）。

prlctl 与 Parallels Service 通信本身不强制 root——在用户 GUI 登录会话（Terminal.app）里以用户身份即可正常使用。只有在 WorkBuddy 等非 GUI 会话上下文、且必须执行系统级操作时，才用 `osascript administrator privileges` 提权突破（沙箱中 `/bin/ps` 也被阻止）：

### 模式 1：直接执行（简单命令）
```bash
osascript -e 'do shell script "/Applications/Parallels\\ Desktop.app/Contents/MacOS/prlctl list -a" with administrator privileges'
```

### 模式 2：Shell 脚本中转（复杂命令，推荐）
多层嵌套转义容易出错，写脚本到 `/tmp` 再执行：
```bash
cat > /tmp/run_vm_cmd.sh << 'SCRIPT'
#!/bin/bash
PRLCTL="/Applications/Parallels Desktop.app/Contents/MacOS/prlctl"
"$PRLCTL" exec "Windows 11" cmd /c "ipconfig"
SCRIPT
chmod +x /tmp/run_vm_cmd.sh
osascript -e 'do shell script "/tmp/run_vm_cmd.sh" with administrator privileges'
```

> **关键陷阱**：`$PRLCTL` **必须加双引号**写成 `"$PRLCTL"`。因为 prlctl 路径含空格（`Parallels Desktop.app`），不加引号时 bash 会做词分割，把 `/Applications/Parallels` 当命令、`Desktop.app/...` 当参数，报 `No such file or directory (127)`。已实战复现。最稳妥的写法是直接用带引号的完整路径，不用变量：`"/Applications/Parallels Desktop.app/Contents/MacOS/prlctl" start "Windows 11"`。同理，heredoc 内其它含空格路径的变量引用也都要加引号。

### 模式 3：ps 包装脚本（沙箱中 /bin/ps 被阻止时）
```bash
mkdir -p /tmp/prlbin
cat > /tmp/prlbin/ps << 'PSWRAPPER'
#!/bin/bash
if [ "$1" = "-A" ] || [ "$1" = "-e" ]; then
    echo "  PID TTY           TIME CMD"
    /usr/bin/ps -A 2>/dev/null || true
else
    /usr/bin/ps "$@" 2>/dev/null || true
fi
PSWRAPPER
chmod +x /tmp/prlbin/ps
# 使用时：PATH=/tmp/prlbin:$PATH prlctl <command>
```

**注意**：`osascript administrator privileges` 会弹出 macOS 密码输入框，需用户配合。

## Parallels Service 管理

当 Parallels Service（`prl_disp_service`）未运行时，所有 prlctl 命令都会失败。

### 检查服务状态
```bash
pgrep -x prl_disp_service
sudo launchctl list | grep parallels
```

### 初始化并启动服务
```bash
# Step 1: 初始化
osascript -e 'do shell script "/Applications/Parallels\\ Desktop.app/Contents/MacOS/inittool2 init" with administrator privileges'

# Step 2: 加载 LaunchDaemon
osascript -e 'do shell script "cp /Applications/Parallels\\ Desktop.app/Contents/LaunchDaemons/com.parallels.desktop.launchdaemon.plist /Library/LaunchDaemons/ && launchctl load /Library/LaunchDaemons/com.parallels.desktop.launchdaemon.plist" with administrator privileges'

# Step 3: 验证
pgrep -x prl_disp_service
```

## VM 注册

当 VM 在磁盘上存在但 `prlctl list -a` 不显示时，需要注册：

```bash
osascript -e 'do shell script "/Applications/Parallels\\ Desktop.app/Contents/MacOS/prlctl register \\"/Users/<user>/Parallels/Windows 11.pvm\\"" with administrator privileges'
```

## 常用命令速查

> **重要**：以下命令**默认应在用户本机 Terminal.app 里以用户身份执行**（不加 sudo），这样 VM 和状态才属于用户上下文、用户可见。**仅当明确标注「需提权」的系统级操作**才用 `osascript administrator privileges`。启动/恢复/重启 VM 一律用户身份，禁止提权（详见「核心原则」）。

### 虚拟机生命周期

```bash
# 列出所有虚拟机（含状态和 IP）
prlctl list -a

# 查看虚拟机详细信息（硬件配置、安全设置等）
prlctl list -i "Windows 11"

# 启动虚拟机（⚠️ 必须用户身份在 Terminal.app 执行，禁止提权！提权启动的 VM 用户看不到）
prlctl start "Windows 11"

# 正常关闭虚拟机（关用户上下文的 VM 也用用户身份；仅清理 root 残留 VM 才提权）
prlctl stop "Windows 11"

# 强制关闭虚拟机（相当于拔电源）
prlctl stop "Windows 11" --kill

# 暂停/恢复虚拟机（同样必须用户身份，禁止提权）
prlctl pause "Windows 11"
prlctl resume "Windows 11"

# 重启虚拟机（同样必须用户身份，禁止提权）
prlctl restart "Windows 11"
```

### 查看关键配置

```bash
# 查看 Secure Boot 状态
prlctl list -i "Windows 11" | grep -i "secure boot"

# 查看 BIOS 类型
prlctl list -i "Windows 11" | grep -i "bios type"

# 查看 TPM 状态
prlctl list -i "Windows 11" | grep -i "tpm"

# 查看 CPU 和内存配置
prlctl list -i "Windows 11" | grep -i "cpu\|memory"

# 查看虚拟机文件路径
prlctl list -i "Windows 11" | grep "Home:"
```

## 状态查询陷阱：prlctl list 可能返回假的 stopped

`prlctl list -a` 经 `osascript ... with administrator privileges`（root 上下文）执行时，可能返回**与实际不符的 `stopped`**——即使虚拟机实际正在运行。已实战复现：root 上下文两次返回 `stopped`，但用户自己的终端（同一系统、同一个 `prl_disp_service`）返回 `running`，且进程树确认 VM 进程存活。

**根因（推测）**：osascript 提权环境下 `prlctl` 与 `prl_disp_service` 的连接/状态同步不稳定，CLI 输出的 STATUS 字段不可全信。

**判断 VM 是否真在运行的硬证据（优先级从高到低）**：
1. 进程树中存在 `prl_vm_app --vm-name "<VM名>"` 进程（最可靠）。
2. 存在 `WinAppHelper`（融合 / Coherence 模式）进程。
3. 用户自己的终端直接运行 `prlctl list -a`（非 osascript）的结果。

**正确的状态核查方式（优先用 pgrep，无需 osascript）**：
```bash
# 方法 A：pgrep 直接命中 VM 进程（沙箱内也可用，无需提权、无需 osascript）
pgrep -fl prl_vm_app
# 输出形如：88395 .../prl_vm_app --vm-name Windows 11 ...
# 只要出现 prl_vm_app --vm-name "<VM名>"，即证明 VM 在运行

# 方法 B：交叉验证 .pvm 锁文件与日志（VM 运行时 vm.lock 存在、parallels.log 持续更新）
ls -la "/Users/<user>/Parallels/Windows 11.pvm/" | grep -E "vm.lock|parallels.log|VmInfo.pvi"

# 方法 C（兜底）：若仍想看完整进程树，沙箱内 /bin/ps 被拦截，需用 osascript 提权
osascript -e 'do shell script "ps -A -o pid,user,command | grep -i parallels | grep -v grep" with administrator privileges'
```
> 沙箱提示：`/bin/ps`、`/usr/bin/ps` 通常被拦截返回空，但 `pgrep` 可用，因此**方法 A 是最稳的非 osascript 核查手段**。

> 注意：在 WorkBuddy 这类非 GUI 会话上下文里，即使**关闭沙箱、赋予完全权限**，直接运行 `prlctl` 仍会报 `Unable to connect to Parallels Service`（exit 253）——这不是沙箱/权限问题，而是 `prlctl` 只能从用户 GUI 会话或 osascript 提权上下文连上服务。而 osascript 提权查到的 STATUS 又可能是假的 `stopped`——因此**判断 VM 是否真在运行请以 `pgrep -fl prl_vm_app` 进程树为准**，不要只信 `prlctl list` 的输出。
> **根因**：macOS bootstrap 命名空间。GUI 服务（含 `prl_disp_service`）只在 GUI 会话命名空间（loginwindow/WindowServer 创建）注册；SSH/非 GUI 会话创建独立命名空间看不到它。切 WorkBuddy「完全访问」只解沙箱拦截，不换命名空间，所以仍 253。
> 命名空间切换工具：`launchctl asuser <uid>` 与 `launchctl bsexec <GUI-pid>`——**非 root 下都是空操作，会失败**（已实测）。但 `bsexec` 补上 root + `chroot -u` 降权后可行，见下节「非 GUI 会话复用 GUI 会话 prlctl」。

## 非 GUI 会话复用 GUI 会话 prlctl（osascript admin + bsexec + chroot）

> 这是**从 WorkBuddy / SSH / launchd 等 non-GUI 会话执行 VM 命令的唯一可行解**。2026-08-10 实测确认。

**原理**：用 `osascript ... with administrator privileges` 拿 root → `launchctl bsexec <GUI-pid>` 切到 GUI 会话的 bootstrap 命名空间（能看到 `prl_disp_service`）→ `chroot -u <uid> -g <gid> /` 降权回用户身份（避免 root 上下文的"假 stopped"陈旧视图）→ prlctl 以用户身份在用户命名空间跑，与 Terminal.app 完全一致。

**三个对照实验结论**（uid=501, gid=20, GUI-pid=prl_client_app 10738）：
| 方式 | list -a 结果 | 解读 |
|---|---|---|
| root 直接跑 prlctl（不切命名空间） | `stopped` ❌假 | 连上服务但 root 陈旧视图 |
| `launchctl asuser 501 prlctl` | `stopped` ❌假 | asuser 没真正切到用户 GUI 命名空间 |
| `launchctl bsexec <pid> chroot -u 501 -g 20 / prlctl` | **`running`** ✅真 | 切命名空间+降权，唯一正确 |

**命令模板**（单条，弹一次 macOS 密码框）：
```bash
osascript -e 'do shell script "launchctl bsexec <GUI-pid> chroot -u <uid> -g <gid> / \"/Applications/Parallels Desktop.app/Contents/MacOS/prlctl\" exec \"Windows 11\" cmd /c \"<cmd>\"" with administrator privileges'
```
- `<GUI-pid>`：任意 GUI 会话进程 pid（`prl_client_app` / `loginwindow` / `WindowServer`），用 `pgrep -fl prl_client_app` 查
- `<uid>`/`<gid>`：`id -u` / `id -g`
- 复杂/批量命令：写脚本到 `/tmp` 再 osascript admin 执行（避免转义地狱，见「权限提升·模式 2」），一次密码框跑完多条

**实测成功的 exec 输出**：`ver`→版本号、`hostname`→PE7D、`ipconfig`→10.211.55.5，且**中文不乱码**（osascript do shell script 全程 UTF-8，优于 Terminal.app 直接跑的 GBK 乱码）。

**关键约束**：
- **必须 root**：bsexec 改引导空间需 root，不加 sudo 是空操作。
- **必须 chroot -u 降权**：否则 prlctl 以 root 跑在 GUI 命名空间，仍看到"假 stopped"。
- **不违反"禁止提权启动 VM"铁律**：这里 root 仅用于切命名空间，prlctl 最终以用户身份跑；且 `exec` 不涉及 VM 进程归属（那个问题是 `start` 才有）。`start`/`stop`/`resume` 等生命周期命令仍禁止用此法（会让 VM 挂错上下文）——**本节方案只用于 `exec` / `list` / `set` 等非生命周期操作**。
- **每次弹密码框**：osascript admin 每次调用都弹一次，批量命令写进一个脚本一次密码框搞定。
- **asuser 不可用**：实测 `asuser` 仍返回假 stopped，只有 `bsexec` + `chroot -u` 正确。

## 一劳永逸：GUI 会话 LaunchAgent + 文件 IPC 桥接（推荐，永久免密）

> 上一节 osascript admin 方案每次弹密码框，跑多条命令很烦。sudoers NOPASSWD 不可行——WorkBuddy 沙箱直接拦截 `sudo`（`operation not permitted: sudo` exit 127）。**本节方案一次设置、之后每条命令零密码零 sudo**。

**架构**：在用户 GUI 会话装一个常驻 agent（LaunchAgent，RunAtLoad+KeepAlive），它原生跑 prlctl（GUI 命名空间，无 253、无命名空间问题）。WorkBuddy（非 GUI 会话）通过文件和 agent 通信：写请求文件 → agent 轮询发现 → 跑 prlctl → 写响应文件 → WorkBuddy 读。纯文件 IO，沙箱友好。

**三个文件**：
1. `~/.prlctl-bridge/agent.sh` — 轮询 agent（**bash 3.2 兼容，用 while-read 读数组，不能用 mapfile**——macOS /bin/bash 是 3.2 不支持）：
```bash
#!/bin/bash
BRIDGE_DIR="$HOME/.prlctl-bridge"
REQ="$BRIDGE_DIR/req"; RES="$BRIDGE_DIR/res"
PRLCTL="/Applications/Parallels Desktop.app/Contents/MacOS/prlctl"
mkdir -p "$BRIDGE_DIR"; rm -f "$REQ" "$RES"
while true; do
  if [ -f "$REQ" ]; then
    args=()
    while IFS= read -r line; do [ -n "$line" ] && args+=("$line"); done < "$REQ"
    rm -f "$REQ"
    if [ ${#args[@]} -gt 0 ]; then output=$("$PRLCTL" "${args[@]}" 2>&1); code=$?; else output="(no args)"; code=1; fi
    tmp="$RES.tmp.$$"; printf '%d\n%s' "$code" "$output" > "$tmp"; mv -f "$tmp" "$RES"
  fi
  sleep 0.3
done
```
2. `~/.prlctl-bridge/call.sh` — WorkBuddy 侧调用器（写 req → 轮询 res → 打印输出 + 退出码）：
```bash
#!/bin/bash
BRIDGE_DIR="$HOME/.prlctl-bridge"; REQ="$BRIDGE_DIR/req"; RES="$BRIDGE_DIR/res"
[ $# -eq 0 ] && { echo "Usage: $0 <prlctl args...>" >&2; exit 2; }
rm -f "$RES"; printf '%s\n' "$@" > "$REQ"
for i in $(seq 1 150); do [ -f "$RES" ] && break; sleep 0.2; done
[ ! -f "$RES" ] && { echo "ERROR: timeout (is LaunchAgent running? check ~/.prlctl-bridge/agent.err)" >&2; exit 1; }
code=$(head -1 "$RES"); output=$(tail -n +2 "$RES"); rm -f "$RES"
printf '%s' "$output"; exit "${code:-0}"
```
3. `~/Library/LaunchAgents/com.user.prlctl-bridge.plist` — LaunchAgent（RunAtLoad+KeepAlive，日志到 `~/.prlctl-bridge/agent.log`/`.err`），ProgramArguments = `/bin/bash` + `~/.prlctl-bridge/agent.sh`

**协议**：req 文件每行一个 prlctl 参数（处理 "Windows 11" 这种含空格参数）；res 文件首行退出码、其余输出（tmp+rename 原子写，调用方不会读到半写文件）。

**一次性加载（唯一一次密码）**：
```bash
chmod +x ~/.prlctl-bridge/agent.sh ~/.prlctl-bridge/call.sh
osascript -e 'do shell script "launchctl bootstrap gui/<uid> ~/Library/LaunchAgents/com.user.prlctl-bridge.plist" with administrator privileges'
```
之后 agent 常驻 GUI 会话（开机自启，KeepAlive 保活）。

**使用（永久免密）**：
```bash
~/.prlctl-bridge/call.sh list -a
~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "ver"
~/.prlctl-bridge/call.sh exec "Windows 11" cmd /c "chcp 65001 >nul && ipconfig"  # 中文乱码时用 chcp 65001
```

**编码注意**：文件 IPC 传原始字节，cmd /c 的 GBK 中文会乱码。`chcp 65001 >nul && <cmd>` 前缀实测有效（输出转英文标签 + 干净 UTF-8）；PowerShell 经 prlctl exec 反而无效（仍 GBK，与 Terminal.app 直接跑不同）；纯 ASCII 输出不受影响。

**卸载**：`launchctl bootout gui/<uid>/com.user.prlctl-bridge`（需 root）+ 删 plist + 删 `~/.prlctl-bridge/`。

## Secure Boot 安全启动问题修复

### 问题现象

启动虚拟机时提示："安全启动功能防止操作系统启动：安全启动功能发现未经授权更改固件、操作系统或UEFI驱动程序"

### 诊断

```bash
# 检查 Secure Boot 状态
prlctl list -i "Windows 11" | grep -i "secure boot"
# 如果输出 "EFI Secure boot: on" 则为问题根源
```

### 修复（Parallels 20.x 唯一有效方法）

GUI 中的引导标记（Boot Flags）在 Parallels 20.x 中不生效，必须使用命令行：

```bash
# 关闭 Secure Boot
prlctl set "Windows 11" --efi-secure-boot off

# 确认已关闭
prlctl list -i "Windows 11" | grep -i "secure boot"
# 应输出 "EFI Secure boot: off"

# 启动虚拟机
prlctl start "Windows 11"
```

### 重新开启 Secure Boot

```bash
prlctl set "Windows 11" --efi-secure-boot on
```

### 常见触发原因

| 原因 | 说明 |
|------|------|
| macOS 系统更新 | 大版本更新后虚拟 UEFI 固件签名链变化 |
| Parallels 版本过旧 | 与当前 macOS 不兼容，Secure Boot 校验逻辑异常 |
| 虚拟机配置变更 | 修改硬件配置后 Secure Boot 认为固件被篡改 |
| Windows 更新 | Windows 更新了 UEFI 驱动但签名不匹配 |

## 虚拟机卡死强制关闭

当虚拟机无响应、无法通过正常方式关闭时，按以下顺序尝试：

### 方法 1：prlctl 强制停止

```bash
prlctl stop "Windows 11" --kill
```

### 方法 2：杀掉虚拟机进程

```bash
killall -9 prl_vm_app
```

### 方法 3：杀掉 Parallels 服务进程

```bash
killall -9 prl_vm_app
killall -9 prl_disp_service
launchctl start com.parallels.desktop.launchdaemon
```

### 方法 4：Mac 强制退出界面

按 `⌘ + ⌥ + Esc`，选择 Parallels 相关进程强制退出。

### 方法 5：重启 Mac（最后手段）

按 `Control + Command + 电源键` 强制重启。重启后先执行 `prlctl stop --kill` 确保无残留状态，再启动虚拟机。

## 硬件配置修改

```bash
# 修改 CPU 核心数
prlctl set "Windows 11" --cpus 4

# 修改内存大小（MB）
prlctl set "Windows 11" --memsize 8192

# 开启/关闭嵌套虚拟化
prlctl set "Windows 11" --nested-virt on
prlctl set "Windows 11" --nested-virt off

# 开启/关闭 TPM
prlctl set "Windows 11" --tpm on
prlctl set "Windows 11" --tpm off
```

## 网络问题排查

### bridge100 无 IP 地址
Parallels Service 异常重启后，`bridge100` 接口（Shared Network 的宿主侧）可能没有 IP，导致无法从 macOS 访问 VM：
```bash
# 检查
ifconfig bridge100

# 手动分配 IP（需要 root）
osascript -e 'do shell script "ifconfig bridge100 inet 10.211.55.1 netmask 255.255.255.0" with administrator privileges'
```

### VM 无外网（NAT 守护进程未运行）
VM 无法访问外网时，检查 `prl_naptd` 是否运行：
```bash
pgrep -x prl_naptd
# 如未运行，重启 Parallels Service 或手动启动
```

### macOS 无法 ping 通 Windows VM
Windows 防火墙默认阻止入站 ICMP，所以 macOS ping 不通 VM，但 VM 能 ping 通 macOS。这是**预期行为**，不代表网络故障。用 TCP 端口测试代替 ping：
```bash
nc -z 10.211.55.5 3389    # 测试 RDP 端口
```

如需允许 ICMP：
```bash
prlctl exec "Windows 11" cmd /c "netsh advfirewall firewall add rule name=\"Allow ICMPv4\" protocol=icmpv4:8,any dir=in action=allow"
```

## VM 内执行复杂命令（共享文件夹+批处理模式）

通过 `prlctl exec` 执行复杂 Windows 命令时，多层转义容易出错。更可靠的方式：

1. 写 `.bat` 文件到 macOS Home（VM 中通过 `Z:\` 访问）
2. 通过 `prlctl exec` 执行批处理

```bash
# 写批处理文件
cat > ~/vm_cmd.bat << 'BAT'
@echo off
ipconfig
BAT

# 在 Terminal.app 里以用户身份执行（不提权）。复杂命令用脚本中转避免转义问题：
cat > /tmp/run_vm_cmd.sh << 'SCRIPT'
#!/bin/bash
"/Applications/Parallels Desktop.app/Contents/MacOS/prlctl" exec "Windows 11" cmd /c "Z:\\vm_cmd.bat"
SCRIPT
chmod +x /tmp/run_vm_cmd.sh
/tmp/run_vm_cmd.sh
```

## 注意事项

- **优先用户身份，禁止提权启动 VM**：`prlctl start/resume/restart` 必须由用户在本机 Terminal.app 不加 sudo 执行；提权（root 上下文）启动的 VM 用户 GUI 看不到。`list`/`set`/`exec` 等也优先用户身份。提权仅用于 inittool2 / LaunchDaemon / bridge100 / 清理 root 残留 VM 等系统级操作（详见「核心原则」）
- **prlctl list 的 STATUS 不可全信**：经 osascript 提权查询可能返回假的 `stopped`，判断 VM 是否真在运行请以 `prl_vm_app` 进程树为准（详见「状态查询陷阱」章节）
- **Shell 脚本中转**：复杂命令（尤其 `prlctl exec` 带嵌套引号）建议写脚本到 `/tmp` 再执行
- **Parallels Service 必须运行**：prlctl 无法连接时用 `inittool2 init` 初始化
- **VM 需注册**：磁盘上存在但 `prlctl list -a` 不显示时，用 `prlctl register` 注册
- **bridge100 可能需要手动分配 IP**：服务重启后检查 `ifconfig bridge100`
- **Windows 防火墙阻止 ICMP**：macOS ping 不通 VM 是预期行为
- **NAT 守护进程**：VM 无外网时检查 `prl_naptd` 是否运行
- 修改虚拟机配置前必须先关闭虚拟机（`prlctl stop`）
- `--kill` 强制关闭可能导致虚拟机文件系统不一致，Windows 下次启动会提示"未正常关机"，选择正常启动即可
- Parallels 20.x 版本的 GUI 中没有 Secure Boot 开关，只能通过 `prlctl set --efi-secure-boot off` 命令关闭
- 引导标记（Boot Flags）中填入 `vm.bios.secure_boot=0` 或 `tools.disable_secure_boot=1` 在 Parallels 20.x 中不生效
- 优先使用命令行控制（prlctl exec, prlctl start/stop），避免 GUI 操作
