# read_reject_modal.py — 验证步骤(可独立调用)
# 只读被拒弹窗的标题/正文文字, 确认是否为「验证码超时/错误」类弹窗。
# 不截图。结果写入 C:/rpa/modal_read.json 供直接读取。
import json
import traceback
import rpa_core as R
from flow_lib import read_reject_modal

OUT = "C:/rpa/modal_read.json"


def main(r):
    try:
        info = read_reject_modal(r)
        r.emit("read_result", detail=info)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        return info
    except Exception as e:
        err = {"error": repr(e), "trace": traceback.format_exc()}
        try:
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(err, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    R.run(main)
