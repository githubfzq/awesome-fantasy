---
name: herdr-nvim
description: >-
  herdr-nvim 插件（herdr 的 nvim 侧栏）安装、配置与排错技能。用于 prefix+e /
  prefix+o 快捷键按下无反应、herdr plugin install 后侧栏不打开、bin/herdr-nvim
  报 version `GLIBC_2.39` not found、插件预编译二进制与本机 glibc 不兼容需 cargo
  源码重编、cargo 构建时 ustc 镜像 404、配置 nvim_bin = "lvim" 后侧栏行为异常、
  herdr-nvim doctor 检查结果解读等场景。当用户提到 herdr-nvim、herdr 插件、
  nvim sidebar、快捷键没反应而 herdr config check 通过时，务必使用本技能——
  即使用户只说「herdr 按键失效」也应触发。
agent_created: true
---

# herdr-nvim 插件安装与排错

## Overview

herdr-nvim（ChmaraX/herdr-nvim）是 herdr 的插件，提供 `prefix+e` 一键开合的全高 nvim 侧栏和 `prefix+o` 文件 picker。它由两半组成：herdr 侧插件（Rust 二进制 `bin/herdr-nvim`，负责 toggle/分屏/daemon）和 nvim 侧 lua（标注与发送）。

**头号故障模式：预编译二进制与本机 glibc 不兼容。** `install.sh` 只要预编译下载成功就直接采用，**不做兼容性检查**；按下快捷键时 action 进程立刻因 GLIBC 报错退出——现象是「配置全对、按键毫无反应、日志无报错」。排查时先怀疑二进制本身，再查配置。

## 组件地图

| 文件 | 作用 |
|------|------|
| `~/.config/herdr/config.toml` | 按键绑定：`[[keys.command]]`，`type = "plugin_action"`，`command = "chmarax.herdr-nvim.<action-id>"` |
| `~/.config/herdr/plugins.json` | 插件注册表（安装是否成功、enabled、action 清单） |
| `~/.config/herdr/plugins/github/chmarax.herdr-nvim-<hash>/` | 插件本体：`herdr-plugin.toml`（manifest）、`herdr/run.sh`（入口）、`bin/herdr-nvim`（Rust 二进制） |
| `~/.config/herdr-nvim/config.toml` | 插件自身配置（注意：**不是** herdr 的 config）：`[sidebar] nvim_bin`（默认 `"nvim"`）、`nvim_env`、`position` |
| `~/.config/herdr/herdr-server.log` | herdr 服务端日志（本故障通常**无**相关记录） |

## 诊断 workflow（按序执行）

1. **`herdr config check`** —— 期望输出 `config: ok`。通过则按键语法与插件注册无问题，排除配置层。
2. **直接运行插件二进制**（完成判据：看到真实输出而非动态链接报错）：

   ```bash
   "$HOME/.config/herdr/plugins/github/"chmarax.herdr-nvim-*/bin/herdr-nvim 2>&1 | head -2
   ```

   看到 `version 'GLIBC_2.39' not found (required by ...)` 即为本故障：预编译二进制要求更新版的 glibc。对照 `ldd --version` 确认本机版本。
3. **`herdr-nvim doctor`** —— 官方自检，在 scratch workspace 里跑全链路（分屏/toggle 往返/daemon/remote-ui）并自动清理：

   ```bash
   HERDR_PLUGIN_ROOT=<插件根目录> <插件根目录>/bin/herdr-nvim doctor
   # 可选对照：HERDR_NVIM_CONFIG=/tmp/xx.toml 覆写插件配置
   ```

   各项含义：`D-F7 toggle-roundtrip`（真实按键链路）、`D-F18 daemon-healthy`（`nvim_bin` 能否拉起 daemon）、`D-F19 remote-ui-attach`（画面能否渲染）。

## 修复：源码重编替换二进制

