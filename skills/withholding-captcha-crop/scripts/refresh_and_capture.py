# refresh_and_capture.py — 刷新验证码 + 精确截取验证码区域
#
# 薄封装: 逻辑全部在 flow_lib.refresh_and_capture(r, unit, password)。
# 该单元会: 幂等填表 → 点验证码图片中心刷新 → ImageGrab 抓真整屏 → 相对定位裁图。
# 产出: C:/rpa/screenshots/{full_real.png, captcha_only.png}
#
# 用法:
#   push_run.sh --lib rpa_core.py --args-json '{"unit":"...","password":"..."}' refresh_and_capture.py
import flow_lib as FL
import rpa_core as R


def main(r):
    args = R.parse_args_b64()
    unit = args.get("unit") or "修文县关珍养殖场"
    password = args.get("password") or ""
    return FL.refresh_and_capture(r, unit, password)


if __name__ == "__main__":
    R.Runner("refresh_and_capture",
             expected_windows={"Tfrm_LoginViewer", "Tfrm_MainFrame",
                               "Tfrm_IntelligentSearchPop"}).run(main)
