---
name: hermes-web-search-backends
description: "Use when Hermes 搜索配置/排障：web_search 后端、env 变量、优先级。"
---

# Hermes Web Search Backends（web_search / web_extract 后端配置）

Hermes 的 web_search 是可插拔后端架构。用户问"有哪些搜索工具/怎么配搜索/搜索报错"时，按本页作答；细节与源码出处见 references/backend-resolution.md。

## 后端注册表（8 个）

| backend | 环境变量 | 免费档 | 说明 |
|---|---|---|---|
| tavily | `TAVILY_API_KEY` | 1000 次/月 | 质量好，自动探测优先级最高 |
| exa | `EXA_API_KEY` | 有 | |
| parallel | `PARALLEL_API_KEY` | — | `PARALLEL_SEARCH_MODE` 可选 |
| firecrawl | `FIRECRAWL_API_KEY` | — | 无任何 key 时是最终兜底名（会报错）；另有 Nous 订阅 tool-gateway 通路 |
| searxng | `SEARXNG_URL` | 自建免费 | 指向自建 SearXNG 实例 URL，无限额 |
| brave-free | `BRAVE_SEARCH_API_KEY` | 2000 次/月 | brave.com/search/api 领取 |
| ddgs | 无需 key | 免费 | 需 `~/.hermes/hermes-agent/venv/bin/pip install ddgs`，装上即自动可用 |
| xai | `XAI_API_KEY` 或 Grok OAuth | — | 走 Grok 搜索 |

## 解析优先级

1. `web.search_backend`（config.yaml，仅 search）> `web.backend`（search+extract 共用）显式指定优先。
2. 未指定时自动探测，顺序固定：tavily > exa > parallel > firecrawl(key 或 gateway) > searxng > brave-free > ddgs。
3. 都没有 → 兜底返回 "firecrawl"，无 key 时 web_search 实际不可用。
4. web_extract 另有 `web.extract_backend`（如设 `native` 不依赖搜索后端）；超长页受 `web.extract_char_limit`（默认 15000）截断。

## 配置步骤

1. key 只放 `~/.hermes/.env`（secrets 归 .env，设置归 config.yaml，勿混）。
2. 多个 key 并存且想指定主力：`hermes config set web.search_backend brave-free`（不要手编 config.yaml）。
3. 生效需新会话（`/reset`），工具集变更不进当前会话。

## 验证

```bash
cd ~/.hermes/hermes-agent && venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from tools.web_tools import _get_search_backend
print(_get_search_backend())"
```
输出解析出的 backend 名；与预期不符时按优先级逐个查 .env。

## 排障

- "No web search provider configured" → .env 无任何搜索 key 且 ddgs 未装。
- 报 firecrawl 相关错误但用户没配过 firecrawl → 就是走到了空兜底，按上表补 key。
- 想搜 X/Twitter → 是独立工具集 `x_search`（`hermes tools enable x_search`），凭证用 `XAI_API_KEY` 或 X OAuth，与 web_search 后端无关。
- session_search（本地会话检索）无需任何配置，别和 web_search 混淆。

## Pitfalls

- 优先级陷阱：tavily 和 brave key 并存时默认走 tavily，用户想用 Brave 当主力必须显式 `hermes config set web.search_backend brave-free`。
- ddgs 要装进 Hermes 自己的 venv，不是系统 python。
- 判断"哪些后端已配置"别只看 config.yaml——自动探测看的是 .env key 存在性，config 里 backend 为空串是常态。

细节/源码出处/升级后复核方法：references/backend-resolution.md
