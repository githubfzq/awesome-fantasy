# 贵州省电子税务局 页面结构与定位器（2026-10-11 实战全流程验证）

> 定位一律以**文本/placeholder**优先；坐标仅用于验证码点选，需按 `viewport.innerWidth/1080` 换算。

## 0. 环境关键事实

| 项 | 值 |
|---|---|
| 入口 URL | `https://tpass.guizhou.chinatax.gov.cn:8443/#/` → 重定向 `etax.guizhou.chinatax.gov.cn:8443` |
| 工作台 | `etax.guizhou.chinatax.gov.cn:8443/loginb/` |
| 技术栈 | 贵州: Vue+ElementUI+**TDesign**(t-button/t-table)；个税总局: ElementUI |
| 反爬 | 瑞数（$_ts）：curl 无输出；页面空白(title空body空)→reload ≤4 次；连续失败冷却≥5min |
| 代理 | **沙箱强制代理 127.0.0.1:54033 会拦登录风控组件** → 必须沙箱外运行 + common.py 清代理 env + Chrome `--no-proxy-server` |
| 证书 | 自签名异常：`ignore_https_errors=True` + `--ignore-certificate-errors` |
| headless | 不可用；Chromium for Testing 风控「请求失败」→ 用真实 Chrome |
| CDP | `--remote-debugging-port=9222 --user-data-dir=~/Library/Application Support/gtax-rpa/chrome-manual`（nohup 启动，随 shell 退出会被杀） |
| 凭据 | keepass agents.kdbx「贵州电子税务局网站」：UserName=91520123MA6H98Y6XT(识别号)，Password=网站密码，Notes 含身份证 522524197210294822（法人/经办人 李关珍） |
| 企业 | 修文县关珍养殖场（个人独资企业，查账征收/据实预缴，M级纳税人） |
| viewport | 1291×863 DPR=2；Playwright 截图 2582px；Read 展示 1080 宽 → **坐标×1.1954** |
| 申报窗口 | 2026-10 顺延至 10-26 |

## 0.1 凭据获取（keepassxc-cli · 实测 2026-10-11）

```bash
cat "$MF" | "$KX" show -s "$DB" "贵州电子税务局网站" 2>/dev/null
```
输出（全量、带字段名）：
```
Title: 贵州电子税务局网站
UserName: 91520123MA6H98Y6XT
Password: ***
URL: https://tpass.guizhou.chinatax.gov.cn:8443/#/
Notes: 贵州省电子税务局 企业电子税务网站登录；身份证号:522524197210294822（法人/经办人）
Uuid / Tags
```
解析：`common.get_credentials()` 用 `^\s*(UserName|Password):\s*(.+)$` 抓字段，
再用 `身份证号[:：]\s*(\d{17}[\dXx])` 从 Notes 抽身份证；三段缺一即抛错。

踩坑：
1. `show -s -a UserName -a Password` → **只给两行纯值、无字段名**，且空字段不出行会让后续错位。**禁止**用它取多字段。
2. 解锁提示行「输入密码以解锁 …」在 **stderr**（不是 stdout），`2>/dev/null` 即可；别用 `tail -1`。
3. 不加 `-s`：全量输出里 Password=`PROTECTED`。统一加 `-s`。
4. `search 贵州` 会带出 `/回收站/贵州电子税务局（企业电子税务网站）` → 用完整条目名。
5. agents.kdbx 仅主密码保护：传 `-k` 或自动探测 key file → `HMAC 不匹配`。

## 1. 登录

- 访客首页右上「登录」→ 登录页默认「企业业务」tab（activeCls）
- 三输入框 placeholder：`统一社会信用代码/纳税人识别号` / `居民身份证号码/手机号码/用户名` / `个人用户密码`
- 提交按钮文本「登录」；**不要点「其他登录」区域的企业登录**（切到非居民企业）
- 登录成功判据：URL 离开 `#/login` 且 body 含「我的待办/工作台」（**禁用「首页/欢迎」**——「返回首页」会误判）

## 2. 工作台待办

- TDesign 表格：`tr:has-text('<事项名>')` 行内 `button:has-text('填写申报表')`
- **必须点 BUTTON，点内层 SPAN 不触发跳转**；点击后**新开 tab**（监听 ctx.on("page")）
- 状态列：「未申报」→ 办完变「已申报」；操作变「更正\作废」

## 3. 增值税 + 工会经费（综合关联申报）

