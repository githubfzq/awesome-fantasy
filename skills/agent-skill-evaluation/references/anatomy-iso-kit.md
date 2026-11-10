# anatomy（wheresryan22/anatomy）API 速查与绘图坑

2026-11-01 实测。仓库装于 ~/.hermes/skills/anatomy，Node>=20.10 零 npm 依赖，安全审计干净（kit 无网络/eval/env）。

## 用法骨架

非 React 站点写 Node build 脚本（仿 examples/dial-indicator/build.mjs）：

```js
import * as k from "../../kit/iso-kit.mjs";
import { tubePieces, tubeSvg } from "../../kit/tube.mjs";   // 管路/线缆
import { kitScript } from "../../scripts/inline-kit.mjs";   // 内联进独立 HTML

const P = k.fitProjection([...k.boxCorners(PLATE, z0, z1), 其他点], W, H, { pad: 28, azimuth: 42 });
const at = p => k.iso(p, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (pts, style) => k.dotsSvg(pts, style);
// 常用几何: slabOf, cylinder, insetPlan, planOutline, lineOnTop, ring,
// knurl, sideArc, topTicks, sideTicks, radialTicks, haloOf, depthOf,
// translateAlong, faceTextSvg + topMatrix
const svg = k.figureSvg({ width, height, label, body: [...] });
const body = k.plateHtml({ fig, title, hint, readout, keys, caption, body: `<div class="iso-stage" ...>${svg}</div>` });
writeFileSync(out, k.pageHtml({ title, theme, body, script: kitScript() + live }));
```

live 脚本里不能直接用 kit 导入，需把必要函数内联/序列化进去（dial-indicator 的做法：`k.lineOnTop` 用 `needleAt.toString().replace("k.lineOnTop", "lineOnTop")` 注入，几何函数在 live 里重写一份纯 JS）。

## 三个实测坑

1. **包裹件必须拆半。** kit 没有 halfSlabOf；craft.md 的规则是"back half → inner part → front half"。实测：水箱沿 y 中线手动切两个 slab（backHalf/frontHalf），水 slab 夹中间，否则水画在前壁之上（穿墙）。
2. **件要放在它画的深度。** 表盘原设计在 tank 后方 y=-62，却画在 tank 之后 → 立柱穿墙。把表盘挪到前方台面上（y=30），paint 顺序才真。设计阶段就想好每件的屏幕深度。
3. **路由两端落在真实端口。** pipe 用 `tubePieces(route, r, P, { spacing: 2.2 })` 逐段 `tubeSvg`，两端各画一个 collar（cylinder）压住接口；route 拐点用折线，入口最后一段沿 z 直插 filler 环。

## 工作流要点（SKILL.md 摘要）

- 概念→实体映射：把技术概念映射成一个"机制即概念"的真实机械（电容→手动泵+压力水箱）。
- 分级：Figure 40-80 零件/约1小时、Hero 80-150/2-4h、Epic 6h+ 不自动开工。
- tone 层级：base=lo、structure=mid、subject=hi，唯一 accent=lit；刻度 minor=lo major=mid。
- `node build.mjs --audit`（auditOrExit）验证几何：间隙/终端/深度序等，生产级图必跑；`node build.mjs --light` 出亮色版。
- examples/ 有 8 个参考实现，质量基线是 test-rig（绘图）与 raptor-engine（shader）。

## community 仓库（wheresryan22/anatomy-community）

仅是画廊：main 存 figure 源码（build.mjs+figure.json），CI 在沙箱重建，previews 分支放成品。投稿走 publish.mjs 或 issue 表单。**不是 skill，不要装它。**
