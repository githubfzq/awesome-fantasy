# check_status.py — 启动扣缴端 → 申报密码登录 → 查 2026-07 申报状态（状态机版）
#
# 依赖: rpa_core.py（--lib 推送）；并复用 login_declare.py 的定位/验证逻辑。
# 设计已审查 PASS；本脚本只产出 + 运行说明，真实点击由 --args 控制。
#
# 运行（Mac 侧，经 push_run.sh；密码由 keepass-lookup 运行时取，绝不硬编码/落盘）:
#   干跑:  cd ~/.workbuddy/skills/withholding-login/scripts && \
#          ./push_run.sh --lib rpa_core.py --args-json '{"dry_run":true}' check_status.py
#   正式: 见同目录 run_check_status.sh（运行时从 KeePass 取密注入 base64 参数）
#
# 行为契约（继承 rpa_core）:
#   每步 = guard(统一阻塞弹窗) → pre → action → verify(条件轮询+超时) → 日志；
#   验证不过 = step_fail + 冻结现场(窗口树 JSON + 全屏 PNG)。Phase C 90s 预算 + 加载瞬态轮询 + unsupported 降级。
import json
import os
import sys
import time
import subprocess

import rpa_core as R
import login_declare as LD  # 复用 locators / 验证逻辑

LOGIN_CLS = LD.LOGIN_CLS
MAIN_CLS = LD.MAIN_CLS
POP_CLS = LD.POP_CLS
EDIT_CLS = LD.EDIT_CLS
BTN_CLS = LD.BTN_CLS
SELECTOR_CLS = LD.SELECTOR_CLS

# 统一阻塞弹窗枚举：同时认 Tfrm_MsgDlgRich 与 Tfrm_MsgDlg（修复只认 Rich 导致点击穿透）
MODAL_CLASSES = {"Tfrm_MsgDlgRich", "Tfrm_MsgDlg"}

EXE = r"C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe"
EXE_DIR = r"C:\ITSKHD\EPPortal_DS3.0"
PSEXEC = r"C:\rpa\pstools\PsExec64.exe"
VM_SHOT_DIR = r"C:\rpa\screenshots"


# ----------------------------------------------------------------- 增强 Runner
class RpaRunner(R.Runner):
    """统一 blocking_modal：同时枚举两类 owner-drawn 弹窗，修复点击穿透。"""

    def blocking_modal(self):
        for w in R.enum_top_windows():
            if w["class"] in MODAL_CLASSES and w["visible"]:
                return w
        return None

    def guard(self, step):
        m = self.blocking_modal()
        if m:
            self.fail(step,
                      "存在阻塞模态弹窗(%s)，已中止（禁止在被遮挡状态下盲点）" % m["class"],
                      {"modal": m,
                       "hint": "先关闭弹窗/确认原因再重试"})


# --------------------------------------------------------------------- 工具
def normalize_period(s):
    """2026-07 / 2026年07月 / 202607 -> 2026-07"""
    s = (s or "").strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 6:
        return "%s-%s" % (digits[:4], digits[4:6])
    return s or "2026-07"


def enum_all_descendants(hwnd):
    out = []

    def rec(h):
        for c in R.enum_children(h):
            out.append(c)
            rec(c["hwnd"])

    rec(hwnd)
    return out


def find_grid(main_hwnd):
    kids = enum_all_descendants(main_hwnd)
    grids = [k for k in kids if k["visible"] and
             ("Grid" in k["class"] or "TDBGrid" in k["class"]
              or "VirtualStringTree" in k["class"] or "TVirtual" in k["class"])]
    if not grids:
        return None
    grids.sort(key=lambda g: (g["rect"][2] - g["rect"][0]) * (g["rect"][3] - g["rect"][1]),
               reverse=True)
    return grids[0]


def save_screenshot(r, main_hwnd, grid, period, reason):
    """裁剪 grid 客户区截图；grid 为 None 时退化为主窗全图。落盘 VM 路径并回报。"""
    os.makedirs(VM_SHOT_DIR, exist_ok=True)
    fname = "status_%s_%s.png" % (period, reason)
    path = os.path.join(VM_SHOT_DIR, fname)
    try:
        from PIL import ImageGrab
        if grid is not None:
            rc = tuple(grid["rect"])
            img = ImageGrab.grab(bbox=rc)
        else:
            rc = tuple(R.rect_of(main_hwnd))
            img = ImageGrab.grab(bbox=rc)
        img.save(path)
        r.emit("snapshot_shot", detail={"path": path, "rect": list(rc), "grid": bool(grid)})
        return path
    except Exception as e:
        r.emit("snapshot_error", detail={"error": repr(e)})
        return None


