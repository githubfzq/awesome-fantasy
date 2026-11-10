# WDA HTTP 直连引擎（绕过 MCP 逐条调用）

批量采集/长任务时，直连 WDA HTTP API 比 MCP `pua_*` 逐条调用快一个数量级。本机运行时：`http://localhost:18100`（forward.mjs 转发到设备 8100）。实战项目：`~/.hermes/cache/qingteng/`（青藤之恋用户采集，collect.py 引擎）。

## 端点速查

| 操作 | 端点 | 要点 |
| --- | --- | --- |
| 会话 | `POST /session` `{"capabilities":{}}` | **手势类端点必须挂 session**，否则 404 |
| 树 | `GET /source?format=json&excluded_attributes=isReady` | 无需 session 前缀 |
| 截图 | `GET /screenshot` | 返回 **JSON，`value` 是 base64**，必须解码后再写文件 |
| 点按 | `POST /session/<sid>/actions` | W3C pointer 格式，**每个 action 必须带 `id`**（缺了报 mandatory action id） |
| 拖拽 | `POST /session/<sid>/wda/dragfromtoforduration` | `{"fromX","fromY","toX","toY","duration"}`，滚动用它最稳 |

## 正确的 tap payload（W3C pointer）

```json
{"actions": [{
  "type": "pointer", "id": "any-finger",
  "parameters": {"pointerType": "touch"},
  "actions": [
    {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": X, "y": Y},
    {"type": "pointerDown", "button": 0},
    {"type": "pause", "duration": 50},
    {"type": "pointerUp", "button": 0}
]}]}
```

（`{"type":"tap","x":..}` 不是 WDA 认的格式；参考 iPhone-use 源码 `iphone_use.py` 的 screen_event + pointer 合成。）

## JSON 树解析

- 坐标在 `frame` **字符串**字段：`"{{x, y}, {w, h}}"`，要正则解析；部分节点另有 `rect` 对象（两处都要兜底）
- 可见性 `isVisible`: `"1"/"0"` 字符串；**重要元素的 label 可能 isVisible=0**（被头图盖住的昵称、折叠资料卡、整页隐藏的 QA 数据）——提取数据时不要按可见性过滤
- 页面判定用 `name`/`label` 里的 ViewController 名（如 `ivylove.MyLikeView`）

## 大坑：滚动后 AX frame 归零（缓存失效）

连续滚动 2-3 屏后，snapshot 里所有 StaticText 的 frame 变成 `{{0,0},{0,0}}`，**截图和视觉上卡片完全正常**，但无法定位点击点。实测结论（2026-11-01）：

- 等待 5-20 秒 **不会恢复**；微小回弹/30px 滚动 **无效**
- DOM 顺序 ≠ 视觉顺序，**禁止**用 DOM 序虚拟展开坐标（会点错卡片）
- 唯一可靠恢复：**back 退出列表页 → 重新进入**（代价：回到列表顶部）
- 对策组合：滚动节奏放慢（≥3s/屏）+ 识别卡数<2 时先补一次半屏慢滚触发懒加载 + frame 归零时退列表重进 + 断点状态（seen 签名/顺序）让重进后快速跳回进度
- 阈值注意：状态栏/导航节点零坐标是常态，判定失效要看「零坐标显著多于正常坐标文本」，别只看绝对数

## 引擎设计要点（通用于 App 列表采集）

- **卡片识别**：列表信息文本按 (列 x<190/≥190, 行 y±32) 聚簇，每卡 ≥2 行文本；签名 = 标签集合的 md5（内容稳定，坐标不稳定）
- **断点续采**：state.json 记 seen 签名 + 采集顺序 + dupkey（昵称‖介绍‖特征）；dupkey 从历史 profiles JSON 载入实现跨会话防重
- **防重复进主页**：发现重复立即把卡片签名写入 seen+skip（**绝不重试二次进入**——重试是用户明确反感的浪费）
- **详情页**：整页数据常在一次树 dump 里（含折叠/隐藏区），按 Table→Cell 结构解析 QA 键值对；深滚动到底（树签名连续 2 次相同），每屏截图覆盖照片墙；tab 区（动态）单独采集后切回
- **服务死亡自愈**：USB 线掉/runner 挂 → 18100 无监听；批处理外层先 curl /status，断开等 30s 重试，连续 10 次退出等人工插线；WDA 重启后**必须先 launch_app 回到目标 App** 再识别页面