预编译不可用时，用本机 cargo 重编并把产物放回 `bin/herdr-nvim`（与 install.sh 的 fallback 产物位置一致）：

```bash
rsync -a --exclude .git --exclude target <插件根目录>/ /tmp/opencode/herdr-nvim-src/
cd /tmp/opencode/herdr-nvim-src
CARGO_HOME=/tmp/opencode/cargo-home cargo build --release
cp target/release/herdr-nvim <插件根目录>/bin/herdr-nvim
```

本地编译链接本机 glibc，天然兼容。**必须**重跑 doctor 验证后再交给用户按键测试。

### 构建陷阱（本项目机器实测）

1. **`/home/data` 下的 cargo 配置会压住 `CARGO_HOME`**：cargo 从 cwd 逐级向上找 `.cargo/config`，项目在 `/home/data` 下必然命中 `/home/data/.cargo/config`，其 `[source]` 替换优先生效。因此**在 `/tmp` 下构建**，不要在插件目录里直接 build，也不要指望 env 覆写（`CARGO_SOURCE_USTC_REGISTRY` 实测不生效）。
2. **全局 `~/.cargo/config` 的 ustc git index 已 404**（中科大已改 sparse 协议）：`registry="https://mirrors.ustc.edu.cn/crates.io-index/"` 会导致 `Updating 'ustc' index` 后 404 失败。临时 `CARGO_HOME` 里写 sparse 形式即可：

   ```toml
   [source.crates-io]
   replace-with = "ustc"

   [source.ustc]
   registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
   ```

   该文件属于用户全局配置，**只诊断、不代改**，除非用户明确要求。

## LunarVim（nvim_bin = "lvim"）注意事项

`nvim_bin = "lvim"` 是官方支持写法，LunarVim 满足 nvim ≥ 0.10 要求，**真实单侧栏流程可用**。但有两个已实测的坑：

- **headless 参数污染**：LunarVim 以 headless 启动时（`lvim/config/settings.lua` 的 `load_headless_options`）设置 `cmdheight=9999`、`columns=9999`（为 CI 场景设计）。第一个 client 以正常尺寸 attach 后这些值被钳制残留，**第二个 client attach 时画面可能冻结**——doctor 的 `D-F19` 对 lvim 报 FAIL 多为此假阳性（doctor 的 daemon 此前已被 toggle 用过一个 client）。真实使用（per-tab 全新 daemon、侧栏即第一个 client）不受影响。
- **首次启动约 5 秒**：含 LunarVim 全量插件加载，属正常，勿误判为失败。
- 对照实验用 `HERDR_NVIM_CONFIG=<path>` 覆写插件配置（如临时换 `nvim_bin = "nvim"`），可干净地区分「lvim 特有」与「链路通用」问题。
- 复现/验证时客户端 pane 要放**满宽新 tab**；连续 `--direction right` 的窄 split 会让 remote-ui 渲染冻结，制造假阴性。

## 快速诊断命令

```bash
# 配置层
herdr config check

# 二进制层（头号嫌疑）
ldd --version | head -1
"$HOME/.config/herdr/plugins/github/"chmarax.herdr-nvim-*/bin/herdr-nvim 2>&1 | head -2

# 全链路
HERDR_PLUGIN_ROOT=$(dirname "$HOME/.config/herdr/plugins/github/"chmarax.herdr-nvim-*/herdr-plugin.toml) \
  "$HOME/.config/herdr/plugins/github/"chmarax.herdr-nvim-*/bin/herdr-nvim doctor

# lvim 可用性（作为 nvim_bin）
lvim --headless +qa && echo lvim-ok
```

## 长期注意

- **会复发**：`herdr plugin update` 或重装会重新下载 GLIBC_2.39 预编译二进制并覆盖 `bin/herdr-nvim`，需按上文重新本地编译。
- 修复后让用户在 herdr UI 里按 `prefix+e` 做最终确认；代理侧只以 doctor 与手工 sentinel 渲染为验证依据。
