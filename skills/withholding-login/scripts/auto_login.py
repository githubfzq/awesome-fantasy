# auto_login.py — 扣缴端「一键登录」状态机（Agent 最小交互版）
#
# 设计目标：整个登录流程 = 一次 VM 调用；Agent 只看返回的顶层 `status` 字段分支，
# 不需要逐步骤读日志/枚举窗口。验证码路径 = 脚本自动截好图并落到 Mac 侧共享盘
# （~/Documents/rpa/captcha.png），Agent 读图后带 --captcha 再调一次即完成。
#
# 用法（Mac 侧推荐经 ~/Documents/rpa/auto_login.sh，参数 base64 JSON 传）：
#   run_vm.sh --args-json '{"unit":"...","password":"...","captcha":"<4位码>","dry_run":true,
#                           "auto_close_modal":true,"start_app":true,"login_timeout":45}' auto_login.py
#
# 返回 last_result.json 的顶层字段：
#   status:
#     already_logged_in  主界面已可见，无需重复登录（幂等）
#     not_started        登录窗不可见且 start_app=false（未自动启动）
#     start_timeout      已自动启动扣缴端，但等待登录窗超时（可能弹系统错误框）
#     dry_run            只读体检+定位，未做任何点击/输入（located 含控件矩形）
#     modal_blocked      有阻塞模态弹窗且未授权自动关闭（modal/modal_text/screen）
#     captcha_required   已填好表单并截好验证码图；captcha_mac 为 Mac 侧 PNG 路径
#     success            登录成功（main_rect）
#     rejected           登录被拒（非验证码类，如密码错误）→ 停机，绝不自动重试
#     timeout            点登录后超时未进主界面、无弹窗
#   reason/note/failed_step/screen/captcha_mac 等为补充信息
#
# 默认 start_app=true：登录窗不可见时自动 Start-Process 扣缴端并等待出现，
# 整条登录流程 = 一次 VM 调用（验证码路径 = 两次：截码 → 填码提交）。
#
# 硬约束（与 login_declare 一致，不可绕过）：
#   - 只用「申报密码登录」（spDeclare）；禁实名/账号密码登录。
#   - 有验证码框但未提供验证码 → 拒绝点登录（防密码错误累计锁定）。
#   - 被拒弹窗只有读文案确认是「验证码/超时」类才自动关闭并刷新换码；否则停机交人工。
#   - 密码/验证码日志只记长度（mask），绝不落明文。
import ctypes
import os
import time

import rpa_core as R
import flow_lib as FL

LOGIN_CLS = "Tfrm_LoginViewer"
MAIN_CLS = "Tfrm_MainFrame"
MODAL_CLS = "Tfrm_MsgDlgRich"
SHARED_CAPTCHA = r"\Mac\Home\Documents\rpa\captcha.png"   # 共享盘 → Mac ~/Documents/rpa/captcha.png
LOCAL_CAPTCHA = r"C:/rpa/screenshots/captcha_only.png"
APP_EXE = r"C:\ITSKHD\EPPortal_DS3.0\EPEvenue_SH.exe"      # 启动器，拉起 EPPortalITS2.exe
APP_WORKDIR = r"C:\ITSKHD\EPPortal_DS3.0"
APP_WAIT = 45                                              # 启动后等登录窗出现的秒数


def start_app(r):
    """启动扣缴端并等待登录窗出现。返回 None（成功，继续主流程）或失败 status 字典。"""
    import subprocess
    r.emit("start_app", detail={"exe": APP_EXE})
    try:
        subprocess.Popen([APP_EXE], cwd=APP_WORKDIR)
    except Exception as e:
        return {"status": "error", "reason": "启动扣缴端失败",
                "failed_step": "start_app", "detail": repr(e)}

    def check():
        return R.find_window(LOGIN_CLS, visible_only=True)

    v, el = R.wait_until(check, timeout=APP_WAIT, interval=1.0)
    if not v:
        art = r.snapshot("start_timeout")
        return {"status": "start_timeout",
                "reason": "启动扣缴端后 %.0fs 未见登录窗（可能弹了系统错误框）" % el,
                "screen": art.get("screen")}
    r.emit("app_started", detail={"elapsed_s": el})
    return None


