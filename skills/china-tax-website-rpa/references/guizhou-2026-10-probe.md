# 2026-10-11 会话排查记录（贵州电子税务局登录表单不渲染）

## 现象
agent-browser 打开 `https://tpass.guizhou.chinatax.gov.cn:8443/#/`：
- 首次加载 200，页面壳渲染（蓝色顶栏、长城背景、企业业务/自然人业务/代理业务三标签，企业业务 activeCls）
- 登录表单区（.password_ddd 内 tabsCls 以下）永远空白，input 数量恒为 0
- 业务 API `POST /sys-api/v1.0/auth/oauth2/getPublicKey?8i8UWOrl=<动态token>` 返回 400，响应体 `\r\n\r\n\r\n`
- reload 后主文档直接 400 → 白屏（app innerHTML 长度 0）

## 识别为瑞数类防护的依据
- 挑战脚本：`https://tpass.guizhou.chinatax.gov.cn:8443/WbyjBgFqJiQt/ZExeYh5ovY3r.7d8b3b3.js`（混淆路径固定 hash）
- URL 上的动态 token 参数 `8i8UWOrl=`，每次刷新变化
- localStorage/sessionStorage 出现 `$_YWTU`、`_$rc`、`ded0`、`ded`、`$_YVTX`、`timestamp` 等 key
- cookie `1zIlXIQYC8aAP=<长混淆串>`
- 400 空体（`\r\n\r\n\r\n`）是瑞数拦截响应的典型特征

## 已排除的组合（不要重试）
| 尝试 | 结果 |
|---|---|
| agent-browser 默认（Playwright Chromium headless） | 表单不渲染 |
| `--headed` | 同 |
| `--executable-path` 指向真实 Google Chrome | 同 |
| `--args "--disable-blink-features=AutomationControlled"` | navigator.webdriver 仍 true（Playwright 层覆盖） |
| Playwright launch_persistent_context + add_init_script stealth（webdriver=undefined、chrome.runtime、plugins、languages、permissions.query 补丁）+ locale=zh-CN + timezone Asia/Shanghai | webdriver 已 None 仍 400 |
| headed + persistent context | 同 |

结论：防护检测点是 CDP 自动化协议本身（而非 UA/webdriver 等表层指纹），无表层 stealth 可绕。

## 正确路线
computer_use 驱动用户日常 Chrome（非 CDP 控制、真实用户 profile、与手动浏览同指纹）。
用户确认手动 Chrome 可正常渲染登录表单；其 Chrome 中已有该站登录 tab（带 OAuth 参数：
`#/login?redirect_uri=https://etax.guizhou.chinatax.gov.cn:8443/mhzx/api/mh/tpass/code&client_id=aec7eia2ab294w26aw2899f9ded277e5&response_type=code&state=...`）。

注意：computer_use `app='Chrome'` 的 vision capture 曾返回 0 元素（width/height 0），som 模式可拿到 AXWindow 与浏览器 chrome 元素；页面 web 内容元素可能需要先 focus/前置窗口或用 ax 模式。未完成验证，下次会话续查。

## 后续流程（已定未执行）
1. 登录：识别号 91520123MA6H98Y6XT + 身份证 522524197210294822 + 「企业电子税务网站」入口 + 密码（KeePass agents.kdbx 条目「贵州电子税务局网站」）→ 短信验证码 → 飞书往返
2. 待办四项：增值税及附加（含工会经费）、经营所得 A 表×2（有实名认证拦截弹窗待解）、财务报表季报（模板 Excel 上传）
3. 端到端脚本沉淀为 skill
