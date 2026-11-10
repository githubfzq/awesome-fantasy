# Jev 决策模型（TypeSafe）经 Magpie 网关调用

2026-11-01 实战验证。Magpie 网关（127.0.0.1:3425）已配置 TypeSafe provider，模型 `jev-latest`（实际 jev-1.14.0）。

## 唯一可用端点：systemone

```
POST http://127.0.0.1:3425/v1/systemone
{"model":"jev-latest","state":[...文本串列表...],"questions":{"q1":{"type":"noul","instructions":"..."}}}
```

响应：`{"model":"jev-1.14.0","answers":{"q1":{"type":"noul","noul":0.98}},"usage":{...}}`

## 坑

- **`/v1/chat/completions` 调 jev 会报错**：`typesafe/jev-latest only decides a routing group's model and effort; it holds no conversation` —— Jev 不是 chat 模型，必须走 systemone 端点
- `POST /v1/decisions` 和 `/api/alpha/decisions` 在网关上 404（那是 OpenRouter 官方路径；Magpie 用自己的 systemone 转发）
- state 是**字符串数组**，不是对象；questions 支持一次多问（q1/q2/...），批量判重就靠这个
- choice 返回 `{"choice":"0","probabilities":{"0":1.0,...}}` —— key 是 criteria 的字符串索引
- noul 门槛建议 0.6（0.5 太激进会误跳新人）

## 图片输入（Box 原语）在 Magpie 上不可用（2026-11-01 实测）

- Jev 官方要求图片请求带 header `TypeSafe-Danger-Zone-Images: true`，否则 400 `Images are experimental`
- **Magpie 网关不透传自定义 header**——在 systemone 请求里加上照样 400 同样报错
- 因此 **Box 视觉定位必须直连 `https://api.typesafe.ai/v1/systemone`**（key 在 `~/.config/magpie/providers.json` 的 typesafe provider；需用户授权脚本读取）
- Box 请求格式：state 里放 `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`，questions 用 `{"type":"box","instructions":"描述目标"}`，可一问一框多问并行

## 四种原语

| 原语 | 问什么 | 返回 |
| --- | --- | --- |
| noul | 条件成立吗 | 概率 |
| choice | 选哪个 | 选中项+各选项概率 |
| score | 有序量表几分 | 位置+概率分布 |
| box | 图里在哪 | top/bottom/left/right 分数坐标（图片输入见上节限制） |

## 采集流水线的接入点（jev_batch.py 模式）

1. **免进主页查重**（最大收益）：列表卡片标签集 vs 已采标签库，一屏一次批量 noul，重复卡直接跳过省 25s/人
2. 异常弹窗处置：未知界面时从候选按钮里 choice 选"关闭/返回"
3. 分区完整性校验：解析详情页后 noul 验证"是否漏了照片墙/问答区"

设计原则（hermes-jev-skills）：代码拥有组合权与副作用，Jev 只回答"哪个下一步"；候选表只含 id/role/label，不含坐标；置信度低于门槛退化为 reobserve 而非硬选。

## 参考

- OpenRouter 文档: https://openrouter.ai/docs/guides/community/jev（官方 Decisions API 路径仅对 OpenRouter key 有效）
- hermes-jev-skills（GUI action_choice_request_v1 模式）: github.com/kerpopule/hermes-jev-skills
