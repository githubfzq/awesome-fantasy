---
name: docsify-sidebar
description: >-
  从 docs/ 目录树生成 docsify 分层侧边栏 _sidebar.md，并确保 index.html 开启
  loadSidebar，以及用 Mermaid 9.3 同步渲染流程图。用于 docsify 目录、侧边栏、
  _sidebar.md、docsify serve、mermaid 流程图、docsify-auto-sidebar 报错、
  plans/solutions 等子目录新增文档后要进目录、以及「文档目录不会自动更新」
  的场景。当用户提到 docsify、_sidebar、文档目录、mermaid、流程图、
  docsify-auto-sidebar、stat '/README.md'、ENOENT README.md、或要给 docs
  生成可按层级浏览的目录时，务必使用本技能——即使用户只说「帮我生成文档目录」
  或「plans 里新文件怎么进侧边栏」也应触发。不要使用已损坏的
  docsify-auto-sidebar，改跑本技能附带的生成脚本。
agent_created: true
---

# Docsify 分层目录生成

## Overview

Docsify 的侧边栏**不会**扫描磁盘。新 md 放进 `docs/plans/` 不会自动出现，除非重写 `docs/_sidebar.md`。

不要用 `docsify-auto-sidebar`。该包 1.0.0 会把 URL 路径 `/README.md` 拿去 `fs.statSync`，报：

```text
ENOENT: no such file or directory, stat '/README.md'
```

根因：`tPath + '/' + item` 在根层变成 `/README.md`，却拿去 stat，而不是 `path.join(docsDir, item)`。npm 上也没有修复版。

本技能用附带脚本按真实目录树生成 `_sidebar.md`，并打开 docsify 的 `loadSidebar`。

## Workflow

1. 确认文档根目录（通常是项目下的 `docs/`，里面有 `index.html` 或一堆 `.md`）。
2. **跑生成脚本**，不要手写整份侧边栏，也不要调用 `docsify-auto-sidebar`：

```bash
python3 <this-skill>/scripts/generate_sidebar.py /path/to/docs
```

默认会：

- 写入 `docs/_sidebar.md`（按目录层级嵌套列表）
- 若没有 `index.html` 则创建一份 Docsify 4 入口（含侧边栏 + Mermaid 9.3 同步渲染）
- 若已有 `index.html`，补上 `loadSidebar: true`、alias，以及 Mermaid 9.3 + `markdown.renderer.code`

只预览不写文件：

```bash
python3 <this-skill>/scripts/generate_sidebar.py /path/to/docs --dry-run
```

3. 预览：`docsify serve docs`（在项目根，文档目录为 `docs` 时）。
4. 以后 `plans/`、`solutions/` 等有新文件：再跑同一条命令覆盖 `_sidebar.md`。

`<this-skill>` 是本技能目录，例如当前仓库的 `skills/docsify-sidebar`。

## 生成规则

脚本行为（改目录规则时改脚本，不要让模型另写一份）：

- 收录 `.md` / `.html` / `.txt`
- 跳过 `index.html`、`_sidebar.md`、`_navbar.md`、`_coverpage.md`、点开头文件、`node_modules`
- 同一层：`README.md` 优先，其余按文件名；然后是子目录
- 空目录不出现
- 链接从 docs 根算起，以 `/` 开头（例如 `/plans/foo.md`），避免嵌套页相对路径错位
- 标题优先：HTML `<title>` → YAML `title:` → 首个 `#` 标题 → 文件名

`index.html` 里必要配置：

```js
window.$docsify = {
  loadSidebar: true,
  alias: {
    '/.*/_sidebar.md': '/_sidebar.md'
  }
}
```

没有 alias 时，打开 `/plans/xxx` 会去找 `docs/plans/_sidebar.md`，侧边栏空白。

## Mermaid 流程图

文档里的流程图用 fenced code，语言标记为 `mermaid`：

````markdown
```mermaid
flowchart LR
  A[开始] --> B[结束]
```
````

**不要用 Mermaid 10 + `mermaid-docsify`。** 两个已知坑：

1. `cdn.jsdelivr.net/npm/mermaid-docsify/dist/mermaid-docsify.min.js` 是 **404**，插件根本不会加载。
2. Docsify 4 的 markdown renderer 必须**同步返回 HTML 字符串**。Mermaid 10 的 `render()` 返回 Promise，页面上会变成 `[object Promise]` 或空白代码块。

正确做法是 **Mermaid 9.3.0**（同步 `render`）+ `$docsify.markdown.renderer.code`：

1. 先加载 `mermaid@9.3.0/dist/mermaid.min.js`
2. `mermaid.initialize({ startOnLoad: false })`
3. 在 `code` renderer 里对 `lang === 'mermaid'` 调用 `mermaid.render(id, text)`，包进 `<div class="mermaid">`
4. 再加载 Docsify 4

生成脚本的 `index.html` 模板已经按这个顺序写好。`startOnLoad` 必须是 `false`，否则会在 Docsify 注入页面前空跑一遍。

## 手动改一行（可选）

脚本每次全量覆盖 `_sidebar.md`。若只想改文案、暂时不重跑：

```markdown
- Plans
  - [已有条目](/plans/2026-08-18-001-feat-xxx.md)
  - [新计划标题](/plans/2026-08-20-001-feat-yyy.md)
```

缩进两空格一层。根目录文件加在文件顶部。新分组用无链接的组名，下面再列文件。

下次跑脚本后，手改文案会被标题提取结果盖掉。要长期保留手写标题，就改文档自己的 `#` 标题，或改脚本后再生成。

## 预览环境坑（顺带）

- `docsify-cli@5` 在 pnpm 全局下会因未声明的 `ansi-colors` / `semver` 启动失败（幽灵依赖）。预览用 `docsify-cli@4`：`pnpm add -g docsify-cli@4`。
- `docsify --help` 也会加载全部子命令，5.x 同样会炸。
- 本技能生成的是静态 `_sidebar.md`，与 CLI 版本无关。

## 验证

- `_sidebar.md` 存在，且每个收录文件都有对应链接
- `index.html` 含 `loadSidebar: true`、`/.*/_sidebar.md` alias、`mermaid@9.3.0` 和 `mermaid.render`
- 在文档根执行 `--dry-run`，输出与写入文件一致
- 不要出现 `/README.md` 这种对文件系统根目录的 stat 错误
