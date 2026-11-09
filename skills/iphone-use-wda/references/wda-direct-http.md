# WDA HTTP 直连引擎：API 细节与坑（2026-10-31 青藤之恋批量采集实战验证）

## 会话与端点

- `POST /session` body `{"capabilities":{}}` → `value.sessionId`（WDA 16.14.0）。
- 需要会话前缀的端点：`/actions`、`/wda/dragfromtoforduration` 等；`/source`、`/screenshot`、`/status`、`/session` 可裸访问。
- 端点拼错只报 `Unhandled endpoint`，不会提示缺 session 前缀——404 时先查 URL 再查参数。

## 手势

- 点击：`POST /session/{sid}/actions`，W3C pointer 语法，`id` 字段必填（缺了报 "mandatory action id field is missing"）：

```json
{"actions":[{"type":"pointer","id":"finger","parameters":{"pointerType":"touch"},
  "actions":[{"type":"pointerMove","duration":0,"origin":"viewport","x":76,"y":252},
             {"type":"pointerDown","button":0},{"type":"pause","duration":50},
             {"type":"pointerUp","button":0}]}]}
```

- 拖拽/滚动：`POST /session/{sid}/wda/dragfromtoforduration`，`{"fromX":196,"fromY":640,"toX":196,"toY":206,"duration":0.4}`（point 坐标，fromY>toY 即向上滚）。
- `wda/tap/{x}/{y}` 端点在此版本不可用（unknown command），别照旧文档用。

## AX 树（/source?format=json）

- 坐标在 `frame` 字符串里：`"{{x, y}, {w, h}}"`，正则解析；部分节点另有 `rect` 对象——两者都试（node_rect fallback）。
- **isVisible='0' ≠ 数据不可得**：详情页折叠资料卡（IP/MBTI/认证/问答对）整簇 vis=0 但 label 齐全。读取型任务不要按可见性过滤，一次 dump 常含整页内容。
- y 超出屏幕高度（如 y=1200）的节点 = 未滚动到的下方内容，同样在树里。
- 详情页内容区是 `Table` 节点，每个 child = 一个 cell：自我介绍 cell、标签 cell、每组问答一个 cell（Q 和 A 在同一子树，文档顺序 Q 在前）。按 cell 解析天然得到 key-value，比按屏幕 y 坐标猜分节靠谱得多。
- 页面标识看导航栏 `name` 的 VC 名（如 `ivylove.MyLikeView`），比猜 label 可靠。
- 列表页画廊卡片无可读 label（昵称是图片）。去重用「卡片底部小文本行聚簇 → 标签集合哈希」做签名，不要用坐标（滚动后坐标变）。
- 加载中的树缩成 1 个节点；列表滚动惯性中所有文本 y=0/vis=0——拿到异常树先 sleep 1~2s 重读两三次，别急着改逻辑或点东西。

## 截图

- `GET /screenshot` 返回 `{"value":"<base64>"}`，必须 `base64.b64decode` 再写盘，否则得到几 MB 的 ASCII 文本（file 命令一看便知）。

## 长任务架构（3000 人级采集验证）

- **state.json 原子写**：tmp + os.replace。内容：order（已采序列+每卡标签）、seen（卡片签名）、dupkeys（昵称+介绍指纹）、skip_sigs（resume 跳过记录）。
- **batch.sh 包装**：循环 `collect.py collect 25`，每轮前 curl /status 健康检查；失败等 30s 重试，连续 10 次失败退出等人工。USB 掉线、手机锁屏、WDA 进程死，表现都是 18100 拒连。
- **有序 resume（跨天增量）**：列表按时间新→旧，新条目插顶部。存昨日采集序列（每卡标签 frozenset），重跑逐屏顺序核对：连续匹配的旧卡记 skip_sigs 跳过（不点开，~2s/屏），遇到不匹配即新人、进详情采集（~40s/人，含深滚动）。新增几十人时前段全是采、滚到旧区后自动全跳。
- **慢 IO 解耦**：osascript 写 Apple Notes 每条数秒，独立脚本增量写（自带 notes_written.json 进度），cron 或循环驱动，绝不内联在采集循环里。
- **防重复双保险**：列表签名去重 + 详情页内容指纹去重；指纹撞车时先回列表重试同一张卡一次（可能点错位），仍重复才放弃并删残file。
- **进入详情校验**：tap 后轮询「树签名变化 + VC 名变化」；失败 back 恢复、跳过该卡，绝不在未知页面上继续点击。
- **列表页恢复器 restore_list.py**：连续 back 到 TabBar 出现 → 重新点入口 → 轮询等卡片渲染（≥2 簇）。任何树异常/点错页/回不来，都先跑它。
- **深度采集用户纠正（2026-10-31）**：只滚一屏不够——照片墙、全部 QA、动态 tab 都在更深处。正确做法：滚动到树签名连续 2 轮稳定（最多 14 屏），每屏截图；新增文本并入「滚动补充」；再切「动态」tab 采完切回「关于我」。

## 实测速度与预期

深滚动详情页（14屏+动态tab+全屏截图）约 40s/人；纯列表跳过约 2s/屏。3000 人约 20-30 小时，按天分段跑，state 断点续采。
