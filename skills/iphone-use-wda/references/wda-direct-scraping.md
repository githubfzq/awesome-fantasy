# WDA 直连 HTTP 抓取（青藤之恋实战，2026-11-01 v3 修正）

v1 的三处错误（tap 简写、截图二进制、卡片=大矩形）与 v2 的一处策略错误（dup 重试）已在实战推翻。以本文为准。

## 端点速查
| 用途 | 调用 |
| --- | --- |
| 健康 | `GET /status` → value.ready |
| 建会话 | `POST /session` `{"capabilities":{}}` → value.sessionId |
| AX 树 | `GET /source?format=json&excluded_attributes=isReady` → `{"value": 树}` |
| tap | `POST /session/{sid}/actions` W3C pointer 序列（见下） |
| 拖拽/滚动 | `POST /session/{sid}/wda/dragfromtoforduration` `{"fromX","fromY","toX","toY","duration"}` |
| 截图 | `GET /screenshot` → `{"value":"<base64>"}`，**json 解析后再 b64decode**；响应字节直接落盘 = JSON 文本假 jpg |

## 动作语法（实测可用）
```python
# tap —— 必须完整 pointer 序列；{"type":"tap"} 报 missing id / unknown error
{"actions": [{"type": "pointer", "id": "finger", "parameters": {"pointerType": "touch"},
  "actions": [{"type": "pointerMove", "duration": 0, "origin": "viewport", "x": cx, "y": cy},
              {"type": "pointerDown", "button": 0},
              {"type": "pause", "duration": 50},
              {"type": "pointerUp", "button": 0}]}]}
# swipe/scroll = /wda/dragfromtoforduration（press/wait/release 三段式已废弃不用）
# 返回上级：优先点 label="back"，其次左缘右滑 drag(3,400 → 300,400, 0.25)
```
坐标单位 iPhone points（viewport 393x852）。除 `/source /screenshot /status /session` 外都要挂 `/session/{sid}` 前缀，否则 404。

## source 树节点形状（与 pua_observe 不同！）
```json
{"type": "StaticText", "label": "喜欢", "frame": "{{143, 65}, {33, 21}}",
 "isVisible": "1", "children": [...]}
```
- 树在响应 `value` 下；`frame` 字符串须正则解析；`isVisible` 是字符串
- **isVisible='0' 节点不可丢弃**：折叠资料卡（QA/星座/MBTI/认证，y≈296）、被头图盖住的昵称都在里面；y>852 说明整页内容已在树中
- 所有卡片文本 y 突变 0/负 + vis=0 = 页面加载中/滚动惯性中，等待重读

## 无 ID 画廊的卡片识别（v2 有效方案）
v1 的"带 label 中矩形=卡片"在该 App 不成立（卡片容器无 label）。改用内容聚簇：
1. 收集小字号 StaticText（height<24、60≤y≤845、排除导航/横幅词）
2. 按 y 邻接(<32) + 左右列（x<190 左 / ≥190 右）聚簇；≥2 行文本才算完整卡片
3. 卡片签名 = 簇内 label 集合的 md5 → state.seen 去重
4. 点击点 = 簇顶部 y-60、列中心 x（左92/右290）——照片区，避开右下角功能按钮（青藤 "hi" 误点=发消息）
5. 列表页懒加载：进页先只有导航栏+ActivityIndicator，轮询等节点数长出来（>60）再识别

## 详情页结构化（ProfileContainer，Table-cell 模型）
- 页面判定：NavigationBar name 含 `MyLikeView`=列表 / `ProfileContainer`=详情
- Table 元素的每个 child = 一个 cell = 一个资料单元，**按文档顺序**展平 cell 内 label：
  - QA 问答对（用户强调的 key-value）：问题+答案在同一 cell → `{"q": labs[0], "a": labs[1]}`；问题识别=已知题干库（向往的恋爱/下一个旅行目的地/我最近爱听音乐…）OR 以 `？/?/是…` 结尾
  - 分节标题：自我介绍（cell 内其余文本 join 成一段）/我的标签/更多资料/我的认证/IP所属地/性格测试
  - IP 问答分属相邻 cell，按省份名单独提
- 头部：昵称=y140-260 宽 StaticText；年龄=y190-260 窄文本；星座=12星座名单；MBTI=正则 `^[IE][NS][FT][JP]·`；认证徽章=头像/实名/学历/婚况；亮点=「亮点」label 的下一文本
- 清理：已结构化值从 QA 答案与 sections 剔除，防重复

## 彻底采集（用户 2026-10-31 明确要求）
- **只滚一屏不够**：QA/相册在更深处。循环 滚动→读树签名，连续 2 轮不变判到底（上限 14 屏）
- **每屏截图**：照片墙/大图无 AX 文本，截图是唯一留档方式（`NNNN_uX_s{n}.jpg`）
- 滚动新增文本并入「滚动补充」节
- 「动态」tab：点 tab（label="动态" 的 Button）→ 同法滚屏采文本 → 点回「关于我」，完成才算了采完一人

