---
name: iphone-use-wda
description: 用 iPhone-use MCP 经 USB 操作真实 iPhone：装签名 WDA、排障、就绪验证。
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [iOS, automation, WDA, MCP, USB]
---

# iPhone-use：USB 操作真实 iPhone

基于 https://github.com/zhongerxin/iPhone-use（源码装在 ~/Public/Projects/iPhone-use），MCP 服务已注册到 Hermes config.yaml（`mcp_servers.iphone_use`，pyenv python3.10 运行 `server/iphone_use.py`）。工具名前缀 `pua_`。

## 前置依赖（一次性）

- macOS + 完整 Xcode（仅 CLT 不够）+ USB 数据线 iPhone（能传数据的线）
- Python 3.9+（本机用 pyenv python3.10，系统 python3 缺 mcp 包）
- Node 20+（USB 转发 forward.mjs 用）
- `pip install mcp`（装到运行 MCP 服务的那个解释器）

## 配置流程（configure → fetch → build → start）

通过 MCP 调 `pua_setup`，或直接 CLI：`python3.10 server/iphone_use.py --doctor`（JSON 诊断，含设备/签名/服务状态）。

1. `pua_setup(action='configure', udid=..., team_id=..., bundle_id='com.<user>.wda.runner')`
   - **Team ID 查法**：`plutil -p ~/Library/Preferences/com.apple.dt.Xcode.plist | grep -A3 teamID`。证书 CN 括号里的字符串**不是** Team ID（CN 是 `Apple Development: email (TEAMID)`，但真实 Team ID 在 subject OU 字段/Xcode Accounts 记录里，两者可能不同——本机 CN 括号是 ARNHN3RZNS 而真实 Team 是 2N697H3F5J，用 CN 括号会 build 失败）
2. fetch WDA 源码：默认走 HTTPS 克隆 GitHub。**HTTPS 不通的机器改用 SSH 手动克隆**到 `~/.local/share/iphone-use/runtime/WebDriverAgent`（checkout 到项目 pin 的 commit），然后跳过 fetch 直接 build
3. `pua_setup(action='build')` — 后台任务，轮询 `action='status', job_id=...`
4. `pua_setup(action='start', wait_seconds=20)` — 构建安装到手机并启动服务
5. 验证：`pua_ready` 返回 ready=true 后才能调手机工具

## 需要用户在手机上手动做的事（不能代办）

1. 信任此电脑（首次插线弹窗）
2. 设置 → 隐私与安全性 → 开发者模式：开启（需重启手机生效）
3. 设置 → 通用 → VPN与设备管理 → 信任开发者 App 证书（首次装 WDA 后）
4. **设置 → 开发者 → Enable UI Automation：开启**（iOS 17+ 必需，不开则 runner 启动即退出）
5. Apple ID 登录 Xcode（Settings → Accounts）——签名前必须
6. 启动 WDA 期间手机保持解锁亮屏（锁屏时 xcodebuild 卡在 "Unlock ... to Continue" preflight 等待，日志里可见）

## 排障速查

| 症状 | 原因/解法 |
| --- | --- |
| build: No Accounts | Xcode 未登录 Apple ID，用户手动登录 |
| build: No profiles for xxx.xctrunner | Team ID 错（见上面查法） |
| start: USB connect failed (no device) | 线不传数据/没插直/未信任；`xcrun devicectl list devices` 看 connection_state，paired≠USB connected |
| start: Developer App Certificate is not trusted | 手机 VPN与设备管理里信任证书 |
| start: Unlock iPhone to Continue | 手机锁屏，解锁即继续（xcodebuild 会一直等） |
| start: exit code 74 (EX_TEMPFAIL) | 见下节 |
| Local forward port occupied | 18100 被 forward.mjs 占用且 WDA 未 ready：先查 `lsof -iTCP:18100`，通常是上一次 start 任务的 xcodebuild 还活着，等它或 stop owned job，勿杀无关进程 |
| 长任务中途 USB 掉线（18100 停止监听、日志刷 "Could not find the expected device"） | 手机端 runner 已死；重插数据线+解锁后 `pua_setup(action='start')` 重启一次，`pua_ready` 验证后从 state.json 断点续采，勿盲目重放已完成动作 |
| WDA 服务正常但 /source 节点极少/为空 | 手机不在目标 APP 或 APP 刚被拉起还在加载。先 launch_app + 轮询等节点数涨起来（个位数→几十），再谈页面识别 |
| devicectl 显示 connected 但 system_profiler SPUSBDataType 无 iPhone | 设备走的是 Wi-Fi 配对连接，USB 数据层不通。WDA runner 启动和长任务必须真 USB 线；用户重插线后重新 start |

## exit code 74 排查路径（2026-10-30 已解决 ✅）

**根因与修复**：iOS 17+ 的「设置 → 开发者 → Enable UI Automation」开关，打开后**必须重启手机才真正生效**（与开发者模式同款行为）。重启后 runner 一次启动成功。设备日志里的 `kernel(Sandbox) applekeystored deny(1) file-write-xattr` 拒绝正是开关未生效的表象，不是签名问题。

