---
name: china-tax-website-rpa
description: 电子税务局网站RPA：登录、飞书短信验证码往返、季度申报。瑞数反爬须用真实Chrome驱动。
---

# 电子税务局网站 RPA（贵州站实测）

## 反爬现实（先读，决定技术路线）

贵州电子税务局 `https://tpass.guizhou.chinatax.gov.cn:8443/#/` 有**瑞数类 JS 动态防护**（特征：挑战脚本 `WbyjBgFqJiQt/*.js`、URL 随机 token `8i8UWOrl=`、localStorage 里 `$_YWTU`/`_$rc`/`ded` 等行为采集 key）。

实测结论（2026-10）：
- agent-browser / Playwright（headless、headed、真实 Chrome executable、`--disable-blink-features=AutomationControlled`、stealth 注入 navigator.webdriver=undefined）**全部被识别**：页面壳（三个业务标签）能渲染但登录表单永不挂载，业务 API（如 `/sys-api/v1.0/auth/oauth2/getPublicKey`）全 400（响应体 `\r\n\r\n\r\n` 是瑞数拦截页特征）。
- 防护识别的是 CDP 自动化本身，不是 UA/指纹参数。**不要再在这条路上试新组合。**
- 可行路线：**computer_use 后台驱动用户日常的真实 Chrome**（与手动浏览同指纹）。ax 模式可拿页面结构，vision 截图判读文字。
- 登录态活在用户 Chrome profile 中，"登录一次后免登录"依赖用户 Chrome 自身的会话保持。

详细排查记录（瑞数特征、已排除组合、computer_use 未验证点）见 `references/guizhou-2026-10-probe.md`。

## 登录流程

1. URL：`https://tpass.guizhou.chinatax.gov.cn:8443/#/`，自动跳 `#/login`
2. 三个标签：企业业务（默认选中）/ 自然人业务 / 代理业务
3. 企业登录要素：扣缴义务人识别号 + 身份证号 + 选「企业电子税务网站」入口 + 密码
4. 凭据从 KeePass 取（agents.kdbx 条目「贵州电子税务局网站」：UserName=识别号，Notes 含身份证号）；kp_get.py 只返回 username/password，身份证号需直接 keepassxc-cli `show -s -a Notes` 提取

## 短信验证码经飞书往返

双向通道已验证（bot 可发可读）：
- 发送：`echo "请回复短信验证码" | hermes send --to feishu` 或直接调飞书 API（tenant_access_token 见 `~/.hermes/.env` 的 FEISHU_APP_ID/SECRET）
- 接收：GET `/open-apis/im/v1/messages?container_id_type=chat&container_id=YOUR_FEISHU_CHAT_ID&sort_type=ByCreateTimeDesc`，按 sender 的 id_type 区分 bot（app_id，跳过）与用户（open_id，提取数字验证码），轮询至出现新消息

## 申报待办清单（季度申报，每 3 个月过后的下一月 15 日前）

业务都在「我的待办」里：

1. **增值税及附加税费申报（小规模纳税人）**：填写申报表 → 综合关联申报页自动勾选「增值税及附加税费」+「工会经费」（工会经费与增值税统一办理）→ 去办理 → 确认合计 0 元 → 应税项填 0 → 下一步 → 确认表 → 提交申报 → 申报成功 → 返回首页
2. **个人所得税经营所得（A表）×2**：各点填写申报表 → 录入被投资单位信息（统一社会信用代码填扣缴义务人识别号搜索）→ 所属期止选季度最后一个月 → 下一步计税信息 → 「是否均在综合所得中扣除」选是 → 下一步减免税额 → 下一步确认申报信息（确认全 0）→ 提交
   - **已知拦截**：点填写申报表时弹「您的电子税务局账户实名认证登录未满足要求，请您返回原系统进行相关操作」→ 需额外实名认证操作，待解决
3. **财务报表报送**：填写申报表 → 报送期间选「季报」→ 下一步财报导入 → 首次需下载模板 → Excel 填纳税人识别号、纳税人信息、所属期起止 → 上传导入 → 提交申报 → 报送成功

## 与月度申报（扣缴端）的关系

月度工资薪金申报走 Parallels Windows VM 里的客户端（见 wage-withholding-rpa 技能），与本技能的**网站**季度申报是两条独立通道。
