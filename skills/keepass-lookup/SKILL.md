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
{"db":"...","entry":"/自然人电子税务局扣缴端","username":"9135...","password":"****",
 "fields":{"Title":"...","UserName":"...","Password":"...","URL":"...","Notes":"..."},
 "attrs":{}}
```
> 多个匹配时脚本取第一个（自动跳过 `/回收站/` 条目）并在 stderr 打印候选列表，需要时人工指定 `--search` 更精确。

### 1.1) 取受保护自定义属性（如「API key」）

```bash
python3 kp_get.py --db /path/to/agents.kdbx --master-file <主密码文件路径> \
  --search deepseek --attr "API key"
# -> JSON 里 attrs: {"API key": "sk-..."}
```
`--attr` 可重复；脚本先在全量结果里找，找不到自动降级为 `-a <名>` 单取（见下方坑 #3）。

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
cat <主密码文件> | "$KX" ls <db>                   # 列条目
cat <主密码文件> | "$KX" search <db> <词>          # 搜条目
cat <主密码文件> | "$KX" show -s <db> <条目路径>    # 全量明文（带"字段名: 值"）
cat <主密码文件> | "$KX" show -s -a "API key" <db> <条目> 2>/dev/null   # 单取值（仅一行）
cat <主密码文件> | "$KX" clip <db> <条目> [超时秒]  # 仅复制密码到剪贴板（不打屏）
```
- `-s/--show-protected` 显示受保护字段明文；`-a/--attributes` 可重复指定要取的字段（Title/UserName/Password/URL/Notes 及自定义）。
- `-k <keyfile>` 支持密钥文件；`-y <slot>` 支持 YubiKey。

## keepassxc-cli 输出格式与坑（2026-10-11 实测 · 必读）

**两种输出形态，别混用：**

| 调用 | 输出形态 | 用途 |
|---|---|---|
| `show -s <db> <entry>`（全量，不加 `-a`） | 每行 `字段名: 值`（Title/UserName/Password/URL/Notes/Uuid/Tags + 非受保护自定义属性） | ✅ 首选：按行首字段名解析，字段缺失也不会错位 |
| `show -s -a X -a Y <db> <entry>`（多 `-a`） | **只有值，一行一个，不带字段名** | ⚠️ 靠顺序取值，极易错位 |
| `show -s -a X <db> <entry>`（单 `-a`） | 只有值一行 | ✅ 取受保护自定义属性唯一办法 |

坑清单：

1. **多 `-a` 不带字段名**：`show -s -a UserName -a Password` 输出就是两行纯值，无法判断哪行是哪个字段；**某个字段为空时整行不输出，后面全部前移错位**。→ 要多个字段就用全量 `show -s` + 行首正则（kp_get.py 已这么干）。
2. **受保护自定义属性不在全量输出里**：实测 deepseek 条目全量 `show -s` 只列出 deepseek-v4-flash/pro/chat/reasoner 等普通自定义属性，**「API key」（受保护）不出现**，只能用 `-a "API key"` 单取。→ 先试全量，取不到再 `-a` 单取（kp_get.py `--attr` 已自动降级）。
3. **解锁提示行在 stderr**：`输入密码以解锁 xxx.kdbx：` 走 stderr 而非 stdout，因此**命令尾巴加 `2>/dev/null` 即可得到干净 stdout**；不必靠 `tail -1` 猜（那在多行 Notes 时会截错）。
4. **不加 `-s` 时全量输出 Password 显示 `PROTECTED`**（拿不到明文）；指定 `-a` 时反而会输出明文——别依赖这个不一致行为，统一加 `-s`。
5. **`search` 会连 `/回收站/` 里的同名条目一起返回**（如搜"贵州"命中 `/贵州电子税务局网站` 与 `/回收站/贵州电子税务局（企业电子税务网站）`）。→ 搜索词尽量精确；kp_get.py 已自动过滤 `/回收站` 前缀条目，多命中时在 stderr 打印候选。
6. **字段名不存在会报错**：`错误：未知属性 NoSuchField。`（退出码非 0），解析脚本要判 rc。
7. **主密码错 / 误加密钥文件** → `读取数据库时出错：输入的凭据无效…（HMAC 不匹配）`。库仅用主密码保护时**绝不能传 `-k`**，也不要自动探测同目录 key file。
8. **路径含空格**（如坚果云同步目录）必须整段加引号；主密码经 stdin 管道传入（`cat <主密码文件> | ...`），不要出现在命令行/历史里。
9. **主密码文件读首行**：`open(...).read().strip()`，文件末尾换行不要算进密码。
10. 库放在坚果云同步目录时，确保同步完成再读（读到旧版会 HMAC 失败）。

## 安全要点（务必遵守）

- 主密码只在运行时提供，**不写入** 任何记忆文件、日志、commit。
- 凭据 JSON 仅在编排层内存中使用；不要 `echo` 到屏幕或落地到文件。
- 优先用 `clip` 把密码直接送剪贴板，而非打印明文（高敏感场景）。
- `.kdbx` 文件本身受主密码保护；脚本只读不写，不会修改你的密码库。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `凭据无效 / HMAC 不匹配` | 主密码错；或库仅用主密码却传了 `-k` | 换正确主密码；去掉 `--key-file` |
| `未找到 ~/Documents/密码*.kdbx` | 库不在默认位置 | `--db` 指定绝对路径 |
| 匹配到多个条目（含 `/回收站/…`） | 搜索词太宽 | 用更精确的 `--search`（脚本已自动跳过回收站条目） |
| 取到的 username/password 为空 | 该条目无对应字段 | `show -s <db> <entry>` 看全部字段名 |
| 取自定义属性（如 API key）为空 | 它是受保护属性，全量输出里没有 | `--attr "API key"`（脚本自动降级为 `-a` 单取） |
| 值串到了别的字段 | 用了多 `-a`（空字段导致错位） | 改全量 `show -s` + 行首字段名解析 |
| stdout 混进「输入密码以解锁…」 | 提示行在 stderr | 命令加 `2>/dev/null` |
| 明文拿到 `PROTECTED` | 全量模式没加 `-s` | 加 `-s` |

## 边界（保持本技能独立）

本技能**只负责取凭据**：不关心取到的密码往哪填、不做任何业务（税务/余额/登录）动作。
调用方技能各自记录"取哪个条目、用哪个字段"（如 `guizhou-tax-quarterly` 取「贵州电子税务局网站」
的 UserName+Notes 身份证、`withholding-login` 取「自然人电子税务局扣缴端」的 Password、
`deepseek-usage-check` 取 deepseek 的「API key」），彼此不共享脚本、不互相依赖。
