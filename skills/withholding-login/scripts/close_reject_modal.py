# close_reject_modal.py — 关闭「验证码/密码错误」被拒弹窗(Tfrm_MsgDlgRich)
#
# 这是 flow_lib.dismiss_reject_modal(r) 的【薄封装/CLI 入口】, 不是独立逻辑。
# 真正可独立调用的逻辑单元是 flow_lib.dismiss_reject_modal(r),
# 主流程(如 solve_loop)会直接 import 调用它, 此脚本仅用于单独手动触发。
#
# 用法:
#   push_run.sh --lib rpa_core.py close_reject_modal.py
import flow_lib as FL


def main(r):
    return FL.dismiss_reject_modal(r)


if __name__ == "__main__":
    import rpa_core as R
    R.Runner("close_reject_modal",
             expected_windows={"Tfrm_LoginViewer", "Tfrm_MainFrame",
                               "Tfrm_MsgDlgRich"}).run(main)
