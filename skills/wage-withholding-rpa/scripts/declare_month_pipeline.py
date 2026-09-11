# -*- coding: utf-8 -*-
# declare_month_pipeline.py — 2026-09 申报期（税款所属期 2026年08月）综合所得（工资薪金）
#   端到端申报流水线（VM 侧内核）。由 Mac 侧 declare_month.sh 按阶段驱动。
#
# 阶段（args: {"stage": ...}）:
#   preflow  登录后：月份门 → 进模块 → 步骤1 → 点「填写」自判草稿（幂等门）→
#            [无草稿] 向导选①复制上月 → 断言选中 → 导入 → 结果框 N≥1∧M==0(硬门) →
#            【关闭】(967,600, 用户权威流程 G7/T2) → 明细页截图 → 返回 → 网格截图
#            → status=copy_done_need_visual（等编排端视觉确认 填写人数==1∧李关珍）
#   finish   （visual_ok=true 后）进步骤2 → 三险一金【继续算税】→ 计税收敛 → E14 memo 翻转 →
#            步骤4 双门（memo 无负态 ∧ 发送钮 enabled∧visible）→ 发送（今日用户显式事先授权，
#            授权记录写日志）→ 终态等待（正向白名单/未知即冻结，绝不重发）
#   recheck  退出模块 → 重进综合所得申报 → 步骤4 再读数 + 截图（第二次独立读数）
#   dry_run  （任意 stage 参数下 dry_run=true）0 真实点击：只读门 + 定位器意图计划
#
# 今日裁决（2026-09-12 用户指令，优先级最高）:
#   1) 忽略历史执行状态，从 0 开始：干净关闭→全新启动→全新登录→从申报第一步做起。
#   2) 发送确认门被显式事先授权取代：硬门全过即直接发送，授权记录写入日志与报告。
#   3) G3b+ 收窄：硬门 = 复制证据（结果框「成功复制【N】条，失败【0】条」N≥1 ∧ 网格
#      填写人数==1 ∧ 人员为李关珍[截图判读]）。复制证据成立后收入合计 0.00 属预期
#      （上月记录本身为 0，G1 数据口径=复制上月，用户 G8 已确认），照常发送。
#      复制 0 条 / 失败 / 填写人数≠1 → 停机冻结。
#   4) 其余安全阀不变：月份必须实测 2026年08月（不符停机绝不改）；止于申报成功无缴款；
#      不带专项附加扣除（严禁点【预填扣除信息】）；发送后负态/未知态绝不重发；
#      未知模态停机冻结；通道每次调用过 run_id 新鲜度门（Mac 驱动实现）。
#
# 工程契约：每步 action/verify/timeout/fail-fast；JSONL 日志（C:\rpa\logs\<run_id>.jsonl）；
#   冻结现场（顶层窗 JSON + 全屏 PNG）；密钥不经过本脚本（登录属上游 auto_login）；
#   定位 = 运行时控件树 + 主窗/弹窗原点相对偏移（容忍窗口整体平移，尺寸做硬断言）。
import os
import re
import json
import time
import ctypes
import shutil

import rpa_core as R

user32 = ctypes.windll.user32
BM_GETCHECK = 0x00F0

# ---- 窗口类（全部实测自 discovery/*.json，勿凭记忆改动） ----
MAIN_CLS = "Tfrm_MainFrame"
LOGIN_CLS = "Tfrm_LoginViewer"
MODAL_CLS = "Tfrm_MsgDlgRich"
WIZ_CLS = "TFrm_ImportConfig"
BOX_CLS = "TfrmBase"
MEMO_CLS = "TXPFarmerMemoEx"
DT_CLS = "TXPFarmerDTPicker"
VST_CLS = "TVirtualStringTree"
GUIDE_CLS = "TGuideButton"
REPORT_CLS = "TFrm_YKYJView_ReportFill"   # 明细页
STEP1_CLS = "Tfrm_SelectSDXM"
STEP2_CLS = "Tfrm_YKYJCalcTax"
STEP4_CLS = "Tfrm_YKYJReportDeclare"
NSR_CLS = "TfrmNsrMgrView"
IGNORE_CLS = {"Shell_TrayWnd", "Progman", "TFormShadow",
              "Windows.UI.Core.CoreWindow", "TApplication"}   # T9: IME 候选窗等
BTN_PREFIXES = ("TITSSpeedButton", "TModalSpeedButton",
                "TModalSpeedButtonRound", "TButton", "TBitBtn")

EXPECT_MONTH = "2026年08月"
PIPE_DIR = r"\Mac\Home\Documents\rpa\pipeline"      # VM 侧共享盘 → Mac ~/Documents/rpa/pipeline
MAC_PIPE = "~/Documents/rpa/pipeline"

# ---- 相对几何（主窗/弹窗原点相对偏移，来源 constraints §H4/H6e/H6g/H8/F3，尺寸硬断言） ----
NAV_DECLARE = (79, 309)     # 左导航「综合所得申报」 = 主窗原点 + (79,309)（实测 y=413, 主窗 y=104）
NAV_PERSON = (79, 152)      # 左导航「人员信息采集」(实测 y=256)
GRID_REL = [218, 223, 987, 660]     # 步骤1 网格 VST [469,327,1238,764] - 主窗原点(251,104)
FILL_OFF = (620, 64)                # 首行「正常工资薪金所得」填写链接 = 网格原点 + (620,64) → (1089,391)
SEND_REL = [887, 239, 975, 271]     # 发送申报 [1138,343,1226,375] - 主窗原点
MEMO_Y_REL = (450, 700)             # 校验 memo 上沿相对主窗 y：计税前实测 517；计税后
                                    # （无校验错误）实测下移至 661（[469,765]-主窗104），留带包容两种态
WIZ_SIZE = (565, 253)               # 向导 TFrm_ImportConfig [473,346,1038,599]
WIZ_RADIO1_REL_C = (267, 72)        # 第①项单选中心 (740,418) - 向导原点(473,346)
WIZ_IMPORT_REL = [242, 209, 302, 241]   # 【导入】[715,555,775,587] - 向导原点
WIZ_CANCEL_REL = [314, 209, 374, 241]   # 【取消】[787,555,847,587] - 向导原点
BOX_SIZE = (500, 350)               # 结果框 TfrmBase(结果/进度用同类) [506,273,1006,623]
BOX_BTN1_REL = [351, 312, 418, 342]     # 左钮【保存】/【继续算税】[857,585,924,615] - 框原点
BOX_BTN2_REL = [428, 312, 495, 342]     # 右钮【关闭】/【暂不算税】[934,585,1001,615] - 框原点
BACK_FALLBACK = (253, 197)          # 明细页「返回」兜底 = 主窗原点 + (253,197)（实测 504,301）

