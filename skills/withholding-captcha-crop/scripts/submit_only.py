# submit_only.py — 在已填好表单的登录窗上, 只填验证码 + 点登录。
#
# 薄封装: 逻辑全部在 flow_lib.submit_captcha(r, captcha)。
# 注意: flow_lib.submit_captcha 被拒时【返回状态 dict 而非 fail】, 便于主流程循环重试。
#       此独立脚本为保留"单次必成"语义, 遇到 rejected 状态仍 r.fail(冻结现场供排查)。
# 必须在 refresh_and_capture 之后、同一屏幕上立即调用(避免码过期)。
#
# 用法:
#   push_run.sh --lib rpa_core.py --args-json '{"captcha":"<读出4位>"}' submit_only.py
import flow_lib as FL
import rpa_core as R


def main(r):
    args = R.parse_args_b64()
    captcha = args.get("captcha") or ""
    status = FL.submit_captcha(r, captcha)
    if status.get("rejected"):
        r.fail("click_login", "登录被拒（验证码/密码错误）",
               {"modal": status.get("modal")})
    if status.get("timeout"):
        r.fail("click_login", "登录超时", {"waited_s": status.get("waited_s")})
    return status


if __name__ == "__main__":
    R.Runner("submit_only",
             expected_windows={"Tfrm_LoginViewer", "Tfrm_MainFrame"}).run(main)