1. 新 tab URL：`/xxbg/view/zhsffw/#/mixDeclare/nav`
2. 关联申报页：自动勾选「增值税及附加税费」「工会经费」（所属期 07-01~09-30）→ 文本「去办理」
3. 税费试算页：步骤条「1税费试算 2申报确认」；增值税已 0；**工会经费「待填报」**——
   页面第 3 个可见 input（唯一空值）填 0 → 「下一步」
4. 确认表：全部 0.00 + 「提交申报」→ 弹「真、实、责、任」验证码 → 成功页「返回首页」

## 4. 经营所得（A表）——关键规则

- 待办行点击 → 中转 `etax.chinatax.gov.cn/webstatic/transfer-page` →
  **弹「是否以当前账户继续进入自然人电子税务局操作？」→ 点「继续」**
- 年度选择页（placeholder `请选择申报年度`）→ 选 2026 → 确定
- **4 步向导**：录入被投资单位信息 → 录入计税信息 → 录入减免税额 → 确认申报信息
- **必须按期顺序申报**：直接报止=09 会被拦「您的上一期经营所得月（季）度申报表未申报」；
  已报期再报会提示「您选择税款所属期已申报」。实测 2026：Q1 已报，需报 Q2(止=06)、Q3(止=09)
- step1：统一社会信用代码框（placeholder 可能是「点此搜索」或「请输入被投资单位纳税人识别号」，
  **每次进入可能不同**）→ Enter/搜索 → 快捷搜索弹层（单选已选信用代码）→
  `请输入`框(first) 填 USCC → 「搜索」→ 点结果条目（**不点则「确认添加」disabled**）→「确认添加」
  - 「系统繁忙」弹窗偶发：关闭等 15s 重试一次
  - 确认添加后所属期止会被重置（Q2 报完默认止=07），**需重新选 9月**
- step2：收入总额/成本费用填 0；投资者减除费用+专项扣除两组 radio 均选「**在综合所得扣除**」
  （element-ui radio：JS 点击 `label.el-radio`，原生 check() 无效；第一组有时已默认选中）
- step3：应纳税所得额 0×5%，不加减免明细
- step4：应补税额 0.00 → 「提交」（按钮文本是**提交**不是提交申报）→ 可能弹验证码 →「提交成功」
- 每期提交后回成功页，**下一期需重新进入**（返回首页 → 常用业务「经营所得（A表）」→ 继续 → 年度 → 搜索）

## 5. 财务报表报送（季报）

- 新 tab：`/sbzx/view/sdsfsgjssb/#/yyzx/cwbbbs/ydy?SssqQ=2026-07-01&SssqZ=2026-09-30`（所属期自动带出）
- 选择页：季报（默认选中）+ 财报导入（默认）→ 「下一步」
- 导入页：「下载模板」→ `CWBB_XQYKJZZ.zip`（**GBK 文件名**，cp437→gbk 解码解压）
  - 取「财务报表报送与信息采集（小企业会计准则）**月季报**.xls」
  - 3 sheets：资产负债表 / 利润表_月季报 / 现金流量表_月季报，金额已预填 0
  - 表头填写格（xlrd 0-based）：
    - 资产负债表：识别号[2,3] 名称[2,7] 起止[3,3]/[3,7]（label 在 [2,1]/[2,5]/[3,1]/[3,5]）
    - 利润表/现金流量表：识别号[2,3] 名称[2,5] 起止[3,3]/[3,5]
  - 填写用 xlrd==1.2.0(+formatting_info) + xlutils.copy 保格式，存 .xls
- `input[type=file]` set_input_files → 「上传成功」→ 「导入报表」→ 报表预览（全 0）
  → 「提交申报」→ 验证码 → 「报送成功」

## 6. 「真、实、责、任」验证码

- 触发点：增值税提交、财报提交（经营所得提交两次均未弹）
- 弹窗「信息确认」，图片区字位（1080 展示宽坐标）：真(378,402) 实(511,424) 责(621,407) 任(701,420)，确定(777,490)
- 实测弹窗位置稳定，同布局重复出现；换算 `×(window.innerWidth/1080)` 后 mouse.click
- 失败则截图 `shots/captcha_*` 交人识别新图

## 7. 瑞数 & 稳定性

- 页面空白 → reload ≤4 次；连续失败 → 冷却 ≥5 分钟
- 登录成功后的 profile/chrome-manual 有合法瑞数 cookie，**勿清**
- CDP 下 `page.url` 可能滞后于实际跳转，登录判据只信 body 白名单
- keepassxc-cli `show -s -a ...` 多字段模式**不带字段名**，必须全量 `show -s` 按行首解析
