# capture_captcha.py — 扣缴端登录：稳定截取验证码图片区域
# 验证码是 owner-drawn 位图（无 HWND），enum 枚举不到其矩形；
# 故用「验证码输入框右侧同排」相对定位，从 ImageGrab.grab() 真整屏中裁出。
#
# 用法:
#   push_run.sh --lib rpa_core.py --args-json '{"unit":"...","password":"..."}' capture_captcha.py
# 产出:
#   C:/rpa/screenshots/full_real.png   真整屏（ImageGrab.grab，物理像素）
#   C:/rpa/screenshots/captcha_only.png 验证码图（相对定位裁出）
#   C:/rpa/screenshots/children.json   登录窗子控件明细 + scale + login_rect（双保险）
import json
import os
import time
import ctypes
from PIL import ImageGrab

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
MAIN_CLS = "Tfrm_MainFrame"
POP_CLS = "Tfrm_IntelligentSearchPop"
EDIT_CLS = "TXPFamerEditEx"
BTN_CLS = "TITSSpeedButton"
SELECTOR_CLS = "TIntelligentSearch"
OUT_DIR = "C:/rpa/screenshots"


# ---------------- 填表辅助（独立副本，不依赖其它技能脚本）----------------
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
    out = {"all": dedup}
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


def close_known_modal(r):
    m = r.blocking_modal()
    if not m:
        return
    btns = [b for b in R.enum_children(m["hwnd"])
            if b["class"] == BTN_CLS and b["visible"]]
    if btns:
        R.click_at(*R.center(btns[0]["rect"]))
    time.sleep(0.6)
    if r.blocking_modal():
        r.fail("close_modal", "弹窗关闭后仍被阻塞")


def fill_form(r, unit, password):
    # 1 切到「申报密码登录」页
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

    # 2 选单位（识别号联动带出）
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
        r.fail("fill_form", "单位列表找不到目标",
               {"want": unit, "candidates": items})
    R.listbox_click_item(lbs[0]["hwnd"], idx)
    time.sleep(0.8)
    if R.find_window(POP_CLS, visible_only=True):
        r.fail("fill_form", "弹窗未收起")
    if not ident_is_filled():
        r.fail("fill_form", "识别号未联动带出")

    # 3 填密码（绕过中文输入法）
    e = declare_edits()
    if not e.get("pwd"):
        r.fail("fill_form", "找不到密码框")
    R.wm_set_text(e["pwd"]["hwnd"], password)
    time.sleep(0.5)
    if R.wm_get_len(e["pwd"]["hwnd"]) != len(password):
        r.fail("fill_form", "密码长度不符")


# ---------------- 主流程 ----------------
def main(r):
    args = R.parse_args_b64()
    unit = args.get("unit") or "修文县关珍养殖场"
    password = args.get("password") or ""
    r.emit("params", detail={"unit": unit, "password": R.mask(password)})

    if not password:
        r.fail("preflight", "缺少 password 参数")
    if R.find_window(MAIN_CLS, visible_only=True):
        return {"logged_in": True, "note": "主界面已可见"}

    lw = login_win()
    if not lw:
        r.fail("preflight", "登录窗不可见")
    if r.blocking_modal():
        close_known_modal(r)
        time.sleep(0.6)
        if r.blocking_modal():
            r.fail("preflight", "关闭弹窗后仍被阻塞")

    # 填表 → 验证码出现
    fill_form(r, unit, password)
    e = declare_edits()
    cf = e.get("captcha")
    if not cf:
        r.fail("captcha_gate", "无验证码框（首次可直接登录）")
    r.emit("captcha_present", detail={"rect": cf["rect"]})

    os.makedirs(OUT_DIR, exist_ok=True)

    # 真整屏（ImageGrab.grab，物理像素）—— 唯一可靠的截图方式
    full = ImageGrab.grab()
    full_path = os.path.join(OUT_DIR, "full_real.png")
    full.save(full_path)
    FW, FH = full.size

    # scale = 物理整屏宽 / 逻辑屏幕宽（SM_CXSCREEN）；现算，不硬编码
    logical_w = ctypes.windll.user32.GetSystemMetrics(0)
    scale = FW / float(logical_w) if logical_w else 1.0
    r.emit("scale", detail={"full_w": FW, "full_h": FH,
                            "logical_w": logical_w, "scale": round(scale, 3)})

    # 子控件明细（双保险：万一相对定位偏了，人可用它在 Mac 侧按同坐标系重裁）
    kids = R.enum_children(lw["hwnd"])
    children_info = [{"class": k["class"], "title": k["title"],
                     "visible": k["visible"], "rect": k["rect"]} for k in kids]
    children_path = os.path.join(OUT_DIR, "children.json")
    with open(children_path, "w", encoding="utf-8") as f:
        json.dump({"login_rect": lw["rect"], "scale": scale,
                   "children": children_info}, f, ensure_ascii=False, indent=2)

    # ---- 验证码位图矩形：路径 B（直接暴露）优先，失败回退路径 A（相对定位）----
    cx1, cy1, cx2, cy2 = cf["rect"]
    wx1, wy1, wx2, wy2 = lw["rect"]
    chosen, method = None, None

    # 路径 B：输入框右侧、垂直重叠、非编辑/按钮类的子控件（如 TImage）
    for k in kids:
        if not k["visible"]:
            continue
        cls = k["class"]
        if cls.startswith(EDIT_CLS) or cls.startswith(BTN_CLS) or cls.startswith(SELECTOR_CLS):
            continue
        kx1, ky1, kx2, ky2 = k["rect"]
        w, h = kx2 - kx1, ky2 - ky1
        if w < 40 or w > 260 or h < 20 or h > 90:
            continue
        if kx1 < cx2 - 30:
            continue
        if ky2 < cy1 - 20 or ky1 > cy2 + 20:
            continue
        chosen, method = k["rect"], "exposed_child:" + cls
        break

    # 路径 A：owner-drawn 无 HWND → 用「输入框右侧同排」相对定位
    if not chosen:
        pad_x = max(3, int((cx2 - cx1) * 0.02))
        pad_y = max(7, int((cy2 - cy1) * 0.2))
        chosen = [cx2 + pad_x, cy1 - pad_y, wx2 - 2, cy2 + pad_y]
        method = "relative_to_input"

    r.emit("captcha_image", detail={"method": method, "logical_rect": chosen})

    # 物理 bbox 精确截取
    bbox = (int(chosen[0] * scale), int(chosen[1] * scale),
            int(chosen[2] * scale), int(chosen[3] * scale))
    cap = ImageGrab.grab(bbox=bbox)
    cap_path = os.path.join(OUT_DIR, "captcha_only.png")
    cap.save(cap_path)
    r.emit("captcha_crop", detail={"bbox": bbox, "size": cap.size})

    return {"captcha_image_method": method,
            "captcha_rect_logical": chosen,
            "bbox": bbox,
            "captcha_only": cap_path,
            "full": full_path,
            "children": children_path,
            "scale": scale,
            "login_rect": lw["rect"],
            "captcha_input_rect": cf["rect"],
            "note": "验证码图已按相对定位精确截取；下一步由 OCR/视觉读出 4 位字符后，"
                    "用 submit_only.py 只填码点登录（勿重填表单，避免刷新验证码）"}


if __name__ == "__main__":
    R.Runner("capture_captcha",
             expected_windows={LOGIN_CLS, MAIN_CLS, POP_CLS}).run(main)
