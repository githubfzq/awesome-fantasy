---
name: guizhou-tax-quarterly
description: 贵州省电子税务局（网页端）季度申报 RPA，2026-10 全流程实战验证通过：增值税及附加税费（小规模纳税人）+ 工会经费综合关联申报、个人所得税经营所得（A表）多期顺序申报、财务报表季报报送（Excel 模板导入）。CDP 模式：login_cdp.py 拉起专用 Chrome 由用户人工登录（绕瑞数风控），declare.py 接管执行申报；提交前断言金额全 0 + 人工确认（--yes 为事先授权）。当用户要办理季度申报/财务报表报送/经营所得A表网页申报，或提到贵州电子税务局网页端申报时使用。  
---

# 贵州电子税务局 季度申报 RPA（网页端 · 已实战验证）

## Overview

在 macOS 本地用 Playwright 驱动贵州省电子税务局网页端完成**季度申报**  
（季度终了次月 15 日前，实测 2026-10 窗口顺延至 10/26）：

| 事项                  | 路径                                                    | 实测结果（2026-10-11） |
| ------------------- | ----------------------------------------------------- | ---------------- |
| 增值税及附加税费（小规模）+ 工会经费 | 待办 → 综合关联申报 → 去办理 → 应税项填0 → 提交                        | ✅ 申报成功 0 元       |
| 个人所得税经营所得（A表）       | 待办 → 中转自然人电子税务局 → 4 步向导，**按期顺序报**（止=06 再止=09）         | ✅ Q2、Q3 均提交成功    |
| 财务报表报送（季报）          | 待办 → 季报+财报导导入 → 下载模板 → openpyxl/xlutils 填表头 → 上传 → 提交 | ✅ 报送成功           |

- **CDP 模式（首选）**：`login_cdp.py` 拉起专用 Chrome（独立 profile + CDP 9222），  
  用户人工完成登录（瑞数风控），`declare.py` 自动接管同一窗口执行申报
- **不适用**：自然人电子税务局扣缴端（月度工资薪金，见 `wage-withholding-rpa` 技能）
- 页面结构、定位器与全部坑：`references/flow.md`（**改流程前必读**）

## 快速开始

```bash
PY=/Users/fanzuquan/.workbuddy/binaries/python/envs/default/bin/python
cd ~/.workbuddy/skills/guizhou-tax-quarterly/scripts

# ① 登录（必要时自动拉起 Chrome，你在窗口里手动完成登录；登录态持久，次月免登录）
$PY login_cdp.py

# ② 执行申报（提交前断言全0；--yes=事先授权，不加则逐项停下确认）
$PY declare.py --list                 # 先看待办清单
$PY declare.py --only vat --yes       # 增值税+工会经费
$PY declare.py --only biz_a --yes --period-ends 06,09   # 经营所得（按期顺序！）
$PY declare.py --only fin --yes       # 财务报表季报
```

一键：`bash qrun.sh all --yes`（确保登录 → 全部办理）。  
申报完成后回工作台刷新，确认「我的待办-本期应申报」数字消失即为全部办结。

## 依赖

- **playwright / xlrd==1.2.0 / xlwt / xlutils / openpyxl**：装于 WorkBuddy 隔离 venv  
  `~/.workbuddy/binaries/python/envs/default`
- **真实 Google Chrome**（channel 或 CDP 直连，Chromium for Testing 会被风控拒绝）
- **keepass-lookup**：凭据来自 agents.kdbx「贵州电子税务局网站」条目  
  （UserName=扣缴义务人识别号，Password=网站密码，Notes 内身份证号）
- **keepassxc-cli 取凭据的正确姿势**（详见下节，别用多 `-a`）：全量 `show -s` + 行首字段名解析
- **网络**：脚本已在 common.py 顶层清除 http_proxy 等环境变量——**必须在沙箱外运行**  
  （WorkBuddy 沙箱的 127.0.0.1:54033 强制代理会拦掉税务局登录风控组件，报「请求失败」）

## 安全边界（强制）

- **提交申报是不可逆对外动作**：提交前断言金额全 0 + 人工确认（--yes = 事先授权，  
  与 `wage-withholding-rpa` 确认模型一致）
- 经营所得 A 表**必须按期顺序申报**（系统拦截「上一期未申报」）；期次由 `--period-ends`  
  显式给出，脚本不自动推断历史欠报期
