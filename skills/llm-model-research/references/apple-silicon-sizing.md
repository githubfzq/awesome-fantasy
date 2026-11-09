# Apple Silicon 体积速查与实测案例（2026-10-31 会话）

## 本机基线（用户 Mac，会话时实测）
- MacBook Pro M1 Pro：8 核（6P+2E）/ 16GB 统一内存
- 磁盘 460GB，数据卷当时仅剩 11GB（98% 满）→ 评估大模型前先 df 确认
- 已装推理工具：ollama 0.40.13（/usr/local/bin/ollama）、llama-cli（homebrew）

## 体积速查（通用规则）
| 精度 | 每参数字节 | 7B | 35B |
|---|---|---|---|
| FP16/BF16 | 2B | ~14 GB | ~70 GB |
| Q8_0 | ~1.07B/参数 | ~7.5 GB | ~37 GB |
| Q4_K_M | ~0.6B/参数 | ~4.4 GB | ~22 GB |

经验值：GGUF Q4_K_M ≈ 0.6 GB/B 参数；再加 1-2GB KV cache 与 mmproj。

## 16GB 统一内存判定线
- ≤ 8GB 模型文件：流畅（GPU 可全载）
- 8-12GB：可用，上下文要短
- > 12GB：mmap 换页主导，个位数 tok/s，仅"能跑"不"能用"
- MoE 模型按总参数体积判定（激活量只影响算力不影响内存）；除非运行时支持专家按需换页（如 OpenBMB LES）

## 实测案例：MiniCPM-V 4.7（openbmb，2026-10 发布）
VLM 系列：35B-A3B（MoE，系列首个）+ 1B（实际 1.3B）。视觉压缩 4x/16x 可选，mmproj f16 约 1.1GB（4x 版 0.9GB）。GGUF 仓库 `thinking/` 子目录为带思考版（模板不同，权重相同）。

35B-A3B GGUF 体积（HF tree API 实测）：F16 69.4GB / Q8 36.9GB / Q5_K_S 28.5GB / Q4_K_S 24.0GB / Q4_1 21.2GB / IQ4_XS 19.7GB / IQ3_XS 19.8GB
→ 16GB 内存 + 11GB 磁盘：**不可行**。双杀：任何 Q4 档都放不进磁盘；即便清盘，>12GB 主线程无 LES 必换页降速。
1B GGUF：Q4_K_M 0.67GB / Q8 1.08GB / F16 2.02GB → 全档可跑，推荐 `ollama run openbmb/minicpm-v4.7:1b`（q4 1.8GB 含 mmproj）。

## MiniCPM-V 4.7 35B-A3B 基准速览（官方 Instruct 模式图读数）
- 强项：OmniDocBench 94.24（碾压同级 ~82）、MMBench 91.72、MathVista 88.0、OCRBench 91.2、MMMU 80.22、CMLU 90.21、τ²-Bench 84.65（agentic 工具调用第一）、Video-MME 76.4
- 短板：LiveCodeBench 56.57（对手 Gemma-4 31B 71.24）、AIME26 76.46（Qwen3.6-27B 80.42）、ScreenSpot GUI 定位 86.99（Qwen3.8 93.31）
- 对比基线：Qwen3.6 35B-A3B / Qwen3.6 27B / Qwen3.8 27B / Gemma-4 31B
- 1B 版亮点：OCRBench 86.10（超 5.1B 的 Gemma-4-E2B 的 73.50）、OmniDocBench 85.39，端侧 OCR/文档首选

## 来源 URL 模板
- 变体清单：https://huggingface.co/api/models?author=openbmb&search=MiniCPM-V&sort=lastModified&direction=-1
- 模型卡：https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B/raw/main/README.md
- GGUF 清单：https://huggingface.co/api/models/openbmb/MiniCPM-V-4.7-35B-A3B-gguf/tree/main
- Ollama tags：https://ollama.com/openbmb/minicpm-v4.7/tags
- 基准图：https://raw.githubusercontent.com/OpenBMB/MiniCPM-o/main/assets/minicpmv4.7/*.png