# RPA Pipeline Playbook — Kernel, Template, Worked Example

This file is the deeper companion to `SKILL.md`. It gives a portable kernel
skeleton, a copy-paste step template, and one fully worked example. It contains
**no infrastructure commands** — it assumes the Windows app is reachable and the
driver can call the control-tree primitives (`find_window`, `enum_children`,
`set_text`, `get_text_length`, `click_at`, `list_items`). Those primitives are
provided by whatever desktop-driver the ops experts stand up.

---

## 1. Kernel skeleton (port this into every pipeline)

The kernel is a single module every pipeline script imports. It makes the
engineering contract (see `SKILL.md`) impossible to bypass.

```python
import json, time, os

class StepFailed(Exception):
    pass

class Runner:
    def __init__(self, run, expected_windows=None, log_dir="C:/rpa/logs"):
        self.run = run
        self.run_id = time.strftime("%Y%m%d-%H%M%S-") + os.urandom(3).hex()
        self.expected = expected_windows or {}
        self.log_path = os.path.join(log_dir, f"{self.run_id}.jsonl")
        self.seq = 0
        self._emit("run_start", ok=None)

    # ---- logging ----
    def emit(self, event, step=None, ok=None, **detail):
        self.seq += 1
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_id": self.run_id,
               "seq": self.seq, "event": event}
        if step is not None: rec["step"] = step
        if ok is not None: rec["ok"] = ok
        rec["detail"] = detail
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- verification primitive ----
    def wait_until(self, predicate, timeout=10, interval=0.3):
        """Condition polling. Returns (value, elapsed). The ONLY sanctioned sleep replacement."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            v = predicate()
            if v:
                return v, deadline - time.time()
            time.sleep(interval)
        return None, timeout

    # ---- guard: refuse to act through a blocking modal ----
    def blocking_modal(self):
        """Return the HWND of any blocking modal dialog, else None.
        Implement with find_window over known modal classes; return None if none."""
        raise NotImplementedError  # provided by the driver layer

    # ---- the enforced step loop ----
    def step(self, name, action, verify, verify_desc="", timeout=10,
             guard=True, allow_no_verify=False, pre=None):
        if verify is None and not allow_no_verify:
            self.fail(name, "step declared without verify (blind click forbidden)")
        if guard and self.blocking_modal() is not None:
            self.fail(name, "blocking modal present before action; refuse to act through it")
        if pre is not None and not pre():
            self.fail(name, "pre-condition not met")
        action()
        value, elapsed = self.wait_until(verify, timeout=timeout)
        if value is None:
            self.fail(name, f"verify failed: {verify_desc}", elapsed=round(elapsed, 2))
        self.emit("step_ok", step=name, ok=True, verify=verify_desc,
                  elapsed_s=round(elapsed, 2))
        return value

    # ---- fail-fast + scene freeze ----
    def snapshot(self, reason):
        """Dump control tree (JSON) + full-screen PNG into the run's freeze dir.
        Provided by the driver layer; returns the paths."""
        raise NotImplementedError

    def fail(self, step, reason, **extra):
        self.snapshot(reason)
        self.emit("step_fail", step=step, ok=False, reason=reason, **extra)
        raise StepFailed(f"[{step}] {reason}")

    # ---- top-level wrapper (rule 5) ----
    def run(self, main):
        try:
            result = main(self)
            self.emit("run_end", ok=True, **result)
            self._write_result({"ok": True, **result})
            return result
        except StepFailed:
            self._write_result({"ok": False, "reason": "step_failed"})
            raise
        except Exception as e:  # crash is still observable
            self.snapshot(f"crash: {type(e).__name__}: {e}")
            self.emit("crash", ok=False, error=str(e))
            self._write_result({"ok": False, "reason": "crash", "error": str(e)})
            raise

    def _write_result(self, d):
        with open("C:/rpa/last_result.json", "w", encoding="utf-8") as f:
            json.dump({**d, "run_id": self.run_id, "log": self.log_path}, f, ensure_ascii=False)
```

