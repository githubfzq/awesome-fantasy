# login_declare.py — 申报密码登录（状态机版，每步强制验证）
#
# 用法（VM 内，经 PsExec -i 1；参数用 base64 JSON 传，绕开桥接编码问题）：
#   pythonw.exe login_declare.py --args-b64 <base64({"unit":"...","password":"..."})>
# Mac 侧推荐用: scripts/push_run.sh --lib rpa_core.py --args-json '{...}' login_declare.py
#
# 步骤与验证判据（每步验证不过即中止，绝不继续点击）：
#   0 preflight     登录窗存在/可见/enabled、无阻塞模态弹窗
#   1 switch_tab    可见的 TIntelligentSearch（单位选择器仅存在于申报密码登录页）
#   2 open_picker   Tfrm_IntelligentSearchPop 可见 且 列表项数 > 0
#   3 select_unit   弹窗已关闭 且 识别号框被自动带出（长度 >=15 且非占位符）
#   4 fill_password WM_GETTEXTLENGTH == len(password)
#   5 captcha_gate  无验证码框才放行；有验证码框但未提供 --captcha → 拒绝点登录（防密码错误累计锁定）
#   6 click_login   轮询到 Tfrm_MainFrame 可见 = 成功；出现 Tfrm_MsgDlgRich = 被拒（立即停机+冻结现场）
#   7 post_verify   登录窗已关闭 且 主窗可见+enabled
import json
import time

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
MAIN_CLS = "Tfrm_MainFrame"
POP_CLS = "Tfrm_IntelligentSearchPop"
EDIT_CLS = "TXPFamerEditEx"
BTN_CLS = "TITSSpeedButton"
SELECTOR_CLS = "TIntelligentSearch"


# ------------------------------------------------------------------ 定位器
def login_win():
    return R.find_window(LOGIN_CLS, visible_only=True)


def visible_kids(parent_hwnd, cls_prefix):
    return [k for k in R.enum_children(parent_hwnd)
            if k["class"].startswith(cls_prefix) and k["visible"]]


def declare_edits():
    """返回 spDeclare 页的编辑框: {'ident':info,'pwd':info,'captcha':info|None}
    按纵向顺序识别（识别号在上、密码居中、验证码在下），过滤不可见的幽灵副本。"""
    lw = login_win()
    if not lw:
        return {}
    edits = visible_kids(lw["hwnd"], EDIT_CLS)
    # 同一纵向位置的重复副本去重（Delphi 幽灵控件）
    edits.sort(key=lambda w: (w["rect"][1], w["hwnd"]))
    dedup = []
    for e in edits:
        if dedup and abs(e["rect"][1] - dedup[-1]["rect"][1]) <= 5:
            continue
        dedup.append(e)
    out = {"all": dedup}
    if len(dedup) >= 1:
        out["ident"] = dedup[0]
    if len(dedup) >= 2:
        out["pwd"] = dedup[1]
    if len(dedup) >= 3:
        out["captcha"] = dedup[2]
    return out


def login_button():
    """登录钮：编辑框下方、宽度最大的可见 TITSSpeedButton。"""
    lw = login_win()
    if not lw:
        return None
    e = declare_edits()
    floor_y = e["pwd"]["rect"][1] + 80 if e.get("pwd") else lw["rect"][1] + 400
    cands = [b for b in visible_kids(lw["hwnd"], BTN_CLS)
             if b["rect"][1] > floor_y and (b["rect"][2] - b["rect"][0]) >= 150]
    if not cands:
        return None
    cands.sort(key=lambda b: (b["rect"][2] - b["rect"][0]), reverse=True)
    return cands[0]


def ident_value():
    e = declare_edits()
    if not e.get("ident"):
        return None
    return R.wm_get_text(e["ident"]["hwnd"])


def ident_is_filled():
    """识别号被单位联动带出的判据：长度 >=15 且不是占位符文案。"""
    t = ident_value()
    if t and len(t) >= 15 and "识别号" not in t:
        return {"ident_len": len(t), "ident_tail": t[-4:]}
    return None


def captcha_field():
    """验证码框（仅登录失败/异常时出现）。"""
    e = declare_edits()
    c = e.get("captcha")
    if not c:
        return None
    # 第三个编辑框存在即视为验证码行
    return c


# ------------------------------------------------------------------ 步骤实现
def close_known_modal(r):
    """显式关闭已知的『提示信息』弹窗（owner-drawn，pywinauto 坐标不可用，必须真实 rect）。"""
    m = r.blocking_modal()
    if not m:
        return {"closed": False, "reason": "无可见弹窗"}
    btns = [b for b in R.enum_children(m["hwnd"])
            if b["class"] == BTN_CLS and b["visible"]]
    if not btns:
        r.fail("close_modal", "弹窗内未找到确定钮", {"modal": m})
    b = btns[0]
    R.click_at(*R.center(b["rect"]))
    return {"clicked": b["rect"], "modal_hwnd": m["hwnd"]}


