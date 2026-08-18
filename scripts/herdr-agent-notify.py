#!/usr/bin/env python3
"""Subscribe to herdr pane.agent_status_changed over SSH and notify Windows via notify-send-wsl."""

from __future__ import annotations

import argparse
import io
import json
import os
import select
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

DEFAULT_SSH_HOST = "herdr"
DEFAULT_NOTIFY_CMD = "notify-send-wsl"
DEFAULT_RECONNECT_DELAY = 3.0

STATUS_LABELS = {
    "idle": "空闲",
    "working": "工作中",
    "blocked": "等待输入",
    "done": "已完成",
    "unknown": "未知",
}

REMOTE_RELAY = r"""
import os
import select
import socket
import sys

path = os.path.expanduser(sys.argv[1])
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(path)
inputs = [sys.stdin.buffer, sock]
while True:
    readable, _, _ = select.select(inputs, [], [])
    for src in readable:
        if src is sys.stdin.buffer:
            chunk = sys.stdin.buffer.read1(65536)
            if not chunk:
                sys.exit(0)
            sock.sendall(chunk)
        else:
            chunk = sock.recv(65536)
            if not chunk:
                sys.exit(0)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
"""

LIFECYCLE_SUBSCRIPTIONS = [
    {"type": "pane.created"},
    {"type": "pane.closed"},
    {"type": "pane.agent_detected"},
]


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def expand_remote_socket_path(session: str | None, socket_path: str | None) -> str:
    if socket_path:
        return socket_path
    if session:
        return f"~/.config/herdr/sessions/{session}/herdr.sock"
    return "~/.config/herdr/herdr.sock"


def status_label(status: str, state_labels: dict[str, str] | None = None) -> str:
    if state_labels and status in state_labels:
        return state_labels[status]
    return STATUS_LABELS.get(status, status)


