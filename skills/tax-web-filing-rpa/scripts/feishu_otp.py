#!/usr/bin/env python3
"""feishu_otp.py — 飞书 DM 短信验证码双向通道（贵州税务登录用）。

用法:
  feishu_otp.py ask [--chat oc_xxx] [--msg "自定义请求文案"]   # 发消息请用户回验证码
  feishu_otp.py wait [--chat oc_xxx] [--timeout 240] [--interval 10]  # 轮询读用户回复，打印验证码

凭据从 ~/.hermes/.env 读 FEISHU_APP_ID / FEISHU_APP_SECRET。
默认 chat_id 取 ~/.hermes/channel_directory.json 里 feishu 的第一个 DM。
只认 wait 启动之后用户(open_id)发的新消息，忽略 bot(app_id) 自己的历史消息。
"""
import json
import os
import re
import sys
import time

import requests

HOME = os.path.expanduser("~")
ENV_PATH = os.path.join(HOME, ".hermes", ".env")
DIR_PATH = os.path.join(HOME, ".hermes", "channel_directory.json")
BASE = "https://open.feishu.cn"  # FEISHU_DOMAIN=lark 时改 https://open.larksuite.com


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def default_chat():
    with open(DIR_PATH) as f:
        d = json.load(f)
    return d["platforms"]["feishu"][0]["id"]


def tenant_token(app_id, app_secret):
    r = requests.post(
        f"{BASE}/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    tok = r.json().get("tenant_access_token")
    if not tok:
        raise SystemExit("failed to get tenant_access_token")
    return tok


def send(tok, chat_id, text):
    r = requests.post(
        f"{BASE}/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {tok}"},
        json={"receive_id": chat_id, "msg_type": "text",
              "content": json.dumps({"text": text})},
        timeout=10,
    )
    if r.json().get("code") != 0:
        raise SystemExit(f"send failed: {r.text[:200]}")


def fetch_user_messages(tok, chat_id):
    r = requests.get(
        f"{BASE}/open-apis/im/v1/messages",
        params={"container_id_type": "chat", "container_id": chat_id,
                "sort_type": "ByCreateTimeDesc", "page_size": 10},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    items = (r.json().get("data") or {}).get("items", [])
    out = []
    for it in items:
        if it.get("sender", {}).get("id_type") != "open_id":
            continue  # 忽略 bot 自己的消息
        try:
            body = json.loads(it.get("body", {}).get("content", "{}"))
        except Exception:
            continue
        text = body.get("text", "")
        ts = float(it.get("create_time", "0")) / 1000.0  # ms -> s
        out.append((ts, text))
    return out


def extract_code(text):
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else None


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "ask"
    chat_id = default_chat()
    timeout, interval = 240, 10
    msg = "贵州电子税务局登录需要短信验证码，请把收到的验证码直接回复给我"
    i = 1
    while i < len(args):
        if args[i] == "--chat":
            chat_id = args[i + 1]; i += 2
        elif args[i] == "--timeout":
            timeout = int(args[i + 1]); i += 2
        elif args[i] == "--interval":
            interval = int(args[i + 1]); i += 2
        elif args[i] == "--msg":
            msg = args[i + 1]; i += 2
        else:
            i += 1

    env = load_env()
    tok = tenant_token(env["FEISHU_APP_ID"], env["FEISHU_APP_SECRET"])

    if cmd == "ask":
        send(tok, chat_id, msg)
        print("ASK_SENT")
        return

    if cmd == "wait":
        started = time.time()
        deadline = started + timeout
        while time.time() < deadline:
            for ts, text in fetch_user_messages(tok, chat_id):
                if ts <= started:
                    continue  # 只认新消息
                code = extract_code(text)
                if code:
                    print(code)
                    return
            time.sleep(interval)
        raise SystemExit("TIMEOUT waiting for OTP reply")
    raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
