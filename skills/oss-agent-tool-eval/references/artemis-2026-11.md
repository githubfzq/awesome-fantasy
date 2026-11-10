# ARTEMIS 本地试跑实录（2026-11-01，含验证与首跑）

## 项目事实

- 仓库：github.com/google/artemis，Apache-2.0，15.8k star，121 commits（2026-09-09 开源）
- 定位：自然语言 → 安卓真机自动化。AndroidWorld 基准自称 99%+ 完成率
- Python 3.12+，uv 管理。依赖 langgraph/langchain + adbutils + uiautomator2 + google-genai + langchain-openai/anthropic
- 仅支持 Android（USB 调试或无线 ADB）。四种用法：CLI / Web 控制台（localhost:8000）/ MCP Server / Python SDK
- 双模式：flash = 反应式循环 3–5s/步；pro = 完整多 Agent 图（默认）
- 设备侧装「Artemis Accessibility Helper」v1.2.0 无障碍服务 APK；开关：ARTEMIS_HELPER_AUTO_INSTALL=false 禁自动装、ARTEMIS_HIERARCHY_BACKEND=uiautomator 换后端、`artemis helper install/status/uninstall`

## 模型后端（源码考古 + 实测）

- 路由：`artemis/llm/router.py`。google 读 GOOGLE_API_KEY → GEMINI_API_KEY env 链；校验在 `third_party/mobile_use/config/llm.py` 的 `validate_provider`（google 只认 GOOGLE_API_KEY → **.env 两个都填**，避免校验报错）
- `object_detector` 节点强制 `gemini-robotics-er-2-preview`（ER 具身推理模型）做坐标定位
- 配置解析（`artemis/config/paths.py:149`）：ARTEMIS_* env → `<repo>/config/artemis.jsonc` → 项目根 → 用户目录 → 内置模板
- **改 jsonc 后必须 `uv run artemis restart`**（daemon 常驻，不重启不生效）；改完用项目自己的解析器验证：
  `uv run python -c "from artemis.config.llm import parse_llm_config; c=parse_llm_config(); print(c.operator.model, c.operator.fallback.model)"`
  （注意：object_detector/hopper/outputter 是 utils 节点，不在 LLMConfig 顶层属性里，别按 agent 节点访问）

## Gemini 免费层配额实测（2026-11-01，AI Studio 免费 key）

- **配额是按模型独立计的**：`GenerateRequestsPerDayPerProjectPerModel-FreeTier`，gemini-3.x-flash 系每模型每天仅 **20 次**请求
- 当日 429 被限的模型：gemini-3.8-flash、gemini-3.7-flash、gemini-flash-latest（RetryInfo retryDelay ≈ 43500s ≈ 12h，按太平洋时间午夜重置）
- 当日仍可用：gemini-3.6-flash、gemini-3.5-flash、gemini-3.5-flash-lite、gemini-3.1-flash-lite、gemini-robotics-er-2-preview、gemini-2.5-flash
- 503 "high demand" ≠ 配额耗尽，是瞬态拥塞，等 15–60s 重试即可；429 + QuotaFailure 才是真额度用完 → **别等 12h，直接探测兄弟模型换配置**
- 一次多步任务消耗多倍请求数（首跑 flash 单步=1 call/8247 tokens；pro 全图每步多节点），免费层 20 次/天撑不起连续测试，多模型轮换是常态

## ER 坐标模型实测（gemini-robotics-er-2-preview）

- 可用且免费层有额度，单次 2–4s
- **坐标协议**：返回归一化 0–1000 的 `{"point": [y, x]}`（注意顺序是 [y, x]！）。验证图 640×360、红圆心 (480,120) → 返回 [335, 750]，误差 <1px
- prompt 不写明协议时它仍按 [y,x] 0-1000 返回，但顺序解读容易踩坑——测试时先固定协议措辞

## ER 模型免费层配额实测（2026-11-01，压测探测法）

官方文档（rate-limits 页）只给方法论不给数字，"具体限额看 AI Studio Rate Limit 看板"。实测法：小请求连发直到 429，从 429 详情的 QuotaFailure 直接读出 quotaId + limit 值——这是拿未公开配额数字的最快手段。

- **RPM = 5**（`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`），超限 retryDelay 仅 21s 级，窗口滚动
- **RPD 未触发**：当日累计 13+ 次仍 200，日限 >15；估计同为十几~几十。Artemis 的 object_detector 按需触发（每任务 0–几次），5 RPM 实际不构成瓶颈
- **403 坑**：ER 模型拒绝 unrestricted API key（官方 robotics-overview 页明确），新建 key 记得加限制
- 对比：Flash 系免费 RPD=20 才是真瓶颈（一个多步任务烧 10–20 call）；ER 触发频率低，够用
- **混合后端思路**（未实施）：operator 等主力节点走 Magpie custom provider（省 Gemini 配额），ER 节点保住 Gemini key（Magpie 无法做坐标定位）——两者正好互补。实施方式：jsonc 里 default 节点 provider 改 custom + OPENAI_BASE_URL 指向网关，object_detector 保留 google provider

## 端到端首跑记录（2026-11-01 02:54）

- 设备：小米 M2012K11AC（alioth），**无线 ADB pair/TLS**（`adb devices` 显示为 `adb-xxx._adb-tls-connect._tcp`，非传统 serial）
- 流程：`artemis doctor`（All passed）→ `artemis helper install` → `artemis run "打开设置，告诉我当前电池电量百分比" --profile flash --disable-planner-validation --disable-committee --disable-checker --disable-step-summarizer --disable-outputter`
- 结果：PASS。1 步、1 次 LLM call、8247 tokens，正确读出电量 90%。operator thinking 正常输出中文推理
- flash 模式直连 default 模型（当时已换 gemini-3.6-flash），未触发 3.8 配额墙

## 排障路径（首跑失败时踩出来的）

1. `traces/<session>_FAIL_*/steps.json` 失败时是**空的**，别在这找原因
2. 真错误在 daemon 日志：`~/Library/Application Support/artemis/logs/daemon-8000.log`（grep 429/quota/timeout）
3. 会话状态走 daemon API：`/api/sessions/{id}`（status）、`/api/sessions/{id}/usage`（llm_calls/tokens/profile）、`/api/sessions/{id}/steps`（逐步 action + operator_raw_thinking，成功后才有内容）
4. trace 目录：`~/Public/Projects/artemis/traces/`，PASS 会话有 recording.mp4 + steps.json

## Magpie 探测数据（回环 3425，免 key）— 已确认方案 B 不可行

| 模型 id | 实测结果 |
|---|---|
| auto/gemini-3.8-flash | 拒："Copilot: model not supported" |
| copilot/gemini-* | 同上 |
| auto/gemini-3.5-flash | 拒："WorkBuddy AI: not allowed for user type personal_free_user" |
| auto/glm-5.3-flashx | 可用但 reasoning 吃 token |

结论：最终走方案 A（用户自己有 AI Studio 免费 key）。免费层按模型轮换用，ER 节点保住了。

## 首选参考

- README 缓存：`~/.hermes/cache/web/github.com-3c87705c98.md`（159–278 行 Quick Start/MCP/SDK）
- MCP 规则文件：repo 内 `mcp_server/rules.md`
- 本地工作区：`~/Public/Projects/artemis`（.env 已配 key，config/artemis.jsonc 已改为 3.6-flash 主 + 3.5-flash 备）
