# OpenBiliClaw × Magpie 接入实录（2026-10-29）

会话级细节，正文 SKILL.md 已提炼为通用规则；此处留底供追溯。

## 最终生效配置（config.toml，gitignore 本地文件）

```toml
[llm]
default_chain = ["magpie"]

[llm.instances."magpie"]
name = "Magpie 本机网关"
provider_type = "openai_compatible"
enabled = true
api_key = "***"            # 非空占位（安全层把占位符改写后的字面值），Magpie 不校验
model = "auto/auto"        # Magpie 全自动路由
base_url = "http://127.0.0.1:3425/v1"
```

原有实例保留：deepseek（官方）、qwen（百炼 compatible-mode）；embedding 走本地 Ollama bge-m3。

## 过程记录

1. `lsof` 发现 magpie 监听 `*:3425`；`/v1/models` 约 170 个模型；任意 Bearer curl `/v1/chat/completions` 得 200，确认不校验 key。
2. 用户决策（clarify）：模型选 `auto/auto`，默认链整体替换为 magpie。
3. 首次 `config-show` 报 blocking issue「缺少 API Key」（src/openbiliclaw/config.py:3852 对启用实例校验非空）→ 填占位值。
4. 占位符折腾：写 `{{SECRET_...}}` 形式 → 落盘被安全层改写为 `***`，且 patch diff 回显不可信，浪费多轮。教训已进正文坑 2/坑 6。
5. 端到端验证：`uv run python` 直连 `OpenAIProvider(api_key=占位, model="auto/auto", base_url=...3425/v1)` 发真实对话，返回「你好」、实际 model=hy4-preview（auto 路由选择的底层模型）。
6. `pytest` 全量：8525 通过 / 5 失败——stash 干净工作区复跑仍失败，确认为存量失败（storage temporal + saved_sync），与本次无关。
7. 环境修复：.venv 缺 dev 依赖导致 `uv run pytest` 落到 homebrew pytest（232 收集错误）→ `uv sync --extra dev`；uv sync 把 uv.lock 重写为阿里云镜像源 → `git checkout uv.lock` 还原。

## 验证命令

```bash
uv run openbiliclaw config-show          # 实例注册 + Provider 概览
uv run pytest -q                          # 全量（先 uv sync --extra dev）
curl -s http://127.0.0.1:3425/v1/models   # 网关模型清单
```
