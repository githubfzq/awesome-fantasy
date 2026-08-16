---
name: keepass-lookup
description: >-
  从 Mac 本地的 KeePass(.kdbx) 密码库中提取某条目的用户名/密码，用于自动登录等场景。
  底层用 KeePassXC 自带的命令行工具 keepassxc-cli（位于
  /Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli）做解密与查询。
  当用户说"从 KeePass 取密码""登录需要用户名密码""查一下 xx 的凭据"
  "把 KeePass 里的 xxx 账号填进去"等时使用。常见场景：配合 tax-withholding-vm
  技能，从 KeePass 取出自然人电子税务局扣缴端的账号密码并填入 VM 登录界面。
agent_created: true
---

# KeePass 凭据提取（keepass-lookup）

## 何时用

- 需要某个系统/网站的账号密码，且凭据存在本机 KeePass 库（`.kdbx`）
- 自动登录（如把账号密码填进 VM 里的扣缴端登录框）
- 不想手写/明文保存密码，统一从密码库取

## 环境事实

- KeePassXC CLI：`/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli`
- **本技能不绑定任何具体密码库**：调用方必须显式用 `--db <路径>` 指定要打开的 `.kdbx`。具体用哪个库、主密码从哪来，由调用专家（如本机运维专家）在其记忆里决定。
- 主密码来源（优先级）：`--master` 参数 > 环境变量 `KEEPASS_MASTER` > `--master-file <文件>`（读文件首行）> 交互输入。**绝不写进日志/记忆**。

## 工作流

### 1) 提取凭据
```bash
cd /Users/fanzuquan/.workbuddy/skills/keepass-lookup/scripts

# 显式指定库 + 交互输入主密码（推荐，避免明文出现在参数/日志）
python3 kp_get.py --db /path/to/xxx.kdbx --search 自然人电子税务局

# 主密码来自文件（具体路径由调用专家的记忆决定，例如本机运维专家 local-machine-ops 记忆中指定的 Agent 库主密码文件；本技能不绑定具体路径）
python3 kp_get.py --db /path/to/agents.kdbx --master-file <主密码文件路径> --search 扣缴端

# 或环境变量主密码（脚本/自动化）
KEEPASS_MASTER='***' python3 kp_get.py --db /path/to.db --search xxx
```
输出 JSON：
```json
{"db":"/path/to/xxx.kdbx","entry":"/个税/自然人电子税务局（扣缴端）","username":"9135...","password":"****"}
```
> 多个匹配时脚本取第一个并在 stderr 打印候选列表，需要时人工指定 `--search` 更精确。

### 2) 把凭据用于登录（以扣缴端 VM 为例）
配合 `tax-withholding-vm` 技能：聚焦用户名框 → 键入 `username` → 聚焦密码框 → 键入 `password` → 回车/点登录。
```bash
# 取出凭据（交给编排层，勿落盘）
CRED=$(python3 kp_get.py --db /path/to/agents.kdbx --master-file <主密码文件路径> --search 自然人电子税务局)
USER=$(echo "$CRED" | python3 -c "import sys,json;print(json.load(sys.stdin)['username'])")
PASS=$(echo "$CRED" | python3 -c "import sys,json;print(json.load(sys.stdin)['password'])")
# 再用 tax-withholding-vm 的 computer_type 分别键入 $USER / $PASS
```

## 命令速查（keepassxc-cli 原生）

```bash
KX=/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli
echo "主密码" | "$KX" ls <db>                      # 列条目
echo "主密码" | "$KX" search <db> <词>             # 搜条目
echo "主密码" | "$KX" show -s -a UserName -a Password <db> <条目路径>   # 取明文凭据
echo "主密码" | "$KX" clip <db> <条目> [超时秒]     # 仅复制密码到剪贴板（不打屏）
```
- `-s/--show-protected` 显示受保护字段明文；`-a/--attributes` 可重复指定要取的字段（Title/UserName/Password/URL/Notes 及自定义）。
- `-k <keyfile>` 支持密钥文件；`-y <slot>` 支持 YubiKey。

## 安全要点（务必遵守）

- 主密码只在运行时提供，**不写入** 任何记忆文件、日志、commit。
- 凭据 JSON 仅在编排层内存中使用；不要 `echo` 到屏幕或落地到文件。
- 优先用 `clip` 把密码直接送剪贴板，而非打印明文（高敏感场景）。
- `.kdbx` 文件本身受主密码保护；脚本只读不写，不会修改你的密码库。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `凭据无效 / HMAC 不匹配` | 主密码错 | 重新提供正确主密码 |
| `未找到 ~/Documents/密码*.kdbx` | 库不在默认位置 | `--db` 指定绝对路径 |
| 匹配到多个条目 | 搜索词太宽 | 用更精确的 `--search`，或先在库里确认条目全路径 |
| 取到的 username/password 为空 | 该条目无对应字段 | `show --all <db> <entry>` 看全部字段名 |