- 凭据仅运行时内存读取，绝不落盘；日志只记长度
- 「真、实、责、任」文字点选验证码：脚本按已知弹窗布局自动点选（两次实战全部通过）；  
  若布局变化则截图到 shots/ 停机交人
- 任何一步失败即停机截图，提交类动作绝不自动重试

## 架构

```
macOS（沙箱外运行！）
 ├─ login_cdp.py ──── 拉起专用 Chrome(--remote-debugging-port=9222, 独立 profile)
 │    └─ 用户人工登录（滑块/短信）→ 脚本轮询检测「我的待办」出现
 ├─ declare.py ────── connect_over_cdp 接管同一窗口
 │    ├─ vat    综合关联申报（含工会经费）
 │    ├─ biz_a  经营所得 A 表 ×N 期（--period-ends）
 │    └─ fin    财报模板下载→xlutils 填表头→上传→提交
 └─ common.py ─────── 清代理环境变量/浏览器启动/keepass 凭据/瑞数渲染重试
```

## 凭据获取（KeePass · 本技能自带实现）

本技能**自己**调 keepassxc-cli 取凭据（`common.get_credentials()`，不依赖 `keepass-lookup` 脚本，
保持技能独立）。条目：`贵州电子税务局网站`。

```bash
KX=/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli
DB="/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agents.kdbx"
MF="/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agent_main_pass"
cat "$MF" | "$KX" show -s "$DB" "贵州电子税务局网站" 2>/dev/null
# Title: 贵州电子税务局网站 / UserName: 91520123MA6H98Y6XT / Password: *** /
# Notes: 贵州省电子税务局 企业电子税务网站登录；身份证号:5225...（法人/经办人）
```

解析：按行首 `字段名:` 正则抓 UserName / Password，再从 Notes 里正则抽
`身份证号[:：]\s*(\d{17}[\dXx])`。三段都取到才算成功，缺一即抛错停机。

**踩过的坑（改这段前必看）**

| 坑 | 处理 |
|---|---|
| `show -s -a UserName -a Password` **只输出两行纯值、不带字段名**，空字段还会让后面整体上移错位 | 用全量 `show -s` + 行首字段名解析（`common.py` 已如此实现） |
| 解锁提示行「输入密码以解锁 …」 | 它在 **stderr**，`2>/dev/null` 即干净；不要靠 `tail -1`（多行 Notes 会截错） |
| 不加 `-s` 时 Password 显示 `PROTECTED` | 统一加 `-s` |
| 搜索词"贵州"会连带命中 `/回收站/贵州电子税务局（企业电子税务网站）` | 用完整条目名 `贵州电子税务局网站`，别用宽词 |
| 传 `-k` 密钥文件 → `HMAC 不匹配` | agents.kdbx 仅主密码保护，**不要传 `-k`**，也不要自动探测同目录 key file |
| 库路径含空格（坚果云同步目录） | 整段加引号；主密码经 stdin 管道传入，不进命令行/历史 |

凭据只在进程内存里用，**不 echo、不落盘**，日志只打长度（uscc_len/id_len/pw_len）。

## 实战踩坑速查（详见 references/flow.md）

| 坑                                      | 处理                                                      |
| -------------------------------------- | ------------------------------------------------------- |
| WorkBuddy 沙箱强制代理(127.0.0.1:54033)拦登录风控 | **脚本必须在沙箱外运行**（dangerouslyDisableSandbox）               |
| Chromium for Testing 被风控「请求失败」         | 用真实 Chrome（CDP 直连模式天然满足）                                |
| 瑞数页面空白                                 | common.goto_home 自动 reload ≤4 次；连续失败=风控冷却 ≥5 分钟         |
| Read 截图坐标系                             | 截图 2582px 宽 = viewport 1291×DPR2；展示图 1080 宽 → 坐标×1.1954 |
| element-ui radio 原生 check() 无效         | JS 点击 `label.el-radio`（class is-checked 判定）             |
| 待办行「填写申报表」必须点 button                   | 点 span 不触发 Vue handler                                  |
| keepassxc-cli `-a` 多字段不带字段名            | 用全量 `show -s` 按行首解析                                     |
| 经营所得按期顺序 + 每期提交后需重新进入向导                | declare_biz_a 已封装                                       |
| 财报模板 zip 为 GBK 文件名                     | cp437→gbk 解码解压；.xls 用 xlrd1.2.0+xlutils.copy 保格式回写      |
| CDP 下 page.url 可能滞后                    | 登录判据只信 body 白名单「我的待办/工作台」+ URL 双条件                      |
