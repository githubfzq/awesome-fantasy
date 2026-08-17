---
name: create-windows-rpa-pipeline
description: "This skill should be used when building, scaffolding, or reviewing a Windows desktop RPA pipeline (GUI automation against a Windows application). It enforces a robust, observable, fail-fast engineering contract where every action step is verified and logged before the next step runs. It provides a reusable step/guard/verify/logging kernel pattern, a verification-criteria hierarchy, safety-valve patterns (e.g. never click submit when a captcha is unknown), idempotency rules, and a build workflow (discover locators, design state machine, implement kernel-driven steps, dry-run, audit, run). It is infrastructure-agnostic: VM lifecycle, remote command channels, and desktop drivers are delegated to dedicated ops experts and must not appear in this skill."
agent_created: true
---

# Create Windows RPA Pipeline

## Overview

A Windows RPA pipeline is **not** a script that clicks through a UI. It is an
**observable state machine**: every step transitions the target app from one
verified state to the next, and any step that cannot prove it succeeded must stop
the run and freeze the scene for inspection. This skill captures the hard
constraints, the kernel pattern, and the build workflow that make a pipeline
safe to run unattended and auditable after the fact.

Use this skill as the **common contract** that the RPA Architect plans against,
the RPA Executor implements against, and the RPA Reviewer audits against. It is
deliberately free of any infrastructure commands (`prlctl`, `ssh`, `PsExec`,
`cua`/`MCP` calls, etc.) — those live with the ops experts. A pipeline built with
this skill runs unchanged whether the Windows app sits in a local VM, a remote
desktop, or a physical machine.

## When to use

- Starting a new RPA pipeline against any Windows desktop application.
- Reviewing or hardening an existing RPA script that "sometimes gets stuck" or
  "clicks blindly".
- Answering "does this automation verify each step?" — apply the robustness
  checklist at the end.

## Core mental model

> A step that is not verified is a step that may have driven the app into an
> unknown state. Unknown state is how automations cause account locks, duplicate
> submissions, and silent data corruption.

Each step is a closed loop:

```
guard (blocking modal?) → pre-condition → action → verify (poll until true / timeout) → emit log
                                  │                                              │
                                  └── verify fails ──► fail-fast: snapshot + freeze + stop
```

No step may proceed on a guess. `sleep(N)` is **never** a verification.

## The engineering contract (hard rules, not suggestions)

1. **Every action step has a post-verify.** A `step()` call without a `verify`
   predicate is rejected by the kernel (allow `verify`-less steps only for pure
   read/probe steps, explicitly flagged).
2. **Verify is an observable state, not a return code.** Prefer "the target
   window/control now exists / has this text / is visible" over "the click
   returned 0". See the criteria hierarchy below.
3. **Fail-fast on verify failure.** On timeout or a negative assertion, stop the
   whole run immediately; snapshot the window tree (JSON) + a full-screen PNG;
   write the failure to the log; never retry by blindly repeating the action.
4. **Structured step logging.** Every step emits one JSONL line:
   `{ts, run_id, seq, event, step, ok, detail}`. A run that cannot be replayed
   from its log is not done.
5. **Top-level catch.** A single top-level handler wraps the whole run so an
   unexpected exception still produces a `crash` log line + a snapshot, not a
   silent hang.
6. **Idempotency.** Re-running the pipeline on an already-completed app must
   detect the "already done" state and exit cleanly (e.g. main window already
   visible → `already_done`), never re-perform destructive steps.
7. **Safety valves.** Encode business guards that a human would apply: do not
   click "login/submit" when a captcha is present but its value is unknown (prevents
   password-lockout from repeated failures); do not close a dialog whose meaning
   is unreadable; pause on any unexpected modal.
8. **Deterministic locators.** Discover controls **at runtime** from the live
   control tree (class + title + hierarchy), not from hardcoded pixel coordinates
   that drift when the window moves or the screen resolution changes.
9. **IME-safe text input.** For CJK (or any non-ASCII) text, set the control's
   text via the native "set text" message / API, not by synthesizing keystrokes,
   which get composed by the input method and produce wrong lengths/content.
10. **Headless output is lost.** If the driver runs without a console
    (`pythonw`/detached), `print` goes nowhere — log to a file (JSONL) and write a
    machine-readable result file; never rely on stdout for observability.

## The execution kernel pattern

Adopt (or port) a small kernel module that every pipeline script depends on. The
kernel owns: `step`, `guard`, `wait_until`, `snapshot`, `emit`, `fail`, `finish`,
`run`. Responsibilities:

- `step(name, action, verify, verify_desc, timeout, guard=True, allow_no_verify=False)`:
  runs the loop above; enforces rule 1; on failure calls `snapshot()` + `emit()`
  + raises.