排查步骤（其他机器遇到 exit 74 时按此路径走）：
1. 先确认四件套：开发者模式开、UI Automation 开、证书已信任、profile 未过期（`security cms -D -i <mobileprovision> | grep Expiration`）
2. **以上都确认后重启手机**（解除锁屏状态下启动 WDA）
3. 仍失败才深挖：Mac 上 `brew install libimobiledevice` → `idevicesyslog > /tmp/syslog.txt`（后台）→ 触发 start → grep 设备日志
4. 已排除的干扰项：证书过期、设备不在 ProvisionedDevices、bundle ID 不匹配、锁屏、未信任、Team ID 错
5. xcresult 挖矿基本无用：`xcrun xcresulttool get object --legacy --path <xcresult> --format json` 只有一句 exit 74；设备日志才是正路

## 操作手机的标准循环

1. `pua_setup(action='status')` 确认 service ready
2. `pua_apps` **必须带 query 参数**：`pua_apps(query='牵手', source='installed')` —— 无参会报 Missing required fields；拿 bundle ID 后 `pua_launch_app(bundle_id=...)`
3. `pua_launch_app` 报 phone_locked → 让用户解锁手机再重试
4. `pua_observe`（AX树+截图）→ `pua_find`/`pua_tap`/`pua_swipe`/`pua_type_text` 操作
5. 列表类页面用 `pua_collect_list` 收集去重，控件定位失败时看截图改坐标点击
6. 实时画面：`pua_screen`；截图回退：`pua_screenshot`
7. Hermes 内工具名带前缀：`mcp__iphone_use__pua_*`（session 重启后 MCP 工具自动加载）

