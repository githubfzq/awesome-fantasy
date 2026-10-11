#!/usr/bin/env python3
"""login_cdp.py — CDP 模式登录（瑞数风控首选）。

拉起专用 Chrome（独立 profile + CDP 9222）→ 你在窗口里手动完成登录（验证码等）
→ 脚本轮询检测登录成功 → 退出（Chrome 保持运行，declare.py 接管同一窗口）。

profile 持久化：下次运行时若 cookie 未过期，检测到已登录会直接通过，无需重新登录。

用法：
  python3 login_cdp.py           # 确保 Chrome 在线且已登录（可能等你人工操作）
  python3 login_cdp.py --check   # 只检测，不拉起 Chrome

退出码：0 已登录 / 1 未登录 / 2 等待人工登录超时
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    RUN_DIR, cdp_alive, connect_cdp, is_logged_in, launch_chrome_manual,
    log, shot, TAX_URL,
)
from playwright.sync_api import sync_playwright  # noqa: E402

WAIT_HUMAN_SECONDS = 600  # 人工登录最长等 10 分钟


def find_tax_page(ctx):
    for pg in ctx.pages:
        if "chinatax.gov.cn" in pg.url:
            return pg
    return None


def check_logged(ctx) -> bool:
    page = find_tax_page(ctx)
    if page and is_logged_in(page):
        log(f"已登录 ✓ ({page.url[:80]})")
        shot(page, "cdp_login_ok")
        return True
    return False


def main() -> int:
    check_only = "--check" in sys.argv
    log(f"=== login_cdp.py start {datetime.now().isoformat(timespec='seconds')} ===")

    if not cdp_alive():
        if check_only:
            log("CDP Chrome 未运行")
            return 1
        log("CDP Chrome 未在线，拉起专用 Chrome…")
        launch_chrome_manual()
        # 等 CDP 就绪
        deadline = time.time() + 30
        while time.time() < deadline and not cdp_alive():
            time.sleep(1)
        if not cdp_alive():
            log("Chrome CDP 启动失败")
            return 1
        time.sleep(4)

    with sync_playwright() as p:
        browser, ctx, page = connect_cdp(p)
        try:
            if check_logged(ctx):
                return 0
            if check_only:
                log("Chrome 在线但未登录")
                return 1

            print("\n" + "=" * 60, flush=True)
            print("请在弹出的 Chrome 窗口里手动完成登录：", flush=True)
            print("  1. 右上角点【登录】", flush=True)
            print("  2. 企业业务 tab：识别号/身份证/密码已在浏览器记住可自动带出，否则手动输入", flush=True)
            print("  3. 完成滑块/短信验证码", flush=True)
            print(f"脚本轮询等待中（最长 {WAIT_HUMAN_SECONDS // 60} 分钟）…", flush=True)
            print("=" * 60 + "\n", flush=True)

            deadline = time.time() + WAIT_HUMAN_SECONDS
            while time.time() < deadline:
                if check_logged(ctx):
                    log("登录成功，Chrome 保持运行；接下来可执行：declare.py（自动接管）")
                    return 0
                time.sleep(3)
            log(f"等待人工登录超时（{WAIT_HUMAN_SECONDS}s）")
            return 2
        finally:
            try:
                browser.close()  # CDP 连接断开，不杀 Chrome 进程
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
