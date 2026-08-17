# close_modal.py — 关闭挡窗的隐形 Tfrm_MsgDlgRich 弹窗
# owner-drawn 文字读不出、但模态挡住所有点击；pywinauto 给的坐标对它是错的，必须用真实 rect。
# 依赖 rpa_core.py。带每步验证：点完确定钮后轮询确认弹窗已消失。
import rpa_core as R

MODAL_CLS = "Tfrm_MsgDlgRich"
BTN_CLS = "TITSSpeedButton"


def main(r):
    def find_modal():
        return R.find_window(MODAL_CLS, visible_only=True)

    m = find_modal()
    if not m:
        return {"closed": False, "reason": "无可见 Tfrm_MsgDlgRich（可能已关闭）"}

    def do_close():
        btns = [b for b in R.enum_children(m["hwnd"])
                if b["class"] == BTN_CLS and b["visible"]]
        if not btns:
            r.fail("close_modal", "弹窗内未找到确定钮", {"modal": m})
        b = btns[0]
        R.click_at(*R.center(b["rect"]))
        return {"clicked_center": list(R.center(b["rect"])),
                "button_rect": b["rect"], "modal_hwnd": m["hwnd"]}

    r.step("close_modal", action=do_close,
           verify=lambda: {"gone": True} if find_modal() is None else None,
           verify_desc="弹窗已消失", timeout=8, guard=False)
    return {"closed": True, "modal_hwnd": m["hwnd"]}


if __name__ == "__main__":
    R.Runner("close_modal", expected_windows={MODAL_CLS}).run(main)
