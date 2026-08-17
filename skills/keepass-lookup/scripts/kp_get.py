#!/usr/bin/env python3
"""
kp_get.py — 从 Mac 上的 KeePass(.kdbx) 数据库提取某条目的用户名/密码。

通用技能：本脚本不绑定任何具体密码库，调用方必须用 --db 显式指定要打开的 .kdbx。
具体用哪个库、主密码从哪来，由调用专家（如本机运维专家）在其记忆里决定。

用法:
  # 指定库 + 交互输入主密码（推荐，避免明文出现在参数/日志）
  python3 kp_get.py --db /path/to/agents.kdbx --search 某条目

  # 主密码来自环境变量
  KEEPASS_MASTER='***' python3 kp_get.py --db /path/to.db --search xxx

  # 主密码来自文件（如本机运维专家从 <主密码文件路径> 读取 Agent 库主密码）
  python3 kp_get.py --db /path/to.db --master-file <主密码文件路径> --search xxx

输出: JSON {"db","entry","username","password"} 到 stdout。
安全: 主密码只经 stdin 传给 keepassxc-cli，不回显、不落盘；不要在记忆文件里保存密码。
"""
import argparse, subprocess, sys, os, json, getpass

KX = "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli"


def _read_master(args):
    # 优先级: --master > 环境变量 KEEPASS_MASTER > --master-file > 交互
    if args.master:
        return args.master
    env = os.environ.get("KEEPASS_MASTER")
    if env:
        return env
    if args.master_file:
        p = os.path.expanduser(args.master_file)
        if not os.path.exists(p):
            sys.exit(f"主密码文件不存在: {p}")
        with open(p, "r", encoding="utf-8") as f:
            return f.read().strip()
    return getpass.getpass("KeePass 主密码: ")


# 注意：密钥文件必须显式用 --key-file 指定，绝不自动探测同目录文件。
# 自动加错误的 key file 会导致 HMAC 校验失败（例如 agents.kdbx 仅用主密码保护）。


def _run(args, master, keyfile=None):
    if keyfile:
        args = ["-k", keyfile] + args
    p = subprocess.run([KX] + args, input=master,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True,
                    help=".kdbx 路径（本技能不绑定具体库，必须显式指定）")
    ap.add_argument("--search", required=True, help="条目搜索词，如 自然人电子税务局 / 扣缴端")
    ap.add_argument("--master", help="主密码（优先于 env/文件，避免在命令行出现）")
    ap.add_argument("--master-file", help="主密码文件路径（具体路径由调用专家记忆决定，读首行）")
    ap.add_argument("--key-file", help="KeePass 密钥文件路径（可选；库仅用主密码时勿传，否则 HMAC 失败）")
    args = ap.parse_args()

    db = os.path.expanduser(args.db)
    if not os.path.exists(db):
        sys.exit(f"数据库不存在: {db}")

    master = _read_master(args)
    keyfile = args.key_file

    rc, out, err = _run(["search", db, args.search], master, keyfile)
    if rc != 0:
        sys.exit(f"search 失败: {err.strip()}")

    # search 输出每行一个匹配条目；优先取以 "/" 开头的完整路径，否则取非空行
    lines = [l.rstrip() for l in out.splitlines() if l.strip()]
    entries = [l.strip() for l in lines if l.strip().startswith("/")]
    if not entries:
        entries = [l.strip() for l in lines if l.strip()
                   and "搜索" not in l and "结果" not in l and "No" not in l]
    if not entries:
        sys.exit(f"未找到匹配 '{args.search}' 的条目。原始输出:\n{out}")
    if len(entries) > 1:
        # 多个匹配：打印列表让用户确认，取第一个但提示
        sys.stderr.write("匹配到多个条目（取第一个）:\n" + "\n".join(entries) + "\n")
    target = entries[0]

    rc, out2, err2 = _run(
        ["show", "-s", "-a", "UserName", "-a", "Password", db, target], master, keyfile)
    if rc != 0:
        sys.exit(f"show 失败: {err2.strip()}")

    vals = [l for l in out2.splitlines() if l is not None]
    username = vals[0] if len(vals) > 0 else ""
    password = vals[1] if len(vals) > 1 else ""
    print(json.dumps({"db": db, "entry": target,
                      "username": username, "password": password},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
