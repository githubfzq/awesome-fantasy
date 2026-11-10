# OpenBiliClaw 生产服务运行时环境事实（2026-10-30 快照）

本文件记录 OpenBiliClaw 本机部署的运行时状态与测试环境相互作用，供后续会话快速对齐。过时内容应更新而非累积。

## 服务运行形态

- 启动方式：herdr pane 内 `source .venv/bin/activate && exec openbiliclaw start`（pane id 会变，用 `herdr pane list` 现查）
- 端口：8420（`[api]` 配置），探活 `curl http://127.0.0.1:8420/` 返回 302
- 配置热加载：改 config.toml 后 `/api/config` 即返回新值，无需重启；`openbiliclaw config-show` 可交叉验证
- 日志：`logs/openbiliclaw.log`，单文件从 2026-08 起未轮转（77MB+，2.4 万条 Traceback 大部分是历史遗留）；**排查问题先按时间戳切片**（`awk '/<起始时间>/,0'`），别被存量报错误导

## LLM 链路（当前）

- 默认链 `["magpie"]` → Magpie 本机网关 `http://127.0.0.1:3425/v1`
- model = `group/openbiliclaw`（Magpie 专属路由组，4 厂商：workbuddy/auto → copilot/auto → zcode/GLM-5.3-Flash → minimax-cn/MiniMax-M3.1-Flash，routing=smart，levels=none）
- levels=none 修复了 reasoning 模型（hy4-preview 等）吃光 max_tokens 导致 `finish_reason=length` → `All providers failed` 的问题
- 组员故障转移内建（超额/宕机自动换下一个）

## 测试与运行时服务的相互作用

- `pytest -k "config or registry or provider"`：998 passed；但 `test_cli.py::test_start_uses_configured_api_host_and_port` 在服务运行时**必失败**——`_acquire_server_migration_guard`（cli.py）发现 data 目录被运行中服务锁定即 `typer.Exit(1)`，该测试未 mock guard。属环境性失败，非代码问题；停机窗口内跑也一样失败（服务重启后几秒即重新持锁）。
- `uv run pytest` 会把 `uv.lock` 重写为镜像源（conda/镜像环境相互作用），跑完测试需 `git checkout uv.lock` 还原。
- `.venv` 缺 dev 依赖时 `uv run pytest` 会落到 homebrew pytest（232 个收集错误），`uv sync --extra dev` 修复。

## 存量失败（v0.3.210，与配置无关）

git stash 到干净 main 后仍复现的 5 个失败：tests/test_storage.py 的 4 个 temporal 状态测试 + tests/test_saved_sync_identity_pipeline.py 1 个，伴随 "Invalid temporal metadata coerced" 警告。上游代码问题，等升级 v0.3.232 时观察。

## 上游更新状态（2026-10-30 查）

本地 v0.3.210 → 上游 v0.3.232：463 commits（106 feat / 180+ fix / 20 releases）。主要新功能：TikTok + Instagram 来源、GitHub 来源、事件时间溯源重构、蓝鱼实验室、多语言（简繁英）、聊天逐字流式、Cheaper Inference/Jev/Keenable provider、macOS 正式签名公证。升级前备份 config.toml（`[llm]` 配置结构有演进，embedding 段已独立）。