## 长任务编排（采集器/落盘器分离）
- 采集器：每人 `profiles/NNNN_uX.json`（结构化字段+qa+moments+shots 列表）+ 多截图；state.json `{order, seen[], dupkeys[], target, bottom, fails}` tmp+os.replace 原子写
- 落盘器：cron 每 30 分钟增量消费 profiles/，`notes_written.json` 记已写 idx；osascript argv 传 title+body（HTML：h1/h3/p/b/br），文件夹须已存在
- batch.sh：每批 25 人；批前 curl /status 探活，断链重试 10 次退出；达标或 bottom 退出
- 断点恢复：重插线+解锁 → pua_setup start → pua_ready → 重跑脚本自动续；「我喜欢的」总数与已采数核对防跳号

## 防重复（v3 最终策略，用户 2026-11-01 纠正后）
v2 的"重复时回列表重试同一张卡一次"是**错误方案**：用户看到同一人主页被反复点开。正确做法：
1. dupkey = 昵称 || 首段介绍 || 基础行（默认昵称撞名靠介绍+年龄区分，实测同校默认昵称"中国科学院大学"多个不同人并存）
2. **dup 命中立即永久放弃该卡**：签名同时写入 state.seen 和 state.skip_sigs，删除本轮半成品文件（glob `NNNN_uX*` 全部后缀），绝不再点
3. **dupkey 集跨会话持久**：collect() 启动时 load_dupkeys() 从 profiles/*.json 全量重建历史特征集，不只靠 state.json 的 dupkeys 列表（state 可能被清、profile 是事实源）
4. 幂等性：dup 跳过不计入 done 计数，同卡后续扫屏因 skip_sigs 排除不再出现

## 跨天 resume（有序跳过）
列表按时间倒序、新人插队首时的增量采集协议：
- `build_expected_tail(state)`: 昨日 order 的 labels frozenset 序列
- 每屏：当前卡按 (info_y, tap_x) 排序 → 与 exp[exp_pos:] 顺序比对 → 相等则记 skip_sigs 且 exp_pos++；不等则是插入的新人 → 采集
- resume 结束条件：exp_pos >= len(exp)，此后纯靠 seen/skip_sigs 去重
- **别在 resume 阶段判"到底"**：连续 DIFF 是新人插入的正常形态（实测一次插入几百人，核对了 8 屏仍未见到昨日第一张卡）；empty_rounds 判到底只对 resume 完成后的纯采集阶段生效
- **resume 空转硬上限**：顺序核对长期无推进（exp_pos 卡 0）时设 10 轮上限强制切纯采集——新人太多时顺序核对无意义，纯靠 Jev 批量查重+dupkey 就够（v3 默认 resume=False，验证了这一判断）

## AX frame 归零（滚动后识别全灭的根因，2026-11-01 深挖）

连续滚动 2-3 屏后，snapshot 里 StaticText 的 frame 大面积变 `{{0,0},{0,0}}` 且节点丢失——**截图视觉完全正常**（8 张卡都在），纯 AX 问题。已排除的恢复手段：等 5-20 秒、微小回弹拖拽、30px 小幅滚动、降速 3.2s/屏——**全部无效**。唯一可靠恢复：back 退列表重进（回顶部）。

- **诊断阈值要防误判**：状态栏/导航栏零坐标是常态。判失效用 `zero_cnt > ok_cnt and zero_cnt >= 4`，不是绝对数。阈值过松会陷入「重进→回顶→重滚→再失效」循环，45 分钟只推进 1 人（实测）
- **懒加载 ≠ 无卡**：正常坐标文本 2-5 条 = 半屏白块懒加载中，半屏慢滚 (196,620→196,460, 0.5s) + sleep 3s 触发加载，不是滚动到底
- **假 bottom 事故**：frame 失效空转累积 empty_rounds 到 6 会误判「列表到底」收工（实测 45/3000 触发一次）。bottom 判定只在正常坐标轮累积，失效/懒加载轮必须重置 empty_rounds；且 bottom 标志不持久化——load_state 时强制复位，每次启动重新判定
- **DOM 序虚拟展开是陷阱**：frame 全零时曾尝试按 DOM 顺序给零坐标文本配对赋虚拟坐标——实测 DOM 顺序与视觉顺序不一致，会**点错卡片**。零坐标屏只配等/重进，不配点击
- 未落地的终极方案：Jev Box 从截图定位卡片（绕开 AX），图片请求需直连 typesafe.ai（见 jev-magpie-gateway.md 的网关限制节）

## 任务现场
- 引擎/状态：`~/.hermes/cache/qingteng/`（collect.py v3, state.json, profiles/, notes_writer.py, batch.sh, restore_list.py, test_resume.py）
- APP 青藤之恋 com.wepie.ivylove；「我喜欢的」9600+，目标 3000；v1 数据（#1-25）缺 QA 字段不补采，v3 从 #26 起
- 目标备忘录文件夹「青藤之恋-我喜欢的」；恢复命令 `cd ~/.hermes/cache/qingteng && FAILENT=0 bash batch.sh`
- 已知残留：wait_profile 进入判定在返回列表后误判（同签名+back 存在），靠 ensure_list_page 前置校验兜底；日期跨天后 vis=0 头部簇 y≈296 的隐藏卡在部分用户树上缺失，QA 以 Table cell 解析为准
- 效率实测：新人路径 35-40s/人（QA+深滚动+动态）；frame 失效重进循环期间效率崩到 45 分钟 1 人——AX 失真频率与滚动总距离正相关，未根治前按「采 1-3 人→失效→重进」预期节奏排产