# ---------------------------------------------------------------- 截图发布
def publish_captcha(r):
    """把 VM 内已截好的 captcha_only.png 复制到共享盘（Mac 可直接读），返回双路径。
    共享盘写入失败则回退 VM 本地路径（Agent 需 pull_file.sh 回传）。"""
    mac = None
    try:
        if os.path.exists(LOCAL_CAPTCHA):
            from PIL import Image
            Image.open(LOCAL_CAPTCHA).save(SHARED_CAPTCHA)
            mac = "~/Documents/rpa/captcha.png"
    except Exception as e:
        r.emit("captcha_publish_fallback", detail={"error": repr(e)})
    return {"captcha_vm": LOCAL_CAPTCHA, "captcha_mac": mac}


def _capture_after_refresh(r, unit, password):
    """刷新验证码并截取（复用 flow_lib；必要时幂等重填表单），返回 status 字典。"""
    try:
        info = FL.refresh_and_capture(r, unit, password)
    except R.StepFailed as e:
        # 无验证码框等异常 → 原样失败信息
        return {"status": "error", "reason": e.reason,
                "failed_step": e.step, "detail": e.detail}
    cap = publish_captcha(r)
    return {
        "status": "captcha_required",
        "note": "验证码已刷新并截取，请读图后带 --captcha 重跑",
        "captcha_vm": cap["captcha_vm"],
        "captcha_mac": cap["captcha_mac"],
        "bbox": info.get("bbox"),
        "scale": info.get("scale"),
    }


def _read_modal_safe(r):
    """读被拒/阻塞弹窗文案（纯读控件文字，不截图）。"""
    try:
        return FL.read_reject_modal(r)
    except Exception as e:
        return {"found": False, "read_error": repr(e)}


# ---------------------------------------------------------------- 点登录
def _click_login(r, unit, password, login_timeout):
    """填好表单后点登录，轮询三态；被拒时读文案分流（验证码类→自动关+换码，否则停机）。"""
    lw = FL.login_win()
    btn = FL.login_button(lw)
    if not btn:
        r.fail("click_login", "找不到登录按钮")
    R.click_at(*R.center(btn["rect"]))

    def check():
        if R.find_window(MAIN_CLS, visible_only=True):
            return "logged_in"
        if r.blocking_modal():
            return "rejected"
        return None

    v, el = R.wait_until(check, timeout=login_timeout, interval=0.5)
    if v == "logged_in":
        mw = R.find_window(MAIN_CLS, visible_only=True)
        return {"status": "success", "main_rect": mw["rect"], "elapsed_s": el}
    if v == "rejected":
        info = _read_modal_safe(r)
        if info.get("is_captcha_reject"):
            # 验证码超时/错误 → 自动关弹窗 → 刷新并截新码 → 交 Agent 重读重填
            try:
                FL.dismiss_reject_modal(r)
                time.sleep(0.6)
            except R.StepFailed as e:
                return {"status": "error", "reason": e.reason,
                        "failed_step": e.step}
            cap = _capture_after_refresh(r, unit, password)
            cap["note"] = "验证码错误/超时：已自动关弹窗并刷新新码"
            return cap
        # 非验证码类被拒（密码错误/账号异常等）→ 停机，绝不自动重试
        art = r.snapshot("rejected")
        return {"status": "rejected",
                "reason": "登录被拒（非验证码类），已停机",
                "modal_text": info.get("message") or info.get("title"),
                "screen": art.get("screen")}
    art = r.snapshot("timeout")
    return {"status": "timeout", "screen": art.get("screen"),
            "reason": "点登录后 %.1fs 未进主界面、无弹窗" % el}


