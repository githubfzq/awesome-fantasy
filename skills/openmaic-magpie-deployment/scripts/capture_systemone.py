#!/usr/bin/env python3
"""Echo server that captures the exact System One request a client sends.

Point the client's base URL at this server to see the wire body without
spending tokens:

    export TYPESAFE_BASE_URL=http://127.0.0.1:8899   # SDK appends /v1/systemone
    export TYPESAFE_API_KEY=dummy

The server prints the request (path, selected headers, body keys, model, state,
each question) and answers with a plausible payload built from the questions it
received: every choice question answers with its first criterion, every noul
question answers 0.5. That keeps a capture run end-to-end executable so you can
see how the client's own validation reacts to the answer shape.

Usage: python3 capture_systemone.py [port]
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            body = {}

        print(f"=== PATH: {self.path}")
        print("=== HEADERS:", {
            k: v for k, v in self.headers.items()
            if k.lower() in {"authorization", "content-type", "user-agent"}
        })
        print("=== BODY KEYS:", list(body))
        print("=== MODEL:", body.get("model"))
        state = body.get("state")
        print("=== STATE:", json.dumps(state, ensure_ascii=False)[:800])

        answers = {}
        for name, question in (body.get("questions") or {}).items():
            print(f"--- QUESTION {name}: {json.dumps(question, ensure_ascii=False)[:800]}")
            if question.get("type") == "choice":
                labels = list(question.get("criteria") or {})
                chosen = labels[0] if labels else "other"
                answers[name] = {
                    "type": "choice",
                    "choice": chosen,
                    "confidence": 0.9,
                    "probabilities": {
                        label: (1.0 if label == chosen else 0.0) for label in labels
                    },
                }
            else:
                answers[name] = {"type": "noul", "noul": 0.5}

        payload = json.dumps({
            "model": body.get("model", "jev-captured"),
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "answers": answers,
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"capturing System One requests on http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