CAP_COPY_N = re.compile(r"成功复制【(\d+)】条，失败【(\d+)】条")
SJXJ_KW = "未填写三险一金"
LOGIN_TIMEOUT_KW = ("登录超时", "超时")
NEGATIVE_KW = ("申报失败", "校验不通过", "发送失败", "操作失败", "错误")


class Frozen(R.StepFailed):
    """停机冻结：payload 进 last_result.json 的 detail，绝不继续。
    继承 StepFailed：Runner.run 原生捕获 → finish(False, failed_step, detail)。"""

    def __init__(self, payload):
        self.payload = payload
        R.StepFailed.__init__(self, payload.get("status", "frozen"),
                              payload.get("reason", ""), payload)


# ================================================================ 基础工具
def comp_name(t):
    return bool(t) and bool(re.fullmatch(r"[a-z][a-z0-9_]{1,30}", t or ""))


def rel(win_rect, node_rect):
    return [node_rect[0] - win_rect[0], node_rect[1] - win_rect[1],
            node_rect[2] - win_rect[0], node_rect[3] - win_rect[1]]


def rel_close(a, b, tol=8):
    return a is not None and b is not None and len(a) == 4 and len(b) == 4 \
        and all(abs(x - y) <= tol for x, y in zip(a, b))


def dfs_tree(hwnd, cap=4000):
    """主窗全后代扁平表（enum_children 即递归）+ WM_GETTEXT 文本。"""
    out = []
    for n in R.enum_children(hwnd):
        if len(out) > cap:
            break
        info = dict(n)
        try:
            info["text"] = R.wm_get_text(n["hwnd"])
        except Exception:
            info["text"] = None
        out.append(info)
    return out


def mainframe():
    return R.find_window(MAIN_CLS, visible_only=True)


def mf_enabled():
    mw = mainframe()
    return bool(mw and mw["enabled"])


def shot(name):
    os.makedirs(PIPE_DIR, exist_ok=True)
    from PIL import ImageGrab
    p = os.path.join(PIPE_DIR, name)
    ImageGrab.grab().save(p)
    return MAC_PIPE + "/" + name


