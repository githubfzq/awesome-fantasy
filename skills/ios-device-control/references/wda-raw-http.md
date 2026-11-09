# WDA 原生 HTTP API 速查（绕过 MCP 直连，用于高频采集/自动化脚本）

适用场景：需要每秒多次观察+操作的长任务（如 App 内批量采集）。MCP `pua_*` 每次调用带校验开销，
直连 WDA HTTP 快一个数量级。端口默认 18100（USB 转发），见 `~/.local/share/iphone-use/config.json`。

## 端点与格式（2026-11-01 实测，WDA 16.14.0）

### 建会话（所有动作端点都需要 session 前缀）
```
POST /session  body: {"capabilities": {}}
→ value.sessionId
```
- `/source`、`/screenshot`、`/status` 可以不带 session；`/actions`、`/wda/*` 必须 `/session/{sid}/...`

### 读控件树
```
GET /source?format=json
```
- 返回 `{value: <tree>}`，**必须取 `.value`**
- 节点字段：`label`、`type`、`children`、`isVisible`("0"/"1" 字符串)、
  **`frame` 是字符串 `"{{x, y}, {w, h}}"` 需正则解析**（不是 rect 对象！）
- 树里的节点可能 `isVisible='0'` 但内容有效（被头图盖住的折叠资料卡）——按用途决定是否过滤可见性

### 点击（W3C pointer 格式，必须带 id）
```
POST /session/{sid}/actions
{"actions":[{"type":"pointer","id":"my-finger","parameters":{"pointerType":"touch"},
  "actions":[{"type":"pointerMove","duration":0,"origin":"viewport","x":X,"y":Y},
             {"type":"pointerDown","button":0},{"type":"pause","duration":50},
             {"type":"pointerUp","button":0}]}]}
```
- ❌ `{"type":"tap","x":..}` 会报 "mandatory action id field is missing"
- ❌ 不带 session 前缀 → 404

### 拖拽/滚动
```
POST /session/{sid}/wda/dragfromtoforduration
{"fromX":196,"fromY":640,"toX":196,"toY":206,"duration":0.4}
```

### 截图（JSON base64，不是二进制流！）
```
GET /screenshot → {"value": "<base64>"}   # 需 base64 解码后才是 JPEG
```

## 已验证的坑

1. **AX frame 滚动后失效（最阴）**：列表页滚动后，App 的 frame 数据会整体归零
   （所有节点 y=0,x=0），且等待数秒不恢复、换 snapshot 参数也不恢复——是 WDA 缓存与
   App 渲染不同步。视觉截图完全正常，但无法定位。缓解：
   - 滚动后先等树签名连续 2 次相同再识别
   - 识别不足（<4 条有效坐标文本）时**不要**用 DOM 顺序虚拟展开坐标——实测 DOM 顺序
     ≠ 视觉顺序，会点错卡片
   - 兜底方案：固定网格坐标点击（规整两列画廊）、新建 WDA session 强制重建快照、
     或视觉模型定位（如 Jev Box 原语）
2. **防重复点击必须永久标记**：检测到重复（dupkey 比对）后立即把卡片签名写入
   seen+skip 集合，绝不做「重试一次再进入」——用户明确反馈过重复进同一人主页不可接受。
   dupkey 应跨会话持久化（启动时从全部历史产物 JSON 载入）。
3. **滚动漂移防护**：处理每张卡前重取当前屏，确认目标卡仍在屏上并刷新坐标
   （上一屏的 tap_y 在滚动后可能指向另一张卡）。
4. **进入详情页校验**：tap 后轮询树签名变化 + 页面特征（如 NavigationBar name），
   超时未变则 back 恢复而不是继续。
5. 批处理包装器模式：每批 N 人一个 python 进程，批间检查 WDA /status 存活，
   断链重试有限次数后退出（防死循环刷日志）。

## Jev 决策模型（Magpie 网关内置，2026-11-01 跑通）

- 端点：`POST http://127.0.0.1:3425/v1/systemone`，body `{"model":"jev-latest","state":[...],"questions":{...}}`
- 原语：`noul`（是/否→概率）、`choice`（选项→`criteria:{key:desc}`）、`score`（有序评分）、
  `box`（图内定位→top/bottom/left/right 比例）
- 响应：`answers.<qname>.noul / .choice / .probabilities`，模型实际 jev-1.14.0
- ❌ 不要走 `/v1/chat/completions` 调 jev——报 "only decides a routing group's model"
- 用法参考（本机）：`~/.hermes/cache/qingteng/jev_client.py`（单问）、`jev_batch.py`
  （一次请求判多卡，比逐卡问快 N 倍）
- 采集流水线最佳实践：候选卡免进主页查重（Noul 批量）→ 疑似重复直接跳过省 25s/人；
  Jev 不可用时自动降级为纯规则路径，不阻塞主流程
