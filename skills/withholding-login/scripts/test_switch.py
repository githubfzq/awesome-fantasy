# test_switch.py — 精准定位「申报密码登录」页签并切换
#
# 策略: 登录窗顶部 86px 区域是自绘页签头(TJdlsPanel)。
#   两个 tab 大致均分宽度 → 左 tab 中心 ≈ x + W/4, 右 tab 中心 ≈ x + 3W/4
#   优先试右 tab（"申报密码登录"通常在右侧备选位），
#   点击后验证 TIntelligentSearch 是否出现（该控件仅存在于申报密码登录页）。
import time

import rpa_core as R

LOGIN_CLS = "Tfrm_LoginViewer"
SELECTOR_CLS = "TIntelligentSearch"


def main(r):
    lw = R.find_window(LOGIN_CLS, visible_only=True)
    if not lw:
        r.fail("preflight", "登录窗未找到")

    rc = lw["rect"]  # [left, top, right, bottom]
    W = rc[2] - rc[0]   # 窗口宽度 ~442
    H_header = 86       # 顶部页签头高度（来自 snap_login 诊断）
    tab_y = rc[1] + H_header // 2  # 页签头垂直中心

    candidates = [
        ("right_tab", rc[0] + W * 3 // 4, tab_y),   # 右侧：推测「申报密码登录」
        ("left_tab",  rc[0] + W // 4,     tab_y),   # 左侧：推测「企业申报/证书」
    ]

    for name, cx, cy in candidates:
        r.emit("try_click", detail={"name": name, "point": [cx, cy]})
        R.click_at(cx, cy)
        time.sleep(1.5)  # 等 TabSheet 切换 + 子控件创建

        # 检查单位选择器是否出现
        sel = [k for k in R.enum_children(lw["hwnd"])
               if k["class"] == SELECTOR_CLS and k["visible"]]
        if sel:
            r.emit("switch_success", detail={
                "clicked": name,
                "point": [cx, cy],
                "selector_rect": sel[0]["rect"],
                "note": "TIntelligentSearch 已出现 → 已切到申报密码登录页",
            })
            return {"success": True, "clicked": name, "point": [cx, cy],
                    "selector": sel[0]["rect"]}

        r.emit("switch_no_effect", detail={
            "clicked": name,
            "point": [cx, cy],
            "selector_visible": False,
        })

    r.fail("switch_tab", "两个候选位置均未唤出单位选择器",
           {"candidates": [(n, [cx, cy]) for n, cx, cy in candidates],
            "hint": "页签头 Y 坐标或 X 分布可能与诊断不符，需重新截图确认"})


if __name__ == "__main__":
    R.Runner("test_switch", expected_windows={LOGIN_CLS}).run(main)
