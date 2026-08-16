#!/usr/bin/env python3
"""
mcp_call.py — minimal MCP-over-HTTP (streamable) client for cua computer_server.

Used to smoke-test a Parallels Windows VM running `computer_server` and to drive
it from the Mac. Performs the initialize -> notifications/initialized -> tools/call
handshake and parses the SSE response.

Examples
--------
# screenshot smoke test (saves win_shot.png)
python3 mcp_call.py http://10.211.55.5:8000/mcp computer_screenshot --save win_shot.png

# call with arguments
python3 mcp_call.py http://10.211.55.5:8000/mcp computer_type \
        --args '{"text":"hello"}'

# list available tools
python3 mcp_call.py http://10.211.55.5:8000/mcp --list

Note: when calling from the Mac, bypass any local HTTP proxy for LAN IPs, e.g.
      export no_proxy='*'   (or pass --noproxy)
"""
import argparse
import base64
import json
import sys
import urllib.request

PROTOCOL = "2024-11-05"


def _post(url, payload, session_id=None, noproxy=False):
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    # bypass proxy for private/LAN targets if requested
    proxies = {} if noproxy else None
    opener = urllib.request.build_opener()
    if proxies is not None:
        from urllib.request import ProxyHandler
        opener = urllib.request.build_opener(ProxyHandler({}))
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with opener.open(req, timeout=30) as resp:
        sid = resp.headers.get("Mcp-Session-Id")
        body = resp.read().decode()
    return sid, body


def _parse_sse(body):
    """Return the first JSON-RPC result/error object from an SSE body."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    # some servers return plain JSON
    return json.loads(body)


def call_tool(endpoint, tool, args=None, noproxy=False):
    sid, _ = _post(endpoint, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                   "clientInfo": {"name": "mcp_call", "version": "1.0"}},
    }, noproxy=noproxy)
    _post(endpoint, {
        "jsonrpc": "2.0", "method": "notifications/initialized",
    }, session_id=sid, noproxy=noproxy)
    _, body = _post(endpoint, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": tool, "arguments": args or {}},
    }, session_id=sid, noproxy=noproxy)
    return _parse_sse(body)


def list_tools(endpoint, noproxy=False):
    sid, _ = _post(endpoint, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                   "clientInfo": {"name": "mcp_call", "version": "1.0"}},
    }, noproxy=noproxy)
    _post(endpoint, {"jsonrpc": "2.0", "method": "notifications/initialized"},
          session_id=sid, noproxy=noproxy)
    _, body = _post(endpoint, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
    }, session_id=sid, noproxy=noproxy)
    return _parse_sse(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("endpoint", help="e.g. http://10.211.55.5:8000/mcp")
    ap.add_argument("tool", nargs="?", default=None, help="tool name")
    ap.add_argument("--args", help="JSON object of tool arguments")
    ap.add_argument("--save", help="save first returned image to this path")
    ap.add_argument("--list", action="store_true", help="list tools instead")
    ap.add_argument("--noproxy", action="store_true",
                    help="bypass HTTP proxy (use for LAN IPs)")
    a = ap.parse_args()

    if a.list:
        res = list_tools(a.endpoint, a.noproxy)
        tools = (res.get("result", {}).get("tools") or [])
        for t in tools:
            print(f"- {t['name']}: {t.get('description','')[:80]}")
        return

    if not a.tool:
        ap.error("tool name required (or use --list)")

    try:
        args = json.loads(a.args) if a.args else {}
    except json.JSONDecodeError as e:
        sys.exit(f"bad --args JSON: {e}")

    res = call_tool(a.endpoint, a.tool, args, a.noproxy)
    if "error" in res:
        sys.exit(f"MCP error: {res['error']}")

    content = res.get("result", {}).get("content", [])
    for item in content:
        if item.get("type") == "image" and a.save:
            raw = base64.b64decode(item["data"])
            with open(a.save, "wb") as f:
                f.write(raw)
            print(f"[saved image -> {a.save} ({len(raw)} bytes)]")
        elif item.get("type") == "text":
            print(item.get("text", ""))
        else:
            print(item)


if __name__ == "__main__":
    main()
