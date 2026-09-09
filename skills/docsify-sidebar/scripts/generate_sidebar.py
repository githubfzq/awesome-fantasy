#!/usr/bin/env python3
"""Generate a hierarchical docsify `_sidebar.md` from a docs directory.

Do not use `docsify-auto-sidebar`: it stats URL paths like `/README.md`
(filesystem root) instead of the real file under docs/.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SKIP_NAMES = {
    "index.html",
    "_sidebar.md",
    "_navbar.md",
    "_coverpage.md",
}
SKIP_DIR_NAMES = {"node_modules"}
DOC_SUFFIXES = {".md", ".html", ".txt"}

TITLE_HTML = re.compile(r"<title>([^<]+)</title>", re.I)
TITLE_YAML = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.M)
TITLE_H1 = re.compile(r"^#\s+(.+)$", re.M)

MERMAID_CSS = (
    '  <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.css">'
)
MERMAID_SCRIPT = (
    '  <script src="//cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js"></script>'
)
MERMAID_RENDERER = """      markdown: {
        renderer: {
          code: function (code, lang) {
            var text = code && typeof code === 'object' ? code.text : code
            var language = code && typeof code === 'object' ? code.lang : lang
            if (language === 'mermaid') {
              window.__mermaidSeq = (window.__mermaidSeq || 0) + 1
              try {
                return (
                  '<div class="mermaid">' +
                  mermaid.render('mermaid-svg-' + window.__mermaidSeq, text) +
                  '</div>'
                )
              } catch (e) {
                console.error('mermaid render failed, showing code block:', e)
                return this.origin.code.apply(this, arguments)
              }
            }
            return this.origin.code.apply(this, arguments)
          }
        }
      }"""

# 旧版模板生成的 renderer 没有 try/catch（本会话踩过的坑：单张坏图让整页空白）。
# 匹配旧版「无 try/catch」的 renderer 核心（不限定缩进），替换成防御版。
RENDERER_CORE = """if (language === 'mermaid') {
  window.__mermaidSeq = (window.__mermaidSeq || 0) + 1
  try {
    return (
      '<div class="mermaid">' +
      mermaid.render('mermaid-svg-' + window.__mermaidSeq, text) +
      '</div>'
    )
  } catch (e) {
    console.error('mermaid render failed, showing code block:', e)
    return this.origin.code.apply(this, arguments)
  }
}"""

OLD_UNGUARDED_CORE = re.compile(
    r"([ \t]*)if \(language === 'mermaid'\) \{"
    r"[ \t]*\n[ \t]*window\.__mermaidSeq = \(window\.__mermaidSeq \|\| 0\) \+ 1"
    r"[ \t]*\n[ \t]*return \("
    r"[ \t]*\n[ \t]*'<div class=\"mermaid\">' \+"
    r"[ \t]*\n[ \t]*mermaid\.render\('mermaid-svg-' \+ window\.__mermaidSeq, text\) \+"
    r"[ \t]*\n[ \t]*'</div>'"
    r"[ \t]*\n[ \t]*\)"
    r"[ \t]*\n[ \t]*\}"
)

# docsify 核心不处理 YAML frontmatter：不剥的话，每篇带 frontmatter 的文档
# 顶部都会显示原始 `--- date: ... ---` 文本。插件脚本须在 $docsify 配置
# 之后、docsify 主库之前加载。
FRONTMATTER_PLUGIN = r"""  <script>
    // docsify 核心不处理 YAML frontmatter：剥掉每篇文档开头的 --- 元数据块，
    // 避免正文顶部显示原始 frontmatter 文本。
    window.$docsify.plugins = (window.$docsify.plugins || []).concat(function (hook) {
      hook.beforeEach(function (content) {
        return content.replace(/^---\s*\n(?:[A-Za-z_][\w-]*:\s*[^\n]*\n)+---\s*\n?/, '')
      })
    })
  </script>"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{name}</title>
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
  <meta name="description" content="{name}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
  <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/docsify@4/lib/themes/vue.css">
  <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.css">
</head>
<body>
  <div id="app"></div>
  <script src="//cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{ startOnLoad: false }});
    window.$docsify = {{
      name: '{name}',
      repo: '',
      loadSidebar: true,
      alias: {{
        '/.*/_sidebar.md': '/_sidebar.md'
      }},
      subMaxLevel: 2,
      auto2top: true,
      markdown: {{
        renderer: {{
          code: function (code, lang) {{
            var text = code && typeof code === 'object' ? code.text : code
            var language = code && typeof code === 'object' ? code.lang : lang
            if (language === 'mermaid') {{
              window.__mermaidSeq = (window.__mermaidSeq || 0) + 1
              try {{
                return (
                  '<div class="mermaid">' +
                  mermaid.render('mermaid-svg-' + window.__mermaidSeq, text) +
                  '</div>'
                )
              }} catch (e) {{
                console.error('mermaid render failed, showing code block:', e)
                return this.origin.code.apply(this, arguments)
              }}
            }}
            return this.origin.code.apply(this, arguments)
          }}
        }}
      }}
    }}
  </script>
  <script>
    // docsify 核心不处理 YAML frontmatter：剥掉每篇文档开头的 --- 元数据块，
    // 避免正文顶部显示原始 frontmatter 文本。
    window.$docsify.plugins = (window.$docsify.plugins || []).concat(function (hook) {{
      hook.beforeEach(function (content) {{
        return content.replace(/^---\s*\n(?:[A-Za-z_][\w-]*:\s*[^\n]*\n)+---\s*\n?/, '')
      }})
    }})
  </script>
  <script src="//cdn.jsdelivr.net/npm/docsify@4"></script>