# --------------------------------------------------------------- Phase A 启动
def phase_a_launch(r, args):
    timeout = float(args.get("launch_timeout", 45))
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if lw and lw["enabled"] and r.blocking_modal() is None:
        r.emit("skip", step="phase_a_launch", reason="登录窗已可见且未遮挡，跳过启动")
        return {"already_running": True}

    def launch_exe():
        # PsExec -i 1 -d detached 拉起，避免随脚本退出被杀（防 137）
        cmd = '%s -i 1 -d -accepteula -w %s %s' % (PSEXEC, EXE_DIR, EXE)
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            return {"launch_error": repr(e)}
        return {"cmd": cmd}

    def login_ready():
        w = R.find_window(LOGIN_CLS, visible_only=True)
        if not w or not w["enabled"]:
            return None
        if r.blocking_modal() is not None:   # 含 Tfrm_MsgDlg / Tfrm_MsgDlgRich
            return None
        return {"login": w}

    r.step("phase_a_launch", action=launch_exe, verify=login_ready,
           verify_desc="Tfrm_LoginViewer 可见+enabled 且无非预期挡窗",
           timeout=timeout, interval=0.5, guard=False)
    return {"launched": True}


# ----------------------------------------------------- Phase B 申报密码登录
def _close_modal_step(r):
    def do_close():
        return LD.close_known_modal(r)
    def modal_gone():
        return {"gone": True} if r.blocking_modal() is None else None
    r.step("close_modal", action=do_close, verify=modal_gone,
           verify_desc="阻塞弹窗已消失", timeout=8, guard=False)


