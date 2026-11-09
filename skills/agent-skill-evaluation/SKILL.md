---
name: agent-skill-evaluation
description: Use when 调研/评估第三方 agent skill：安装、安全审计、实跑验证。
---

# 评估第三方 agent skill

用户说"调研这个 skill / 试试效果"时的完整流程。核心原则：必须实际产出，不能只读文档下结论。

## Workflow

1. **辨认真身仓库。** 很多 GitHub 仓库是画廊/元仓库（如 `wheresryan22/anatomy-community` 只是投稿画廊），真正的 skill 本体在主仓库（`wheresryan22/anatomy`）。先 web_search 或读 README 确认 SKILL.md 在哪，再向用户指出区别。

2. **安装到本地。**
   - 优先 `hermes skills tap add owner/repo`（注意 tap 只认默认分支，非默认分支用 raw.githubusercontent.com 直装 URL，见 hermes/skill-sources 技能）。
   - 带 kit/examples 目录的 Node/Python 类 skill 直接 `git clone --depth 1` 到 `~/.hermes/skills/<name>/` 更实用：保留全部示例和库文件，克隆即安装。外网 git 需先 `export https_proxy=http://127.0.0.1:7899`。

3. **跑代码前先安全审计。** 对 kit/lib 目录 grep：`fetch|XMLHttpRequest|eval|new Function|child_process|process.env`。
   - 合理例外：构建侧脚本（如 headless Chrome 截图器的 spawn）、publish/submit 脚本（只在用户明确要求投稿时才碰网络）。
   - 运行时库应零网络、零 eval、零环境变量读取。有越界就停下向用户报告，不要试运行。

4. **核对环境要求。** 读 SKILL.md 的 compatibility 段（Node>=20.10、Chrome 等），先 `node --version` 验证。

5. **冒烟验证（分级）。**
   a. 先构建/打开它**自带的 example**，用 `browser_navigate` 打开 `file://` 本地页面看效果——这是 skill 官方质量基线。
   b. 读 SKILL.md 的 workflow + 一个最小 example 的源码，然后**自己写一个测试产物**（按它的概念→实体映射流程）。只有亲手跑通 API 才算验证了 skill 可用。
   c. 目检：`browser_vision` 问具体问题——部件是否齐全、有无 z-order 穿帮、有无浮空件、是否读起来像真东西。
   d. 交互验证：`browser_console` 里 `dispatchEvent(new PointerEvent('pointerdown', {bubbles:true}))` 模拟按住，setTimeout 后读 readout / aria-valuenow，确认"模型驱动输出"整条链路真的在动。
   e. 对自己写的测试文件，用临时验证脚本断言关键行为（重建→断言输出 HTML/产物内容），跑完即删。

6. **收尾：** 安装位置 + 一句话用法记入 memory（不含任务过程）；学到的 API 坑写进本技能 `references/`。

## Pitfalls

- `write_file` 拒绝写 `/private/var/folders/...` 等系统临时路径；临时验证脚本用 terminal 的 `mktemp` + heredoc 写，跑完 `rm`。
- 三方 skill 的仓库本体是用户安装物，**不要 patch 它的 SKILL.md / kit**（升级即丢、且属用户所有）；发现它的坑记到本技能的 references/ 里。
- 改动过的文件才算"本次产出"，验证脚本的断言应针对本轮改动的行为，不要照抄上游测试。

## References

- `references/anatomy-iso-kit.md` — anatomy skill（wheresryan22/anatomy）的 API 速查与三个绘图坑，2026-11 实测。
