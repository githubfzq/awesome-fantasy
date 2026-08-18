# close_refresh_capture.py — 一键：关弹窗(如有) → 刷新验证码 → 截取到共享文件夹
# 合并三步为一次 PsExec 调用，最大限度压缩验证码有效期内的时间窗口。
import os, time, ctypes
from PIL import ImageGrab
import rpa_core as R
from flow_lib import (login_win, declare_edits, captcha_image_rect,
                      LOGIN_CLS, MAIN_CLS, EDIT_CLS,
                      MODAL_CLS, BTN_CLS)

VM_OUT = r"C:\rpa\screenshots\captcha_only.png"
SHARE = r"\\Mac\Home\Documents\rpa\captcha_only.png"


def main(r):
    if R.find_window(MAIN_CLS, visible_only=True):
        return {"logged_in": True}
    lw = login_win()
    if not lw:
        r.fail("preflight", "登录窗不可见")

    # ---- 1 关闭任何 Tfrm_MsgDlgRich 弹窗（不验证文字，直接点确定钮） ----
    m = R.find_window(MODAL_CLS, visible_only=True)
    if m:
        btns = [b for b in R.enum_children(m["hwnd"])
                if b["visible"] and b["class"] == BTN_CLS]
        if btns:
            R.click_at(*R.center(btns[0]["rect"]))
            r.emit("modal_closed", detail={"title": m["title"], "hwnd": m["hwnd"]})
            time.sleep(0.7)
            if R.find_window(MODAL_CLS, visible_only=True):
                r.fail("close_modal", "点击后弹窗仍存在")
        else:
            r.emit("no_button_on_modal", detail=m)
    else:
        r.emit("no_modal")

    # ---- 2 表单状态诊断 ----
    e = declare_edits()
    ident_len = R.wm_get_len(e["ident"]["hwnd"]) if e.get("ident") else 0
    pwd_len = R.wm_get_len(e["pwd"]["hwnd"]) if e.get("pwd") else 0
    r.emit("form_state", detail={"ident_len": ident_len, "pwd_len": pwd_len})

    cf = e.get("captcha")
    if not cf:
        r.fail("captcha_gate", "无验证码框")

    # ---- 3 点击验证码图片中心刷新 ----
    cr = captcha_image_rect(cf, lw)
    ccx, ccy = (cr[0] + cr[2]) // 2, (cr[1] + cr[3]) // 2
    R.click_at(ccx, ccy)
    time.sleep(1.2)

    # ---- 4 截取验证码区域（物理像素 bbox） ----
    full = ImageGrab.grab()
    FW, FH = full.size
    logical_w = ctypes.windll.user32.GetSystemMetrics(0)
    scale = FW / float(logical_w) if logical_w else 1.0
    cr2 = captcha_image_rect(cf, lw)
    bbox = (int(cr2[0] * scale), int(cr2[1] * scale),
            int(cr2[2] * scale), int(cr2[3] * scale))
    cap = ImageGrab.grab(bbox=bbox)
    os.makedirs(os.path.dirname(VM_OUT), exist_ok=True)
    cap.save(VM_OUT)
    shared = None
    try:
        cap.save(SHARE)
        shared = SHARE
    except Exception as ex:
        r.emit("share_err", detail=repr(ex))
    return {"form": {"ident_len": ident_len, "pwd_len": pwd_len},
            "captcha_only": VM_OUT, "captcha_shared": shared,
            "bbox": bbox, "scale": round(scale, 3),
            "note": "已关闭弹窗+刷新+截取；下一步立即 Read 共享图片识别后 submit_only 提交"}


if __name__ == "__main__":
    R.Runner("close_refresh_capture",
             expected_windows={LOGIN_CLS, MAIN_CLS, MODAL_CLS}).run(main)
