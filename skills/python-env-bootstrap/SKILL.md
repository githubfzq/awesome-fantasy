---
name: python-env-bootstrap
description: Set up or audit a project-local Python env for ML/RL work.
version: 1.0.0
author: Hermes Agent
license: Apache-2.0
metadata:
  hermes:
    tags: [python, uv, venv, torch, cuda, constraints, ml, rl, environment]
    related_skills: [repo-dev-server-bootstrap, systematic-debugging]
---

# Prepare and audit a project-local Python environment

## When to Use

- The user asks whether the environment for a course/project is ready, where it
  lives, or asks you to install the missing dependencies.
- A repo has a project-local env (`.venv/`, uv, constraints file) or per-chapter
  `requirements.txt` files that must be assembled into one working environment.
- A CUDA/GPU training stack must be installed without breaking an existing
  torch/CUDA pin.

Class of task: make one Python environment in the project that can run the
project's own code, verify it by executing real project code, and report
exactly where the environment lives and what is still missing.

## 1. Locate the environment first, do not create a new one

Look, in order, at: `.venv/` in the repo root, `.python-version`,
`constraints.txt`, `pyproject.toml`/`requirements*.txt`, per-chapter
`requirements.txt` files under `code/`, and the repo's setup docs
(`docs/preface/env-setup.md` or similar). Also list conda envs
(`conda env list`) so you can tell the project env apart from a pre-existing
personal one — two coexisting envs on one machine is the main source of
"which interpreter am I using" mistakes.

Report the env's absolute path and interpreter (`<repo>/.venv/bin/python -V`).
A project-local env that lives inside the repo and is gitignored is the
preferred layout: it travels with the code and needs no global tooling.

## 2. Install with a constraints file, never bare

`pip install <pkg>` pulls whatever the resolver wants, and ML stacks routinely
drag torch forward. Resolve against the repo's pinned versions:

```bash
uv pip install --python .venv/bin/python -c constraints.txt \
  transformers==4.57.3 trl==0.24.0 datasets==4.4.1 accelerate==1.10.1 \
  peft swanlab imageio json5 openai seaborn
```

Rules:

- Use `-c constraints.txt` (pip) / `--constraint` (uv) whenever the repo ships
  one; the constraint pins the package that everything else fights over.
- Prefer `uv pip install --python <env>/bin/python` over activating the env:
  it targets the exact interpreter and needs no shell state, which matters for
  non-interactive and background runs.
- Install the union of the per-chapter `requirements.txt` files the user
  actually needs, not the whole set; a full install can be GBs and pull
  simulator toolkits nobody will use.
- Long installs exceed the foreground timeout: run them as a tracked
  background process and wait on it, do not restart the install.

## 3. Verify the CUDA pin survived the install

Import the stack and print the versions that matter — the install succeeding
does not mean torch survived:

```bash
.venv/bin/python -c "import torch, transformers, trl; \
print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); \
print(transformers.__version__, trl.__version__)"
```

Pitfall: `stable-baselines3[extra]` and `trl`/`datasets` resolve to a torch
2.8+ build that ships a CUDA 13 runtime, which silently replaces a working
cu124 wheel. The symptom is a version string with a different `+cuXXX` local
tag and `torch.version.cuda` no longer matching the installed driver stack.
With a constraints file this cannot happen; without one it does, and the fix
is to reinstall with the pin, not to debug the CUDA error.

## 4. Verify by running the project's own code

A version matrix proves nothing. Execute real code from the repo:

- a fast smoke of the core stack (env reset/step, one short SB3 training run),
- one script from the repo's own experiment directory.

Check how the repo runs its experiments before inventing commands: look for an
executor script (`scripts/execute_*_notebooks.py`) and its README section for
the canonical invocation and its dependency-install cell.

## 5. Report honestly, including the blocker

Say where the env is, what is installed, what you ran and what it printed, and
what is still missing or blocked. If GPU work cannot run right now, say so and
name the cause (see below). Do not present a "ready" verdict from an import
check alone.

## Pitfalls

- Installing LLM/RL stacks without the repo's constraints file upgrades torch
  and swaps the CUDA runtime — the mechanism is the dependency resolver
  choosing the newest torch, so pin it explicitly.
- Two environments on one machine (project `.venv` plus a conda env) lead to
  running the wrong interpreter; always state the absolute path of the one
  you used.
- A GPU can be fully occupied by unrelated processes, in which case large
  training silently OOMs or crawls. Check occupancy and report it:
  `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` and
  `nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv`.
  Never kill another user's or another project's GPU processes on your own
  initiative — report the pids and let the user decide.
- Headless simulator installs (MuJoCo, Isaac, MineStudio) need
  `MUJOCO_GL=egl`/`osmesa` and often a separate env; do not fold them into
  the main env by default.
- `pip list` inside a uv-created venv may print nothing (no pip in the venv);
  use `uv pip list --python <env>/bin/python` instead.

## References

- `references/rl-course-env.md` — the hands-on-modern-rl course: project-local
  `.venv`, `constraints.txt`, known-good install set, notebook execution and
  publishing commands, machine notes.
