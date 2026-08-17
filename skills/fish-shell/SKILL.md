---
name: fish-shell
description: >-
  Fish shell 配置与排错技能。用于编写和修复 ~/.config/fish/config.fish、处理 omf
  reload 报错、将 bash/zsh 语法迁移为 fish 语法、用 fish_add_path 管理 PATH、
  排查 pnpm ls -g / x-cmd 因 PATH 顺序或列表语义出错等问题。当用户提到 fish、
  config.fish、omf、Oh My Fish、fish_add_path、'case' builtin not inside of switch
  block、export 在 fish 中报错、echo $PATH 没有冒号、pnpm global bin not in PATH、
  从 bashrc 复制配置时，务必使用本技能——即使用户只说「shell 启动报错」或
  「PATH 看起来不对」且涉及 fish，也应触发。
agent_created: true
---

# Fish Shell 配置与排错

## Overview

Fish 与 bash/zsh **语法不兼容**。安装脚本（pnpm、nvm、conda 等）和从 `~/.bashrc` 复制的片段，直接粘贴进 `~/.config/fish/config.fish` 会导致启动失败或 PATH 语义错误。

本技能覆盖两类真实故障：

1. bash 的 `case ... in` / `export` 写入 fish → `omf reload` 报 `'case' builtin not inside of switch block`
2. PATH 用 bash 冒号拼接、或错误 prepend `PNPM_HOME` → `pnpm ls -g` 报 global bin not in PATH；`echo $PATH` 看起来「没有冒号」其实是 fish 列表显示

## 配置文件位置

| 文件 | 用途 |
|------|------|
| `~/.config/fish/config.fish` | 主配置，fish 启动与 `omf reload` 都会 source |
| `~/.config/fish/conf.d/*.fish` | 按文件名排序自动加载，适合拆分工具初始化 |
| `~/.config/fish/functions/*.fish` | 自定义函数 |

Oh My Fish（omf）主题/插件变更后执行 `omf reload`，会重新加载 `config.fish`——配置里有 bash 语法会在此暴露。

## 核心原则：不要混用 bash 语法

Fish 没有 `export`、`case ... in ... esac`、`:$PATH:` 子串匹配。常见安装脚本输出的是 bash 片段，**必须改写**后再写入 fish 配置。

### 对照表（高频）

| bash/zsh | fish | 说明 |
|----------|------|------|
| `export VAR=value` | `set -gx VAR value` | `-g` 全局，`-x` 导出到子进程 |
| `export PATH="$A:$PATH"` | `fish_add_path --path $A`（或 append） | **优先**用内置函数，勿手写冒号拼接 |
| `case ":$PATH:" in *":$DIR:"*) ;; *) export PATH="$DIR:$PATH" ;; esac` | `fish_add_path --path $DIR` | 去重与存在性检查内置 |
| `source file` | `source file` 或 `. file` | 相同 |
| `[ -f file ]` | `test -f file` | fish 推荐 `test` |
| `&&` / `\|\|` | `and` / `or` | fish 用关键字 |
| `$HOME` | `$HOME` 或 `~` | 相同 |

### 典型错误与含义

```
'case' builtin not inside of switch block
```

原因：单独写了 bash 风格的 `case ":$PATH:" in`，而 fish 的 `case` 只能出现在 `switch` 块内：

```fish
switch $variable
    case pattern1
        ...
    case pattern2
        ...
end
```

这与 bash 的 `case ... in` 完全不是同一套语法。

## PATH 管理：优先用 `fish_add_path`

PATH 在 fish 中是**列表**，不是冒号字符串。往 PATH 加目录时，优先用内置 `fish_add_path`，不要手写 `if not contains` + `set -gx PATH`，更不要写自定义 dedupe 函数。

### 为什么用 `fish_add_path`

| 能力 | 手写 `set -gx PATH` | `fish_add_path` |
|------|---------------------|-----------------|
| 去重 | 需自己写 | 内置 |
| 路径规范化 | 无 | `realpath` |
| 目录不存在时跳过 | 无 | 自动跳过 |
| 列表语义 | 容易写错 | 正确处理 |

### 推荐写法

```fish
set -gx PNPM_HOME "/path/to/pnpm"
# 追加勿 prepend：见下方 pnpm 陷阱
fish_add_path --append --global --path $PNPM_HOME
fish_add_path --append --global --path /opt/nvim-linux64/bin
```

常用参数：

| 参数 | 含义 |
|------|------|
| `--path` | 直接改 `$PATH`（适合 `config.fish`） |
| `--global` | global 作用域（配合 `--path`） |
| `--append` | 追加到末尾 |
| （默认） | 写入 universal `fish_user_paths` 并 **prepend** |

不加 `--path` 时默认写 `fish_user_paths`（universal），适合交互会话里一次性执行；在 `config.fish` 里建议显式 `--global --path`，行为更清晰。

### 禁止 / 易错写法

```fish
# ❌ bash 冒号拼接：在 fish 里可能把整串当成异常 PATH 语义
set -gx PATH "$PNPM_HOME:$PATH:/other"

# ❌ 手写 dedupe 用 echo $out 做命令替换：多元素会被压成「一个」空格串，毁掉 PATH
set -gx PATH (__my_dedupe $PATH)

# ❌ 无条件 prepend PNPM_HOME：可能遮蔽 ~/.npm/bin/pnpm
set -gx PATH $PNPM_HOME $PATH
```

