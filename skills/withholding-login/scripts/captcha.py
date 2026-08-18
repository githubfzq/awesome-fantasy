# captcha.py — 验证码：定位 → 刷新 → 客观验证已刷新 → 截图存盘（供 Mac 回传识别）
#
# 用法(VM 内): pythonw.exe captcha.py [--args-b64 <base64({"no_refresh":true})>]
# 依赖 rpa_core.py。
#
# 关键：验证码图是画在面板上的位图（无 HWND），无法用控件树定位，只能靠图像。
# 因此本脚本用两级客观验证，杜绝"盲点几十次也不知有没有点中"：
#   1) 前置守卫：存在阻塞模态弹窗时直接中止（弹窗会吃掉所有点击 —— 这曾是耗时最久的坑）
#   2) 后置验证：对比点击前后该矩形的像素差异，差异过小 = 未刷新 → 失败并冻结现场
import os

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
SAVE_PATH = r"C:\rpa\captcha.png"
WIN_W, WIN_H, STEP = 260, 80, 12
DIFF_THRESHOLD = 0.02  # 平均像素差比例，低于此判定为"没刷新"


def grab(box):
    from PIL import ImageGrab
    return ImageGrab.grab(tuple(box))


def detect_captcha_rect(win_rect):
    """在登录窗右下区域找"边缘最密"的矩形：验证码图满是字符/干扰线，暗像素密度远高于
    白色输入框与灰色背景。返回 (rect, score)。"""
    left, top, right, bottom = win_rect
    x0, x1 = left + 200, right - 40
    y0, y1 = top + 300, bottom - 80
    if x1 - x0 < WIN_W or y1 - y0 < WIN_H:
        return None, 0
    crop = grab((x0, y0, x1, y1)).convert("L")
    px = crop.load()
    W, H = crop.size
    best, best_score = None, -1
    for yy in range(0, H - WIN_H, STEP):
        for xx in range(0, W - WIN_W, STEP):
            score = 0
            for cy in range(yy, yy + WIN_H, 3):
                for cx in range(xx, xx + WIN_W, 3):
                    if px[cx, cy] < 128:
                        score += 1
            if score > best_score:
                best_score = score
                best = [x0 + xx, y0 + yy, x0 + xx + WIN_W, y0 + yy + WIN_H]
    return best, best_score


def mean_diff(img_a, img_b):
    """两图平均灰度差（归一化 0~1），用于客观判定图片是否变化。"""
    a = img_a.convert("L")
    b = img_b.convert("L")
    if a.size != b.size:
        return 1.0
    pa, pb = a.load(), b.load()
    W, H = a.size
    total, n = 0, 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            total += abs(pa[x, y] - pb[x, y])
            n += 1
    return (total / n / 255.0) if n else 0.0


def main(r):
    args = R.parse_args_b64()
    no_refresh = bool(args.get("no_refresh"))
    click_pt = args.get("click")  # 可选 [x,y] 手工覆盖

    # ---- 0 前置：登录窗在、且没有弹窗挡着（否则点击必然无效） ----
    def login_ready():
        lw = R.find_window(LOGIN_CLS, visible_only=True)
        if not lw or not lw["enabled"]:
            return None
        return {"login": lw}

    st = r.step("preflight", verify=login_ready,
                verify_desc="登录窗可见且 enabled", timeout=10, guard=True)
    win_rect = st["login"]["rect"]

    # ---- 1 定位验证码图 ----
    def locate():
        rect, score = detect_captcha_rect(win_rect)
        if not rect:
            r.fail("locate_captcha", "登录窗尺寸不足以容纳验证码搜索区",
                   {"win_rect": win_rect})
        if score < 50:
            r.fail("locate_captcha",
                   "未找到验证码图（暗像素密度过低）——当前很可能没有验证码框",
                   {"best_rect": rect, "score": score,
                    "hint": "首次正常登录本就无验证码；确认确实处于失败重试场景"})
        return {"rect": rect, "edge_score": score}

    loc = r.step("locate_captcha", action=locate,
                 verify=lambda: True, verify_desc="定位成功(动作内校验)",
                 timeout=3, guard=False)
    rect = loc["rect"]

    # ---- 2 刷新 + 客观验证图片确实变了 ----
    if no_refresh:
        r.emit("skip", step="refresh", reason="no_refresh=true")
    else:
        before = grab(rect)
        cx, cy = (click_pt if click_pt else list(R.center(rect)))

        def do_refresh():
            R.click_at(cx, cy)
            return {"clicked": [cx, cy], "rect": rect}

        def image_changed():
            d = mean_diff(before, grab(rect))
            r.emit("probe", step="refresh", mean_diff=round(d, 4))
            return {"mean_diff": round(d, 4)} if d >= DIFF_THRESHOLD else None

        r.step("refresh", action=do_refresh, verify=image_changed,
               verify_desc="点击后图片像素变化 >= %.0f%%" % (DIFF_THRESHOLD * 100),
               timeout=6, interval=0.5)

    # ---- 3 截图存盘 ----
    def save_shot():
        rect2, _ = detect_captcha_rect(win_rect)
        shot = grab(rect2 or rect)
        shot.save(SAVE_PATH)
        return {"saved": SAVE_PATH, "rect": rect2 or rect}

    def saved_ok():
        try:
            return {"bytes": os.path.getsize(SAVE_PATH)} \
                if os.path.getsize(SAVE_PATH) > 200 else None
        except Exception:
            return None

    shot = r.step("save_shot", action=save_shot, verify=saved_ok,
                  verify_desc="PNG 已落盘且 >200 字节", timeout=5, guard=False)

    return {"captcha_png": SAVE_PATH, "rect": shot,
            "next": "用 pull_file.sh C:/rpa/captcha.png 回传 Mac 后识别，"
                    "再以 captcha 参数重跑 login_declare.py"}


if __name__ == "__main__":
    R.Runner("captcha", expected_windows={LOGIN_CLS}).run(main)
