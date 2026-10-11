#!/usr/bin/env python3
"""login.py — 阶段1：登录贵州省电子税务局（企业业务），保存登录态到 persistent profile。

流程：
1. keepass 取凭据（识别号 / 身份证 / 网站密码）
2. 打开首页 → 登录页（默认「企业业务」tab）
3. 自动填三项 + 点登录
4. 验证码（短信/滑块）由用户在弹出的浏览器窗口人工完成 —— 脚本轮询等待
5. 检测到登录成功 → 截图留痕 → 退出（profile 保留登录态）

用法：
  python3 login.py            # 常规登录
  python3 login.py --check    # 仅检查现有登录态是否有效，不重新登录

退出码：0 成功 / 1 失败 / 2 超时未完成验证
"""
import sys
import time
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import (  # noqa: E402
    RUN_DIR, SHOTS_DIR, log, shot, get_credentials, open_browser,
    is_logged_in, goto_home, goto_login, body_text, fill_by_placeholder,
    click_button, click_text,
)
from playwright.sync_api import sync_playwright  # noqa: E402

WAIT_HUMAN_SECONDS = 300  # 人工验证码最长等待 5 分钟


def already_logged_in(page) -> bool:
    try:
        goto_home(page)
    except RuntimeError as e:
        log(f"首页渲染失败（{e}），视为未登录，继续登录流程")
        return False
    if is_logged_in(page):
        log("已有有效登录态（首页出现工作台特征），无需重新登录")
        shot(page, "login_skip_already")
        return True
    return False


def do_login(page, cred: dict, dry: bool = False) -> bool:
    goto_login(page)
    page.wait_for_timeout(2000)

    # 填三项（企业业务 tab 默认激活）
    fill_by_placeholder(page, "统一社会信用代码/纳税人识别号", cred["uscc"])
    fill_by_placeholder(page, "居民身份证号码/手机号码/用户名", cred["id_card"])
    fill_by_placeholder(page, "个人用户密码", cred["password"])
    shot(page, "login_filled")
    if dry:
        log("dry 模式：只填表不点击登录，请人工核对截图")
        return True

    click_button(page, "登录")
    log("已点击登录，等待验证码/跳转（人工在浏览器窗口完成验证）")
    page.wait_for_timeout(3000)
    shot(page, "login_after_click")

    # 轮询等待登录成功
    deadline = time.time() + WAIT_HUMAN_SECONDS
    while time.time() < deadline:
        try:
            if is_logged_in(page):
                log("登录成功")
                shot(page, "login_success")
                return True
        except Exception:
            pass
        # 页面可能跳转到新 tab / 新地址
        try:
            for pg in page.context.pages:
                if is_logged_in(pg):
                    log(f"登录成功（检测于其他 tab: {pg.url[:80]}）")
                    page = pg
                    shot(page, "login_success")
                    return True
        except Exception:
            pass
        time.sleep(3)
    log(f"等待人工验证超时（{WAIT_HUMAN_SECONDS}s）")
    shot(page, "login_timeout")
    return False


def main() -> int:
    check_only = "--check" in sys.argv
    log(f"=== login.py start  {datetime.now().isoformat(timespec='seconds')} ===")
    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            if check_only:
                ok = already_logged_in(page)
                return 0 if ok else 1
            if already_logged_in(page):
                return 0
            cred = get_credentials()
            ok = do_login(page, cred, dry=("--dry" in sys.argv))
            if ok:
                log("登录态已保存于 persistent profile，后续 declare.py 可直接使用")
                return 0
            return 2
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