## 批量采集：直连 WDA HTTP（绕过 MCP，快一个量级）
几百上千条级别的逐项抓取（社交 APP 喜欢/好友列表 → 逐个进详情 → 写出）走 MCP 太慢：用 python urllib 直连 `http://localhost:18100` 自己跑循环。API 细节与实战坑：`references/wda-direct-scraping.md`（含 AX 树 cell 解析、跨天有序 resume、防重复、WDA 重启后先回 APP 再操作的教训）。要点：
- 所有非全局端点（actions、wda/*）必须挂 `/session/{sid}` 前缀；`POST /session` 建会话拿 sessionId
- `/source?format=json` 返回 `{"value": 树}`；坐标在 `frame` **字符串** `"{{x, y}, {w, h}}"` 里，须正则解析——与 pua_observe 输出的 rect 数组格式不同，拿 MCP 输出形状去套原始 source 会一无所获（0 卡片 0 节点的典型症状）
- **tap 必须用 W3C pointer 序列**（pointerMove→pointerDown→pause→pointerUp，带 id 和 pointerType:"touch"）；`{"type":"tap"}` 简写报 "mandatory action id field missing"。拖拽/滚动走 `POST /wda/dragfromtoforduration`
- **截图 `GET /screenshot` 返回 `{"value":"<base64>"}`**，必须 json 解析后再 base64 解码；直接把响应字节写文件会得到 JSON 文本假 .jpg（file 命令一眼识别）
- **vis=0 ≠ 拿不到数据**：折叠资料卡、整页下方内容（y 超屏）的 label 都在树里；详情页内容区是 Table，每个 child cell 是一个语义单元（一组 QA 的问和答同 cell），按 cell 解析天然得到 key-value。读取型任务不要按可见性过滤
- 页面过渡判定：对整树 label 序列做 md5 签名，tap 后轮询签名变化；列表页加载慢（先只有导航栏+ActivityIndicator，节点从个位数涨起来），进页后要轮询等节点数增长，别固定 sleep
- 长任务必须断点续采：state.json 记 order/seen 签名/dupkeys/fails，每条原子写回；连续多轮滚动无新卡片才判到底
- 卡片无业务 ID 时：小字号信息行（height<24）按 y 邻接(<32)+左右列(x<190)聚簇成卡，簇内 label 集合 md5 = 卡片签名；点击点取卡片照片区，避开角落功能按钮（青藤右下角 "hi" 误点会发消息）
- 详情页防重复（用户 2026-11-01 纠正后的最终策略）：昵称+首段文本+基础行 md5 作 dupkey，**命中立即永久跳过，绝不重试二次进入**（旧方案"重试一次再放弃"会让用户看到重复点开同一人主页）。dup 命中时把卡片签名同时写入 state.seen 和 skip_sigs；dupkey 比对集须跨会话——启动时从全部历史 profiles JSON 载入（load_dupkeys），不能只用本次会话内存
- 滚动漂移防护（用户 2026-11-01 纠正"卡在同一个人主页"后的修复）：处理每张卡前**重取当前屏**识别簇，确认目标卡签名仍在屏上并改用**新坐标**点击；用过期坐标盲点是"误入随机详情页/点错人"的根源。卡已滚出屏幕就跳过本轮，别硬点
- resume 空转兜底：「无卡可核→继续滚动核对」的降级必须设硬上限（如 10 轮），超限强制切纯采集模式。否则一次滚动误触打开详情页后，主循环会在详情页里**永久空转**（识别不出列表卡→fresh 永远空→无限滚动恢复不了），用户侧表现为"卡在同一个人的主页既不退出也不翻页"。恢复手段：pkill 采集进程 → back_to_list/restore → 重启批处理
- Jev 决策模型免进主页查重（Magpie 网关已配 typesafe）：一屏全部候选卡**一次 systemone 请求**批量判重（比逐卡 Noul 快 6 倍），精确集合命中短路不发请求，置信度门槛 0.6，连续失败自动停用不拖慢主流程。API 与坑见 `references/jev-magpie-gateway.md`，可直接跑的客户端在 `scripts/jev_client.py`、`scripts/jev_batch.py`
- 返回上级页优先点 label="back" 按钮，失败再左缘右滑 do_drag(3,400,300,400,0.25)；每轮 tap 前先确认还在列表页（树里搜 MyLikeView 类导航名），不在就先恢复
- **AX frame 归零缓存失效（2026-11-01 卡死根因，与前条不同）**：连续滚动 2-3 屏后 snapshot 里全部 StaticText frame 变 `{{0,0},{0,0}}`——截图视觉上卡片完全正常，但无法定位点击。实测：等 5-20 秒**不恢复**、微小回弹/30px 滚动**无效**；DOM 顺序≠视觉顺序，禁止按 DOM 序虚拟展开坐标（会点错卡）。唯一可靠恢复：**back 退列表重进**（代价：回到顶部，靠签名去重+Jev 快速跳回）。对策：滚动节奏 ≥3s/屏、识别卡数<2 先补半屏慢滚触发懒加载（正常坐标文本 2-5 条=懒加载中，不是无卡）、判定失效看「零坐标是否显著多于正常坐标文本」（状态栏/导航零坐标是常态，只看绝对数会误判）、重进后 bottom/空转计数器复位——否则误判"列表到底"提前收工
- **WDA 重启后先回 APP**：重启 WDA/USB 掉线重连后，手机常停在桌面或输入法页；先 launch_app 从树里确认目标 APP（TabBar/VC 名），再进目标页面，否则列表识别会作用在错误界面上得出垃圾结果（实测 restore 跑在 SpringBoard 上把状态栏当卡片）
- **深度采集**：只滚一屏会漏照片墙/全部 QA/动态 tab——滚动到树签名连续 2 轮稳定（上限 14 屏），每屏截图；再切「动态」类 tab 采完切回。慢 IO（写备忘录等）独立脚本增量跑，别内联进采集循环

## 跨天/增量 resume（2026-11-01 实战新增）
社交列表按时间从新到旧排，隔天会有新人插在队首。**有序跳过机制**：
- 启动时把 state.order 里昨日每张卡的 labels 集合构建成期望序列（frozenset 列表）
- resume 阶段逐屏把当前卡片按 (info_y, tap_x) 排序后与序列**顺序比对**：labels 集合相等 = 旧卡，签名记入 skip_sigs 直接跳过（不点开）；不等 = 插入的新人，采集
- 匹配位置 exp_pos 只前进不回退；序列全部核对完切换纯采集模式
- 实测注意：新人可能一次插入几百个，resume 阶段会长时间处于"全是 DIFF"状态——这是正常的，DIFF 卡就是待采新人，别把"匹配不上"当故障
- 彻底防重的三层：卡片签名去重（seen）→ 详情 dupkey 比对（跨会话历史集）→ 默认昵称撞名时靠介绍+基础行区分（同校"中国科学院大学"多个不同人）
- **"列表到底"防误判**：bottom=True 必须只在「正常坐标识别、连续 6 轮无新卡」时设置；frame 失效/懒加载轮应重置 empty_rounds 而不是累积——否则 AX 缓存失效的空转会被当成"到底了"提前收工（实测 45/3000 时假 bottom 一次，屏幕上明明还有卡）

## 本机现状（2026-10-30 01:38）

- 全链路已通：MCP 注册 ✅ → WDA 构建 ✅ → 证书信任 ✅ → UI 自动化 ✅ → **pua_ready=true ✅**
- 关键经验：UI Automation 开关 + 重启手机 = exit 74 的完整解
- 手机锁屏会导致两类报错：xcodebuild 卡 "Unlock iPhone to Continue"、pua_launch_app 返回 phone_locked —— 操作前先让用户解锁
- 当前任务：打开「牵手」(com.yaymedialabs.love) 抓最近 15 条对话列表（用户已确认 APP 名为牵手，非千牛）
- 用户的 iPhone 名带 Unicode 易混字符（范祖权 vs 范祖権字形），grep 日志时注意
