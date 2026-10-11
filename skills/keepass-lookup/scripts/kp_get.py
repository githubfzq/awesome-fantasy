#!/usr/bin/env python3
"""
kp_get.py — 从 Mac 上的 KeePass(.kdbx) 数据库提取某条目的凭据。

通用技能：本脚本不绑定任何具体密码库，调用方必须用 --db 显式指定要打开的 .kdbx。
具体用哪个库、主密码从哪来，由调用专家（如本机运维专家）在其记忆里决定。

用法:
  # 指定库 + 交互输入主密码（推荐，避免明文出现在参数/日志）
  python3 kp_get.py --db /path/to/agents.kdbx --search 某条目

  # 主密码来自环境变量
  KEEPASS_MASTER='***' python3 kp_get.py --db /path/to.db --search xxx

  # 主密码来自文件（如本机运维专家从 <主密码文件路径> 读取 Agent 库主密码）
  python3 kp_get.py --db /path/to.db --master-file <主密码文件路径> --search xxx

  # 额外取受保护自定义属性（如「API key」）——全量输出里没有，必须 -a 单取
  python3 kp_get.py --db /path/to.db --search deepseek --attr "API key"

输出: JSON {"db","entry","username","password","fields","attrs"} 到 stdout。
安全: 主密码只经 stdin 传给 keepassxc-cli，不回显、不落盘；不要在记忆文件里保存密码。
"""
import argparse, subprocess, sys, os, json, getpass, re

KX = "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli"

# keepassxc-cli 输出形如（全量 show -s，一行一个字段，值可为空）：
#   Title: xxx
#   UserName: xxx
#   Password: xxx
#   Notes: 多行时后续行不带冒号，需回拼
FIELD_RE = re.compile(r"^\s*([^:]+):\s?(.*)$")


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


def _run(args_list, master, keyfile=None):
    if keyfile:
        args_list = ["-k", keyfile] + args_list
    p = subprocess.run([KX] + args_list, input=master + "\n",
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def parse_fields(stdout: str) -> dict:
    """全量 show -s 输出 -> {字段名: 值}。
    坑：解锁提示行在 stderr（已被分离），stdout 每行 '字段名: 值'；
    Notes 等长文本会折行，无冒号的行回拼到上一个字段。"""
    fields, last = {}, None
    for line in stdout.splitlines():
        m = FIELD_RE.match(line)
        if m:
            last = m.group(1).strip()
            fields[last] = m.group(2).strip()
        elif last is not None:
            fields[last] = (fields[last] + "\n" + line.strip()).strip()
    return fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True,
                    help=".kdbx 路径（本技能不绑定具体库，必须显式指定）")
    ap.add_argument("--search", required=True, help="条目搜索词，如 自然人电子税务局 / 扣缴端")
    ap.add_argument("--master", help="主密码（优先于 env/文件，避免在命令行出现）")
    ap.add_argument("--master-file", help="主密码文件路径（具体路径由调用专家记忆决定，读首行）")
    ap.add_argument("--key-file", help="KeePass 密钥文件路径（可选；库仅用主密码时勿传，否则 HMAC 失败）")
    ap.add_argument("--attr", action="append", default=[],
                    help="额外要取的字段（可重复）。受保护自定义属性如「API key」全量输出里没有，会自动改用 -a 单取")
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
    # 坑：search 会连「/回收站/...」里的同名条目一起返回，优先取非回收站条目
    live = [e for e in entries if not e.startswith("/回收站")]
    if live:
        entries = live
    if len(entries) > 1:
        sys.stderr.write("匹配到多个条目（取第一个）:\n" + "\n".join(entries) + "\n")
    target = entries[0]

    rc, out2, err2 = _run(["show", "-s", db, target], master, keyfile)
    if rc != 0:
        sys.exit(f"show 失败: {err2.strip()}")

    fields = parse_fields(out2)
    username = fields.get("UserName", "")
    password = fields.get("Password", "")

    # 受保护自定义属性：全量输出里缺失 -> 用 -a 单字段取（输出只有值一行）
    attrs = {}
    for name in args.attr:
        if name in fields and fields[name]:
            attrs[name] = fields[name]
            continue
        rc3, out3, err3 = _run(["show", "-s", "-a", name, db, target], master, keyfile)
        if rc3 != 0:
            sys.stderr.write(f"取属性 '{name}' 失败: {err3.strip()}\n")
            continue
        vals = [l for l in out3.splitlines() if l.strip()]
        if vals:
            attrs[name] = vals[0].strip()

    print(json.dumps({"db": db, "entry": target,
                      "username": username, "password": password,
                      "fields": fields, "attrs": attrs},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
