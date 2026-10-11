#!/usr/bin/env python3
"""common.py — 贵州省电子税务局季度申报 RPA 公共层。

职责：
- persistent context 浏览器启动（登录态持久化于 ~/Documents/gtax-rpa/profile）
- 凭据获取（keepass agents.kdbx「贵州电子税务局网站」条目，仅内存）
- 截图 / 日志 / 通用等待与断言辅助

安全边界：
- 凭据只在进程内存中传递，绝不 echo、绝不落盘
- 所有对外不可逆动作（提交申报）由 declare.py 的确认门控制
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext

# ---------- 代理清除（必须最先执行） ----------
# 沙箱/系统会注入 http_proxy 环境变量，导致：CDP 连接失败、登录风控组件「请求失败」、
# urllib 检测 127.0.0.1 被劫持。税务局必须直连。
for _k in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

# ---------- 路径 ----------
SKILL_DIR = Path(__file__).resolve().parent.parent
RUN_DIR = Path.home() / "Documents" / "gtax-rpa"
PROFILE_DIR = Path.home() / "Library" / "Application Support" / "gtax-rpa" / "profile"  # 浏览器 persistent profile（登录态；放 Documents 会被安全中心拦截临时文件清理）
SHOTS_DIR = RUN_DIR / "shots"          # 关键步截图
ARTIFACTS_DIR = RUN_DIR / "artifacts"  # 财报 Excel / 下载模板
LOG_FILE = RUN_DIR / "run.log"

TAX_URL = "https://tpass.guizhou.chinatax.gov.cn:8443/#/"
LOGIN_URL_KEYWORD = "#/login"

# ---------- KeePass ----------
KP_CLI = "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli"
KP_DB = "/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agents.kdbx"
KP_MASTER_FILE = "/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agent_main_pass"
KP_ENTRY = "贵州电子税务局网站"

for d in (RUN_DIR, PROFILE_DIR, SHOTS_DIR, ARTIFACTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ---------- 日志 ----------
def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def shot(page: Page, name: str) -> Path:
    p = SHOTS_DIR / f"{datetime.now().strftime('%H%M%S')}_{name}.png"
    try:
        page.screenshot(path=str(p))
        log(f"shot -> {p.name}")
    except Exception as e:  # 页面正在跳转时截图可能失败，不致命
        log(f"shot {name} failed: {e}")
    return p


# ---------- 凭据 ----------
def get_credentials() -> dict:
    """从 keepass 取凭据： UserName=扣缴义务人识别号(统一社会信用代码)，
    Password=网站密码，Notes 内含身份证号。只在内存中返回。
    注意：全量 show -s 输出带字段名（Title/UserName/Password/URL/Notes），
    第一行是「请输入密码…」提示行，用行首锚定解析。"""
    cmd = [KP_CLI, "show", "-s", KP_DB, KP_ENTRY]
    with open(KP_MASTER_FILE, "rb") as mf:
        master = mf.read().splitlines()[0]
    out = subprocess.run(cmd, input=master, capture_output=True).stdout.decode("utf-8", "replace")
    def grab(key):
        m = re.search(rf"^\s*{key}:\s*(.+?)\s*$", out, re.M)
        return m.group(1).strip() if m else ""
    cred = {
        "uscc": grab("UserName"),          # 扣缴义务人识别号 / 统一社会信用代码
        "password": grab("Password"),      # 企业电子税务网站密码
        "id_card": "",                     # 身份证号（Notes 解析）
    }
    m = re.search(r"身份证号[:：]\s*(\d{17}[\dXx])", out)
    if m:
        cred["id_card"] = m.group(1)
    missing = [k for k in ("uscc", "password", "id_card") if not cred[k]]
    if missing:
        raise RuntimeError(f"keepass 凭据字段缺失: {missing}（检查条目 {KP_ENTRY}）")
    log(f"credentials loaded: uscc_len={len(cred['uscc'])} id_len={len(cred['id_card'])} pw_len={len(cred['password'])}")
    return cred


# ---------- CDP 接管模式（瑞数风控首选：人工登录 + 脚本接管） ----------
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MANUAL_PROFILE = Path.home() / "Library" / "Application Support" / "gtax-rpa" / "chrome-manual"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"


def cdp_alive() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2)
        return True
    except Exception:
        return False


def launch_chrome_manual() -> None:
    """启动专用 Chrome（独立 profile，不动日常 Chrome 数据），开放 CDP。"""
    MANUAL_PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        CHROME_BIN,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={MANUAL_PROFILE}",
        "--ignore-certificate-errors",
        "--no-first-run", "--no-default-browser-check",
        "--start-maximized",
        TAX_URL,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_cdp(pw):
    """连接已运行的 Chrome，返回 (context, page)。page 优先选税务站点标签页。"""
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = None
    for pg in ctx.pages:
        if "chinatax.gov.cn" in pg.url:
            page = pg
            break
    if page is None:
        page = ctx.new_page()
        page.goto(TAX_URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(6000)
    return browser, ctx, page


# ---------- 浏览器 ----------
LAUNCH_ARGS = [
    "--ignore-certificate-errors",
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
    "--no-proxy-server",  # 税务局必须直连：走本机代理(如 v2rayN)会导致登录风控组件「请求失败」
]


def open_browser(pw, headless: bool = False) -> BrowserContext:
    """persistent context：登录态、瑞数 cookie 全部持久化。
    用真实 Chrome 内核（channel=chrome）：Chromium for Testing 指纹会被
    瑞数/风控识别导致验证组件「请求失败」。使用独立 profile，不影响日常 Chrome。"""
    try:
        return pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            headless=headless,
            ignore_https_errors=True,
            args=LAUNCH_ARGS,
            no_viewport=True,
            slow_mo=120,
        )
    except Exception as e:
        log(f"channel=chrome 启动失败（{e}），回退 Chromium for Testing")
        return pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            ignore_https_errors=True,
            args=LAUNCH_ARGS,
            no_viewport=True,
            slow_mo=120,
        )


def is_logged_in(page: Page) -> bool:
    """登录成功判据（严格）：URL 离开 /login 路由，且 body 出现工作台正向特征词。
    注意不能用「首页/欢迎」这类宽松词——登录页的「返回首页」会造成误判。"""
    try:
        url = page.url
        if LOGIN_URL_KEYWORD in url:
            return False
        txt = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
        for kw in ("我的待办", "工作台"):
            if kw in txt:
                return True
        return False
    except Exception:
        return False


def goto_home(page: Page, timeout_ms: int = 90000, max_retry: int = 4) -> None:
    """打开首页；瑞数反爬偶发放行失败（页面空白），检测到空白自动 reload 重试。"""
    page.goto(TAX_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    for i in range(max_retry):
        page.wait_for_timeout(6000)
        txt = body_text(page)
        if len(txt) > 50:
            log(f"home rendered ok (try {i + 1}), body_len={len(txt)}")
            return
        log(f"home blank (try {i + 1}) — 瑞数未放行，reload 重试")
        try:
            page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as e:
            log(f"reload failed: {e}")
    raise RuntimeError(f"首页连续 {max_retry} 次渲染失败（瑞数拦截），请稍后再试")


def goto_login(page: Page, timeout_ms: int = 90000) -> None:
    """进入登录页。双保险：首页点「登录」 → 失败则直接导航 #/login 路由。
    返回时保证登录表单（统一社会信用代码输入框）已出现。"""
    if LOGIN_URL_KEYWORD in page.url:
        return

    def form_ready() -> bool:
        try:
            return page.get_by_placeholder("统一社会信用代码/纳税人识别号").count() > 0
        except Exception:
            return False

    # 路线A：首页点击
    try:
        page.locator("text=登录").first.click(timeout=8000)
        page.wait_for_timeout(4000)
        if form_ready():
            return
    except Exception as e:
        log(f"首页点击登录失败（{type(e).__name__}），改走直连路由")

    # 路线B：直接导航登录路由（循环重试渲染）
    for i in range(4):
        page.goto(TAX_URL + "login", wait_until="domcontentloaded", timeout=timeout_ms)
        for _ in range(3):
            page.wait_for_timeout(5000)
            if form_ready():
                log(f"登录页表单就绪 (route B, try {i + 1})")
                return
        log(f"登录页空白 (try {i + 1})，reload")
        try:
            page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
    raise RuntimeError("登录页表单始终未出现（瑞数持续拦截）")


# ---------- 通用页面操作 ----------
def body_text(page: Page) -> str:
    try:
        return page.evaluate("() => document.body ? document.body.innerText : ''") or ""
    except Exception:
        return ""


def click_text(page: Page, text: str, exact: bool = False, timeout: int = 10000):
    """按可见文本点击；exact=True 时要求完全匹配。返回 locator。"""
    loc = page.get_by_text(text, exact=exact).first
    loc.wait_for(state="visible", timeout=timeout)
    loc.click()
    return loc


def fill_by_placeholder(page: Page, placeholder: str, value: str, timeout: int = 10000):
    loc = page.get_by_placeholder(placeholder).first
    loc.wait_for(state="visible", timeout=timeout)
    loc.click()
    loc.fill(value)
    return loc


def click_button(page: Page, text: str, timeout: int = 10000):
    """点按钮（button/a/.el-button），按文本匹配。"""
    loc = page.locator(f"button:has-text('{text}'), a:has-text('{text}'), .el-button:has-text('{text}')").first
    loc.wait_for(state="visible", timeout=timeout)
    loc.click()
    return loc


def dump_visible_texts(page: Page, max_len: int = 25) -> list:
    """dump 可见短文本元素（探查/排错用）。"""
    items = page.evaluate(
        """(ml) => Array.from(document.querySelectorAll('button,a,span,div,li,td,th,[role=button],[role=tab]'))
            .filter(e => { const r=e.getBoundingClientRect();
                return r.width>0 && r.height>0 && e.innerText && e.innerText.trim().length>0
                       && e.innerText.trim().length<ml && e.children.length===0; })
            .map(e => { const r=e.getBoundingClientRect();
                return {t:e.innerText.trim(), x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)}; })""",
        max_len,
    )
    seen, out = set(), []
    for it in items:
        k = (it["t"], it["x"], it["y"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def wait_disappear(page: Page, text: str, timeout_ms: int = 30000) -> bool:
    """等待包含指定文本的元素消失（如 loading、弹窗）。"""
    try:
        page.locator(f"text={text}").first.wait_for(state="hidden", timeout=timeout_ms)
        return True
    except Exception:
        return False


def quarterly_period(today: datetime | None = None) -> tuple[str, str]:
    """根据当前日期推断刚结束的季度所属期。
    季度申报：每 3 个月过后的下一月 15 日前申报上一个季度。
    例：2026-10 -> 所属期 2026-07-01 ~ 2026-09-30。"""
    d = today or datetime.now()
    # 当前季度起点
    q_start_month = (d.month - 1) // 3 * 3 + 1
    # 刚结束的季度 = 当前季度起点往前推 3 个月
    end_y, end_m = d.year, q_start_month - 1
    if end_m <= 0:
        end_y, end_m = end_y - 1, end_m + 12
    start_m = end_m - 2
    start_y = end_y
    if start_m <= 0:
        start_y, start_m = start_y - 1, start_m + 12
    start = f"{start_y}-{start_m:02d}-01"
    end = f"{end_y}-{end_m:02d}-31" if end_m in (1, 3, 5, 7, 8, 10, 12) else f"{end_y}-{end_m:02d}-30"
    return start, end
