#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wage_rpa.py — macOS 编排端：驱动 VM 内 rpa.py 完成「申报当月工资薪金」流程

架构（详见 SKILL.md）：
  macOS 编排端 ──prlctl 桥接(~/.prlctl-bridge/call.sh)──> Windows 11 VM
      └─ psexec -i 1 -s ─> 在交互式会话(session 1)以 venv python 运行
         C:\\rpa\\rpa.py（GUI 自动化引擎，UIA 优先 + 图像匹配回退）

凭据：通过 keepass-lookup 技能从 KeePass 取得（扣缴义务人识别号 / 申报密码），
      主密码绝不落盘（取环境变量 KEEPASS_MASTER 或交互输入）。

安全边界：第 5 步「发送申报」前必须显式确认（默认交互输入 yes；--no-confirm 仅限测试）。

用法：
  python wage_rpa.py                 # 跑完整 5 步流程（发送申报前会停下确认）
  python wage_rpa.py --discover "自然人电子税务局"   # dump 某窗口 UIA 树，用于补全定位器
  python wage_rpa.py --step 3        # 只跑第 3 步（调试用）
  python wage_rpa.py --dry-run       # 只打印将要执行的命令，不真正执行
"""

import os
import sys
import json
import time
import subprocess
import argparse

# ---------------------------------------------------------------------------
# 路径配置（可用环境变量覆盖）
# ---------------------------------------------------------------------------
HOME = os.path.expanduser("~")
BRIDGE_CALL = os.environ.get("BRIDGE_CALL", os.path.join(HOME, ".prlctl-bridge", "call.sh"))
VM_NAME = os.environ.get("RPA_VM", "Windows 11")

# VM 内路径
PSEXEC = os.environ.get("RPA_PSEXEC", r"C:\rpa\pstools\PsExec64.exe")
VENV_PY = os.environ.get("RPA_VENV_PY", r"C:\venv\Scripts\python.exe")
RPA_PY = os.environ.get("RPA_PY", r"C:\rpa\rpa.py")
RESULT_FILE = os.environ.get("RPA_RESULT_FILE", r"C:\rpa\last_result.json")

# KeePass 取密脚本（Mac 侧）
KEEPASS_GET = os.environ.get("KEEPASS_GET",
                              os.path.join(HOME, ".workbuddy", "skills", "keepass-lookup", "scripts", "kp_get.py"))
KEEPASS_ENTRY = os.environ.get("KEEPASS_ENTRY", "自然人电子税务局")

# 扣缴端应用（启动命令；安装位置因机而异，可用环境变量 RPA_TAX_APP 覆盖）
TAX_APP = os.environ.get("RPA_TAX_APP",
                         r"C:\Program Files (x86)\自然人电子税务局扣缴端\EEnterprise.exe")

LOG = lambda *a, **k: print("[wage_rpa]", *a, **k)


# ---------------------------------------------------------------------------
# 底层：桥接执行
# ---------------------------------------------------------------------------
def bridge_exec(args, timeout=120):
    """通过 prlctl 桥接在 VM 内执行命令，返回 session-0 侧 stdout。"""
    if not os.path.exists(BRIDGE_CALL):
        raise RuntimeError(f"桥接脚本不存在: {BRIDGE_CALL}")
    cmd = [BRIDGE_CALL, "exec", VM_NAME] + list(args)
    LOG("bridge> ", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        LOG(f"  bridge 返回非 0: rc={r.returncode}")
    return r.stdout


def rpa_run(sub_args, timeout=90):
    """在 VM 交互式会话(session 1)运行 rpa.py 子命令，读取并返回 JSON 结果。"""
    launch = [PSEXEC, "-i", "1", "-s", "-accepteula", VENV_PY, RPA_PY] + list(sub_args)
    bridge_exec(launch, timeout=timeout)               # psexec 等待 session-1 进程结束
    raw = bridge_exec(["cmd", "/c", f"type {RESULT_FILE}"], timeout=30)
    # 提取 JSON（结果文件为纯 JSON）
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 容错：截取最后一个 {...} 块
        s = raw.rfind("{")
        e = raw.rfind("}") + 1
        if s >= 0 and e > s:
            return json.loads(raw[s:e])
        raise RuntimeError(f"无法解析 rpa 结果: {raw!r}")


def keepass_get(entry=KEEPASS_ENTRY):
    """从 KeePass 取得用户名/密码。返回 dict(username, password)。"""
    if not os.path.exists(KEEPASS_GET):
        raise RuntimeError(f"keepass 取密脚本不存在: {KEEPASS_GET}")
    env = dict(os.environ)
    r = subprocess.run([sys.executable, KEEPASS_GET, "--search", entry],
                       capture_output=True, text=True, timeout=120, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"keepass 取密失败: {r.stderr}")
    # kp_get.py 输出 JSON（username/password）
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"keepass 输出非 JSON: {r.stdout!r}")
    return data


# ---------------------------------------------------------------------------
# 高层动作（UIA 优先，图像匹配回退）
# ---------------------------------------------------------------------------
def uia_click(title, name=None, auto_id=None, control_type=None, timeout=15):
    a = ["uia_click", "--title", title]
    if name:
        a += ["--name", name]
    if auto_id:
        a += ["--auto_id", auto_id]
    if control_type:
        a += ["--control_type", control_type]
    res = rpa_run(a, timeout=timeout)
    if res.get("status") == "ok" and res.get("found", True) is not False:
        LOG(f"  [UIA click] {name or auto_id or control_type} -> ok")
        return res
    LOG(f"  [UIA click] 失败: {res}")
    return res


def uia_type(title, text, name=None, auto_id=None, control_type=None, append=False, timeout=15):
    a = ["uia_type", "--title", title, "--text", text]
    if name:
        a += ["--name", name]
    if auto_id:
        a += ["--auto_id", auto_id]
    if control_type:
        a += ["--control_type", control_type]
    if append:
        a += ["--append"]
    res = rpa_run(a, timeout=timeout)
    LOG(f"  [UIA type] {name or auto_id} -> {res.get('status')}")
    return res


def uia_exists(title, name=None, auto_id=None, control_type=None, timeout=12):
    a = ["uia_locate", "--title", title]
    if name:
        a += ["--name", name]
    if auto_id:
        a += ["--auto_id", auto_id]
    if control_type:
        a += ["--control_type", control_type]
    res = rpa_run(a, timeout=timeout)
    return res.get("status") == "ok" and res.get("found") is True


def wait_for(predicate, timeout=60, interval=2.0, label="条件"):
    """轮询 predicate()（无参，返回 bool），直到为真或超时。"""
    LOG(f"  [wait] 等待「{label}」(<= {timeout}s)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                LOG(f"  [wait] 「{label}」满足")
                return True
        except Exception as e:
            LOG(f"  [wait] 探测异常(忽略): {e}")
        time.sleep(interval)
    LOG(f"  [wait] 「{label}」超时")
    return False


def screenshot(b64=False, tag=""):
    a = ["screenshot"]
    if b64:
        a += ["--b64"]
    res = rpa_run(a, timeout=30)
    if b64 and res.get("b64"):
        import base64 as _b
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"shot_{tag}_{int(time.time())}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(_b.b64decode(res["b64"]))
        LOG(f"  [screenshot] 保存到 {path}")
    return res


# ---------------------------------------------------------------------------
# 5 步流程
# ---------------------------------------------------------------------------
def step1_login(creds):
    """启动扣缴端，选「申报密码登录」，填入识别号与申报密码，登录。"""
    LOG("== 步骤1：启动扣缴端并登录 ==")
    # 启动应用（若已在运行可跳过，这里直接启动）
    bridge_exec(["cmd", "/c", f'start "" "{TAX_APP}"'], timeout=30)
    # 等待登录窗口出现
    ok = wait_for(lambda: uia_exists("自然人电子税务局", name="申报密码登录") or
                  uia_exists("自然人电子税务局", name="登录"),
                  timeout=40, label="登录窗口")
    if not ok:
        LOG("  未检测到登录窗口，请检查应用是否已启动/窗口标题")
        return False
    # 选择「申报密码登录」页签
    uia_click("自然人电子税务局", name="申报密码登录")
    # 填写扣缴义务人识别号
    uia_type("自然人电子税务局", creds.get("username", ""), name="扣缴义务人识别号", control_type="Edit")
    # 填写申报密码
    uia_type("自然人电子税务局", creds.get("password", ""), name="申报密码", control_type="Edit")
    # 点击登录
    uia_click("自然人电子税务局", name="登录")
    # 等待主界面（综合所得申报）
    wait_for(lambda: uia_exists("自然人电子税务局", name="综合所得申报"),
             timeout=40, label="进入主界面")
    return True


def step2_person_and_report():
    """人员信息采集：勾选1名人员 -> 下一步 -> 报表填写 -> 综合所得申报(自动进入第1步)。"""
    LOG("== 步骤2：人员信息采集 -> 报表填写 ==")
    uia_click("自然人电子税务局", name="人员信息采集")
    # 勾选 1 名人员（首个可勾选的复选框；具体定位器见 locators override）
    ok = wait_for(lambda: uia_exists("人员信息采集", control_type="CheckBox"), timeout=30, label="人员列表复选框")
    if ok:
        uia_click("人员信息采集", control_type="CheckBox")
    uia_click("人员信息采集", name="下一步")
    # 跳转综合所得申报，自动进入第1步「收入及减除填写」
    wait_for(lambda: uia_exists("综合所得申报", name="正常工资薪金所得"), timeout=40, label="综合所得申报-第1步")
    return True


def step3_fill_salary():
    """正常工资薪金所得 -> 填写 -> 确定(未生成明细) -> 复制上月当期数据 -> 立即复制数据 -> 成功复制1条 -> 关闭。"""
    LOG("== 步骤3：填写正常工资薪金所得（复制上月数据）==")
    uia_click("综合所得申报", name="正常工资薪金所得", control_type="Button")
    # 「填写」按钮（列内）
    uia_click("综合所得申报", name="填写")
    # 弹窗「未生成明细」-> 确定
    if uia_exists("综合所得申报", name="确定"):
        uia_click("综合所得申报", name="确定")
    # 选择「复制上月当期数据（不含专项附加扣除）」
    uia_click("综合所得申报", name="复制上月当期数据（不含专项附加扣除）")
    uia_click("综合所得申报", name="立即复制数据")
    # 等待「成功复制1条」
    ok = wait_for(lambda: uia_exists("综合所得申报", name="成功复制1条"),
                  timeout=30, label="成功复制1条")
    uia_click("综合所得申报", name="关闭")
    return ok


def step4_calc():
    """返回4步骤页 -> 税款计算（请重新计税）-> 点税款计算 -> 进入第4步申报表报送。"""
    LOG("== 步骤4：税款计算 ==")
    # 返回4步骤页（综合所得申报主界面），第2步「税款计算（请重新计税）」
    ok = wait_for(lambda: uia_exists("综合所得申报", name="税款计算"), timeout=30, label="税款计算按钮")
    if ok:
        uia_click("综合所得申报", name="税款计算")
    # 随后直接进入第4步「申报表报送」
    wait_for(lambda: uia_exists("综合所得申报", name="发送申报"), timeout=40, label="进入申报表报送")
    return True


def step5_send(confirmed):
    """点「发送申报」，等待下载累计数据/自动获取申报结果，直至「申报成功，无需缴款」。"""
    LOG("== 步骤5：发送申报 ==")
    if not confirmed:
        LOG("  [安全] 未获得发送确认，终止于发送前。")
        return False
    uia_click("综合所得申报", name="发送申报")
    # 等待「正在下载累计数据，请稍后」
    wait_for(lambda: uia_exists("综合所得申报", name="正在下载累计数据"), timeout=60, label="下载累计数据")
    # 可选「立即获取」
    if uia_exists("综合所得申报", name="立即获取"):
        uia_click("综合所得申报", name="立即获取")
    # 直至「申报成功，无需缴款」
    ok = wait_for(lambda: uia_exists("综合所得申报", name="申报成功，无需缴款"),
                  timeout=120, label="申报成功，无需缴款")
    return ok


# ---------------------------------------------------------------------------
# 发现模式：dump UIA 树（用于补全定位器）
# ---------------------------------------------------------------------------
def discover(window_title, depth=5):
    res = rpa_run(["uia_tree", "--title", window_title, "--depth", str(depth)], timeout=30)
    if res.get("status") == "ok":
        print(res.get("tree", ""))
    else:
        LOG(f"discover 失败: {res}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run_full(dry_run=False):
    if dry_run:
        LOG("[dry-run] 仅打印步骤，不执行。")
        LOG("  步骤1 登录 / 步骤2 人员采集 / 步骤3 填写 / 步骤4 计税 / 步骤5 发送(需确认)")
        return
    creds = keepass_get()
    steps = [step1_login, step2_person_and_report, step3_fill_salary, step4_calc]
    for i, fn in enumerate(steps, start=1):
        LOG(f"--- 执行步骤 {i} ---")
        if not fn(creds if i == 1 else None):
            LOG(f"步骤 {i} 未达成，中止流程。")
            return
    # 步骤5 发送前确认
    LOG("--- 步骤5 前确认 ---")
    ans = input("即将「发送申报」。确认发送？(yes/no): ").strip().lower()
    confirmed = ans in ("yes", "y", "是")
    ok = step5_send(confirmed)
    LOG("流程结束。" if ok else "流程未成功完成，请检查 VM 界面。")


def main():
    ap = argparse.ArgumentParser(description="申报当月工资薪金 RPA 编排")
    ap.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], help="只跑指定步骤(调试)")
    ap.add_argument("--discover", metavar="WINDOW_TITLE", help="dump 指定窗口 UIA 树")
    ap.add_argument("--dry-run", action="store_true", help="只打印不执行")
    ap.add_argument("--no-confirm", action="store_true", help="跳过发送确认(仅测试用，危险)")
    args = ap.parse_args()

    if args.discover:
        discover(args.discover)
        return
    if args.step:
        # 单步调试：简单起见仍走完整凭据获取
        creds = keepass_get() if args.step == 1 else None
        {
            1: lambda: step1_login(creds),
            2: step2_person_and_report,
            3: step3_fill_salary,
            4: step4_calc,
            5: lambda: step5_send(args.no_confirm),
        }[args.step]()
        return
    run_full(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