> The two `NotImplementedError` hooks (`blocking_modal`, `snapshot`) are the only
> environment-specific parts. They are filled by the driver layer the ops experts
> provide — the pipeline author never touches `prlctl`/`ssh`/`cua` to do it.

---

## 2. Step template (copy for every action step)

```python
r.step(
    "select_unit",                         # unique step name
    action=lambda: listbox_click_item(unit_list_hwnd, idx),   # the ONLY mutation
    verify=lambda: {"tax_id": t} if (t := read_tax_id()) else None,  # observable state
    verify_desc="识别号已随单位选择自动带出",
    timeout=15,
)
```

Rules baked in: `verify` is mandatory; `verify` returns a truthy dict (the
observable proof) or `None`; on `None` the kernel freezes the scene and stops.

---

## 3. Worked example — a login flow (rules applied)

Abstracted from a real tax-portal login. Shows every contract rule.

```python
def main(r):
    # rule 6: idempotency — if already logged in, do nothing destructive
    if r.find_window("Tfrm_MainFrame", visible_only=True):
        r.emit("already_logged_in", hwnd=...)
        return {"logged_in": True}

    # Phase: preflight (read-only, allow_no_verify)
    r.step("preflight", action=lambda: None,
           verify=lambda: r.find_window("Tfrm_Login") is not None,
           verify_desc="登录窗存在", allow_no_verify=True)

    # rule 8: runtime locator — find the unit picker from the live tree, not coords
    picker = r.find_control(class="TComboBox", title="单位")
    r.step("open_picker", action=lambda: click_at(*center(picker.rect)),
           verify=lambda: r.find_window("Tfrm_UnitPick") is not None,
           verify_desc="单位选择弹窗已出现")

    # rule 9: IME-safe input — set_text, never keystrokes
    r.step("fill_password",
           action=lambda: set_text(pwd_hwnd, password),
           verify=lambda: get_text_length(pwd_hwnd) == len(password),
           verify_desc="密码框长度等于期望值")

    # rule 7: safety valve — unknown captcha => refuse submit
    if r.find_control(class="TPanel", title="验证码") and not captcha_value:
        r.fail("click_login", "captcha present but value unknown; refuse to submit")

    # rule 2/3: submit, then poll the THREE terminal states
    def terminal():
        if r.find_window("Tfrm_MainFrame"): return "logged_in"
        if r.find_control(text="密码错误"):   return "bad_pwd"
        if r.find_control(text="已锁定"):     return "locked"
        return None
    r.step("click_login", action=lambda: click_at(*center(login_btn.rect)),
           verify=lambda: terminal() is not None, verify_desc="进入终态(已登录/错密/锁定)",
           timeout=45)
    state = terminal()
    if state != "logged_in":                 # rule 7: negative => stop, never loop
        r.fail("click_login", f"login ended in {state}; do not retry")
    return {"logged_in": True}
```

What this example demonstrates: every mutation has a `verify`; the only sleeps are
inside `wait_until` (polling); captcha-unknown and negative outcomes both stop the
run instead of guessing; secrets are compared by length, never logged in clear.

---

## 4. Parameter passing (avoid shell encoding breakage)

When the pipeline is launched by an orchestrator that relays arguments through a
shell/bridge, **pass parameters as base64-encoded JSON**, not as raw CLI args —
raw non-ASCII or quoted values get mangled by the shell layer. Decode inside the
script:

```python
import base64, json
def parse_args_b64(argv):
    for i, a in enumerate(argv):
        if a == "--args-b64" and i + 1 < len(argv):
            return json.loads(base64.b64decode(argv[i+1]))
    return {}
```

This is a **coding pattern**, not an infrastructure command — it belongs in the
pipeline regardless of how the environment is reached.

---

## 5. Reading the log back (observability)

Logs are JSONL; grep for the high-signal events to audit a run:

```
step_ok | step_fail | run_end | crash | already_logged_in | snapshot
```

A `step_fail` or `crash` line is always accompanied by a frozen scene
(control-tree JSON + PNG) in the run's freeze directory — that is the artifact to
open when diagnosing "why did it stop".