def main(r):
    args = R.parse_args_b64()
    unit = args.get("unit") or "修文县关珍养殖场"
    password = args.get("password") or ""
    captcha = args.get("captcha") or ""
    dry_run = bool(args.get("dry_run"))
    auto_close_modal = bool(args.get("auto_close_modal"))
    login_timeout = float(args.get("login_timeout", 45))

    r.emit("params", detail={"unit": unit, "password": R.mask(password),
                            "captcha": R.mask(captcha), "dry_run": dry_run,
                            "auto_close_modal": auto_close_modal,
                            "login_timeout": login_timeout})

    # 已登录则幂等返回，避免重复操作把状态搞乱
    mw = R.find_window(MAIN_CLS, visible_only=True)
    if mw:
        r.emit("already_logged_in", detail=mw)
        return {"logged_in": True, "note": "主界面已可见，无需重复登录"}

    if not password and not dry_run:
        r.fail("preflight", "缺少 password 参数（应由 KeePass 取，勿硬编码）")

    # ---- 0 preflight：环境体检（不点击） ----
    def preflight_ok():
        lw = login_win()
        if not lw:
            return None
        return {"login": lw, "modal": r.blocking_modal()}

    st = r.step("preflight",
                verify=preflight_ok,
                verify_desc="登录窗可见",
                timeout=15, guard=False)
    if st["modal"]:
        if not auto_close_modal:
            r.fail("preflight",
                   "存在阻塞模态弹窗（登录窗被禁用，此时点击全部无效）",
                   {"modal": st["modal"],
                    "hint": "确认弹窗内容后运行 close_modal.py，或传 auto_close_modal=true"})
        r.step("close_modal",
               action=lambda: close_known_modal(r),
               verify=lambda: {"modal_gone": True} if r.blocking_modal() is None else None,
               verify_desc="阻塞弹窗已消失", timeout=8, guard=False)
    if not st["login"]["enabled"]:
        r.fail("preflight", "登录窗 enabled=false（被模态窗禁用或程序忙）",
               {"login": st["login"]})

    # ---- 1 切到「申报密码登录」页 ----
    def click_left_tab():
        # 真实 tab 页签头是 TITSTabControl（自绘，标题读不出，不响应 TCM_* 消息）。
        # 登录窗含两个：左半(x最小)=申报密码登录 / 右半=实名登录。spDeclare(申报密码页)
        # 激活后单位选择器 TIntelligentSearch 才可见。逐候选点击并验证，命中即停。
        lw = login_win()
        tabs = [c for c in R.enum_children(lw["hwnd"]) if "TITSTabControl" in c["class"]]
        if not tabs:
            return {"clicked": None}
        tabs.sort(key=lambda c: c["rect"][0])
        # 1) 每个 tab 控件中心（左=申报密码登录，优先）
        for t in tabs:
            r0 = t["rect"]
            cx, cy = (r0[0] + r0[2]) // 2, (r0[1] + r0[3]) // 2
            R.click_at(cx, cy)
            time.sleep(0.5)
            if declare_page_active():
                return {"clicked": [cx, cy]}
        # 2) 兜底：每个 tab 的左右 1/4、3/4 分位（子标签，如 spAccount/spDeclare 并列）
        for t in tabs:
            r0 = t["rect"]
            for fx in (0.25, 0.75):
                cx = int(r0[0] + (r0[2] - r0[0]) * fx)
                cy = (r0[1] + r0[3]) // 2
                R.click_at(cx, cy)
                time.sleep(0.4)
                if declare_page_active():
                    return {"clicked": [cx, cy]}
        return {"clicked": None}

    def declare_page_active():
        lw = login_win()
        if not lw:
            return None
        sel = visible_kids(lw["hwnd"], SELECTOR_CLS)
        return {"selector_rect": sel[0]["rect"]} if sel else None

    if declare_page_active():
        r.emit("skip", step="switch_tab", reason="已在申报密码登录页")
    else:
        r.step("switch_tab", action=click_left_tab,
               verify=declare_page_active,
               verify_desc="单位选择器 TIntelligentSearch 可见", timeout=8)

    if dry_run:
        e = declare_edits()
        btn = login_button()
        return {"dry_run": True, "logged_in": False,
                "located": {
                    "edits": [x["rect"] for x in e.get("all", [])],
                    "ident": e.get("ident", {}).get("rect"),
                    "pwd": e.get("pwd", {}).get("rect"),
                    "captcha": e.get("captcha", {}).get("rect"),
                    "login_button": btn["rect"] if btn else None,
                },
                "note": "dry_run：仅体检+定位，未做任何点击/输入"}

    # ---- 2 打开单位选择弹窗 ----
    def open_picker():
        lw = login_win()
        sel = visible_kids(lw["hwnd"], SELECTOR_CLS)
        if not sel:
            r.fail("open_picker", "找不到单位选择器 TIntelligentSearch")
        R.click_at(*R.center(sel[0]["rect"]))
        return {"clicked_rect": sel[0]["rect"]}

    def picker_ready():
        p = R.find_window(POP_CLS, visible_only=True)
        if not p:
            return None
        lbs = [k for k in R.enum_children(p["hwnd"])
               if k["class"].startswith("TListBox")]
        if not lbs:
            return None
        items = R.listbox_items(lbs[0]["hwnd"])
        if not items:
            return None
        return {"pop_hwnd": p["hwnd"], "list_hwnd": lbs[0]["hwnd"],
                "item_count": len(items), "items": items[:20]}

    picker = r.step("open_picker", action=open_picker,
                    verify=picker_ready,
                    verify_desc="单位列表弹出且项数>0", timeout=10)

    # ---- 3 选单位 → 识别号自动带出 ----
    def pick_unit():
        items = R.listbox_items(picker["list_hwnd"])
        idx = next((i for i, t in enumerate(items) if unit in (t or "")), None)
        matched_by = "exact"
        if idx is None and len(unit) > 1:
            # 容错：末字差异（例：养殖厂 / 养殖场）
            stem = unit[:-1]
            idx = next((i for i, t in enumerate(items) if stem in (t or "")), None)
            matched_by = "stem:" + stem
        if idx is None:
            r.fail("select_unit", "单位列表中找不到目标单位",
                   {"want": unit, "candidates": items})
        info = R.listbox_click_item(picker["list_hwnd"], idx)
        info.update({"matched_by": matched_by, "text": items[idx]})
        return info

    def unit_selected():
        # 双判据：弹窗已收起 且 识别号已联动带出
        if R.find_window(POP_CLS, visible_only=True):
            return None
        return ident_is_filled()

    r.step("select_unit", action=pick_unit, verify=unit_selected,
           verify_desc="弹窗收起且识别号自动带出(>=15位)", timeout=10)

    # ---- 4 填密码（WM_SETTEXT 绕过中文输入法） ----
    def fill_pwd():
        e = declare_edits()
        if not e.get("pwd"):
            r.fail("fill_password", "找不到密码编辑框", {"edits": e.get("all")})
        R.wm_set_text(e["pwd"]["hwnd"], password)
        return {"hwnd": e["pwd"]["hwnd"], "rect": e["pwd"]["rect"],
                "wrote": R.mask(password)}

    def pwd_len_ok():
        e = declare_edits()
        if not e.get("pwd"):
            return None
        n = R.wm_get_len(e["pwd"]["hwnd"])
        return {"len": n} if n == len(password) else None

    r.step("fill_password", action=fill_pwd, verify=pwd_len_ok,
           verify_desc="密码框长度==%d" % len(password), timeout=5)

    # ---- 5 验证码闸门（安全阀：防明知失败仍点登录导致锁定） ----
    cf = captcha_field()
    if cf:
        if not captcha:
            r.fail("captcha_gate",
                   "检测到验证码框但未提供验证码，已拒绝点登录（避免累计密码错误次数导致锁定）",
                   {"captcha_rect": cf["rect"],
                    "hint": "运行 captcha.py 截图 → pull_file.sh 回传识别 → 带 captcha 参数重跑"})

        def fill_captcha():
            R.wm_set_text(cf["hwnd"], captcha)
            return {"rect": cf["rect"], "wrote": R.mask(captcha)}

        def captcha_len_ok():
            n = R.wm_get_len(cf["hwnd"])
            return {"len": n} if n == len(captcha) else None

        r.step("fill_captcha", action=fill_captcha, verify=captcha_len_ok,
               verify_desc="验证码框长度==%d" % len(captcha), timeout=5)
    else:
        r.emit("captcha_gate", detail={"present": False,
                                      "note": "首次正常登录无验证码框，放行"})

    # ---- 6 点登录 → 轮询三态结局 ----
    def do_login():
        b = login_button()
        if not b:
            r.fail("click_login", "找不到登录按钮")
        R.click_at(*R.center(b["rect"]))
        return {"button_rect": b["rect"]}

    def login_outcome():
        m = R.find_window(MAIN_CLS, visible_only=True)
        if m:
            return {"outcome": "logged_in", "main": m}
        modal = r.blocking_modal()
        if modal:
            return {"outcome": "rejected", "modal": modal}
        return None

    res = r.step("click_login", action=do_login, verify=login_outcome,
                 verify_desc="主界面可见(成功) 或 出现提示弹窗(被拒)",
                 timeout=login_timeout, interval=0.5)

    if res["outcome"] == "rejected":
        r.fail("click_login",
               "登录被拒：出现提示弹窗（可能密码错误/需验证码/网络异常）",
               {"modal": res["modal"],
                "hint": "先看 snapshot 截图确认弹窗文案，勿盲目重试——密码错误累计会锁定账号"})

    # ---- 7 登录后终态复核 ----
    def post_ok():
        lw = R.find_window(LOGIN_CLS, visible_only=True)
        mw = R.find_window(MAIN_CLS, visible_only=True)
        if lw:
            return None
        if mw and mw["enabled"]:
            return {"main": mw}
        return None

    fin = r.step("post_verify", verify=post_ok,
                 verify_desc="登录窗关闭且主窗可见+enabled", timeout=20)

    return {"logged_in": True, "main_rect": fin["main"]["rect"],
            "unit": unit}


if __name__ == "__main__":
    R.Runner("login_declare",
             expected_windows={LOGIN_CLS, MAIN_CLS, POP_CLS}).run(main)
