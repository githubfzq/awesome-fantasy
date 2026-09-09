#!/usr/bin/env python3
"""Check DeepSeek account balance via official API.

Reads API key from (in priority order):
  1. --api-key argument
  2. DEEPSEEK_API_KEY environment variable

The API key is never printed or written to disk. Exits 0 on success,
non-zero on failure.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.deepseek.com/user/balance"


def get_key(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key.strip()
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    print("ERROR: no API key. Pass --api-key or set DEEPSEEK_API_KEY env var.", file=sys.stderr)
    sys.exit(2)


def fetch_balance(api_key: str) -> dict:
    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "deepseek-usage-check/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        if e.code == 401:
            print(f"ERROR: 401 Unauthorized - API key is invalid or expired. {body}", file=sys.stderr)
        else:
            print(f"ERROR: HTTP {e.code}. {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach {API_URL}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check DeepSeek remaining balance")
    parser.add_argument("--api-key", default="", help="DeepSeek API key (prefer DEEPSEEK_API_KEY env var)")
    parser.add_argument("--json", action="store_true", help="output raw JSON")
    args = parser.parse_args()

    api_key = get_key(args)
    data = fetch_balance(api_key)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    available = data.get("is_available")
    print(f"账户状态: {'可用' if available else '不可用'}")
    infos = data.get("balance_infos", [])
    if not infos:
        print("未返回余额信息")
        return
    for info in infos:
        currency = info.get("currency", "?")
        total = info.get("total_balance", "N/A")
        granted = info.get("granted_balance", "N/A")
        topped = info.get("topped_up_balance", "N/A")
        print(f"[{currency}] 总余额: {total}  (赠送额度: {granted} | 充值余额: {topped})")


if __name__ == "__main__":
    main()
