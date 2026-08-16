---
name: fish-shell
description: >-
  Fish shell 配置与排错技能。用于编写和修复 ~/.config/fish/config.fish、处理 omf
  reload 报错、将 bash/zsh 语法迁移为 fish 语法、PATH 去重与 conda/pnpm 等工具链初始化。
  当用户提到 fish、config.fish、omf、Oh My Fish、'case' builtin not inside of switch
  block、export 在 fish 中报错、从 bashrc 复制配置、fish PATH 重复等问题时，务必使用本技能——
  即使用户只说「shell 启动报错」且 config.fish 在错误栈里，也应触发。
agent_created: true
---

# Fish Shell 配置与排错

## Overview

Fish 与 bash/zsh **语法不兼容**。安装脚本（pnpm、nvm、conda 等）和从 `~/.bashrc` 复制的片段，直接粘贴进 `~/.config/fish/config.fish` 会导致启动失败。本技能基于真实排错经验：bash 的 `case ... in` / `export` 写入 fish 配置后，`omf reload` 报 `'case' builtin not inside of switch block`。

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
| `export PATH="$A:$PATH"` | `set -gx PATH $A $PATH` | fish 的 PATH 是**列表**，不是冒号字符串 |
| `case ":$PATH:" in *":$DIR:"*) ;; *) export PATH="$DIR:$PATH" ;; esac` | `if not contains $DIR $PATH; set -gx PATH $DIR $PATH; end` | PATH 去重用 `contains` |
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

## PATH 管理（fish 习惯）

PATH 在 fish 中是列表。追加路径时先去重，避免每次 source 重复 prepend：

```fish
set -gx PNPM_HOME "/path/to/pnpm"
if not contains $PNPM_HOME $PATH
    set -gx PATH $PNPM_HOME $PATH
end

if not contains /opt/nvim-linux64/bin $PATH
    set -gx PATH $PATH /opt/nvim-linux64/bin
end
```

注意：

- **不要**写成 `set -gx PATH "$PNPM_HOME:$PATH:/other"`——那是 bash 冒号拼接，在 fish 里会把整串当成一个 PATH 元素。
- 若前面有 `if not contains` 去重，后面又无条件 `set -gx PATH $PNPM_HOME $PATH`，去重会被覆盖；保留一种逻辑即可。

查看 PATH 是否包含某目录：

```fish
if contains $PNPM_HOME $PATH
    echo "pnpm in PATH: yes"
else
    echo "pnpm in PATH: no"
end
```

## 修复 workflow

1. **读报错行号**：错误栈会指向 `~/.config/fish/config.fish` 的具体行。
2. **识别 bash 片段**：搜索 `export`、`case`、`esac`、`[ ]`、`&&`、`||`、`:$PATH:`。
3. **逐段改写为 fish 语法**（参照上表）。
4. **验证**（按顺序执行）：

```bash
fish -c 'source ~/.config/fish/config.fish; echo source OK'
fish -c 'omf reload 2>&1; echo exit:$status'
```

5. **检查环境变量**（可选）：

```bash
fish -c 'source ~/.config/fish/config.fish; echo PNPM_HOME=$PNPM_HOME; if contains $PNPM_HOME $PATH; echo "pnpm in PATH: yes"; end'
```

## 真实案例：pnpm PATH 片段迁移

**错误写法（bash，来自 pnpm 安装提示）：**

```fish
export PNPM_HOME="/path/to/pnpm"
case ":$PATH:" in
 *":$PNPM_HOME:"*) ;;
 *) export PATH="$PNPM_HOME:$PATH" ;;
esac
export PATH="$PNPM_HOME:$PATH:/opt/nvim-linux64/bin"
```

**正确写法（fish）：**

```fish
set -gx PNPM_HOME "/path/to/pnpm"
if not contains $PNPM_HOME $PATH
    set -gx PATH $PNPM_HOME $PATH
end
if not contains /opt/nvim-linux64/bin $PATH
    set -gx PATH $PATH /opt/nvim-linux64/bin
end
```

## conda / 其他工具初始化

`conda init fish` 生成的块应保留在 `config.fish` 中，且使用 fish 语法（`if test -f ...`、`eval ... | source`）。**不要**手动把 `conda init bash` 的输出贴进 fish 配置。

若某工具只提供 bash 安装脚本：

- 查官方是否支持 `fish` / `conda init fish` / `*.fish` conf.d；
- 或把 bash 逻辑**手工翻译**为 fish，而非直接粘贴；
- 复杂初始化可放到 `~/.config/fish/conf.d/tool.fish` 单独维护。

## omf（Oh My Fish）

- 安装插件/主题后：`omf reload`
- reload 失败时，**优先查 config.fish 语法**，而非先怀疑 omf 本身
- 非交互式验证：`fish -c 'omf reload'` 应 exit 0 且无 stderr

## 代理操作时的注意点

- 编辑前**先读取** `~/.config/fish/config.fish` 全文，避免只改报错行而遗漏其他 bash 片段。
- 改动尽量小：只翻译有问题的小节，不动 conda 等已正确的 fish 块。
- 改完后**必须**用 `fish -c 'source ...'` 验证，不要假设语法正确。
- 用户若使用 x-cmd 等第三方 fish rc，保留其 `source` 行，只修复其后的错误片段。

## 快速诊断命令

```bash
# 语法检查：能否成功 source
fish -c 'source ~/.config/fish/config.fish'

# 找出 config.fish 里可疑的 bash 关键字
grep -nE '^\s*(export|case |esac|\[ )' ~/.config/fish/config.fish

# 查看 fish 版本
fish --version
```