def save_json(name, obj):
    os.makedirs(PIPE_DIR, exist_ok=True)
    with open(os.path.join(PIPE_DIR, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return MAC_PIPE + "/" + name


def modal_texts(m):
    """弹窗正文（过滤组件名泄漏与按钮）。"""
    txts = []
    for k in R.enum_children(m["hwnd"]):
        t = (k.get("title") or "").strip()
        if not t or comp_name(t):
            continue
        if any(k["class"].startswith(p) for p in BTN_PREFIXES):
            continue
        if t not in txts:
            txts.append(t)
    return txts


def box_memo(box):
    for k in R.enum_children(box["hwnd"]):
        if k["class"] in ("TMemo", MEMO_CLS):
            try:
                t = R.wm_get_text(k["hwnd"])
            except Exception:
                t = ""
            if t:
                return t
    return ""


def visible_boxes():
    return [w for w in R.enum_top_windows()
            if w["visible"] and w["class"] == BOX_CLS]


def box_by_title(title):
    for w in visible_boxes():
        if w["title"] == title:
            return w
    return None


def visible_msg_modals():
    return [w for w in R.enum_top_windows()
            if w["visible"] and w["class"] == MODAL_CLS]


def top_unknown():
    known = {MODAL_CLS, WIZ_CLS, BOX_CLS, MAIN_CLS, LOGIN_CLS}
    out = []
    for w in R.enum_top_windows():
        if not w["visible"]:
            continue
        if w["class"] in IGNORE_CLS or w["class"] in known:
            continue
        out.append(w)
    return out


def assert_clean_scene(r, ctx):
    """未知模态守卫（T9 忽略集内不算）。"""
    unk = top_unknown()
    if unk:
        art = r.snapshot("unknown-" + ctx)
        raise Frozen({
            "status": "unknown_modal_frozen", "context": ctx,
            "reason": "出现未知可见顶层窗，按安全阀停机冻结（绝不盲点）",
            "unknowns": [{"class": w["class"], "title": w["title"],
                          "rect": w["rect"], "enabled": w["enabled"]} for w in unk],
            "artifacts": art})


def login_timeout_modal(r):
    for m in visible_msg_modals():
        txts = modal_texts(m)
        joined = " ".join(txts)
        if any(kw in joined for kw in LOGIN_TIMEOUT_KW):
            return m, joined
    return None, None


def month_text():
    mfs = mainframe()
    if not mfs:
        return None, None
    hits = [k for k in R.enum_children(mfs["hwnd"])
            if k["class"] == DT_CLS and k["visible"]]
    if len(hits) == 0:
        return None, []          # 冷启动未实例化（同 memo B1）→ 延迟到进模块后断言
    if len(hits) > 1:
        return "AMBIGUOUS", hits
    return R.wm_get_text(hits[0]["hwnd"]), hits[0]


# ---------------------------------------- 页判据（H15b：稳定后再读，DFS 首个非包裹帧）
def first_page_frame(tree, mf_rect):
    seq = []
    for n in tree:
        c = (n["class"] or "")
        if not c.lower().startswith("tfrm") or c == MAIN_CLS:
            continue
        if n["rect"][0] < mf_rect[0] - 2:      # 顶层窗误入（防御）
            continue
        seq.append(c)
    # 跳过宿主/包裹层
    skip = {"Tfrm_DKDJWarpedCustom", "Tfrm_YKYJView_Main", "Tfrm_ITSHomePage",
            "TfrmNsrMgrView"}
    for c in seq:
        if c in ("TFrmView",):
            continue
        if c in skip:
            continue
        return c
    return None


def current_page():
    mf = mainframe()
    if not mf:
        return None
    a = first_page_frame(dfs_tree(mf["hwnd"]), mf["rect"])
    time.sleep(0.6)
    b = first_page_frame(dfs_tree(mf["hwnd"]), mf["rect"])
    return b if a == b else None      # 两次读数一致才算稳定


def wait_page(expect, timeout=15.0):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        last = current_page()
        if last == expect:
            return last
        time.sleep(0.6)
    return last


def guide_buttons():
    mf = mainframe()
    if not mf:
        return []
    gs = [n for n in dfs_tree(mf["hwnd"]) if n["class"] == GUIDE_CLS]
    gs.sort(key=lambda n: n["rect"][0])
    return gs


def goto_tab(idx, expect_cls, r, timeout=15.0):
    """点步骤页签（运行时 rect），verify 稳定页 == expect。"""
    def act():
        gs = guide_buttons()
        if len(gs) < 4:
            raise Frozen({"status": "no_tabs_frozen",
                          "reason": "模块内未找到 4 个步骤页签 (TGuideButton=%d)" % len(gs)})
        g = gs[idx]
        cx, cy = R.center(g["rect"])
        assert_clean_scene(r, "goto_tab%d" % idx)
        click(cx, cy)
        return {"at": [cx, cy], "rect": g["rect"]}

    def verify():
        return current_page() == expect_cls

    return r.step("goto_tab_%d" % idx, action=act, verify=verify,
                  verify_desc="当前页=%s" % expect_cls, timeout=timeout, interval=0.8)


def enter_module(r):
    """S2：左导航 Tier-B 点「综合所得申报」，verify 成员判定（TGuideButton==4 或 in_module）。"""
    def act():
        mf = mainframe()
        x = mf["rect"][0] + NAV_DECLARE[0]
        y = mf["rect"][1] + NAV_DECLARE[1]
        assert_clean_scene(r, "enter_module")
        click(x, y)
        return {"at": [x, y], "anchor": "mainframe_origin+nav_declare"}

    def verify():
        return len(guide_buttons()) == 4

    return r.step("enter_module", action=act, verify=verify,
                  verify_desc="进入综合所得申报模块（TGuideButton==4）",
                  timeout=15.0, interval=0.8)


def assert_month(r):
    def verify():
        t, _ = month_text()
        return t == EXPECT_MONTH

    def act():
        t, hits = month_text()
        return {"month": t, "n_dtp": len(hits) if isinstance(hits, list) else hits}

    v = r.step("assert_tax_period", action=act, verify=verify,
               verify_desc="税款所属期 == %s" % EXPECT_MONTH,
               timeout=6.0, interval=0.5, allow_no_verify=False)
    return v


# ================================================================ 三个阶段
ARGS = {}
DRY = False


def click(x, y):
    if DRY:
        return {"dry": True, "at": [int(x), int(y)]}
    R.click_at(int(x), int(y))
    return {"at": [int(x), int(y)]}


def gate_logged_in(r):
    def verify():
        return mainframe() is not None
    r.step("gate_logged_in", action=lambda: {"main_rect": (mainframe() or {}).get("rect")},
           verify=verify, verify_desc="主窗 Tfrm_MainFrame 可见",
           timeout=5.0, allow_no_verify=False)


def step1_grid_anchor(r):
    """A2'：3 个 VST 中恰好 1 个与期望相对 rect 匹配（相对主窗原点）。"""
    mf = mainframe()
    hits = []
    for n in dfs_tree(mf["hwnd"]):
        if n["class"] != VST_CLS or not n["visible"]:
            continue
        if rel_close(rel(mf["rect"], n["rect"]), GRID_REL, tol=8):
            hits.append(n)
    if len(hits) != 1:
        raise Frozen({
            "status": "grid_anchor_frozen",
            "reason": "步骤1网格锚不唯一（A2' 停机）",
            "vst_rects": [rel(mf["rect"], n["rect"])
                          for n in dfs_tree(mf["hwnd"]) if n["class"] == VST_CLS],
            "matched": len(hits)})
    return hits[0]


def do_preflow(r):
    gate_logged_in(r)
    t, hits = month_text()
    if t == "AMBIGUOUS":
        raise Frozen({"status": "month_picker_ambiguous_frozen",
                      "reason": "TXPFarmerDTPicker 实例数!=1（A2'）", "n": len(hits)})

    if DRY:
        # 0 真实点击：只读门 + 定位意图计划（锚点全部按主窗原点相对推导）
        mf = mainframe()
        plan = {
            "month_now": t,
            "page_now": current_page(),
            "n_guide_buttons": len(guide_buttons()),
            "nav_declare_at": [mf["rect"][0] + NAV_DECLARE[0], mf["rect"][1] + NAV_DECLARE[1]],
            "nav_person_at": [mf["rect"][0] + NAV_PERSON[0], mf["rect"][1] + NAV_PERSON[1]],
            "grid_rel_expected": GRID_REL,
            "fill_click_expected_at": [mf["rect"][0] + GRID_REL[0] + FILL_OFF[0],
                                       mf["rect"][1] + GRID_REL[1] + FILL_OFF[1]],
            "send_rel_expected": SEND_REL,
            "memo_y_rel_expected": list(MEMO_Y_REL),
            "wizard": {"size": WIZ_SIZE, "radio1_rel_c": WIZ_RADIO1_REL_C,
                       "import_rel": WIZ_IMPORT_REL, "cancel_rel": WIZ_CANCEL_REL},
            "result_box": {"size": BOX_SIZE, "btn1_rel": BOX_BTN1_REL,
                           "btn2_rel_关闭": BOX_BTN2_REL},
            "deferred": "网格 VST 锚 / 页签 rect / memo 位置需真实导航后才能运行时校验，"
                        "由实跑各步的前置断言兜底（不唯一即停机）",
        }
        return {"status": "dry_ok", "note": "0 真实点击：只读门通过，定位意图计划如下",
                "dry_plan": plan}

    month_checked = False
    if t is not None:
        assert_month(r)
        month_checked = True

    # 进入模块（幂等：已在模块则不点导航）
    pg = current_page()
    if pg == REPORT_CLS:
        click_back_to_step1(r)          # T6：明细页只能经「返回」离开
        pg = current_page()
    if pg in (None, "Tfrm_ITSHomePage", NSR_CLS) or not guide_buttons():
        enter_module(r)
    if not month_checked:
        assert_month(r)

    # S3 回步骤1（向导会停在上次所在步）
    if current_page() != STEP1_CLS:
        goto_tab(0, STEP1_CLS, r)

    grid = step1_grid_anchor(r)
    r.emit("step1_anchor_ok", detail={"grid_rel": rel(mainframe()["rect"], grid["rect"])})

    # ---- S4' 幂等门：点「填写」，以其反应自判草稿（未生成→确认信息+向导；已生成→直达明细页）
    def act_fill():
        assert_clean_scene(r, "before_fill")
        g = step1_grid_anchor(r)
        x = g["rect"][0] + FILL_OFF[0]
        y = g["rect"][1] + FILL_OFF[1]
        click(x, y)
        return {"fill_click": [x, y]}

    # 反应分类轮询（确认信息→确定→向导；直出向导；直达明细页）
    def classify_reaction():
        wiz = R.find_window(WIZ_CLS, visible_only=True)
        if wiz:
            return "wizard", wiz
        det = current_page()
        if det == REPORT_CLS:
            return "detail", None
        for m in visible_msg_modals():
            if (m["title"] or "") == "确认信息":
                return "confirm", m
        return None, None

    def act_wait():
        t0 = time.time()
        while time.time() - t0 < 14.0:
            kind, obj = classify_reaction()
            if kind:
                return {"reaction": kind}
            time.sleep(0.6)
        art = r.snapshot("fill-no-reaction")
        raise Frozen({"status": "fill_no_reaction_frozen",
                      "reason": "点「填写」14s 无确认信息/向导/明细页反应",
                      "artifacts": art})

    r.step("open_wage_fill", action=act_fill, verify=None, allow_no_verify=True,
           verify_desc="Tier-B 点击（下游由 wait_reaction 分类验证）")
    rw = r.step("wait_fill_reaction", action=act_wait,
                verify=lambda: classify_reaction()[0] is not None,
                verify_desc="确认信息/向导/明细页 三选一出现", timeout=6.0, interval=0.6)

    # ---- 确认信息 → 几何钉死左钮【确定】
    def act_confirm():
        kind, m = classify_reaction()
        if kind != "confirm":
            return {"note": "reaction 已变为 %s" % kind}
        btns = [k for k in R.enum_children(m["hwnd"])
                if k["visible"] and any(k["class"].startswith(p) for p in BTN_PREFIXES)]
        btns.sort(key=lambda b: b["rect"][0])
        if len(btns) != 2:
            art = r.snapshot("confirm-ambiguous")
            raise Frozen({"status": "confirm_modal_frozen",
                          "reason": "「确认信息」按钮数!=2，拒绝自动点（交人工）",
                          "buttons": [{"class": b["class"], "rect": b["rect"]} for b in btns],
                          "texts": modal_texts(m), "artifacts": art})
        left = btns[0]
        if left["rect"][0] >= btns[1]["rect"][0]:
            art = r.snapshot("confirm-order")
            raise Frozen({"status": "confirm_modal_frozen",
                          "reason": "按钮序异常（左钮应为【确定】）", "artifacts": art})
        assert_clean_scene(r, "confirm_click")   # 确认信息自身是 MODAL_CLS，不在 unknown 集
        cx, cy = R.center(left["rect"])
        click(cx, cy)
        return {"clicked_left_confirm": [cx, cy]}

    def verify_confirm_gone_wizard():
        kind, _ = classify_reaction()
        return kind in ("wizard", "detail")

    r.step("confirm_open_wizard", action=act_confirm, verify=verify_confirm_gone_wizard,
           verify_desc="「确认信息」已点左钮【确定】→ 向导/明细页出现",
           timeout=12.0, interval=0.6, guard=False)

    kind, _ = classify_reaction()
    if kind == "detail":
        # 已生成明细（幂等分支）：截图留证 → 返回步骤1 → 网格截图 → 交视觉确认
        png_detail = shot("draft_detail_page.png")
        click_back_to_step1(r)
        png_grid = shot("draft_step1_grid.png")
        return {"status": "draft_present_need_visual",
                "note": "明细已生成（幂等分支，未重复复制）；请视觉确认网格 填写人数==1 ∧ 李关珍",
                "png_detail": png_detail, "png_grid": png_grid}

    # ---- S6 向导：选① → 断言选中 → 【导入】
    do_wizard_copy(r)

    # ---- 复制后：明细页 → 截图 → 返回 → 步骤1 网格截图
    pg = wait_page(REPORT_CLS, timeout=12.0)
    if pg != REPORT_CLS:
        art = r.snapshot("post-copy-page")
        raise Frozen({"status": "postcopy_page_frozen",
                      "reason": "复制后未到明细页(%s)" % pg, "artifacts": art})
    png_detail = shot("copy_detail_page.png")
    click_back_to_step1(r)
    png_grid = shot("copy_step1_grid.png")

    # memo 旁证（存在才读）
    memo_txt = read_memo_optional()
    return {"status": "copy_done_need_visual",
            "note": "复制成功且机器门已过；请视觉确认：明细页 申报总人数==1∧李关珍；网格 填写人数==1",
            "png_detail": png_detail, "png_grid": png_grid,
            "memo_text": memo_txt}


def click_back_to_step1(r):
    """T6：离开明细页点「返回」回步骤1。优先文本匹配，兜底实测几何。"""

    def act():
        mf = mainframe()
        target = None
        for n in dfs_tree(mf["hwnd"]):
            if any(n["class"].startswith(p) for p in BTN_PREFIXES) and n["visible"]:
                if (n.get("text") or "").strip() == "返回":
                    target = n
                    break
        if target:
            cx, cy = R.center(target["rect"])
            via = "text=返回"
        else:
            cx = mf["rect"][0] + BACK_FALLBACK[0]
            cy = mf["rect"][1] + BACK_FALLBACK[1]
            via = "fallback_geo"
        assert_clean_scene(r, "back_click")
        click(cx, cy)
        return {"at": [cx, cy], "via": via}

    def verify():
        return current_page() == STEP1_CLS

    r.step("back_to_step1", action=act, verify=verify,
           verify_desc="返回步骤1（Tfrm_SelectSDXM）", timeout=12.0, interval=0.8)


def read_memo_optional():
    mf = mainframe()
    hits = [n for n in dfs_tree(mf["hwnd"]) if n["class"] == MEMO_CLS and n["visible"]]
    if len(hits) != 1:
        return None
    try:
        return R.wm_get_text(hits[0]["hwnd"])
    except Exception:
        return None


def do_wizard_copy(r):
    """S6/S7'：向导选①复制上月 → BM_GETCHECK 断言 → 导入 → 结果框 N/M 机器硬门 → 【关闭】。"""
    wiz = R.find_window(WIZ_CLS, visible_only=True)
    if not wiz:
        raise Frozen({"status": "wizard_missing_frozen", "reason": "向导窗未出现"})
    if (wiz["title"] or "") != "正常工资薪金所得":
        raise Frozen({"status": "wizard_title_frozen",
                      "reason": "向导 title 异常", "title": wiz["title"]})
    w_size = (wiz["rect"][2] - wiz["rect"][0], wiz["rect"][3] - wiz["rect"][1])
    if abs(w_size[0] - WIZ_SIZE[0]) > 12 or abs(w_size[1] - WIZ_SIZE[1]) > 12:
        raise Frozen({"status": "wizard_size_frozen",
                      "reason": "向导尺寸与实测不符（拒绝在陌生几何上点击）",
                      "size": w_size, "expect": WIZ_SIZE})

    # ① 三个单选，按 wm_gettext 匹配第①项
    radios = []
    for k in R.enum_children(wiz["hwnd"]):
        if k["class"].startswith("TITSRadioButton") and k["visible"]:
            radios.append({"hwnd": k["hwnd"], "class": k["class"], "rect": k["rect"],
                           "text": (R.wm_get_text(k["hwnd"]) or "").strip()})
    if len(radios) != 3:
        art = r.snapshot("wizard-radios")
        raise Frozen({"status": "wizard_radios_frozen",
                      "reason": "向导单选项数!=3", "radios": radios, "artifacts": art})
    tgt = [x for x in radios if "复制上月当期数据" in x["text"]]
    if len(tgt) != 1:
        raise Frozen({"status": "wizard_option_missing_frozen",
                      "reason": "G3a：未找到唯一「复制上月当期数据」选项 → 停机（绝不退化为模板/零申报）",
                      "radios": radios})
    tgt = tgt[0]
    forbidden_hit = [x["text"] for x in radios
                     if x is not tgt and ("标准模板" in x["text"] or "零工资" in x["text"])]
    r.emit("wizard_options", detail={"target": tgt["text"], "others": forbidden_hit})

    def act_select():
        assert_clean_scene(r, "radio_click")
        cx, cy = R.center(tgt["rect"])
        click(cx, cy)
        return {"clicked": tgt["text"], "at": [cx, cy]}

    def verify_selected():
        try:
            c1 = int(user32.SendMessageW(tgt["hwnd"], BM_GETCHECK, 0, 0))
        except Exception:
            return False
        if c1 != 1:
            return False
        for x in radios:
            if x is tgt:
                continue
            try:
                if int(user32.SendMessageW(x["hwnd"], BM_GETCHECK, 0, 0)) != 0:
                    return False
            except Exception:
                return False
        return True

    r.step("select_copy_option", action=act_select, verify=verify_selected,
           verify_desc="G3a'：第①项 bm_getcheck==1 且其余==0", timeout=8.0,
           interval=0.5, guard=False)

    # ② 几何钉死【导入】
    imp = None
    for k in R.enum_children(wiz["hwnd"]):
        if k["class"].startswith("TITSSpeedButton") and k["visible"]:
            if rel_close(rel(wiz["rect"], k["rect"]), WIZ_IMPORT_REL, tol=8):
                imp = k
                break
    if imp is None:
        art = r.snapshot("wizard-import-btn")
        raise Frozen({"status": "wizard_import_btn_frozen",
                      "reason": "【导入】按钮几何不匹配（拒绝点击）", "artifacts": art})

    def act_import():
        assert_clean_scene(r, "import_click")
        cx, cy = R.center(imp["rect"])
        click(cx, cy)
        return {"import_at": [cx, cy]}

    # 进度框（TfrmBase 进度）先等消失，再等结果框
    def verify_result_box():
        prog = box_by_title("进度")
        if prog:
            return False
        rb = box_by_title("结果")
        return bool(rb)

    r.step("click_import", action=act_import, verify=verify_result_box,
           verify_desc="【导入】已点：进度框消失且结果框出现", timeout=40.0,
           interval=0.6, guard=False)

    # ③ 结果框 memo 机器硬门：成功复制【N】条，失败【M】条，N≥1 ∧ M==0
    rb = box_by_title("结果")
    memo_t = box_memo(rb)
    mt = CAP_COPY_N.search(memo_t or "")
    copy_n = int(mt.group(1)) if mt else -1
    copy_m = int(mt.group(2)) if mt else -1
    evidence = {"box_title": rb["title"], "box_rect": rb["rect"],
                "memo_text": memo_t, "copy_n": copy_n, "copy_m": copy_m}
    r.emit("copy_result_evidence", detail=evidence)
    save_json("copy_result_evidence.json", evidence)
    if copy_n < 1 or copy_m != 0:
        art = r.snapshot("copy-gate")
        raise Frozen({"status": "copy_gate_failed_frozen",
                      "reason": "G3b 硬门：成功复制【%s】条/失败【%s】条 不满足 N≥1∧M==0 → 停机"
                                % (copy_n, copy_m),
                      "evidence": evidence, "artifacts": art})

    # ④ 【关闭】（用户权威流程 G7/T2：记录不丢，靠填写人数验证）
    close_btn = None
    for k in R.enum_children(rb["hwnd"]):
        if k["class"].startswith("TModalSpeedButton") and k["visible"]:
            if rel_close(rel(rb["rect"], k["rect"]), BOX_BTN2_REL, tol=8):
                close_btn = k
                break
    if close_btn is None:
        art = r.snapshot("result-close-btn")
        raise Frozen({"status": "result_close_btn_frozen",
                      "reason": "结果框【关闭】钮几何不匹配（拒绝点击）", "artifacts": art})

    def act_close():
        assert_clean_scene(r, "result_close")
        cx, cy = R.center(close_btn["rect"])
        click(cx, cy)
        return {"close_at": [cx, cy]}

    def verify_closed():
        return (box_by_title("结果") is None and box_by_title("进度") is None
                and R.find_window(WIZ_CLS, visible_only=True) is None)

    r.step("close_result_box", action=act_close, verify=verify_closed,
           verify_desc="结果框已关闭（向导/结果框均消失）", timeout=15.0,
           interval=0.6, guard=False)


def terminal_poll(r, term_cache, sjxj_budget=2):
    """发送后的终态轮询（共享）：
    - Tfrm_MsgDlgRich 登录超时 → sent_session_dead_frozen（绝不重发）
    - 任何负态文案 → sent_negative_frozen（绝不重发）
    - TfrmBase(结果) memo 含「未填写三险一金」→ 发送链路自带确认，几何钉死左钮
      【继续申报】(890,600) 继续本次发送（G7-b 提示穿越授权；限 sjxj_budget 次）
    - 树/弹窗出现「申报成功」→ 机器正向信号
    - 超时 → 截图交编排端视觉判读
    """
    t0 = time.time()
    sjxj_clicks = 0
    while time.time() - t0 < float(ARGS.get("terminal_timeout", 240)):
        handled = False
        for m in visible_msg_modals() + visible_boxes():
            memo_t = box_memo(m) if m["class"] == BOX_CLS else ""
            txts = modal_texts(m) or ([memo_t] if memo_t else [])
            joined = " ".join(txts)
            if any(kw in joined for kw in LOGIN_TIMEOUT_KW):
                art = r.snapshot("after-send-timeout-modal")
                raise Frozen({"status": "sent_session_dead_frozen",
                              "reason": "发送后弹登录超时 → 绝不重发，人工到网页端核对",
                              "modal_text": joined, "artifacts": art})
            if any(kw in joined for kw in NEGATIVE_KW) or "失败" in joined:
                art = r.snapshot("after-send-negative")
                raise Frozen({"status": "sent_negative_frozen",
                              "reason": "发送后负态文案 → 绝不重发，人工核对",
                              "texts": txts, "artifacts": art})
            if memo_t and SJXJ_KW in memo_t:
                if sjxj_clicks >= sjxj_budget:
                    art = r.snapshot("send-3in1-over-budget")
                    raise Frozen({"status": "send_3in1_over_budget_frozen",
                                  "reason": "发送链路三险一金确认多次复现，停机冻结（不点取消、不重发）",
                                  "memo_text": memo_t, "artifacts": art})
                btn1 = None
                for k in R.enum_children(m["hwnd"]):
                    if k["class"].startswith("TModalSpeedButton") and k["visible"] \
                            and rel_close(rel(m["rect"], k["rect"]), BOX_BTN1_REL, tol=8):
                        btn1 = k
                        break
                if btn1 is None:
                    art = r.snapshot("send-3in1-btn1")
                    raise Frozen({"status": "send_continue_btn_frozen",
                                  "reason": "【继续申报】钮几何不匹配（拒绝点击）",
                                  "artifacts": art})
                cx, cy = R.center(btn1["rect"])
                click(cx, cy)
                sjxj_clicks += 1
                r.emit("sjxj_during_send", detail={"click": [cx, cy],
                                                   "memo": memo_t[:80], "n": sjxj_clicks})
                handled = True
                break
            if "申报成功" in joined:
                term_cache["machine_success_text"] = term_cache.get(
                    "machine_success_text") or joined
        if handled:
            time.sleep(1.5)
            continue
        mf = mainframe()
        if mf:
            for n in dfs_tree(mf["hwnd"]):
                tt = (n.get("text") or "")
                if "申报成功" in tt:
                    term_cache["machine_success_text"] = term_cache.get(
                        "machine_success_text") or tt
                    break
        if term_cache.get("machine_success_text"):
            break
        time.sleep(2.0)
    term_cache["png"] = shot("after_send_terminal.png")
    term_cache["waited_s"] = round(time.time() - t0, 1)
    return dict(term_cache)


def do_terminal_resume(r):
    """发送已点击后的续段（绝不重发）：处置发送链路三险一金确认【继续申报】→ 终态轮询。"""
    gate_logged_in(r)
    term_cache = {}

    def act_resume():
        rb = box_by_title("结果")
        info = {"box": bool(rb), "memo": (box_memo(rb) or "")[:80] if rb else None}
        if rb and SJXJ_KW in box_memo(rb):
            btn1 = None
            for k in R.enum_children(rb["hwnd"]):
                if k["class"].startswith("TModalSpeedButton") and k["visible"] \
                        and rel_close(rel(rb["rect"], k["rect"]), BOX_BTN1_REL, tol=8):
                    btn1 = k
                    break
            if btn1 is None:
                art = r.snapshot("resume-btn1")
                raise Frozen({"status": "send_continue_btn_frozen",
                              "reason": "【继续申报】钮几何不匹配（拒绝点击）",
                              "artifacts": art})
            cx, cy = R.center(btn1["rect"])
            click(cx, cy)
            info["clicked"] = [cx, cy]
            r.emit("sjxj_during_send", detail={"click": [cx, cy], "n": 1})
        elif rb:
            raise Frozen({"status": "unexpected_box_frozen",
                          "reason": "结果框在场但非三险一金文案，拒绝自动点",
                          "memo_text": (box_memo(rb) or "")[:200]})
        return info

    r.step("continue_send_3in1", action=act_resume,
           verify=lambda: box_by_title("结果") is None,
           verify_desc="发送链路三险一金确认已点【继续申报】，框消失",
           timeout=12.0, interval=0.5, guard=False)

    def act_terminal():
        return terminal_poll(r, term_cache)

    r.step("wait_terminal", action=act_terminal,
           verify=lambda: True, allow_no_verify=True,
           verify_desc="终态采集（续段）", guard=False,
           timeout=30.0, interval=1.0)
    ok_status = "sent_machine_success" if term_cache.get("machine_success_text") \
        else "sent_need_visual"
    payload = {"status": ok_status,
               "note": "发送确认【继续申报】已处置；请读截图确认终态文案"
                       if not term_cache.get("machine_success_text")
                       else "机器读到申报成功文案",
               "machine_success_text": term_cache.get("machine_success_text"),
               "png_terminal": term_cache.get("png")}
    save_json("after_send_summary.json", payload)
    return payload


def do_finish(r):
    if not ARGS.get("visual_ok"):
        raise Frozen({"status": "finish_refused",
                      "reason": "finish 需先通过视觉门（visual_ok=true，填写人数==1∧李关珍）"})
    if not ARGS.get("send_authorized"):
        raise Frozen({"status": "send_auth_missing",
                      "reason": "缺少 send_authorized=true（不可逆动作需显式授权参数）"})

    gate_logged_in(r)
    t, hits = month_text()
    if t == "AMBIGUOUS":
        raise Frozen({"status": "month_picker_ambiguous_frozen", "n": len(hits)})
    month_checked = False
    if t is not None:
        assert_month(r)
        month_checked = True
    if not guide_buttons():
        enter_module(r)
    if not month_checked:
        assert_month(r)

    # 步骤2：场景门 → 进模块页 → 三险一金【继续算税】→ 计税收敛
    def act_sjxj():
        rb = box_by_title("结果")
        if not rb:
            for m in visible_msg_modals():
                joined = " ".join(modal_texts(m))
                if any(kw in joined for kw in LOGIN_TIMEOUT_KW):
                    art = r.snapshot("session-dead-step2")
                    raise Frozen({"status": "session_dead_frozen",
                                  "reason": "计税期出现登录超时弹窗（会话死亡）",
                                  "modal_text": joined, "artifacts": art})
            return {"note": "无三险一金框（可能已算过/算税中）"}
        memo_t = box_memo(rb)
        if SJXJ_KW not in memo_t:
            art = r.snapshot("unexpected-box")
            raise Frozen({"status": "unexpected_box_frozen",
                          "reason": "结果框出现但非三险一金文案，拒绝自动点",
                          "memo_text": memo_t[:200], "artifacts": art})
        btn1 = None
        for k in R.enum_children(rb["hwnd"]):
            if k["class"].startswith("TModalSpeedButton") and k["visible"] \
                    and rel_close(rel(rb["rect"], k["rect"]), BOX_BTN1_REL, tol=8):
                btn1 = k
                break
        if btn1 is None:
            art = r.snapshot("sjxj-btn1")
            raise Frozen({"status": "sjxj_btn_frozen",
                          "reason": "【继续算税】钮几何不匹配（拒绝点击）", "artifacts": art})
        cx, cy = R.center(btn1["rect"])
        click(cx, cy)
        return {"sjxj_click": [cx, cy], "memo": memo_t[:120]}

    def verify_box_cleared():
        # 只断言三险一金(结果)框消失；点【继续算税】后可能立刻弹「进度」框（主窗禁用），
        # 进度收敛由 wait_calc_settle 负责
        return box_by_title("结果") is None

    def verify_sjxj_done():
        # 同上：只断言框消失，页面/收敛由 settle 断言
        return box_by_title("结果") is None

    # 场景门：若已有三险一金框在场（上次停机遗留等），先点【继续算税】，
    # 否则后续任何页签点击都会被禁用的主窗吞掉（H3a）
    r.step("scene_gate_continue_calc", action=act_sjxj, verify=verify_box_cleared,
           verify_desc="在场三险一金框已处置（框消失∧主窗 enabled）",
           timeout=10.0, interval=0.5, guard=False)

    # 进入步骤2：首次点击会触发三险一金框 → 容忍其出现（随后继续算税）
    if current_page() != STEP2_CLS:
        def act_enter_step2():
            gs = guide_buttons()
            if len(gs) < 4:
                raise Frozen({"status": "no_tabs_frozen",
                              "reason": "模块内未找到 4 个步骤页签 (TGuideButton=%d)" % len(gs)})
            g = gs[1]
            cx, cy = R.center(g["rect"])
            assert_clean_scene(r, "goto_tab1")
            click(cx, cy)
            return {"at": [cx, cy], "rect": g["rect"]}

        def verify_enter_step2():
            if current_page() == STEP2_CLS:
                return True
            rb = box_by_title("结果")
            return bool(rb and SJXJ_KW in box_memo(rb))

        r.step("enter_step2", action=act_enter_step2, verify=verify_enter_step2,
               verify_desc="步骤2达成：页面切换 或 三险一金框出现",
               timeout=15.0, interval=0.8)
        r.step("continue_calc_3in1", action=act_sjxj, verify=verify_sjxj_done,
               verify_desc="三险一金【继续算税】已点：框消失∧主窗 enabled∧页面=步骤2",
               timeout=12.0, interval=0.5, guard=False)

    def act_settle():
        t0 = time.time()
        seen_progress = False
        sjxj_clicks = 0
        calc_timeout = float(ARGS.get("calc_timeout", 60))
        while time.time() - t0 < calc_timeout:
            m, joined = login_timeout_modal(r)
            if m:
                art = r.snapshot("session-dead-calc")
                raise Frozen({"status": "session_dead_frozen",
                              "reason": "计税收敛期弹登录超时（H14c：会话死亡）",
                              "modal_text": joined, "artifacts": art})
            if visible_msg_modals():
                m0 = visible_msg_modals()[0]
                art = r.snapshot("calc-modal")
                raise Frozen({"status": "calc_modal_frozen",
                              "reason": "计税期出现未知提示弹窗（拒绝自动点）",
                              "texts": modal_texts(m0), "artifacts": art})
            rb = box_by_title("结果")
            if rb and SJXJ_KW in box_memo(rb):
                # 三险一金框可能在收敛等待期才弹出（竞态）→ 与 act_sjxj 同口径点【继续算税】
                if sjxj_clicks >= 2:
                    raise Frozen({"status": "sjxj_recurred_frozen",
                                  "reason": "三险一金框多次复现，停机冻结"})
                btn1 = None
                for k in R.enum_children(rb["hwnd"]):
                    if k["class"].startswith("TModalSpeedButton") and k["visible"] \
                            and rel_close(rel(rb["rect"], k["rect"]), BOX_BTN1_REL, tol=8):
                        btn1 = k
                        break
                if btn1 is None:
                    art = r.snapshot("sjxj-btn1-settle")
                    raise Frozen({"status": "sjxj_btn_frozen",
                                  "reason": "【继续算税】钮几何不匹配（拒绝点击）",
                                  "artifacts": art})
                cx, cy = R.center(btn1["rect"])
                click(cx, cy)
                sjxj_clicks += 1
                r.emit("sjxj_during_settle", detail={"click": [cx, cy], "n": sjxj_clicks})
                time.sleep(1.0)
                continue
            prog = box_by_title("进度")
            seen_progress = seen_progress or bool(prog)
            if not prog and mf_enabled() and not rb \
                    and current_page() == STEP2_CLS:
                return {"outcome": "settled", "seen_progress": seen_progress,
                        "elapsed": round(time.time() - t0, 1)}
            time.sleep(0.6)
        art = r.snapshot("calc-not-settled")
        raise Frozen({"status": "calc_timeout_frozen",
                      "reason": "计税 %.0fs 未收敛" % calc_timeout, "artifacts": art})

    r.step("wait_calc_settle", action=act_settle,
           verify=lambda: mf_enabled() and not visible_msg_modals(),
           verify_desc="计税收敛（进度消失∧主窗 enabled∧无弹窗）",
           timeout=8.0, interval=0.8)

    # E14：计税后 memo 必须翻转（不含「未计算税款」/「未填写」）
    memo_after = read_memo_optional()
    r.emit("memo_after_calc", detail={"text": memo_after})
    if memo_after and ("未计算税款" in memo_after or "未填写" in memo_after):
        art = r.snapshot("memo-negative-after-calc")
        raise Frozen({"status": "calc_memo_negative_frozen",
                      "reason": "E14：计税后校验 memo 仍为负态（未翻转）",
                      "memo_text": memo_after, "artifacts": art})

    # 步骤4 双门
    if current_page() != STEP4_CLS:
        goto_tab(3, STEP4_CLS, r)

    def read_gates():
        mf = mainframe()
        send = None
        memo = None
        for n in dfs_tree(mf["hwnd"]):
            rr = rel(mf["rect"], n["rect"])
            if n["class"] == MEMO_CLS and n["visible"] \
                    and MEMO_Y_REL[0] <= rr[1] <= MEMO_Y_REL[1]:
                memo = n
            if n["class"].startswith("TITSSpeedButton") and n["visible"] \
                    and rel_close(rr, SEND_REL, tol=10):
                send = n
        memo_t = None
        if memo is not None:
            try:
                memo_t = R.wm_get_text(memo["hwnd"])
            except Exception:
                memo_t = None
        g = {"memo_found": memo is not None, "memo_text": memo_t,
             "memo_rect_rel": rel(mf["rect"], memo["rect"]) if memo else None,
             "memo_bad": bool(memo_t) and any(kw in memo_t for kw in
                                              ("未计算税款", "未填写", "校验不通过")),
             "memo_empty": memo_t == "" ,
             "send_found": send is not None,
             "send_rect": send["rect"] if send else None,
             "send_enabled": bool(send and send["enabled"]),
             "send_visible": bool(send and send["visible"])}
        # E14 实测修订：计税后（无校验错误）memo 文本为空（负态「未计算税款」已翻转消失），
        # 空 = 无负态 = 过守卫；负态文案出现才停机。正向驱动 = 页面正确 + 发送钮 enabled∧visible。
        g["double_gate"] = (g["memo_found"] and not g["memo_bad"]
                            and g["send_found"] and g["send_enabled"] and g["send_visible"])
        return g

    gates_cache = {}

    def _verify_gates():
        g = read_gates()
        gates_cache.update(g)
        return bool(g["double_gate"])

    r.step("s12_double_gate", action=lambda: read_gates(),
           verify=_verify_gates,
           verify_desc="memo 无负态 ∧ 发送钮 enabled∧visible",
           timeout=8.0, interval=0.8)
    gates = gates_cache
    r.emit("s12_gates", detail=gates)
    save_json("s12_gates.json", gates)
    if "已申报" in (gates.get("memo_text") or ""):
        raise Frozen({"status": "already_declared_frozen",
                      "reason": "memo 含「已申报」→ 不重发，交人工核对",
                      "memo_text": gates.get("memo_text")})
    png_pre = shot("pre_send_step4.png")

    # 发送（今日用户显式事先授权；授权记录入日志）
    r.emit("send_authorization", detail={
        "authorized": True,
        "auth": ARGS.get("auth_note"),
        "gates": gates, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})

    def act_send():
        mf = mainframe()
        send = None
        for n in dfs_tree(mf["hwnd"]):
            rr = rel(mf["rect"], n["rect"])
            if n["class"].startswith("TITSSpeedButton") and n["visible"] \
                    and rel_close(rr, SEND_REL, tol=10):
                send = n
        if send is None or not (send["enabled"] and send["visible"]):
            raise Frozen({"status": "send_btn_lost_frozen",
                          "reason": "点击前发送钮复检失败（enabled∧visible）"})
        cx, cy = R.center(send["rect"])
        click(cx, cy)
        return {"send_click": [cx, cy], "rect": send["rect"]}

    r.step("send_declaration", action=act_send,
           verify=lambda: True,
           verify_desc="发送已点击（不可逆动作不设即时重试型 verify；终态由 wait_terminal "
                       "正向白名单 + 编排端视觉 + recheck 独立复核判定，绝不重发）",
           timeout=5.0, guard=False)

    # ---- 终态等待：正向白名单 / 已知负态 / 未知 → 一律不重发
    term_cache = {}

    def act_terminal():
        return terminal_poll(r, term_cache)

    r.step("wait_terminal", action=act_terminal,
           verify=lambda: True, allow_no_verify=True,
           verify_desc="终态采集（白名单判定在编排端/复核阶段）", guard=False,
           timeout=30.0, interval=1.0)
    mf_texts = []
    mf = mainframe()
    if mf:
        for n in dfs_tree(mf["hwnd"]):
            tt = (n.get("text") or "").strip()
            if tt and not comp_name(tt) and len(tt) < 120 and tt not in mf_texts:
                mf_texts.append(tt)
    memo_final = read_memo_optional()
    ok_status = "sent_machine_success" if term_cache.get("machine_success_text") \
        else "sent_need_visual"
    payload = {"status": ok_status,
               "note": "发送已执行；请读截图确认终态文案（申报成功，无需缴款）"
                       if not term_cache.get("machine_success_text")
                       else "发送已执行且机器读到申报成功文案",
               "machine_success_text": term_cache.get("machine_success_text"),
               "png_terminal": term_cache.get("png"),
               "readable_texts": mf_texts[:60],
               "memo_text": memo_final}
    save_json("after_send_summary.json", payload)
    return payload


def do_recheck(r):
    """门3 独立复核：退出模块 → 重进 → 步骤4 再读数 + 截图。"""
    gate_logged_in(r)

    def act_leave():
        mf = mainframe()
        x = mf["rect"][0] + NAV_PERSON[0]
        y = mf["rect"][1] + NAV_PERSON[1]
        assert_clean_scene(r, "leave_module")
        click(x, y)
        return {"at": [x, y]}

    def verify_left():
        mf = mainframe()
        nsr = R.find_window(NSR_CLS, visible_only=True)
        return bool(nsr) or len(guide_buttons()) == 0

    r.step("leave_module", action=act_leave, verify=verify_left,
           verify_desc="已退出综合所得申报模块", timeout=12.0, interval=0.8)

    enter_module(r)

    def act_recheck():
        pg = current_page()
        if pg != STEP4_CLS:
            goto_tab(3, STEP4_CLS, r)
        return {"page": current_page()}

    r.step("goto_step4_recheck", action=act_recheck,
           verify=lambda: current_page() == STEP4_CLS,
           verify_desc="复核：当前页=步骤4", timeout=20.0, interval=1.0)

    texts = []
    mf = mainframe()
    for n in dfs_tree(mf["hwnd"]):
        tt = (n.get("text") or "").strip()
        if tt and not comp_name(tt) and len(tt) < 120 and tt not in texts:
            texts.append(tt)
    memo_txt = read_memo_optional()
    png = shot("recheck_step4.png")
    payload = {"status": "recheck_captured", "png": png,
               "readable_texts": texts[:60], "memo_text": memo_txt,
               "note": "第二次独立读数：请读截图确认 申报状态=申报成功（无需缴款）"}
    save_json("recheck_summary.json", payload)
    return payload


# ================================================================ 入口
def run_stage(r):
    stage = ARGS.get("stage", "preflow")
    if DRY and stage != "preflow":
        raise Frozen({"status": "bad_dry_stage",
                      "reason": "dry_run 仅支持 preflow（0 点击验证只读门+定位计划）"})
    if stage == "preflow":
        return do_preflow(r)
    if stage == "finish":
        return do_finish(r)
    if stage == "terminal_resume":
        return do_terminal_resume(r)
    if stage == "recheck":
        return do_recheck(r)
    raise Frozen({"status": "bad_stage", "reason": "未知 stage=%s" % stage})


def main(r):
    global ARGS, DRY
    ARGS = R.parse_args_b64()
    DRY = bool(ARGS.get("dry_run"))
    r.emit("pipeline_params", detail={"stage": ARGS.get("stage"), "dry_run": DRY,
                                      "visual_ok": bool(ARGS.get("visual_ok")),
                                      "send_authorized": bool(ARGS.get("send_authorized")),
                                      "auth_note_len": len(ARGS.get("auth_note") or "")})
    try:
        out = run_stage(r)
    except Frozen as f:
        p = dict(f.payload)
        try:
            art = r.snapshot("frozen-" + p.get("status", "x"))
            p["artifacts"] = p.get("artifacts") or art
        except Exception:
            pass
        try:
            p["summary_file"] = save_json("frozen-%s.json" % p.get("status", "x"), p)
        except Exception:
            pass
        r.emit("frozen", status=p.get("status"), reason=p.get("reason"))
        raise R.StepFailed(p.get("status", "frozen"), p.get("reason", ""), p)
    return out


if __name__ == "__main__":
    R.Runner("declare_month").run(main)