### `echo $PATH`「没有冒号」是正常现象

- fish 里 `echo $PATH` 用**空格**分隔列表元素，不是 bug
- 传给 `pnpm` / `bash` / `node` 等子进程时，fish **自动用 `:` 拼接**
- 要看冒号形式：`string join : $PATH`
- 要看元素个数：`count $PATH`；详细：`set -S PATH`

## 真实案例 A：pnpm bash 片段 → fish（语法迁移）

**错误写法（bash，来自 `pnpm setup`）：**

```fish
export PNPM_HOME="/path/to/pnpm"
case ":$PATH:" in
 *":$PNPM_HOME:"*) ;;
 *) export PATH="$PNPM_HOME:$PATH" ;;
esac
```

**正确写法（fish）：**

```fish
set -gx PNPM_HOME "/path/to/pnpm"
fish_add_path --append --global --path $PNPM_HOME
```

## 真实案例 B：`pnpm ls -g` 报 global bin not in PATH

**现象：**

```
[ERROR] The configured global bin directory ".../pnpm/bin" is not in PATH
Run "pnpm setup" to update your shell configuration.
```

或用户发现 `which pnpm` 指向 `$PNPM_HOME/pnpm`，而不是 `~/.npm/bin/pnpm`。

**根因（实战）：**

1. `PNPM_HOME`（含全局 bin 与一份 `pnpm` 可执行文件）被 **prepend** 到 PATH 最前
2. `command -v pnpm` 解析到 `$PNPM_HOME/pnpm`，而不是更靠后的 `~/.npm/bin/pnpm`
3. 该路径下的 pnpm 对 global bin 目录的校验与 PATH 不一致时抛错

**修复：** 对 `PNPM_HOME` 使用 **`--append`**，让 `~/.npm/bin`（或 nvm 的 pnpm）优先：

```fish
fish_add_path --append --global --path $PNPM_HOME
```

bash 侧若也有同样问题，对应改为：

```bash
export PATH="$PATH:$PNPM_HOME"   # append，不是 $PNPM_HOME:$PATH
```

验证：

```fish
command -v pnpm   # 期望 ~/.npm/bin/pnpm（或你真正安装的那份）
pnpm ls -g
```

## 修复 workflow

1. **读报错行号**：错误栈会指向 `~/.config/fish/config.fish` 的具体行。
2. **识别 bash 片段**：搜索 `export`、`case`、`esac`、`[ ]`、`&&`、`||`、`:$PATH:`。
3. **PATH 改用 `fish_add_path`**；注意 pnpm 等场景要 `--append`。
4. **验证**（按顺序执行）：

```bash
fish -c 'source ~/.config/fish/config.fish; echo source OK'
fish -c 'omf reload 2>&1; echo exit:$status'
fish -c 'command -v pnpm; pnpm ls -g; type -q x; and x 2>&1 | head -3'
```

5. **检查 PATH 语义**（可选）：

```fish
count $PATH
string join : $PATH
contains -- $PNPM_HOME $PATH; and echo "PNPM_HOME in PATH"
```

## conda / x-cmd / 其他工具初始化

- `conda init fish` 生成的块应保留，且使用 fish 语法。**不要**把 `conda init bash` 贴进 fish。
- x-cmd：保留 `source "$HOME/.x-cmd.root/local/data/fish/rc.fish"`；PATH 被毁掉时（例如错误 dedupe），x-cmd 内部 `cat`/`which` 会连锁失败。
- 若某工具只提供 bash 安装脚本：查官方 fish 支持，或手工翻译；复杂逻辑放到 `~/.config/fish/conf.d/tool.fish`。

## omf（Oh My Fish）

- 安装插件/主题后：`omf reload`
- reload 失败时，**优先查 config.fish 语法**，而非先怀疑 omf 本身
- 非交互式验证：`fish -c 'omf reload'` 应 exit 0 且无 stderr

## 代理操作时的注意点

- 编辑前**先读取** `~/.config/fish/config.fish` 全文，避免只改报错行而遗漏其他 bash 片段或重复的 source 块。
- 改动尽量小：只翻译有问题的小节，不动 conda 等已正确的 fish 块。
- PATH 一律优先 `fish_add_path`；不要引入自定义 PATH dedupe 辅助函数。
- 改完后**必须**用 `fish -c 'source ...'` 验证，并确认 `command -v pnpm` / `x`（若用户用 x-cmd）仍可用。
- 用户若使用 x-cmd，保留其 `source` 行，只修复其后的错误片段。

## 快速诊断命令

```bash
# 语法检查：能否成功 source
fish -c 'source ~/.config/fish/config.fish'

# 找出 config.fish 里可疑的 bash 关键字
grep -nE '^\s*(export|case |esac|\[ )' ~/.config/fish/config.fish

# PATH 列表是否健康
fish -c 'echo count:(count $PATH); string join : $PATH | head -c 200; echo; command -v pnpm'

# 查看 fish 版本
fish --version
```