# ---------------------------------------------------------------- 主流程
def main(r):
    args = R.parse_args_b64()
    unit = args.get("unit") or "修文县关珍养殖场"
    password = args.get("password") or ""
    captcha = args.get("captcha") or ""
    dry_run = bool(args.get("dry_run"))
    auto_close_modal = bool(args.get("auto_close_modal"))
    start_app_flag = bool(args.get("start_app", True))
    login_timeout = float(args.get("login_timeout", 45))

    r.emit("params", detail={
        "unit": unit,
        "password": R.mask(password),
        "captcha": R.mask(captcha),
        "dry_run": dry_run,
        "auto_close_modal": auto_close_modal,
        "start_app": start_app_flag,
        "login_timeout": login_timeout,
    })

    # ---- 幂等：已登录直接返回 ----
    mw = R.find_window(MAIN_CLS, visible_only=True)
    if mw:
        return {"status": "already_logged_in", "main_rect": mw["rect"],
                "note": "主界面已可见，无需重复登录"}

    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if not lw:
        if not start_app_flag:
            return {"status": "not_started", "note": "登录窗不可见（start_app=false 未自动启动）"}
        res = start_app(r)
        if res:
            return res
        lw = R.find_window(LOGIN_CLS, visible_only=True)
        if not lw:
            return {"status": "not_started", "note": "启动后仍未发现登录窗，请人工检查"}

    # ---- dry_run：纯只读体检 + 定位，绝不点击/输入 ----
    if dry_run:
        ed = FL.declare_edits()
        btn = FL.login_button(lw)
        return {"status": "dry_run",
                "located": {
                    "login_rect": lw["rect"],
                    "ident": ed.get("ident", {}).get("rect"),
                    "pwd": ed.get("pwd", {}).get("rect"),
                    "captcha": ed.get("captcha", {}).get("rect"),
                    "login_button": btn["rect"] if btn else None,
                },
                "note": "只读体检+定位，未做任何点击/输入"}

    if not password:
        r.fail("preflight", "缺少 password 参数（应由 KeePass 取，勿硬编码）")

    # ---- 阻塞模态弹窗处理 ----
    modal = r.blocking_modal()
    if modal:
        info = _read_modal_safe(r)
        if auto_close_modal and info.get("is_captcha_reject"):
            try:
                FL.dismiss_reject_modal(r)
                time.sleep(0.6)
            except R.StepFailed as e:
                return {"status": "error", "reason": e.reason,
                        "failed_step": e.step}
        else:
            art = r.snapshot("modal_blocked")
            return {"status": "modal_blocked",
                    "reason": "存在阻塞模态弹窗，未授权/非验证码类，未自动关闭",
                    "modal": modal,
                    "modal_text": info.get("message") or info.get("title"),
                    "screen": art.get("screen"),
                    "hint": "确认弹窗内容后可带 auto_close_modal=true 重跑"}

    # ---- 已带验证码：填码 + 点登录（Agent 读图后的提交路径）----
    if captcha:
        # 保险：若表单未填（重启过/被清空），先幂等重填
        if not FL.declare_page_active() or not FL.ident_is_filled():
            FL.ensure_form_filled(r, unit, password)
        e = FL.declare_edits()
        cf = e.get("captcha")
        if not cf:
            return {"status": "form_cleared",
                    "reason": "登录窗上无验证码框（表单可能已被清空/界面已变），请重跑不带 --captcha",
                    "hint": "直接重跑 auto_login.sh（不带 --captcha）会重填表单"}
        R.wm_set_text(cf["hwnd"], captcha)
        time.sleep(0.4)
        if R.wm_get_len(cf["hwnd"]) != len(captcha):
            r.fail("fill_captcha", "验证码长度不符",
                   {"want": len(captcha), "got": R.wm_get_len(cf["hwnd"])})
        r.emit("captcha_filled", detail={"len": len(captcha)})
        return _click_login(r, unit, password, login_timeout)

    # ---- 无验证码参数：完整登录（填表 → 有码截码 / 无码点登录）----
    if not FL.declare_page_active() or not FL.ident_is_filled():
        FL.ensure_form_filled(r, unit, password)

    cf = FL.declare_edits().get("captcha")
    if cf:
        return _capture_after_refresh(r, unit, password)
    return _click_login(r, unit, password, login_timeout)


if __name__ == "__main__":
    R.Runner("auto_login",
             expected_windows={LOGIN_CLS, MAIN_CLS, MODAL_CLS}).run(main)
