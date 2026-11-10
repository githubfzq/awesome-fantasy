# hands-on-modern-rl course environment

Repo: `/data/workspace/reese/projects/hands-on-modern-rl`.

## Layout

- Project-local env: `<repo>/.venv` (uv, Python 3.10.20, gitignored).
- Version pins: `<repo>/constraints.txt` → `torch==2.6.0`, `torchvision==0.21.0`,
  `stable-baselines3==2.7.0`.
- Per-chapter deps: `code/<chapter>/requirements.txt`; union in
  `code/requirements.txt`.
- Docs describe the env in `docs/preface/env-setup.md` (conda / venv / uv
  variants).

## Known-good install set

Base (already present): torch 2.6.0+cu124, gymnasium 1.2.3, stable-baselines3
2.7.0, numpy 2.2.6, scipy, matplotlib, pandas, tensorboard, pygame, ale-py.

LLM/alignment stack installed with constraints:

```bash
uv pip install --python .venv/bin/python -c constraints.txt \
  transformers==4.57.3 trl==0.24.0 datasets==4.4.1 accelerate==1.10.1 \
  peft swanlab imageio json5 openai seaborn
```

Resulting versions: transformers 4.57.3, trl 0.24.0, datasets 4.4.1,
accelerate 1.10.1, peft 0.21.2, swanlab 0.10.4.

## Running experiments

- Chapter scripts: `code/<chapter>/<script>.py` (see `code/README.md` for the
  per-chapter index and CLI flags, e.g. Ch01 `--device auto|cuda|mps|cpu`,
  shared helper `code/device_utils.py`).
- Lab notebooks: source of truth is `code/chapter-notebooks/*.py`; the
  `.ipynb` files are generated from them. Regenerate and check with
  `python scripts/build_chapter_notebooks.py [--check]` and
  `python scripts/build_localized_notebooks.py [--check]`.
- Execute the lab notebooks with
  `python scripts/execute_chapter_notebooks.py --output-dir <dir>` (each
  notebook's first cell installs its own missing deps), then publish with
  `python scripts/publish_notebook_results.py --run-dir <dir> --locale zh|en`.
- Machine-readable run records: `code/chapter-notebooks/validation.json`
  (and `.en.json`), `code/online-experiments/validation.studio.*.json`. They
  record the interpreter, packages and metrics of the run that produced the
  published outputs, so a version bump there invalidates the published
  results until the notebooks are re-executed.

## Smoke checks that actually pass here

```bash
.venv/bin/python -c "import gymnasium as gym, torch, stable_baselines3 as sb3; \
env=gym.make('CartPole-v1'); env.reset(seed=0); print(sb3.__version__, torch.cuda.is_available())"
.venv/bin/python code/chapter-notebooks/dpo.py   # ~seconds, CPU only
```

## Machine notes

- A second, unrelated conda env exists at
  `/home/data/miniconda3/envs/rl-course` (Python 3.10.22, torch 2.6.0,
  sb3 2.8.0). Do not mix it with the project env; course experiments use
  `<repo>/.venv`.
- GPU: single RTX 3090 (24 GB), driver 595.99.02, CUDA 13.2 driver-level
  while the pinned torch ships cu124. Other projects on this host
  periodically occupy most of the VRAM — check before promising GPU runs.
- Chapters needing extra runtimes (Atari/ALE, VizDoom, MuJoCo, ManiSkill,
  MineStudio, Unity ML-Agents, AI2-THOR) install their own deps inside the
  notebook and may need a separate env; keep them out of the main `.venv`.
