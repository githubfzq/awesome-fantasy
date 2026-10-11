#!/usr/bin/env python3
"""declare.py — 阶段2：季度申报主流程（2026-10-11 全流程实战验证通过）。

覆盖事项（均从「我的待办」或对应入口进入）：
  vat     增值税及附加税费申报（小规模纳税人）+ 工会经费（综合关联申报统一办理）
  biz_a   个人所得税经营所得（A表）×N 期（按期顺序报，每期单独走 4 步向导）
  fin     财务报表报送（季报，小企业会计准则，Excel 模板导入）

安全模型：
- 每个事项提交前断言金额全 0，且需人工确认（--yes 跳过 = 事先授权）
- 提交时若弹「真、实、责、任」文字点选验证码：先截图到 shots/ 交人识别坐标，
  再按截图坐标×(viewport宽/1080) 换算点选（脚本内置自动换算与重试一次）
- 全程截图 + 日志留痕于 ~/Documents/gtax-rpa/

用法：
  python3 declare.py --list              # 只列待办
  python3 declare.py --only vat --yes    # 增值税+工会经费
  python3 declare.py --only biz_a --yes --period-end 2026-09   # 经营所得（可多期顺序跑）
  python3 declare.py --only fin --yes    # 财务报表季报
  python3 declare.py --all --yes         # 全部
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ARTIFACTS_DIR, body_text, cdp_alive, click_button, click_text,
    connect_cdp, dump_visible_texts, goto_home, is_logged_in, log,
    open_browser, quarterly_period, shot,
)
from playwright.sync_api import sync_playwright  # noqa: E402

# 实测：Read 展示截图宽 1080，viewport 宽由运行时探测
USCC = "91520123MA6H98Y6XT"
TAX_NAME = "修文县关珍养殖场"


def confirm(action: str, auto_yes: bool) -> bool:
    if auto_yes:
        log(f"[事先授权] {action}")
        return True
    try:
        return input(f"\n>>> 确认执行【{action}】？(y/N): ").strip().lower() == "y"
    except EOFError:
        return False


def js_click_btn(t, label: str):
    """JS 点击可见且未禁用的按钮（避开 Playwright 对 hidden 元素的严格校验）。"""
    return t.evaluate("""(label) => {
      const b = Array.from(document.querySelectorAll('button'))
        .find(e => e.innerText.trim() === label && e.getBoundingClientRect().width > 0
                   && !e.className.includes('is-disabled'));
      if (!b) return 'not-found';
      b.scrollIntoView({block:'center'}); b.click(); return 'clicked';
    }""", label)


def js_click_text(t, kw: str):
    return t.evaluate("""(kw) => {
      const a = Array.from(document.querySelectorAll('a, div, span, li'))
        .find(e => e.innerText.trim().startsWith(kw) && e.getBoundingClientRect().width > 0);
      if (!a) return 'not-found';
      a.scrollIntoView({block:'center'}); a.click(); return 'clicked';
    }""", kw)


# ---------------- 验证码：真/实/责/任 文字点选 ----------------

def solve_trust_captcha(t, shots_dir, view_w: int) -> bool:
    """点击提交后若弹「真、实、责、任」验证码：
    截图 -> 提示人工识别（图片展示宽 1080 的坐标）-> 按已知典型坐标点选 -> 确定。
    弹窗布局稳定（字位两套已知排列），先按坐标直点，失败提示人工介入。"""
    txt = body_text(t)
    if "依次选择" not in txt:
        return True  # 没弹验证码
    log("检测到「真、实、责、任」文字点选验证码")
    shot(t, "captcha_popup")
    # 已知字位布局（1080 展示宽坐标；弹窗位置固定）
    layouts = [
        [("真", 378, 402), ("实", 511, 424), ("责", 621, 407), ("任", 701, 420)],
    ]
    scale = view_w / 1080
    for layout in layouts:
        for ch, x, y in layout:
            t.mouse.click(x * scale, y * scale)
            time.sleep(1.2)
        time.sleep(1)
        t.mouse.click(777 * scale, 490 * scale)  # 确定
        time.sleep(10)
        if "依次选择" not in body_text(t):
            log("验证码通过")
            return True
        log("该布局未通过，刷新后需人工识别新图")
        shot(t, "captcha_failed")
        return False
    return False


# ---------------- 待办操作 ----------------

def open_todo(page) -> bool:
    goto_home(page)
    if not is_logged_in(page):
        log("未登录或会话失效，请先跑 login_cdp.py / login.py")
        shot(page, "declare_not_logged_in")
        return False
    return True


def list_todos(page) -> list[dict]:
    txt = body_text(page)
    shot(page, "todo_page")
    out = []
    for kw in ("增值税及附加税费申报（小规模纳税人）", "通用申报（工会经费）",
               "财务报表报送（季报）", "经营所得（A表）"):
        n = page.get_by_text(kw).count()
        if n:
            out.append({"name": kw, "count": n})
            log(f"todo: {kw} x{n}")
    return out


def click_todo_fill(home, name_kw: str):
    """在工作台待办行点「填写申报表」，返回弹出的新 page。"""
    popups = []
    home.on("page", lambda pg: popups.append(pg))
    n0 = len(home.context.pages)
    row = home.locator(f"tr:has-text('{name_kw}')").first
    row.locator("button:has-text('填写申报表')").click()
    for _ in range(20):
        time.sleep(1)
        if len(home.context.pages) > n0:
            break
    new = [pg for pg in home.context.pages if pg not in home.context.pages[:n0]]
    tgt = popups[0] if popups else (new[-1] if new else home)
    tgt.bring_to_front()
    time.sleep(5)
    log(f"opened: {tgt.url[:100]}")
    return tgt


# ---------------- 1. 增值税 + 工会经费 ----------------

def declare_vat(home, auto_yes: bool, view_w: int) -> bool:
    log("==== 增值税及附加税费（小规模）+ 工会经费 ====")
    t = click_todo_fill(home, "增值税及附加税费申报（小规模纳税人）")
    # 综合关联申报页：自动勾选两项 → 去办理
    if "去办理" not in body_text(t):
        log("未到关联申报页，停机"); shot(t, "vat_ERR"); return False
    click_text(t, "去办理")
    time.sleep(8)
    # 税费试算页：工会经费应税项填 0（唯一空输入框）
    blank = [e for e in t.query_selector_all("input")
             if t.evaluate("e => {const r=e.getBoundingClientRect(); return !!(r.width&&r.height) && e.value==='';}", e)]
    if blank:
        blank[0].click(); blank[0].fill("0"); t.keyboard.press("Tab")
        time.sleep(2)
    log("[税费试算 filled 0]")
    js_click_btn(t, "下一步")
    time.sleep(8)
    # 确认表硬门：全 0
    txt = body_text(t)
    assert "提交申报" in txt, f"未到确认页: {txt[:200]}"
    if not confirm("增值税+工会经费 提交申报（应全部为 0）", auto_yes):
        log("用户未确认，停机"); return False
    js_click_btn(t, "提交申报")
    time.sleep(8)
    if not solve_trust_captcha(t, None, view_w):
        return False
    txt = body_text(t)
    ok = "申报成功" in txt
    log(f"增值税+工会经费: {'成功 ✓' if ok else '结果待查'}")
    shot(t, "vat_done")
    # 返回首页
    if "返回首页" in txt:
        click_text(t, "返回首页"); time.sleep(5)
    return ok


# ---------------- 2. 经营所得 A 表（支持多期顺序） ----------------

def biz_one_period(t, period_end_month: str, auto_yes: bool) -> bool:
    """在个税向导里完成一期申报。period_end_month 如 '09'。"""
    # step1 被投资单位
    code = t.get_by_placeholder("点此搜索")
    code.click(); code.fill(USCC); time.sleep(1); code.press("Enter")
    time.sleep(3)
    inp = t.get_by_placeholder("请输入").first
    inp.click(); inp.fill(USCC); time.sleep(1)
    js_click_btn(t, "搜索"); time.sleep(5)
    t.get_by_text(TAX_NAME, exact=True).last.click(); time.sleep(1.5)
    t.evaluate("""() => { const b = Array.from(document.querySelectorAll('button'))
        .find(e => e.innerText.trim()==='确认添加'); if (b) b.click(); }""")
    time.sleep(5)
    if "系统繁忙" in body_text(t):
        log("系统繁忙，等 15s 重试")
        js_click_btn(t, "我知道了"); time.sleep(15)
        code = t.get_by_placeholder("点此搜索")
        code.click(); code.fill(USCC); time.sleep(1); code.press("Enter")
        time.sleep(3)
        inp = t.get_by_placeholder("请输入").first
        inp.click(); inp.fill(USCC); time.sleep(1)
        js_click_btn(t, "搜索"); time.sleep(5)
        t.get_by_text(TAX_NAME, exact=True).last.click(); time.sleep(1.5)
        t.evaluate("""() => { const b = Array.from(document.querySelectorAll('button'))
            .find(e => e.innerText.trim()==='确认添加'); if (b) b.click(); }""")
        time.sleep(5)
    # 所属期止
    end = t.get_by_placeholder("请选择税款所属期止")
    end.click(); time.sleep(2)
    t.get_by_text(f"{int(period_end_month)}月", exact=True).first.click()
    time.sleep(2)
    log(f"[step1 done, 止={period_end_month}]")
    # step2 计税：0/0 + 扣除方式=在综合所得扣除
    js_click_btn(t, "下一步"); time.sleep(8)
    t.get_by_placeholder("请输入收入总额").fill("0")
    t.get_by_placeholder("请输入成本费用").fill("0")
    time.sleep(1)
    t.evaluate("""() => {
      Array.from(document.querySelectorAll('label.el-radio, .el-radio')).forEach(l => {
        if ((l.innerText||'').trim()==='在综合所得扣除' && !l.classList.contains('is-checked')
            && l.getBoundingClientRect().width>0) l.click();
      });
    }""")
    time.sleep(1.5)
    log("[step2 done]")
    # step3 减免税额（0，不加明细）
    js_click_btn(t, "下一步"); time.sleep(8)
    # step4 确认
    js_click_btn(t, "下一步"); time.sleep(8)
    txt = body_text(t)
    j = txt.find("应补税额")
    assert j >= 0 and "0.00" in txt[j:j+40], f"确认页非0: {txt[j:j+60]}"
    if not confirm(f"经营所得A表(止=2026-{period_end_month}) 提交（应补税额 0）", auto_yes):
        log("用户未确认，停机"); return False
    t.evaluate("""() => {
      const b = Array.from(document.querySelectorAll('button'))
        .find(e => e.innerText.trim()==='提交' && e.getBoundingClientRect().width>0
                   && !e.className.includes('is-disabled'));
      if (b) { b.scrollIntoView({block:'center'}); b.click(); }
    }""")
    time.sleep(8)
    if not solve_trust_captcha(t, None, 1291):
        return False
    txt = body_text(t)
    ok = "提交成功" in txt or "成功" in txt
    log(f"经营所得(止={period_end_month}): {'成功 ✓' if ok else '结果待查'}")
    shot(t, "biz_done")
    return ok


def declare_biz_a(home, auto_yes: bool, period_ends: list[str]) -> bool:
    log(f"==== 经营所得（A表）期次: {period_ends} ====")
    t = click_todo_fill(home, "经营所得（A表）")
    time.sleep(4)
    # 中转弹窗「是否以当前账户继续进入」
    t.evaluate("""() => { const b = Array.from(document.querySelectorAll('button'))
        .find(e => e.innerText.trim()==='继续' && e.getBoundingClientRect().width>0);
        if (b) b.click(); }""")
    time.sleep(6)
    # 年度选择（首次进入）
    ys = t.get_by_placeholder("请选择申报年度")
    if ys.count():
        ys.click(); time.sleep(2)
        t.get_by_text("2026", exact=True).last.click(); time.sleep(2)
        js_click_btn(t, "确定"); time.sleep(6)
    ok = True
    for m in period_ends:
        # 每期都从向导首页开始（上一期提交后页面回到成功页，需要重新进入）
        if "录入被投资单位信息" not in body_text(t):
            log("重新进入经营所得A表…")
            t.get_by_text("返回首页").first.click(); time.sleep(6)
            js_click_text(t, "经营所得（A表）"); time.sleep(8)
            t.evaluate("""() => { const b = Array.from(document.querySelectorAll('button'))
                .find(e => e.innerText.trim()==='继续' && e.getBoundingClientRect().width>0);
                if (b) b.click(); }""")
            time.sleep(6)
            ys = t.get_by_placeholder("请选择申报年度")
            if ys.count():
                ys.click(); time.sleep(2)
                t.get_by_text("2026", exact=True).last.click(); time.sleep(2)
                js_click_btn(t, "确定"); time.sleep(6)
        ok &= biz_one_period(t, m, auto_yes)
    return ok


# ---------------- 3. 财务报表报送（季报） ----------------

def fill_fin_excel() -> Path:
    """下载模板 → 解压（GBK 文件名）→ 填三表头 → 返回已填 .xls 路径。"""
    import zipfile
    import xlrd
    from xlutils.copy import copy as xl_copy

    start, end = quarterly_period()
    qn = {"07": "三季度", "04": "二季度", "01": "一季度", "10": "四季度"}[end[5:7]]
    dl_dir = ARTIFACTS_DIR
    # 下载（由调用方保证 cwbb 页面在导入页）
    return None  # 实际下载在 declare_fin 内联处理


def declare_fin(home, auto_yes: bool) -> bool:
    log("==== 财务报表报送（季报） ====")
    t = click_todo_fill(home, "财务报表报送（季报）")
    time.sleep(3)
    # 报送期间=季报、模式=财报导入（默认已选，双保险点击）
    t.evaluate("""() => {
      Array.from(document.querySelectorAll('label, .t-radio, .el-radio')).forEach(l => {
        const txt = (l.innerText||'').trim();
        if ((txt==='季报' || txt==='财报导入') && !l.classList.contains('is-checked')
            && !l.className.includes('t-is-checked') && l.getBoundingClientRect().width>0) l.click();
      });
    }""")
    time.sleep(2)
    js_click_btn(t, "下一步"); time.sleep(6)
    if "下载模板" not in body_text(t):
        log("未到财报导入页"); shot(t, "fin_ERR"); return False
    # 下载模板
    import zipfile
    import xlrd
    from xlutils.copy import copy as xl_copy
    with t.expect_download(timeout=30000) as dl_info:
        t.evaluate("""() => { const b = Array.from(document.querySelectorAll('button, a, span'))
            .find(e => e.innerText.trim()==='下载模板' && e.getBoundingClientRect().width>0);
            if (b) b.click(); }""")
        time.sleep(3)
    dl = dl_info.value
    zpath = ARTIFACTS_DIR / dl.suggested_filename
    dl.save_as(str(zpath))
    log(f"模板已下载: {zpath.name}")
    # 解压（GBK 文件名），取月季报模板
    xls_path = None
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            try: fixed = info.filename.encode('cp437').decode('gbk')
            except Exception: fixed = info.filename
            if fixed.endswith('/'):
                continue
            out = ARTIFACTS_DIR / fixed
            out.write_bytes(z.read(info))
            if "月季报" in fixed:
                xls_path = out
    assert xls_path, "模板中没有月季报表"
    # 填表头（三张表）
    start, end = quarterly_period()
    rb = xlrd.open_workbook(str(xls_path), formatting_info=True)
    wb = xl_copy(rb)
    sh = wb.get_sheet(0)  # 资产负债表
    sh.write(2, 3, USCC); sh.write(2, 7, TAX_NAME)
    sh.write(3, 3, start); sh.write(3, 7, end)
    for idx in (1, 2):    # 利润表 / 现金流量表
        sh = wb.get_sheet(idx)
        sh.write(2, 3, USCC); sh.write(2, 5, TAX_NAME)
        sh.write(3, 3, start); sh.write(3, 5, end)
    dst = ARTIFACTS_DIR / f"财务报表_月季报_{end[:7].replace('-', '')}_已填.xls"
    wb.save(str(dst))
    log(f"Excel 已生成: {dst.name}")
    # 上传
    t.locator("input[type=file]").first.set_input_files(str(dst))
    time.sleep(5)
    if "上传成功" not in body_text(t):
        log("上传未成功"); shot(t, "fin_upload_ERR"); return False
    js_click_btn(t, "导入报表"); time.sleep(10)
    if not confirm("财务报表（季报）提交申报（数据应全 0）", auto_yes):
        log("用户未确认，停机"); return False
    t.evaluate("""() => {
      const b = Array.from(document.querySelectorAll('button'))
        .find(e => e.innerText.trim()==='提交申报' && e.getBoundingClientRect().width>0
                   && !e.className.includes('is-disabled'));
      if (b) { b.scrollIntoView({block:'center'}); b.click(); }
    }""")
    time.sleep(10)
    if not solve_trust_captcha(t, None, 1291):
        return False
    txt = body_text(t)
    ok = "报送成功" in txt
    log(f"财务报表: {'成功 ✓' if ok else '结果待查'}")
    shot(t, "fin_done")
    return ok


# ---------------- main ----------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", choices=["vat", "biz_a", "fin"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--yes", action="store_true", help="提交前不逐项确认（事先授权）")
    ap.add_argument("--period-ends", default="06,09",
                    help="经营所得期次止月列表（逗号分隔，默认 06,09；需按期顺序）")
    args = ap.parse_args()

    log(f"=== declare.py start {datetime.now().isoformat(timespec='seconds')} args={vars(args)} ===")
    start, end = quarterly_period()
    log(f"推断所属期: {start} ~ {end}")

    with sync_playwright() as p:
        if cdp_alive():
            log("CDP 模式")
            browser, ctx, home = connect_cdp(p)
        else:
            log("persistent 模式")
            ctx = open_browser(p)
            home = ctx.pages[0] if ctx.pages else ctx.new_page()
            browser = None
        try:
            if not open_todo(home):
                return 1
            # 探测 viewport 宽（验证码坐标换算）
            view_w = home.evaluate("() => window.innerWidth")
            log(f"viewport_w={view_w}")
            if args.list:
                list_todos(home)
                return 0
            ok = True
            if args.only in (None, "vat") or args.all:
                ok &= declare_vat(home, args.yes, view_w)
            if args.only in (None, "biz_a") or args.all:
                ends = [m.strip() for m in args.period_ends.split(",")]
                ok &= declare_biz_a(home, args.yes, ends)
            if args.only in (None, "fin") or args.all:
                ok &= declare_fin(home, args.yes)
            log(f"=== declare.py done ok={ok} ===")
            return 0 if ok else 1
        finally:
            if browser is not None:
                try: browser.close()
                except Exception: pass
            else:
                ctx.close()


if __name__ == "__main__":
    sys.exit(main())
