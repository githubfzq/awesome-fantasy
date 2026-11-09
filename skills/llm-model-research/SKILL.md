---
name: llm-model-research
description: 调研 LLM 模型性能与本机安装可行性：代理网络、基准图读数、MoE 内存判定。
---

# LLM 模型调研与本地可行性评估

## 触发
"调研 XX 模型"、"XX 性能如何"、"本机能不能跑 XX"、"该下哪个量化版本"、"和 YY 比怎么样"。

## 网络前提（本机每次都要做）
终端 curl 访问 HuggingFace/GitHub 直连会超时——系统代理在 127.0.0.1:7899 但终端 env 不继承，必须显式导出：

```bash
export https_proxy=http://127.0.0.1:7899 http_proxy=http://127.0.0.1:7899
```

会话里导出一次即可（terminal 状态延续）。国内网络备选镜像：ModelScope `modelscope.cn/models/<org>/<model>`。

判断一个二进制工具（Rust/Go 编写，如 llmfit、ollama）是否吃代理或能否换端点，直接查二进制：
```bash
strings $(which <tool>) | grep -E 'https?://[a-z.]+|HTTPS_PROXY|ALL_PROXY|HF_ENDPOINT' | sort -u
```
见到 `HTTPS_PROXY/https_proxy/ALL_PROXY` 字样 = 读标准代理 env，export 后即可用；见到硬编码 URL 且无 `_ENDPOINT` 变量 = 镜像源无门。查上游源码确认时，api.github.com 未认证 curl 很快限流，改用 `gh api repos/<org>/<repo>/...`（带 gh 认证）。

## llmfit：本机可装模型速查工具
`llmfit fit` 按本机硬件（RAM/GPU/后端 MLX/Metal）给兼容模型打分，本地计算不走网。`llmfit update` 拉最新模型库——HF API 硬编码（上游 llmfit-core/src/update.rs 的 `HF_API`），**无 HF_ENDPOINT/镜像/ModelScope 支持**，但底层 ureq 读标准代理 env，照上面 export 即可跑通：

```bash
export https_proxy=http://127.0.0.1:7899 http_proxy=http://127.0.0.1:7899
llmfit update --no-dashboard   # 默认 100 trending + 50 downloads
```

`--status` 看缓存（默认 151 模型/全量 1 万+），缓存文件在 `~/Library/Application Support/llmfit/hf_models_cache.json`。不带代理直接 update 会连不上 HF。

## 信息采集（curl 即可，无需搜索工具）

```bash
# 1. 变体清单：author + search，按更新时间排序
curl -s "https://huggingface.co/api/models?author=openbmb&search=MiniCPM-V&sort=lastModified&direction=-1&limit=30" -o /tmp/models.json

# 2. 模型卡全文
curl -sL "https://huggingface.co/<org>/<model>/raw/main/README.md" -o /tmp/model.md

# 3. GGUF 文件清单与体积（各量化档大小，可行性评估的核心输入）
curl -s "https://huggingface.co/api/models/<org>/<model>-gguf/tree/main" -o /tmp/files.json

# 4. Ollama 版本 tag 与体积（HTML 页 grep tag 名和 GB 数）
curl -s "https://ollama.com/<org>/<model>/tags" -o /tmp/tags.html
```

## 坑：基准分数通常在图片里
国产模型（OpenBMB/Qwen 等）的评测表多为 PNG 截图，README 文本里**没有数字**，只有"achieves higher score"式描述：
1. 在模型卡里 `grep -oE "assets/.*\.png"` 找基准图 URL（多托管在 raw.githubusercontent.com）；
2. curl 逐张下载（串行，走代理；`&` 并行会被终端工具拒绝）；
3. `vision_analyze` 读图，指令要具体："列出所有基准项与各模型分数"；
4. VLM 表和语言表分两次读，避免漏行。
表格脚注注意评测口径（Instruct vs Thinking 模式、视觉压缩比 4x/16x）。

## 本机可行性评估（Apple Silicon）
```bash
system_profiler SPHardwareDataType | grep -E "Chip|Memory"
df -h /System/Volumes/Data    # 数据卷才是真实余量，别只看 /
ollama list; which llama-cli llama-server
```

判定规则：
- **MoE 模型（如 35B-A3B）：激活 3B ≠ 内存 3B。** 推理时全部专家权重必须可寻址（内存或 SSD mmap），按**总参数的量化体积**评估，不是激活量；
- 统一内存 16GB：模型文件 ≤ 8GB 可流畅；> 12GB 靠 mmap 换页会掉到个位数 tok/s；
- 厂商专用运行时（如 LES 专家调度）只在官方 fork（如 llama.cpp-omni）里，主线程 llama.cpp/Ollama 没有，别拿论文跑分套主线程体验；
- 结论必须同时报**内存**与**磁盘**两条约束——磁盘快满时（<15% 空闲）再小的量化也装不下。

体积速查与实测案例见 `references/apple-silicon-sizing.md`。

## 输出格式
先一句话结论（是什么/性能定位/本机可行与否），再给对比表和安装命令。用户偏好中文、直答、无客套。若模型不可行，明确说"不可行 + 为什么 + 最小可行替代"（如降档到同系列小模型），并给出一条可直接运行的命令。