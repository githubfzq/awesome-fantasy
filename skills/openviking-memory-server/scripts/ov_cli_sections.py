#!/usr/bin/env python3
"""Write per-harness credential sections into an OpenViking ovcli.conf.

Every official OV plugin reads credentials from one shared file
(~/.openviking/ovcli.conf) or from OPENVIKING_* env vars, and the installer
rewrites the top-level api_key/user on every run. The plugin.<harness>
sections are the supported way to give each harness its own user.

Usage:
  ov_cli_sections.py <ovcli.conf> <keyfile> <url> <account> <harness=user> [...]
  ov_cli_sections.py ~/.openviking/ovcli.conf keys.txt http://host:1933 \\
      fanzuquan codex=codex claude-code=claude opencode=opencode pi=pi dsh=dsh

keyfile format: one "name=key" per line.

The harness name is the ovcli.conf section key (claude_code / codex /
opencode / dsh / pi / ...); the user name is the OV account user. They are
often different ("claude-code=claude").
"""
import json
import os
import sys


def main() -> int:
    if len(sys.argv) < 6:
        print(__doc__)
        return 2
    conf_path = os.path.expanduser(sys.argv[1])
    keyfile = os.path.expanduser(sys.argv[2])
    url = sys.argv[3]
    account = sys.argv[4]
    specs = sys.argv[5:]

    keys = {}
    with open(keyfile, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            keys[name.strip()] = value.strip()

    try:
        with open(conf_path, encoding="utf-8") as fh:
            conf = json.load(fh)
    except (OSError, ValueError):
        conf = {}

    plugin = conf.get("plugin")
    if not isinstance(plugin, dict):
        plugin = {}

    applied = []
    for spec in specs:
        harness, _, user = spec.partition("=")
        harness = harness.strip()
        user = (user or harness).strip()
        key = keys.get(user)
        if not key:
            print(f"skip {harness}: no key for user '{user}' in {keyfile}", file=sys.stderr)
            continue
        section = plugin.get(harness)
        if not isinstance(section, dict):
            section = {}
        section.update({
            "url": url,
            "api_key": key,
            "account": account,
            "user": user,
        })
        plugin[harness] = section
        applied.append(f"{harness}->{user}")

    conf["plugin"] = plugin
    # Keep top-level values as a fallback for clients that don't read sections.
    conf.setdefault("url", url)
    conf.setdefault("account", account)

    tmp = conf_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(conf, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, conf_path)
    print("sections written: " + ", ".join(applied))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
