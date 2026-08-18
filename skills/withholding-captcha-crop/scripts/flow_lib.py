# flow_lib.py — 扣缴端登录「验证码闭环」的可组合逻辑单元
#
# 设计目标（用户明确）:
#   验证码被拒弹窗的关闭, 不是一个独立技能, 而是一个【可独立调用的逻辑单元(函数)】。
#   本模块把闭环切成几个函数, 任何主流程都能 import 后直接调用, 也能被薄脚本单独跑。
#
# 坐标系约定(关键, 勿改):
#   - Win32 矩形 / 点击(SetCursorPos) 均为「逻辑像素」(进程被 DPI 虚拟化)
#   - ImageGrab.grab() 返回「物理像素」, 故 bbox = 逻辑rect × scale
#   - 点击用逻辑中心即可, OS 自动映射物理, 与 fill_form 的点击一致
#
# 暴露的函数(均可独立调用):
#   dismiss_reject_modal(r)      # 关闭被拒弹窗(Tfrm_MsgDlgRich) → 回登录界面
#   ensure_form_filled(r, unit, password)   # 幂等填好单位+密码
#   refresh_and_capture(r, unit, password)  # 点图刷新 + 截验证码区域
#   submit_captcha(r, text)      # 回填验证码 + 点登录(被拒返回状态, 不 fail)
#   solve_loop(r, unit, password, recognize, max_tries)  # 组合闭环模板
import time
import os
import ctypes
from PIL import ImageGrab

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
MAIN_CLS = "Tfrm_MainFrame"
POP_CLS = "Tfrm_IntelligentSearchPop"
EDIT_CLS = "TXPFamerEditEx"
BTN_CLS = "TITSSpeedButton"
SELECTOR_CLS = "TIntelligentSearch"
MODAL_CLS = "Tfrm_MsgDlgRich"
OUT_DIR = "C:/rpa/screenshots"

BTN_PREFIXES = ("TITSSpeedButton", "TModalSpeedButtonRound", "TButton",
                "TBitBtn", "TSpeedButton")
POSITIVE = ("确定", "确认", "是", "OK", "知道了", "关闭")
# 被拒弹窗正文若含这些词, 即判定为「验证码超时/错误」类, 可安全自动关闭并重试
CAPTCHA_KEYWORDS = ("验证码", "超时")


# ---------------- 通用辅助 ----------------
def login_win():
    return R.find_window(LOGIN_CLS, visible_only=True)


def visible_kids(parent, prefix):
    return [k for k in R.enum_children(parent)
            if k["class"].startswith(prefix) and k["visible"]]


def declare_edits():
    lw = login_win()
    if not lw:
        return {}
    edits = visible_kids(lw["hwnd"], EDIT_CLS)
    edits.sort(key=lambda w: (w["rect"][1], w["hwnd"]))
    dedup = []
    for e in edits:
        if dedup and abs(e["rect"][1] - dedup[-1]["rect"][1]) <= 5:
            continue
        dedup.append(e)
    out = {}
    if len(dedup) >= 1:
        out["ident"] = dedup[0]
    if len(dedup) >= 2:
        out["pwd"] = dedup[1]
    if len(dedup) >= 3:
        out["captcha"] = dedup[2]
    return out


def declare_page_active():
    lw = login_win()
    if not lw:
        return None
    sel = visible_kids(lw["hwnd"], SELECTOR_CLS)
    return {"selector_rect": sel[0]["rect"]} if sel else None


def ident_value():
    e = declare_edits()
    return R.wm_get_text(e["ident"]["hwnd"]) if e.get("ident") else None


def ident_is_filled():
    t = ident_value()
    return bool(t and len(t) >= 15 and "识别号" not in t)


def captcha_image_rect(cf, lw):
    """owner-drawn 验证码位图 = 验证码输入框右侧同排(无 HWND, 只能相对定位)"""
    cx1, cy1, cx2, cy2 = cf["rect"]          # 验证码输入框(逻辑)
    wx1, wy1, wx2, wy2 = lw["rect"]          # 登录窗(逻辑)
    pad_x = max(3, int((cx2 - cx1) * 0.02))
    pad_y = max(7, int((cy2 - cy1) * 0.2))
    return [cx2 + pad_x, cy1 - pad_y, wx2 - 2, cy2 + pad_y]


def login_button(lw):
    e = declare_edits()
    floor_y = e["captcha"]["rect"][1] if e.get("captcha") else lw["rect"][1] + 400
    cands = [b for b in visible_kids(lw["hwnd"], BTN_CLS)
             if b["rect"][1] > floor_y and (b["rect"][2] - b["rect"][0]) >= 150]
    if not cands:
        return None
    cands.sort(key=lambda b: (b["rect"][2] - b["rect"][0]), reverse=True)
    return cands[0]


