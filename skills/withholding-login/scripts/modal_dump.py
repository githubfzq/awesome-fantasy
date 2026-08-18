# modal_dump.py — 诊断退出相关确认弹窗（Tfrm_MsgDlgRich / Tfrm_MsgDlg）内按钮结构
# 两类弹窗均为 Delphi owner-drawn，按钮多为无文本圆角按钮：
#   - Tfrm_MsgDlgRich 「确认信息」: 确定(左)/取消(右)，按钮 TModalSpeedButtonRound
#   - Tfrm_MsgDlg    「提示信息」(如数据库备份提示): 单按钮「确认」，按钮 TModalSpeedButton
import rpa_core as R

CONFIRM_CLS = ("Tfrm_MsgDlgRich", "Tfrm_MsgDlg")
BTN_CLS = ("TButton", "TBitBtn", "TITSSpeedButton", "TModalSpeedButtonRound", "TModalSpeedButton")


def main(r):
    out = []
    for w in R.enum_top_windows():
        if w["class"] in CONFIRM_CLS and w["visible"]:
            kids = R.enum_children(w["hwnd"])
            btns = [k for k in kids
                    if k["class"] in BTN_CLS or "button" in k["class"].lower()]
            out.append({
                "hwnd": w["hwnd"],
                "class": w["class"],
                "title": w["title"],
                "rect": w["rect"],
                "buttons": btns,
                "all_classes": sorted({k["class"] for k in kids}),
            })
    return {"confirm_modals": out, "count": len(out)}


if __name__ == "__main__":
    R.Runner("modal_dump", expected_windows=set(CONFIRM_CLS)).run(main)
