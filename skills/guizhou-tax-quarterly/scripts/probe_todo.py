#!/usr/bin/env python3
"""probe_todo.py — 登录后探查「我的待办」页面结构（开发辅助，正式运行不需要）。"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *  # noqa
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        goto_home(page)
        log(f"url: {page.url}")
        if not is_logged_in(page):
            log("未登录！请先跑 login.py")
            shot(page, "probe_not_logged_in")
            ctx.close()
            return 1
        txt = body_text(page)
        log("=== BODY (first 4000) ===")
        print(txt[:4000])
        log("=== CLICKABLES ===")
        for it in dump_visible_texts(page, 40):
            print(it)
        shot(page, "probe_todo")
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
