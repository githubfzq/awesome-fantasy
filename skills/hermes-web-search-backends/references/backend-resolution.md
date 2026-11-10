# Web Search Backend Resolution — 源码出处与复核方法

调研于 2026-11-01，Hermes git 安装于 ~/.hermes/hermes-agent。升级 Hermes 后按下文路径复核。

## 源码出处

- 后端列表与自动探测顺序：`tools/web_tools.py` `_get_web_backend()` 的 `backend_candidates` 元组（约 L234-249）：
  tavily > exa > parallel > firecrawl(key/gateway) > searxng > brave-free > ddgs(package importable)；末尾再遍历插件注册 provider，最终兜底 `"firecrawl"`。
- per-capability 覆盖：`tools/web_tools.py` `_get_search_backend()`（约 L273）——`web.search_backend` > `web.backend`。
- config 默认值：`hermes_cli/config.py` `web` 段（约 L1249-1254）：`backend` / `search_backend` / `extract_backend` / `extract_char_limit: 15000`。
- 插件 provider 实现：`plugins/web/<name>/provider.py`（brave_free, ddgs, exa, firecrawl, parallel, searxng, tavily, xai）。每个实现 `is_available()`（廉价探测，读 env 或 OAuth 状态）。
- xai 特殊性：`is_available()` 委托 `tools/xai_http.has_xai_credentials()`，接受 `XAI_API_KEY` 或 Grok OAuth token，不只看 env。

## 本会话实测记录（2026-11-01）

- 用户机器 8 个后端初始全未配置：config `web.backend`/`search_backend` 为空串，.env 无任何搜索 key，ddgs 包未装，xai 无凭证 → `_get_search_backend()` 兜底 "firecrawl"（不可用）。
- 用户随后把 `BRAVE_SEARCH_API_KEY` 写入 ~/.hermes/.env，`_get_search_backend()` 即解析为 `brave-free`，验证脚本通过。
- 用户再补 Tavily；两 key 并存时自动探测将优先 tavily（顺序表第一位），除非显式 `hermes config set web.search_backend brave-free`。

## 验证脚本（每会话可重跑）

```bash
cd ~/.hermes/hermes-agent && venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from tools.web_tools import _get_search_backend
print(_get_search_backend())"
```

探测各 key 是否就位（不进源码目录也行）：

```bash
grep -oE "^(TAVILY_API_KEY|EXA_API_KEY|PARALLEL_API_KEY|FIRECRAWL_API_KEY|SEARXNG_URL|BRAVE_SEARCH_API_KEY|XAI_API_KEY)" ~/.hermes/.env | sort
~/.hermes/hermes-agent/venv/bin/python -c "import ddgs" 2>/dev/null && echo ddgs: installed
```

## 排障细则

- `_get_search_backend()` 输出与预期不符：按优先级表从上往下找第一个"误就位"的 key。
- web_search 返回 "No web search provider configured"：空兜底路径，全部后端都未就位。
- 关联工具集区分：`x_search`（X/Twitter，独立工具集+独立凭证）、`session_search`（本地 FTS5，零配置）、`browser`（网页自动化，非搜索）。用户问"搜索工具"时先分清是哪类。