</body>
</html>
"""

DOCSIFY_SNIPPET = """
  <div id="app"></div>
  <script src="//cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{ startOnLoad: false }});
    window.$docsify = {{
      name: '{name}',
      repo: '',
      loadSidebar: true,
      alias: {{
        '/.*/_sidebar.md': '/_sidebar.md'
      }},
      subMaxLevel: 2,
      auto2top: true,
      markdown: {{
        renderer: {{
          code: function (code, lang) {{
            var text = code && typeof code === 'object' ? code.text : code
            var language = code && typeof code === 'object' ? code.lang : lang
            if (language === 'mermaid') {{
              window.__mermaidSeq = (window.__mermaidSeq || 0) + 1
              try {{
                return (
                  '<div class="mermaid">' +
                  mermaid.render('mermaid-svg-' + window.__mermaidSeq, text) +
                  '</div>'
                )
              }} catch (e) {{
                console.error('mermaid render failed, showing code block:', e)
                return this.origin.code.apply(this, arguments)
              }}
            }}
            return this.origin.code.apply(this, arguments)
          }}
        }}
      }}
    }}
  </script>
  <script>
    // docsify 核心不处理 YAML frontmatter：剥掉每篇文档开头的 --- 元数据块，
    // 避免正文顶部显示原始 frontmatter 文本。
    window.$docsify.plugins = (window.$docsify.plugins || []).concat(function (hook) {{
      hook.beforeEach(function (content) {{
        return content.replace(/^---\s*\n(?:[A-Za-z_][\w-]*:\s*[^\n]*\n)+---\s*\n?/, '')
      }})
    }})
  </script>
  <script src="//cdn.jsdelivr.net/npm/docsify@4"></script>