# =====================================================================
# 逻辑单元 1: 关闭被拒弹窗 —— 可独立调用
# =====================================================================
# =====================================================================
# 逻辑单元 0: 读被拒弹窗文字并验证(纯读控件文字, 不截图)
# =====================================================================
def read_reject_modal(r):
    """读取被拒弹窗(Tfrm_MsgDlgRich)的标题与正文文字, 确认是否为
    「验证码超时/错误」类弹窗。纯读控件文字, 不截图。

    做法: 枚举弹窗子控件, 取每个非按钮子控件的 title(WM_GETTEXT)。
          Delphi 消息框正文在 TLabel/TStaticText 等子控件中, 文字可直接读。
    返回 dict:
      found              : 是否存在 Tfrm_MsgDlgRich 弹窗
      title              : 弹窗标题(如「提示信息」)
      message            : 合并去重后的正文文字
      is_captcha_reject  : 是否匹配验证码超时/错误关键词(决定可否自动关闭)
      keywords_matched   : 命中的关键词列表
      children_texts     : 各非按钮子控件的 {class,title}
    """
    m = R.find_window(MODAL_CLS, visible_only=True)
    if not m:
        return {"found": False, "note": "当前无 Tfrm_MsgDlgRich 弹窗, 可能已在正常登录界面"}
    title = m["title"] or ""
    kids = R.enum_children(m["hwnd"])
    texts = []
    child_meta = []
    for k in kids:
        t = (k.get("title") or "").strip()
        is_btn = any(k["class"].startswith(p) for p in BTN_PREFIXES)
        if is_btn or not t:
            continue
        child_meta.append({"class": k["class"], "title": t})
        if t not in texts:
            texts.append(t)
    message = " ".join(texts)
    matched = [kw for kw in CAPTCHA_KEYWORDS if kw in message]
    return {
        "found": True,
        "title": title,
        "message": message,
        "is_captcha_reject": bool(matched),
        "keywords_matched": matched,
        "children_texts": child_meta,
    }


# =====================================================================
# 逻辑单元 1: 关闭被拒弹窗 —— 可独立调用
# =====================================================================
def dismiss_reject_modal(r):
    """识别验证码/密码错误等被拒弹窗(Tfrm_MsgDlgRich), 点击其确认钮, 回到登录界面。

    设计要点(用户明确):
      - dismiss 之前必须先「读 + 验证」: 调用 read_reject_modal 取弹窗正文文字,
        仅当 is_captcha_reject=True(验证码超时/错误)时才自动关闭, 否则 STOP 交人工。
      - 这是"被拒恢复"的独立逻辑单元, 主流程在 submit 后检测到 rejected 状态时调用它
      - Tfrm_MsgDlgRich 多用 TModalSpeedButtonRound 自绘按钮, GetWindowTextW 常空串
        → 优先按文本匹配正向词, 失败则按 rect[0] 升序取最靠左可见按钮
          (多数中文对话框「确定」在左、「取消」在右)
      - 切勿误点「取消/重试/关闭」等负向按钮
    返回: {"closed": bool, "verified": bool, ...}
    """
    # ---- 第一步: 读 + 验证(不截图) ----
    info = read_reject_modal(r)
    r.emit("read_modal", detail=info)
    if not info["found"]:
        return {"closed": False, "verified": None,
                "note": "无被拒弹窗, 已在正常登录界面"}
    if not info["is_captcha_reject"]:
        # 非验证码类弹窗(如密码错误/网络异常等) → 不自动关闭, 交人工
        r.emit("not_captcha_modal", detail=info)
        return {"closed": False, "verified": False,
                "title": info["title"], "message": info["message"],
                "note": "弹窗正文非验证码超时/错误类, 已停止自动关闭, 需人工介入"}

    # ---- 第二步: 验证通过才关 ----
    m = R.find_window(MODAL_CLS, visible_only=True)
    r.emit("modal_found", detail={"title": m["title"], "rect": m["rect"]})
    btns = [k for k in R.enum_children(m["hwnd"])
            if k["visible"] and any(k["class"].startswith(p) for p in BTN_PREFIXES)]
    if not btns:
        r.fail("close_modal", "弹窗内未找到按钮",
               {"modal": m["title"],
                "children": [{"class": k["class"], "title": k.get("title")}
                             for k in R.enum_children(m["hwnd"])]})
    r.emit("buttons",
           detail=[{"class": b["class"], "title": b.get("title"), "rect": b["rect"]}
                   for b in btns])

    confirm, method = _pick_confirm(btns)
    if not confirm:
        r.fail("close_modal", "找不到确认按钮")
    r.emit("click",
           detail={"class": confirm["class"], "title": confirm.get("title"),
                   "rect": confirm["rect"], "method": method})
    R.click_at(*R.center(confirm["rect"]))
    time.sleep(0.8)

    # 验证关闭 + 回到登录界面
    if R.find_window(MODAL_CLS, visible_only=True):
        r.fail("close_modal", "点击确认后弹窗仍存在")
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if not lw:
        r.fail("close_modal", "弹窗已关但登录窗不可见")
    r.emit("back_to_login", detail={"login_rect": lw["rect"]})
    return {"closed": True, "verified": True, "message": info["message"],
            "note": "被拒弹窗已确认(验证码类)并关闭, 回到登录界面; 下一步刷新+读码+提交"}