def phase_b_login(r, args, dry_run):
    password = args.get("password") or ""
    unit = args.get("unit") or ""          # 留空 => 运行时从列表发现（不写死单位名）
    captcha = args.get("captcha") or ""
    auto_close = bool(args.get("auto_close_modal"))
    login_timeout = float(args.get("login_timeout", 45))

    # 0 preflight
    def preflight_ok():
        lw = LD.login_win()
        if not lw:
            return None
        return {"login": lw, "modal": r.blocking_modal()}
    st = r.step("preflight", verify=preflight_ok, verify_desc="登录窗可见",
                timeout=15, guard=False)
    if st["modal"]:
        if not auto_close:
            r.fail("preflight", "存在阻塞模态弹窗（登录窗被禁用，点击全部无效）",
                   {"modal": st["modal"],
                    "hint": "确认弹窗后运行 close_modal.py，或传 auto_close_modal=true"})
        _close_modal_step(r)
    if not st["login"]["enabled"]:
        r.fail("preflight", "登录窗 enabled=false（被模态窗禁用或程序忙）",
               {"login": st["login"]})

    # 1 切到「申报密码登录」页
    def click_left_tab():
        lw = LD.login_win()
        tabs = LD.visible_kids(lw["hwnd"], "TITSTabControl")
        if tabs:
            tabs.sort(key=lambda t: t["rect"][0])
            rc = tabs[0]["rect"]
            pt = (rc[0] + (rc[2] - rc[0]) // 4, (rc[1] + rc[3]) // 2)
        else:
            rc = lw["rect"]
            pt = (rc[0] + (rc[2] - rc[0]) // 4, rc[1] + 70)
        R.click_at(*pt)
        return {"clicked": list(pt)}

    def declare_page_active():
        lw = LD.login_win()
        if not lw:
            return None
        sel = LD.visible_kids(lw["hwnd"], SELECTOR_CLS)
        return {"selector_rect": sel[0]["rect"]} if sel else None

    # 干跑：只体检+定位，不点不输
    if dry_run:
        e = LD.declare_edits()
        b = LD.login_button()
        return {"dry_run": True, "logged_in": False,
                "located": {
                    "edits": [x["rect"] for x in e.get("all", [])],
                    "ident": e.get("ident", {}).get("rect"),
                    "pwd": e.get("pwd", {}).get("rect"),
                    "captcha": e.get("captcha", {}).get("rect"),
                    "login_button": b["rect"] if b else None,
                },
                "note": "dry_run：未做任何点击/输入"}

    if declare_page_active():
        r.emit("skip", step="switch_tab", reason="已在申报密码登录页")
    else:
        r.step("switch_tab", action=click_left_tab, verify=declare_page_active,
               verify_desc="单位选择器 TIntelligentSearch 可见", timeout=8)

    # 2 打开单位选择弹窗
    def open_picker():
        lw = LD.login_win()
        sel = LD.visible_kids(lw["hwnd"], SELECTOR_CLS)
        if not sel:
            r.fail("open_picker", "找不到单位选择器 TIntelligentSearch")
        R.click_at(*R.center(sel[0]["rect"]))
        return {"clicked_rect": sel[0]["rect"]}

    def picker_ready():
        p = R.find_window(POP_CLS, visible_only=True)
        if not p:
            return None
        lbs = [k for k in R.enum_children(p["hwnd"]) if k["class"].startswith("TListBox")]
        if not lbs:
            return None
        items = R.listbox_items(lbs[0]["hwnd"])
        if not items:
            return None
        return {"pop_hwnd": p["hwnd"], "list_hwnd": lbs[0]["hwnd"],
                "item_count": len(items), "items": items[:20]}

    picker = r.step("open_picker", action=open_picker, verify=picker_ready,
                    verify_desc="单位列表弹出且项数>0", timeout=10)

    # 3 选单位（从列表发现，不写死）
    def pick_unit():
        items = R.listbox_items(picker["list_hwnd"])
        idx, matched_by = None, "first"
        if unit:
            idx = next((i for i, t in enumerate(items) if unit in (t or "")), None)
            matched_by = "exact"
            if idx is None and len(unit) > 1:
                stem = unit[:-1]
                idx = next((i for i, t in enumerate(items) if stem in (t or "")), None)
                matched_by = "stem:" + stem
        if idx is None:
            idx = 0                      # 发现式：取列表首项
            matched_by = "discover_first"
        if idx >= len(items):
            r.fail("select_unit", "单位索引越界", {"items": items})
        info = R.listbox_click_item(picker["list_hwnd"], idx)  # 真实点击触发 OnClick 带出识别号
        info.update({"matched_by": matched_by, "text": items[idx]})
        return info

    def unit_selected():
        if R.find_window(POP_CLS, visible_only=True):
            return None
        return LD.ident_is_filled()

    r.step("select_unit", action=pick_unit, verify=unit_selected,
           verify_desc="弹窗收起且识别号自动带出(>=15位)", timeout=10)

    # 4 填密码（WM_SETTEXT 绕过中文输入法；密码来自 KeePass，不落明文）
    if not password:
        r.fail("fill_password", "缺少 password（应由 KeePass 运行时取，勿硬编码）",
               {"hint": "经 run_check_status.sh 注入，或传 --args-b64 {\"password\":...}"})

    def fill_pwd():
        e = LD.declare_edits()
        if not e.get("pwd"):
            r.fail("fill_password", "找不到密码编辑框", {"edits": e.get("all")})
        R.wm_set_text(e["pwd"]["hwnd"], password)
        return {"wrote": R.mask(password)}

    def pwd_len_ok():
        e = LD.declare_edits()
        if not e.get("pwd"):
            return None
        n = R.wm_get_len(e["pwd"]["hwnd"])
        return {"len": n} if n == len(password) else None

    r.step("fill_password", action=fill_pwd, verify=pwd_len_ok,
           verify_desc="密码框长度==%d" % len(password), timeout=5)

    # 5 验证码闸门（安全阀：无码不点登录，防锁定）
    cf = LD.captcha_field()
    if cf:
        if not captcha:
            r.fail("captcha_gate", "检测到验证码框但未提供验证码，已拒绝点登录（避免累计错误锁定）",
                   {"captcha_rect": cf["rect"],
                    "hint": "captcha.py 截图→pull_file.sh 回传识别→带 captcha 重跑"})
        R.wm_set_text(cf["hwnd"], captcha)
        r.step("fill_captcha", verify=lambda: {"len": R.wm_get_len(cf["hwnd"])} if R.wm_get_len(cf["hwnd"]) == len(captcha) else None,
               verify_desc="验证码框长度==%d" % len(captcha), timeout=5,
               action=lambda: None, allow_no_verify=False)
    else:
        r.emit("captcha_gate", detail={"present": False, "note": "首次正常登录无验证码框，放行"})

    # 6 点登录 → 三态轮询
    def do_login():
        b = LD.login_button()
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
        r.fail("click_login", "登录被拒：出现提示弹窗",
               {"modal": res["modal"], "hint": "看 snapshot 截图确认文案，勿盲目重试"})

    # 7 登录后终态复核
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
    return {"logged_in": True, "main_rect": fin["main"]["rect"]}


# --------------------------------------------- Phase C 导航到申报状态查询
def phase_c_query(r, args):
    period = normalize_period(args.get("period") or "2026-07")
    budget = float(args.get("phase_c_timeout", 90))
    t0 = time.time()
    left = lambda: max(0.0, budget - (time.time() - t0))

    mw = R.find_window(MAIN_CLS, visible_only=True)
    if not mw:
        r.fail("phase_c_nav", "未找到主窗 Tfrm_MainFrame（登录可能未成功）", {})
    main_hwnd = mw["hwnd"]

    # 1) 运行时发现含『申报』『查询』文本节点
    kids = enum_all_descendants(main_hwnd)
    nodes = [k for k in kids if k["title"] and k["visible"]]
    q = [k for k in nodes if "查询" in k["title"]]
    both = [k for k in q if "申报" in k["title"]]
    targets = both or q
    r.emit("phase_c_nodes",
           detail={"target_count": len(targets),
                   "targets": [{"class": t["class"], "title": t["title"], "rect": t["rect"]} for t in targets[:10]],
                   "sample": [{"class": n["class"], "title": n["title"]} for n in nodes[:30]]})

    if not targets:
        r.emit("phase_c_unsupported", detail={"reason": "no_query_node"})
        png = save_screenshot(r, main_hwnd, None, period, "unsupported_no_query_node")
        return {"status": "unsupported", "reason": "no_query_node",
                "screenshot_vm_path": png}

    # 2) 进查询页（点击首个目标节点；加载中瞬态轮询）
    node = targets[0]

    def enter_query():
        R.click_at(*R.center(node["rect"]))
        return {"clicked": node["rect"], "title": node["title"]}

    def query_page_open():
        ks = enum_all_descendants(main_hwnd)
        loading = [k for k in ks if k["visible"]
                   and any(w in (k["title"] or "") for w in ("加载中", "正在加载", "处理中", "请稍候"))]
        return None if loading else {"loading_gone": True}

    r.step("phase_c_enter", action=enter_query, verify=query_page_open,
           verify_desc="进入查询页（加载中瞬态消失）", timeout=min(30, left()), interval=0.5)

    # 3) 设属期（归一化）；无编辑框则 unsupported 降级（仍截图交人工）
    def editable_period():
        ks = enum_all_descendants(main_hwnd)
        return [k for k in ks if k["visible"]
                and (k["class"] == EDIT_CLS or k["class"].startswith("TEdit"))]

    edits = editable_period()
    if not edits:
        r.emit("phase_c_unsupported", detail={"reason": "no_period_edit", "period": period})
        png = save_screenshot(r, main_hwnd, None, period, "unsupported_no_period_edit")
        return {"status": "unsupported", "reason": "no_period_edit",
                "screenshot_vm_path": png}

    edits.sort(key=lambda e: e["rect"][1])

    def set_period():
        R.wm_set_text(edits[0]["hwnd"], period)
        return {"hwnd": edits[0]["hwnd"], "rect": edits[0]["rect"]}

    def period_ok():
        txt = R.wm_get_text(edits[0]["hwnd"])
        return {"text": txt} if period in (txt or "") or txt == period else None

    r.step("phase_c_set_period", action=set_period, verify=period_ok,
           verify_desc="属期编辑框文本包含 %s" % period, timeout=min(15, left()))

    # 4) 截图（裁剪 grid 客户区）→ 回报 VM 路径（Mac 侧经 pull_file.sh 回传）
    grid = find_grid(main_hwnd)
    png = save_screenshot(r, main_hwnd, grid, period, "status")
    if not png:
        r.fail("phase_c_shot", "截图保存失败（PIL/权限）", {})
    return {"status": "captured", "period": period,
            "screenshot_vm_path": png,
            "pull_cmd": "pull_file.sh %s <workspace>/screenshots/status_%s.png" % (png, period),
            "grid": grid["rect"] if grid else None}


# --------------------------------------------------------------------- main
def main(r):
    args = R.parse_args_b64()
    dry_run = bool(args.get("dry_run"))
    period = normalize_period(args.get("period") or "2026-07")
    r.emit("params", detail={"dry_run": dry_run, "period": period,
                             "password": R.mask(args.get("password") or ""),
                             "unit": args.get("unit") or "(from-list)",
                             "auto_close_modal": bool(args.get("auto_close_modal"))})

    mw = R.find_window(MAIN_CLS, visible_only=True)
    if mw and mw["enabled"]:
        r.emit("already_logged_in", detail=mw)
    else:
        phase_a_launch(r, args)
        out_b = phase_b_login(r, args, dry_run)
        if dry_run:
            return {"dry_run": True, **out_b}

    out_c = phase_c_query(r, args)
    return {"period": period, **out_c}


if __name__ == "__main__":
    RpaRunner("check_status",
              expected_windows={LOGIN_CLS, MAIN_CLS, POP_CLS}).run(main)
