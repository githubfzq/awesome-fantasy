# grab.py — 冻结当前屏幕（全屏 PNG），便于 Mac 侧肉眼判定弹窗按钮
import rpa_core as R


def main(r):
    art = r.snapshot("modal_view")
    return {"screen": art.get("screen"), "windows": art.get("windows")}


if __name__ == "__main__":
    R.Runner("grab", expected_windows={}).run(main)