@dataclass
class HerdrClient:
    ssh_host: str | None
    socket_path: str
    proc: subprocess.Popen[Any] | None = None
    local_sock: socket.socket | None = None
    stdin: io.TextIOBase | None = None
    stdout: io.TextIOBase | None = None
    _read_buffer: bytes = b""
    _request_seq: int = 0

    def connect(self) -> None:
        self.close()
        if self.ssh_host:
            remote_cmd = (
                "SOCK=$(python3 -c 'import os; print(os.path.expanduser(\""
                + self.socket_path.replace('"', '\\"')
                + "\"))'); "
                "if command -v socat >/dev/null 2>&1; then "
                'exec socat STDIO "UNIX-CONNECT:$SOCK"; '
                "else "
                f"exec python3 -u -c {json.dumps(REMOTE_RELAY)} \"$SOCK\"; "
                "fi"
            )
            self.proc = subprocess.Popen(
                ["ssh", self.ssh_host, remote_cmd],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            assert self.proc.stdin and self.proc.stdout
            self.stdin = self.proc.stdin
            self.stdout = self.proc.stdout
        else:
            local_path = os.path.expanduser(
                self.socket_path.replace("$HOME", "~").replace("${HOME}", "~")
            )
            self.local_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.local_sock.connect(local_path)

        self._read_buffer = b""
        self._request_seq = 0

    def close(self) -> None:
        if self.proc is not None:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
            except OSError:
                pass
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            stderr = ""
            if self.proc.stderr:
                try:
                    stderr = self.proc.stderr.read() or ""
                except OSError:
                    pass
            if stderr.strip():
                log(f"transport stderr: {stderr.strip()}")
            self.proc = None

        if self.local_sock is not None:
            try:
                self.local_sock.close()
            except OSError:
                pass
            self.local_sock = None

        self.stdin = None
        self.stdout = None
        self._read_buffer = b""

    def _write_line(self, line: str) -> None:
        payload = (line + "\n").encode()
        if self.local_sock is not None:
            self.local_sock.sendall(payload)
            return
        if not self.stdin:
            raise RuntimeError("herdr transport is not connected")
        self.stdin.write(line + "\n")
        self.stdin.flush()

    def _read_line_local(self, timeout: float | None) -> str | None:
        assert self.local_sock is not None
        while True:
            if b"\n" in self._read_buffer:
                raw, self._read_buffer = self._read_buffer.split(b"\n", 1)
                return raw.decode()
            if timeout is not None and timeout <= 0:
                return None
            wait = timeout if timeout is not None else None
            ready, _, _ = select.select([self.local_sock], [], [], wait)
            if not ready:
                return None
            chunk = self.local_sock.recv(65536)
            if not chunk:
                return None
            self._read_buffer += chunk
            if timeout is not None:
                timeout = max(0.0, timeout - 0.01)

    def read_line(self, timeout: float | None = None) -> str | None:
        if self.local_sock is not None:
            return self._read_line_local(timeout)
        if not self.stdout:
            raise RuntimeError("herdr transport is not connected")
        if timeout is None:
            line = self.stdout.readline()
        else:
            ready, _, _ = select.select([self.stdout], [], [], timeout)
            if not ready:
                return None
            line = self.stdout.readline()
        if line == "":
            return None
        return line.rstrip("\n")

    def send(self, method: str, params: dict[str, Any] | None = None) -> str:
        if not self.local_sock and not self.stdin:
            raise RuntimeError("herdr transport is not connected")
        request_id = self._next_id()
        payload = {"id": request_id, "method": method, "params": params or {}}
        self._write_line(json.dumps(payload, separators=(",", ":")))
        return request_id

    def _next_id(self) -> str:
        self._request_seq += 1
        return f"req_{self._request_seq}"

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
        request_id = self.send(method, params)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for {method}")
            line = self.read_line(timeout=remaining)
            if line is None:
                raise RuntimeError(f"connection closed while waiting for {method}")
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError(
                    f"{method} failed: {message['error'].get('code')}: {message['error'].get('message')}"
                )
            return message.get("result", {})

    def iter_messages(self) -> Iterator[dict[str, Any]]:
        while True:
            line = self.read_line()
            if line is None:
                return
            yield json.loads(line)


def pane_ids_from_snapshot(result: dict[str, Any]) -> set[str]:
    panes = result.get("panes") or []
    return {pane["pane_id"] for pane in panes if pane.get("pane_id")}


def collect_pane_ids(client: HerdrClient) -> set[str]:
    snapshot = client.request("session.snapshot", timeout=15)
    pane_ids = pane_ids_from_snapshot(snapshot)
    if pane_ids:
        return pane_ids
    listed = client.request("pane.list", timeout=15)
    panes = listed.get("panes") or []
    return {pane["pane_id"] for pane in panes if pane.get("pane_id")}


def build_subscriptions(pane_ids: set[str]) -> list[dict[str, Any]]:
    subscriptions = list(LIFECYCLE_SUBSCRIPTIONS)
    for pane_id in sorted(pane_ids):
        subscriptions.append({"type": "pane.agent_status_changed", "pane_id": pane_id})
    return subscriptions


def extract_pane_id_from_lifecycle(event_name: str, data: dict[str, Any]) -> str | None:
    pane = data.get("pane")
    if isinstance(pane, dict) and pane.get("pane_id"):
        return pane["pane_id"]
    if data.get("pane_id"):
        return data["pane_id"]
    return None


@dataclass
class Notifier:
    command: str
    app_name: str = "herdr"
    notify_on: set[str] = field(default_factory=lambda: set(STATUS_LABELS))
    dry_run: bool = False

    def notify(self, title: str, body: str, status: str) -> None:
        if status not in self.notify_on:
            return
        if self.dry_run:
            log(f"[dry-run] {title}: {body}")
            return
        cmd = [
            self.command,
            "--app-name",
            self.app_name,
            "--category",
            f"herdr.agent.{status}",
            title,
            body,
        ]
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            log(f"notify command not found: {self.command}")
            raise
        except subprocess.CalledProcessError as exc:
            log(f"notify command failed ({exc.returncode}): {' '.join(cmd)}")


def format_notification(data: dict[str, Any]) -> tuple[str, str, str]:
    status = data.get("agent_status") or "unknown"
    agent = data.get("display_agent") or data.get("agent") or "Herdr Agent"
    pane_id = data.get("pane_id") or "?"
    workspace_id = data.get("workspace_id") or "?"
    title = data.get("title")
    state_labels = data.get("state_labels") or {}

    label = status_label(status, state_labels)
    summary = f"{agent} · {label}"
    parts = [f"窗格 {pane_id}", f"工作区 {workspace_id}"]
    if title:
        parts.append(title)
    body = " | ".join(parts)
    return summary, body, status


def run_listener(
    ssh_host: str | None,
    socket_path: str,
    notifier: Notifier,
    reconnect_delay: float,
) -> None:
    subscribed_panes: set[str] = set()
    subscribed = False

    while True:
        client = HerdrClient(ssh_host=ssh_host, socket_path=socket_path)
        try:
            log(f"connecting to herdr ({ssh_host or 'local'}:{socket_path})")
            client.connect()

            ping = client.request("ping", timeout=10)
            if ping.get("type") != "pong":
                log(f"unexpected ping response: {ping}")

            subscribed_panes = collect_pane_ids(client)
            log(f"tracking {len(subscribed_panes)} pane(s) for agent status changes")

            subscribe_id = client.send(
                "events.subscribe",
                {"subscriptions": build_subscriptions(subscribed_panes)},
            )
            subscribed = False
            need_resubscribe = False

            for message in client.iter_messages():
                if message.get("id") == subscribe_id and "result" in message:
                    subscribed = True
                    log("subscription started")
                    continue
                if message.get("id") == subscribe_id and "error" in message:
                    raise RuntimeError(
                        "events.subscribe failed: "
                        f"{message['error'].get('code')}: {message['error'].get('message')}"
                    )
                if "error" in message and message.get("id"):
                    log(f"request error: {message['error']}")
                    continue
                if "event" not in message:
                    continue

                event_name = message["event"]
                data = message.get("data") or {}

                if event_name in {"pane_created", "pane_agent_detected"}:
                    pane_id = extract_pane_id_from_lifecycle(event_name, data)
                    if pane_id and pane_id not in subscribed_panes:
                        log(f"new pane detected ({pane_id}); refreshing subscriptions")
                        subscribed_panes.add(pane_id)
                        need_resubscribe = True
                        break

                if event_name == "pane_closed":
                    pane_id = extract_pane_id_from_lifecycle(event_name, data)
                    if pane_id and pane_id in subscribed_panes:
                        subscribed_panes.discard(pane_id)
                    continue

                if event_name != "pane.agent_status_changed":
                    continue

                summary, body, status = format_notification(data)
                log(f"agent status: {summary} ({body})")
                notifier.notify(summary, body, status)

            if need_resubscribe:
                continue

            if subscribed:
                log("herdr connection closed; reconnecting...")
        except KeyboardInterrupt:
            log("stopped")
            return
        except Exception as exc:
            log(f"error: {exc}")
        finally:
            client.close()

        time.sleep(reconnect_delay)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Subscribe to herdr pane.agent_status_changed events over SSH and "
            "send Windows toast notifications via notify-send-wsl."
        )
    )
    parser.add_argument(
        "--ssh-host",
        default=os.environ.get("HERDR_SSH_HOST", DEFAULT_SSH_HOST),
        help=f"SSH host alias for the remote herdr machine (default: {DEFAULT_SSH_HOST}). "
        "Set to empty string for a local socket.",
    )
    parser.add_argument(
        "--session",
        default=os.environ.get("HERDR_SESSION"),
        help="Named herdr session on the remote host.",
    )
    parser.add_argument(
        "--socket-path",
        default=os.environ.get("HERDR_SOCKET_PATH"),
        help="Remote/local herdr socket path. Overrides --session when set.",
    )
    parser.add_argument(
        "--notify-cmd",
        default=os.environ.get("HERDR_NOTIFY_CMD", DEFAULT_NOTIFY_CMD),
        help=f"Notification command (default: {DEFAULT_NOTIFY_CMD}).",
    )
    parser.add_argument(
        "--app-name",
        default=os.environ.get("HERDR_NOTIFY_APP", "herdr"),
        help="Windows toast app name passed to notify-send-wsl.",
    )
    parser.add_argument(
        "--notify-on",
        default=os.environ.get("HERDR_NOTIFY_ON", "idle,working,blocked,done,unknown"),
        help="Comma-separated agent statuses that trigger notifications.",
    )
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=float(os.environ.get("HERDR_RECONNECT_DELAY", DEFAULT_RECONNECT_DELAY)),
        help=f"Seconds to wait before reconnecting (default: {DEFAULT_RECONNECT_DELAY}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print notifications to stderr instead of calling notify-send-wsl.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ssh_host = args.ssh_host or None
    socket_path = expand_remote_socket_path(args.session, args.socket_path)
    notify_on = {item.strip() for item in args.notify_on.split(",") if item.strip()}
    notifier = Notifier(
        command=args.notify_cmd,
        app_name=args.app_name,
        notify_on=notify_on,
        dry_run=args.dry_run,
    )
    run_listener(
        ssh_host=ssh_host,
        socket_path=socket_path,
        notifier=notifier,
        reconnect_delay=args.reconnect_delay,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
