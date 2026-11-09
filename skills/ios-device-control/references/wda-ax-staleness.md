# WDA AX 树失真问题与视觉定位出路（2026-11-01 青藤之恋实战）

## 症状

滚动列表页（约 2-3 屏后）WDA `/source` 返回的 AX 树大面积失真：
- 大量 StaticText 节点 frame 归零（y=0, x=0），其余节点坐标错乱（负值、屏外值）
- 部分节点直接丢失（截图上 8 张卡，AX 只见 2 张的文本）
- **视觉渲染完全正常**（截图确认）——是 App 暴露给 XCTest 的 accessibility 快照坏了，不是渲染问题

等待（最长 20s）、轻扫回弹、30px 微滚、降速滚动、半屏滚动均无法恢复。
唯一可靠恢复手段：**退出列表页重进**（back → 重新点入口），但重进回到列表顶部，
滚动深度丢失，造成「重进→下翻→失效→重进」死循环，吞吐量崩到 1 人/10 分钟。

## 误判教训

1. **零坐标文本不能用 DOM 顺序虚拟展开还原位置**——实测 DOM 顺序与视觉顺序不一致，
   按序配对点击会点错卡片。宁可返回空结果等恢复，不可瞎点。
2. **"连续 N 轮无新卡=到底"的判定会被 AX 失真触发假阳性**。bottom 标志不应持久化到
   state.json（load_state 时强制重置），否则一次误判永久短路后续运行。
3. frame 失效诊断阈值要区分「状态栏/导航栏常态零坐标」（约 2-3 个）与「真失效」
   （零坐标数 > 正常坐标数 且 ≥4）。

## 对抗策略（按优先级）

1. **视觉定位（根治）**: 截图 + Jev Box（TypeSafe 决策模型的多模态框定位）。
   `POST https://api.typesafe.ai/v1/systemone`，state 含 base64 image_url，
   questions type=box，**必须带 header `TypeSafe-Danger-Zone-Images: true`**（否则 400）。
   返回 left/right/top/bottom 归一化坐标 + confidence，乘以 viewport 换算成点击点。
   坑：Magpie 网关不透传该自定义 header（400 报缺 header），必须直连 api.typesafe.ai；
   key 从 `~/.config/magpie/providers.json` 的 typesafe provider 取（网关同款 key 直连验证可用）。
2. **检测 + 自愈（缓解）**: 主循环在"无新卡"分支诊断 frame 状态：
   零坐标占多数 → back+重进刷新 AX（接受回顶代价，靠 Jev 文本查重快速跳过已采卡）；
   正常坐标文本 2-5 条 → 懒加载未完，半屏慢滚+等待触发渲染，不滚动全屏。
3. **规避滚动**: 整页文本在一次 /source dump 全有（AX 失真前），尽量减少列表页滚动次数。

## Jev 决策模型速记（Magpie 网关 / TypeSafe）

- 文本决策（Choice/Noul/Score）: Magpie 网关可用 `POST http://127.0.0.1:3425/v1/systemone`，
  model=jev-latest，无需透传 header。Noul 返回 `{"noul": 0.98}` 概率。
  实战用法：批量列表卡免进主页查重（一次请求判全屏卡，精确集合命中短路，其余打包问），
  疑似重复概率 ≥0.6 直接跳过，省一次详情页往返（~25s → ~1s）。
- 图片 Box: 必须直连 + header（见上）。用户在网关配了 typesafe provider；
  用户自报的 API key 可能遇到 "organization has been deactivated" 403——先测 key 再集成。
- 引擎侧参考实现: `~/.hermes/cache/qingteng/jev_client.py`（文本）、`jev_batch.py`（批量查重）、
  `jev_box.py`（Box 视觉定位，含 box→points 换算）。