- `wait_until(predicate, timeout, interval)`: condition polling — the only
  sanctioned replacement for `sleep`.
- `guard=True`: before the action, check for a blocking modal dialog and refuse
  to click "through" it.
- `snapshot()`: dump the control tree + screenshot to the run's freeze directory.
- `emit(event, **kv)`: append one JSONL line.
- `mask(secret)`: redact secrets in logs (record length only, e.g. `***len=12`).
- `run(main)`: top-level wrapper (rule 5).

A reference implementation of this kernel and a worked example live in
`references/playbook.md`.

## Verification-criteria hierarchy (pick the most reliable that applies)

1. **New window appears / old window disappears** — `find_window(class)`, most reliable.
2. **Control text length / content** — `get_text_length` / `get_text`, for inputs.
3. **Control presence / visibility** — enumerate children, filter by class + visible, for tab/page switches.
4. **List item count > 0** — `list_items()`, for asynchronously loaded data.
5. **Pixel difference** — only for bitmaps with no HWND (e.g. a captcha image with
   no window handle); compare mean pixel diff before/after a refresh to prove the
   image actually changed. Last resort, not a primary signal.

## Safety-valve patterns (concrete)

- **Unknown captcha → refuse submit.** If a captcha control is detected but no
  value was supplied, stop and ask for the value; never submit a guess.
- **Unreadable modal → pause, don't click.** Owner-drawn dialogs may expose no
  readable text via the control tree; treat any unexpected modal as a hard pause
  and snapshot, never auto-dismiss.
- **Negative outcome → stop, never loop.** A "password incorrect" / "locked"
  response terminates the run; automatic retries cause lockouts.

## Build workflow (maps to expert roles)

```
Phase 1  Discover   (Architect + Executor)  — enumerate the live control tree,
                                              record class/title/hierarchy of
                                              every control the flow touches.
Phase 2  Design     (Architect)             — decompose the business process into
                                              verified steps; write the verify
                                              predicate for each; flag safety valves.
Phase 3  Implement  (Executor)              — write kernel-driven steps from the
                                              template; no blind clicks; mask secrets.
Phase 4  Dry-run    (Executor)              — run with actions disabled: confirm
                                              locators resolve and the "already done"
                                              / idempotent branch is correct. 0 real clicks.
Phase 5  Audit      (Reviewer)              — check every step has a verify, fail-fast
                                              on each failure path, logging complete,
                                              safety valves present. Reject if not.
Phase 6  Run        (Executor)              — execute for real; on any failure,
                                              use the frozen snapshot + JSONL to diagnose.
```

## Division of labor (infrastructure is NOT here)

This skill intentionally contains **no** commands for standing up or reaching the
Windows environment. Delegate to the dedicated ops experts:

- **VM lifecycle / network / remote channel** → the VM-ops expert (`prlctl`,
  `PsExec -i 1`, bridge health, IP/routing).
- **Driving the desktop once reachable** → the computer-use expert (`cua`/MCP
  screenshot-click-type, or the win32 driver inside the guest).
- **Mac host housekeeping** → the local-machine-ops expert.

The pipeline script only speaks the kernel API + the target app's control tree.
Swapping the environment (VM ↔ physical PC ↔ remote desktop) changes nothing in
the pipeline.

> **Prerequisite ownership:** the *concrete* pipeline skill (e.g. `withholding-login`)
> — not this infrastructure-agnostic contract — must document how to provision the
> driver layer the kernel primitives depend on: the **isolated venv path** and the
> **exact third-party libs** (e.g. only `Pillow` here, since Win32 calls use stdlib
> `ctypes`). A pipeline that cannot `import` its driver cannot run; that install
> step is a prerequisite the concrete skill must state explicitly.

## Robustness checklist (apply before declaring a pipeline done)

- [ ] Every `step()` has a `verify`; pure-read steps are explicitly flagged.
- [ ] No `sleep` used as a verification anywhere.
- [ ] Every failure path stops the run and freezes the scene (tree JSON + PNG).
- [ ] JSONL log present; a failure is reconstructable from the log alone.
- [ ] Re-running on a completed app is idempotent (detects `already_done`).
- [ ] Safety valves present for captcha-unknown / unreadable-modal / negative-outcome.
- [ ] Locators are runtime-discovered, not hardcoded coordinates.
- [ ] CJK text uses native set-text, not synthesized keystrokes.
- [ ] Secrets are masked in logs; result is machine-readable.
- [ ] Dry-run passed with 0 real clicks before any real run.

## Resources

- `references/playbook.md` — reference kernel skeleton, a copy-paste step template,
  and a worked example (login flow) showing every rule applied.