"""


def should_skip_dir(name: str) -> bool:
    return name.startswith(".") or name in SKIP_DIR_NAMES


def is_doc(path: Path) -> bool:
    if path.name.startswith(".") or path.name in SKIP_NAMES:
        return False
    return path.suffix.lower() in DOC_SUFFIXES


def extract_title(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError:
        return path.stem
    match = TITLE_HTML.search(text)
    if match:
        return match.group(1).strip()
    match = TITLE_YAML.search(text)
    if match:
        return match.group(1).strip()
    match = TITLE_H1.search(text)
    if match:
        return match.group(1).strip()
    return path.stem


def href_for(docs_root: Path, path: Path) -> str:
    rel = path.relative_to(docs_root).as_posix()
    return "/" + rel.replace(" ", "%20")


def sort_files(files: list[Path]) -> list[Path]:
    def key(p: Path) -> tuple:
        is_readme = p.name.lower() in {"readme.md", "readme.html"}
        return (0 if is_readme else 1, p.name.lower())

    return sorted(files, key=key)


def collect_tree(directory: Path) -> tuple[list[Path], list[tuple[str, Path, object]]]:
    files: list[Path] = []
    dirs: list[tuple[str, Path, object]] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return files, dirs
    for entry in sorted(entries, key=lambda p: p.name.lower()):
        if entry.is_dir():
            if should_skip_dir(entry.name):
                continue
            child_files, child_dirs = collect_tree(entry)
            if child_files or child_dirs:
                dirs.append((entry.name, entry, (child_files, child_dirs)))
        elif entry.is_file() and is_doc(entry):
            files.append(entry)
    return sort_files(files), dirs


def render_tree(
    docs_root: Path,
    files: list[Path],
    dirs: list[tuple[str, Path, object]],
    indent: int,
) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for file in files:
        title = extract_title(file)
        lines.append(f"{pad}- [{title}]({href_for(docs_root, file)})")
    for name, _path, children in dirs:
        child_files, child_dirs = children  # type: ignore[misc]
        lines.append(f"{pad}- {name}")
        lines.extend(render_tree(docs_root, child_files, child_dirs, indent + 1))
    return lines


def site_name(docs_root: Path) -> str:
    readme = docs_root / "README.md"
    if readme.is_file():
        return extract_title(readme)
    return docs_root.parent.name or docs_root.name


def generate_sidebar(docs_root: Path) -> str:
    files, dirs = collect_tree(docs_root)
    lines = render_tree(docs_root, files, dirs, 0)
    text = "\n".join(lines).rstrip() + "\n"
    return text


def ensure_mermaid(html: str) -> str:
    if "mermaid@9.3.0/dist/mermaid.min.css" not in html:
        if re.search(r"</head>", html, re.I):
            html = re.sub(r"</head>", MERMAID_CSS + "\n</head>", html, count=1, flags=re.I)
        else:
            html = MERMAID_CSS + "\n" + html
    if "mermaid@9.3.0/dist/mermaid.min.js" not in html:
        html = re.sub(
            r"(<script>\s*\n\s*(?:mermaid\.initialize|window\.\$docsify))",
            MERMAID_SCRIPT + r"\n\1",
            html,
            count=1,
        )
        if "mermaid@9.3.0/dist/mermaid.min.js" not in html:
            html = MERMAID_SCRIPT + "\n" + html
    if "mermaid.initialize" not in html:
        html = re.sub(
            r"(window\.\$docsify\s*=\s*\{)",
            "mermaid.initialize({ startOnLoad: false });\n    \\1",
            html,
            count=1,
        )
    if "mermaid.render" not in html:
        html = re.sub(
            r"(window\.\$docsify\s*=\s*\{)",
            r"\1\n" + MERMAID_RENDERER + ",",
            html,
            count=1,
        )
    elif "catch (e)" not in html:
        # 已有 renderer 但是旧版无防御：就地升级成 try/catch 版本，
        # 保留原缩进（group 1），续行按同一缩进对齐。
        html = OLD_UNGUARDED_CORE.sub(
            lambda m: m.group(1) + RENDERER_CORE.replace("\n", "\n" + m.group(1)),
            html,
            count=1,
        )
    return html


def ensure_frontmatter_plugin(html: str) -> str:
    if "hook.beforeEach" in html:
        return html
    if "cdn.jsdelivr.net/npm/docsify@4" not in html:
        return html
    # 用 lambda 注入，避免 re 把插件文本里的 \s \n 当作替换模板转义
    return re.sub(
        r'(<script src="//cdn\.jsdelivr\.net/npm/docsify@4[^"]*"></script>)',
        lambda m: FRONTMATTER_PLUGIN + "\n" + m.group(1),
        html,
        count=1,
    )


def ensure_index_html(docs_root: Path, name: str, dry_run: bool) -> str:
    index_path = docs_root / "index.html"
    safe_name = name.replace("'", "\\'")
    if not index_path.is_file():
        html = INDEX_TEMPLATE.format(name=safe_name)
        if not dry_run:
            index_path.write_text(html, encoding="utf-8")
        return "created"
    html = index_path.read_text(encoding="utf-8", errors="replace")
    original = html
    if "window.$docsify" not in html and "$docsify" not in html:
        snippet = DOCSIFY_SNIPPET.format(name=safe_name)
        if re.search(r"</body>", html, re.I):
            html = re.sub(r"</body>", snippet + "\n</body>", html, count=1, flags=re.I)
        else:
            html = html.rstrip() + snippet + "\n"
    else:
        if "loadSidebar" not in html:
            html = re.sub(
                r"(window\.\$docsify\s*=\s*\{)",
                r"\1\n      loadSidebar: true,",
                html,
                count=1,
            )
        if "/.*/_sidebar.md" not in html:
            html = re.sub(
                r"(window\.\$docsify\s*=\s*\{)",
                r"\1\n      alias: {\n        '/.*/_sidebar.md': '/_sidebar.md'\n      },",
                html,
                count=1,
            )
    html = ensure_mermaid(html)
    html = ensure_frontmatter_plugin(html)
    if html == original:
        return "unchanged"
    if not dry_run:
        index_path.write_text(html, encoding="utf-8")
    return "updated"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docsify _sidebar.md from a docs tree")
    parser.add_argument(
        "docs",
        nargs="?",
        default="docs",
        help="docs directory (default: ./docs)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print sidebar, do not write files")
    parser.add_argument("--no-index", action="store_true", help="do not create or patch index.html")
    args = parser.parse_args()

    docs_root = Path(args.docs).expanduser().resolve()
    if not docs_root.is_dir():
        raise SystemExit(f"docs directory not found: {docs_root}")

    sidebar = generate_sidebar(docs_root)
    if not sidebar.strip():
        raise SystemExit(f"no documents found under {docs_root}")

    sidebar_path = docs_root / "_sidebar.md"
    if args.dry_run:
        print(sidebar, end="")
    else:
        sidebar_path.write_text(sidebar, encoding="utf-8")
        print(f"wrote {sidebar_path}")

    if not args.no_index:
        status = ensure_index_html(docs_root, site_name(docs_root), args.dry_run)
        print(f"index.html: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
