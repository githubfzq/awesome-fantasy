---
name: tax-web-filing-rpa
description: 电子税务局网页端申报RPA（季度申报等），浏览器自动化+飞书验证码。
---

# 电子税务局网页申报 RPA（浏览器自动化）

与扣缴端 VM 类技能（wage-withholding-rpa / tax-withholding-vm）互补：本技能走浏览器（agent-browser）操作网页端电子税务局。VM 类技能是用户自有资产，不要试图合并或改动它们。

## 总体架构

两个脚本 + 一个共享登录态：

1. `login.sh` — 打开站点 → 企业业务标签 → 填识别号+身份证 → 触发短信 → 飞书要验证码 → 填入完成登录 → `agent-browser state save` 落盘。
2. `declare.sh` — `state load` 跳过登录 → 逐项办理待办（增值税及附加、个税经营所得 A 表×2、财务报表季报）→ 每项写结构化结果 JSON。
3. 编排端（Hermes 会话）负责：调用脚本、在飞书验证码环节穿针引线、失败时带截图人工判读。

目录约定沿用 `~/Documents/rpa/`（月度申报已在用），季度申报放子目录 `~/Documents/rpa/quarterly/`。

## 飞书短信验证码双向通道（已验证可用）

网关 DM chat_id 存于 `~/.hermes/channel_directory.json`（feishu → oc_ 开头）。凭据在 `~/.hermes/.env`（FEISHU_APP_ID / FEISHU_APP_SECRET）。

流程：
1. bot 发消息："贵州电子税务局登录需要短信验证码，请把收到的验证码回复给我"。
2. 轮询 `GET /open-apis/im/v1/messages?container_id_type=chat&container_id=<chat_id>&sort_type=ByCreateTimeDesc&page_size=5`。
3. 过滤 `sender.id_type == 'open_id'`（用户本人）的消息，从 text 提取数字验证码（正则 `\b\d{4,8}\b`）；忽略 `app_id` 发送者（bot 自己的历史消息）。
4. 记录轮询起始时间戳，只认比它新的消息，防旧消息误配。
5. 验证码通常 5 分钟失效：轮询间隔 10s、总超时 4min，超时则重发短信并重来一次。

模板脚本见 `scripts/feishu_otp.py`。

## 防护站探查纪律（重要）

税务局站点普遍带 JS 动态防护（瑞数类：动态挑战脚本 `/<随机串>/*.js` + URL 随机 token）。行为特征与对策：

- 首次打开正常渲染；**reload / 二次导航主文档直接 400、页面空白**。对策：不要 reload，重新 `agent-browser close` 后全新 `open`。登录态要走 `state save/load`，不要指望刷新页面保持。
- 表单不渲染时，先等 15-30s 并轮询 `document.querySelectorAll('input').length`，再下结论。
- **未经用户明确同意，不要手动 fetch 探测站内 API**（如 getPublicKey）。gov 站点接口探测敏感，2026-10-11 会话中此类动作被用户直接拒绝。判断页面状态用 DOM 检查和截图，用 `agent-browser network requests` 看请求状态码即可。
- agent-browser 的无障碍树在这种站点上会缺元素（表单区空白但截图正常）；定位元素优先用 `eval` 查 DOM + 截图视觉确认，不要只信 snapshot。

## 登录态与凭据

- 凭据来源：KeePass（keepass-lookup skill）或运行时用户提供，绝不落盘、绝不 echo。
- `state save` 保存的 JSON 含 cookies+storage，属于敏感凭据文件：放 `~/Documents/rpa/quarterly/` 下并提醒用户注意；过期（一般当天/次日失效）则重走登录流程。

## 季度申报流程（用户提供，2026-10）

详细页面步骤见 `references/guizhou-quarterly-flow.md`。要点：

- 所有业务在"我的待办"里，逐项办理。
- 增值税及附加（小规模）与工会经费是**同一次办理**（综合关联申报自动勾选两项）。
- 个税经营所得 A 表×2 项；点"填写申报表"会弹"实名认证登录未满足要求"拦截——这是**已知阻塞**，需用户额外操作（见 references 文件）。
- 财务报表：季报 + 模板 Excel 填写后上传。
- 硬性约定（沿用月度申报）：所属期一律运行时计算（N 季度申报 = N 季度数据），绝不硬编码；零申报也要逐项确认合计为 0 再提交；每步截图留痕。
