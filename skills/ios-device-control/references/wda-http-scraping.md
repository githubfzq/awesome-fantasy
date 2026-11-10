# WDA HTTP 直连协议（大规模抓取/高频自动化）

适用场景: 对真实 iPhone 做大规模抓取或 >100 次交互的自动化。MCP pua_* 工具每条带校验/观察开销，直连 WDA HTTP（localhost:18100）快约一个数量级。2026-10 青藤之恋『我喜欢的』3000 人采集实战验证。

## 端点与负载（WDA 16.14 实测）

- 健康检查: `GET /status`
- 建会话: `POST /session` `{"capabilities":{}}` → `value.sessionId`
- AX 树: `GET /source?format=json`（不需要 session 前缀）
  - **坑**: 节点坐标在 `frame` 字段，是字符串 `"{{x, y}, {w, h}}"` 而非 rect 对象，需正则解析：
    `\{\{([-\d.]+),\s*([-\d.]+)\},\s*\{([-\d.]+),\s*([-\d.]+)\}\}`
- 截图: `GET /screenshot` → **JSON，base64 在 `value` 字段**（不是原始图片字节，直接落盘会得到文本文件）
- 点击: `POST /session/{sid}/actions`，W3C pointer 格式，**必须有 id 字段**（缺 id 或用 `{"type":"tap"}` 简写都会报 unknown error / 404）:
  ```json
  {"actions":[{"type":"pointer","id":"f1","parameters":{"pointerType":"touch"},
    "actions":[
      {"type":"pointerMove","duration":0,"origin":"viewport","x":92,"y":310},
      {"type":"pointerDown","button":0},
      {"type":"pause","duration":50},
      {"type":"pointerUp","button":0}]}]}
  ```
- 拖动/滚动: `POST /session/{sid}/wda/dragfromtoforduration`
  `{"fromX":196,"fromY":640,"toX":196,"toY":206,"duration":0.35}`

## AX 树解读坑

- `isVisible='0'` 的节点常含关键数据：被头图盖住的昵称、折叠资料卡（IP属地/MBTI/性格测试/婚况/学历）。**提取数据时不要按可见性过滤**（判断可点击才过滤）。
- 整页内容（含折叠区、y>852 的屏外节点）在一次 `/source` dump 里全都有——不需要滚动获取文本，滚动只为截图和触发懒加载（如动态区）。
- 文本一般在 StaticText/Button 的 `label`；导航栏 `name`（如 `ivylove.MyLikeView`）是判断当前页面的稳定锚点，比整树签名或截图对比可靠。

## 大规模抓取架构（验证过的模式）

1. **状态机 checkpoint**: state.json 记 `seen`（卡片签名去重）、`order`、`dupkeys`、`fails`；崩溃/断链后可从断点续跑。
2. **无昵称列表的卡片识别**: 画廊卡片若不带 label，用 StaticText 簇聚合——同列（x 阈值分左右列）且 y 相邻 <32pt 的文本归一簇；签名 = 簇内标签文本排序后 md5；点击点 = 簇上方图片区中央，**避开角落悬浮按钮**（如青藤之恋卡片右下角 "hi" 小纸条按钮，误点会发消息）。
3. **防重复（同页检测）**: 详情页以 `昵称+介绍首行+基础行特征` 三元组为 dupkey；检测到重复→回列表重试同一张卡一次→仍重复则弃卡标记 seen。原因：返回列表后树签名变化方式相同，仅靠「签名变化+有back」会误判进入了新页。
4. **页面往返确认**: 每次点击前确认在列表页（导航栏 name），返回时轮询确认；失败 3 次退出而非死循环。
5. **批处理包装**: bash 循环——先 `curl /status` 健康检查（断链等待重试，连续 10 次失败退出），再跑每批 N 人的采集，日志追加写。配合 Hermes terminal background + notify_on_complete 挂后台。
6. **产物双轨**: 每用户一份结构化 JSON + 2 张截图（首屏+滚后）；写备忘录/上传等慢操作用独立进程异步补（如 osascript 写 Apple Notes，单独记录 written 清单可增量重跑）。

## 服务死亡与恢复

- USB 拔线 → forward 进程死、18100 无监听；手机端 WDA runner 可能还活着（job 日志可证）。
- 手机解锁但线断时，可试 Wi-Fi 直连：WDA 监听全网卡，`curl http://<手机IP>:8100/status`（需同网段、且 runner 存活）。
- 标准恢复序: `pua_setup(action=status)` 确认 service 不可达且无 running job → `pua_setup(action=start)` → `pua_ready`。手机需解锁亮屏、数据线插好。
- 采集脚本本身无需改动：WDA 恢复后同一路径续跑，state.json 保证不重复不遗漏。

## 实例代码

完整可运行引擎见本机 `~/.hermes/cache/qingteng/collect.py`（卡片识别/详情提取/断点续采）与 `batch.sh`（批处理包装），可复制改造。