def _pick_confirm(btns):
    """文本优先(最靠左) → 兜底最靠左可见按钮"""
    for b in sorted(btns, key=lambda b: b["rect"][0]):
        t = (b.get("title") or "").strip()
        if t and any(w in t for w in POSITIVE):
            return b, "text"
    if btns:
        return sorted(btns, key=lambda b: b["rect"][0])[0], "leftmost"
    return None, None


# =====================================================================
# 逻辑单元 2: 确保表单已填(幂等) —— 可被 ensure + refresh 复用
# =====================================================================
def ensure_form_filled(r, unit, password):
    if not declare_page_active():
        tabs = [c for c in R.enum_children(login_win()["hwnd"])
                if "TITSTabControl" in c["class"]]
        tabs.sort(key=lambda c: c["rect"][0])
        done = False
        for t in tabs:
            r0 = t["rect"]
            R.click_at((r0[0] + r0[2]) // 2, (r0[1] + r0[3]) // 2)
            time.sleep(0.5)
            if declare_page_active():
                done = True
                break
        if not done:
            r.fail("fill_form", "无法切到申报密码登录页")

    sel = visible_kids(login_win()["hwnd"], SELECTOR_CLS)
    if not sel:
        r.fail("fill_form", "找不到单位选择器")
    R.click_at(*R.center(sel[0]["rect"]))
    time.sleep(0.8)
    p = R.find_window(POP_CLS, visible_only=True)
    if not p:
        r.fail("fill_form", "单位列表未弹出")
    lbs = [k for k in R.enum_children(p["hwnd"]) if k["class"].startswith("TListBox")]
    if not lbs:
        r.fail("fill_form", "列表控件缺失")
    items = R.listbox_items(lbs[0]["hwnd"])
    idx = next((i for i, t in enumerate(items) if unit in (t or "")), None)
    if idx is None and len(unit) > 1:
        stem = unit[:-1]
        idx = next((i for i, t in enumerate(items) if stem in (t or "")), None)
    if idx is None:
        r.fail("fill_form", "单位列表找不到目标", {"want": unit, "candidates": items})
    R.listbox_click_item(lbs[0]["hwnd"], idx)
    time.sleep(0.8)
    if R.find_window(POP_CLS, visible_only=True):
        r.fail("fill_form", "弹窗未收起")
    if not ident_is_filled():
        r.fail("fill_form", "识别号未联动带出")

    e = declare_edits()
    if not e.get("pwd"):
        r.fail("fill_form", "找不到密码框")
    R.wm_set_text(e["pwd"]["hwnd"], password)
    time.sleep(0.5)
    if R.wm_get_len(e["pwd"]["hwnd"]) != len(password):
        r.fail("fill_form", "密码长度不符")


# =====================================================================
# 逻辑单元 3: 刷新验证码 + 截取(不点登录) —— 供 OCR/视觉读出
# =====================================================================
def refresh_and_capture(r, unit=None, password=None):
    if not password:
        r.fail("preflight", "缺少 password 参数")
    if R.find_window(MAIN_CLS, visible_only=True):
        return {"logged_in": True, "note": "主界面已可见"}

    lw = login_win()
    if not lw:
        r.fail("preflight", "登录窗不可见")
    if r.blocking_modal():
        # 见到弹窗先关(复用单元1), 再继续
        dismiss_reject_modal(r)
        time.sleep(0.6)
        if r.blocking_modal():
            r.fail("preflight", "关闭弹窗后仍被阻塞")

    # 幂等填表
    ed = declare_edits()
    filled = (ed.get("ident") and ident_is_filled()
              and ed.get("pwd") and R.wm_get_len(ed["pwd"]["hwnd"]) == len(password))
    if filled:
        r.emit("form", detail={"state": "already_filled"})
    else:
        r.emit("form", detail={"state": "filling"})
        ensure_form_filled(r, unit or "修文县关珍养殖场", password)

    e = declare_edits()
    cf = e.get("captcha")
    if not cf:
        r.fail("captcha_gate", "无验证码框(首次可直接登录)")

    # 点击验证码图片中心 → 刷新
    cr = captcha_image_rect(cf, lw)
    ccx, ccy = (cr[0] + cr[2]) // 2, (cr[1] + cr[3]) // 2
    r.emit("click_refresh", detail={"logical_center": [ccx, ccy], "image_rect": cr})
    R.click_at(ccx, ccy)
    time.sleep(1.2)

    os.makedirs(OUT_DIR, exist_ok=True)
    full = ImageGrab.grab()
    full_path = os.path.join(OUT_DIR, "full_real.png")
    full.save(full_path)
    FW, FH = full.size
    logical_w = ctypes.windll.user32.GetSystemMetrics(0)
    scale = FW / float(logical_w) if logical_w else 1.0
    r.emit("scale", detail={"full_w": FW, "full_h": FH,
                            "logical_w": logical_w, "scale": round(scale, 3)})

    cr2 = captcha_image_rect(cf, lw)
    bbox = (int(cr2[0] * scale), int(cr2[1] * scale),
            int(cr2[2] * scale), int(cr2[3] * scale))
    cap = ImageGrab.grab(bbox=bbox)
    cap_path = os.path.join(OUT_DIR, "captcha_only.png")
    cap.save(cap_path)
    r.emit("captcha_crop", detail={"bbox": bbox, "size": cap.size})

    return {"captcha_only": cap_path,
            "bbox": bbox,
            "scale": scale,
            "login_rect": lw["rect"],
            "captcha_input_rect": cf["rect"],
            "click_logical_center": [ccx, ccy],
            "note": "验证码已刷新并截取; 下一步读码后 submit_captcha() 回填"}


# =====================================================================
# 逻辑单元 4: 回填验证码 + 点登录(被拒返回状态, 不 fail)
# =====================================================================
def submit_captcha(r, captcha):
    if not captcha:
        r.fail("preflight", "缺少 captcha 参数")
    if R.find_window(MAIN_CLS, visible_only=True):
        return {"logged_in": True, "note": "主界面已可见"}

    lw = login_win()
    if not lw:
        r.fail("preflight", "登录窗不可见")
    if r.blocking_modal():
        return {"rejected": True, "note": "提交前存在阻塞弹窗, 需先 dismiss_reject_modal"}

    e = declare_edits()
    cf = e.get("captcha")
    if not cf:
        r.fail("captcha_gate", "无验证码框（可不必走本步）")
    R.wm_set_text(cf["hwnd"], captcha)
    time.sleep(0.4)
    if R.wm_get_len(cf["hwnd"]) != len(captcha):
        r.fail("fill_captcha", "验证码长度不符",
               {"want": len(captcha), "got": R.wm_get_len(cf["hwnd"])})

    btn = login_button(lw)
    if not btn:
        r.fail("click_login", "找不到登录钮")
    r.emit("click_login", detail={"rect": btn["rect"]})
    R.click_at(*R.center(btn["rect"]))

    def check():
        if R.find_window(MAIN_CLS, visible_only=True):
            return "logged_in"
        m = r.blocking_modal()
        if m:
            return {"rejected": True, "modal": m["title"]}
        return None

    v, el = R.wait_until(check, timeout=20.0, interval=0.4)
    if v == "logged_in":
        return {"logged_in": True, "elapsed_s": el, "note": "主界面可见, 登录成功"}
    if isinstance(v, dict) and v.get("rejected"):
        return {"rejected": True, "modal": v.get("modal"),
                "note": "登录被拒(验证码/密码错误); 应调用 dismiss_reject_modal 后重试"}
    return {"timeout": True, "waited_s": el, "note": "登录超时(未进主界面、无弹窗)"}


# =====================================================================
# 组合: 闭环重试模板(识别回调由外部注入)
# =====================================================================
def solve_loop(r, unit, password, recognize, max_tries=5):
    """完整闭环: 每轮 刷新截取→recognize(读图返回4位)→提交→被拒不失败而是关弹窗重试。
    recognize(info) -> str : 由外部(视觉/OCR)注入; info 含 captcha_only 路径。
    返回最后状态 dict。"""
    for i in range(1, max_tries + 1):
        r.emit("try", detail={"n": i, "max": max_tries})
        info = refresh_and_capture(r, unit, password)
        if info.get("logged_in"):
            return info
        text = recognize(info)
        if not text:
            return {"logged_in": False, "note": f"第{i}轮无法识别验证码"}
        status = submit_captcha(r, text)
        if status.get("logged_in"):
            return status
        if status.get("rejected"):
            res = dismiss_reject_modal(r)   # 单元1: 先读验证, 确认验证码类才关
            if not res.get("closed"):
                # 非验证码类弹窗 / 关失败 → 停止, 交人工, 不再空转重试
                return {"logged_in": False, "stopped": True, **res}
            continue
        return status
    return {"logged_in": False, "note": f"已达最大重试 {max_tries} 次"}
