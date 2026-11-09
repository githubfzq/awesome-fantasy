---
name: oss-agent-tool-eval
description: 调研并本地试跑开源 agent/自动化工具时使用：调研→环境扫描→读代码挖配置→选模型后端→最小验证。
---

# 开源 Agent 工具调研与本地试跑（oss-agent-tool-eval）

规范"调研 GitHub 上某开源工具并在我机器上试一下"这类任务的完整流程。适用对象：AI agent 框架、设备自动化工具（ARTEMIS/MobileAgent 类）、测试框架等。核心原则：**先做足本地功课再问用户**——环境扫描、凭据排查、网关探测全做完，最后只把"需要用户拍板的真决策"递上去。

## 一、调研阶段（15 分钟内出结论）

1. `web_extract` 抓 README（GitHub 页面大，会 head+tail 截断并缓存全文到 `~/.hermes/cache/web/`，用 read_file 翻中间段）。重点提取：license、语言/运行时版本要求、平台支持、benchmark 声明（99%+ 之类都注明来源基准）、装了什么（有无往设备装 helper/daemon）。
2. `web_search` 交叉验证：发布日期、社区实测口碑、已知坑。
3. 给用户先交一份"是什么/亮点/本机可行性"摘要，再继续动手。

## 二、本机可行性扫描（问用户之前先做）

按序检查并记录结果，一次批量跑完：

1. **工具链**：`which <deps...>`（如 adb/scrcpy/ffmpeg/uv/git）+ 版本。
2. **运行时**：项目 pyproject/package.json 的版本要求 vs 本机（注意 PEP 668 环境，一律用 uv）。
3. **凭据排查**（决定能不能跑、走哪条路）：
   - `env | grep -i <KEY_NAMES>`；
   - shell 配置文件 grep（**注释掉的 export = 没有 key**，别当有）；
   - `security find-generic-password -s <svc> -w` 试 keychain；
   - 应用配置目录（`~/.gemini/oauth_creds.json` 等，只看结构不看值）。
4. **本地网关替代**：有 Magpie 类网关时（见技能 local-llm-gateway-config），curl 探测项目需要的模型 id 是否真可用——列出 ≠ 可用，必须实发一条消息验证。

## 三、克隆与装依赖

```bash
export https_proxy=http://127.0.0.1:7899   # git clone 外网必带
git clone --depth 1 https://github.com/<org>/<repo>.git ~/Public/Projects/<repo>
cd ~/Public/Projects/<repo> && uv sync
```

## 四、配置考古（读代码，别猜）

1. `cp .env.example .env` 起步；grep 源码里的 `ENV_*` 常量定义文件，拿到全部环境变量清单——.env.example 往往不全。
2. **读 provider 路由代码**（通常 `llm/router.py` 或等价物）：确认每个 provider 读哪个 env key、有没有 `base_url`/`api_base` 覆盖、fallback 行为、特殊节点是否强制特定厂商（如 ARTEMIS 的 object_detector 强制 Gemini ER 模型做坐标定位——这直接决定"网关平替"会损失什么能力）。
3. **配置文件解析顺序**：grep `get_config_path` 类函数，确认 env 覆盖 → 项目 config/ 目录 → 项目根 → 用户目录 → 内置模板的优先级，改对位置的文件。
4. 注意 `.env` 里影响个人设备的开关（如 ARTEMIS_HELPER_AUTO_INSTALL=false 可禁止往手机自动装 APK）。

## 五、模型后端决策（递给用户的真决策点）

只有做完第二、四节功课才配谈。给出对比表：

- **方案 A（原生厂商 key）**：功能全覆盖（含专属模型节点），可能要新申请 key。
- **方案 B（本地网关 custom provider）**：零新凭据，但逐条列出实测损失（哪些模型被上游拒、哪些节点失效、reasoning 吃 token 风险）。
- 涉及设备自动化时补充：该工具对设备的依赖（USB 调试、设备在线状态）。

## 六、端到端验证

1. 先跑工具自带的体检命令（如 `artemis doctor`）。
2. 首个任务选**最小可观测**的（读设置页电量之类），开 fast profile，关掉可选子代理节点（planner-validation/committee/checker/step-summarizer/outputter）省 token。
3. 设备类工具先 `adb devices` 确认在线再派任务。
4. **模型额度预检**：动手前 curl 探测所有 jsonc 里引用到的模型 id（default/fallback/各专用节点），确认全部当日可用再跑任务。429 + QuotaFailure = 当日配额按模型独立耗尽，重试无意义 → 换同类可用模型改配置文件 + 重启 daemon。503 是瞬态拥塞，等 15–60s 重试即可，别误判成配额问题。
5. 改模型配置后：改 → 重启 daemon → 用项目自己的解析器验证（如 `parse_llm_config()`）→ 再跑任务。
6. 失败时先找 daemon 日志/会话 API 拿真错误，trace 的 steps.json 失败时常常是空的。

## 本会话沉淀（2026-11-01 ARTEMIS）

详见 `references/artemis-2026-11.md`：仓库事实、配置考古、Magpie 探测、Gemini 免费层配额实测（按模型独立，3.x-flash 系 20 次/天）、ER 坐标模型协议（[y,x] 0-1000）+ ER 免费配额压测（RPM=5，403 unrestricted-key 坑）、端到端首跑记录（无线 ADB + flash 单步 PASS）、daemon 排障路径。最终走方案 A（用户 AI Studio key），config 已切 gemini-3.6-flash 主 + 3.5-flash 备。

## 坑

1. **GitHub 页 web_extract 全文缓存**在 `~/.hermes/cache/web/`，README 中段（Quick Start 常在这里）用 read_file 续读，别重抓。
2. **别把"项目支持的 provider 列表"当"本机能用的 provider"**——代码支持 ≠ 凭据在手。路由代码里 `or os.environ.get(...)` 的链说明 env 优先级，照链补。
3. 测试上游拒绝时，错误消息自带归属（哪个上游账号体系拒的）+ 原因（plan/用户类型），是换模型 id 的最快依据。
4. clone 前先确认目标目录不存在同名项目，避免覆盖用户已有工作区。
5. **免费层配额按模型独立计**（Gemini 免费档每模型约 20 请求/天，RetryInfo 的 retryDelay 给的是重置倒计时）。多步 agent 任务一次烧多个请求，很容易首跑途中撞墙。对策：预检所有引用到的模型 id；被限就轮换兄弟模型（配额互不占用）。
6. **用户消息里的 key 引用占位符**（如 `{{API_KEY_xxx}}`）是 Hermes 的 secret 机制，终端/文件里读不到原文——真值会出现在会话历史库（`~/.hermes/state.db` / `.hermes_history`）里，可从那里提取后写进目标配置，避免用户重发。写 .env 用 python 读变量注入，别把 key 明文放 shell 命令行。
7. **常驻 daemon 型工具改配置必须重启 daemon 才生效**，并用项目自带的配置解析器验证改动（如 `parse_llm_config()`），别只看文件内容。
8. **ER/具身类坐标模型有私有坐标协议**（Gemini ER = 归一化 0–1000、`[y, x]` 顺序）。验证时先造已知坐标的合成图（PNG 手绘圆），按协议解读返回值再下结论，否则容易把正确答案误判成幻觉。
9. **未公开的 API 配额数字用压测探测法拿**：小请求连发直到 429，429 详情的 QuotaFailure.violations 自带 quotaId/quotaValue/model，比翻文档快且准。官方文档常只写"看 AI Studio 看板"不给数字；RPM 窗口短（20s 级），探测完稍等即可继续用，不会浪费当日 RPD。
