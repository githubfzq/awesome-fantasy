---
name: skill-sources
description: "Use when adding GitHub repo taps or publishing skills."
platforms: [macos, linux, windows]
---

# Hermes Skill Sources — Taps & Publishing

Managing where Hermes finds skills and how to publish them.

## Adding a GitHub Repo as a Skill Source (Tap)

```bash
hermes skills tap add owner/repo
```

This adds a tap — skills in the repo's `skills/` directory become discoverable via `hermes skills search` and installable via `hermes skills install`.

### ⚠️ Branch Constraint (Critical)

Taps **always use the repo's default branch** (set in GitHub Settings → Branches). There is no `--branch` parameter on `hermes skills tap add`. The source code confirms:

```python
# tools/skills_hub.py:822
default_branch = resp.json().get("default_branch", "main")
```

If your skills are on a non-default branch (e.g. `Skill`), they **will not be visible** through the tap.

### Workaround: Direct URL Install from Any Branch

```bash
hermes skills install https://raw.githubusercontent.com/owner/repo/branch-name/skills/skill-name/SKILL.md
```

`hermes skills install` accepts a direct HTTP(S) URL to a SKILL.md file, so you can install from any branch using a `raw.githubusercontent.com` link. This bypasses the tap entirely.

### Manage Taps

```bash
hermes skills tap list          # Show configured taps
hermes skills tap remove owner/repo  # Remove a tap
```

Taps are stored in `~/.hermes/skills/.hub/taps.json` (internal, read-only via tools).

## Publishing Skills to a GitHub Repo

```bash
hermes skills publish <skill-path> --to github --repo owner/repo
```

### ⚠️ Branch Constraint (Same Issue)

Publishing also uses the **default branch** as the base:

```python
# hermes_cli/skills_hub.py:1578
default_branch = resp.json().get("default_branch", "main")
```

The publish workflow:
1. Forks the target repo
2. Creates a new branch `add-skill-<name>` from the default branch
3. Uploads skill files to `skills/<name>/`
4. Creates a PR

## Recommended Workflow: Separate Branch for Skills

If you keep skills on a non-default branch (e.g. `Skill`):

1. **Change the default branch** on GitHub to the skills branch while developing
2. **Merge** the skills branch into `main` when ready for production
3. **Use direct URL installs** (`hermes skills install https://raw.githubusercontent.com/...`) for ad-hoc installs from any branch

## Quick Reference

| Action | Command |
|--------|---------|
| Add tap | `hermes skills tap add owner/repo` |
| Install from branch | `hermes skills install https://raw.githubusercontent.com/owner/repo/branch/skills/name/SKILL.md` |
| Publish skill | `hermes skills publish path --to github --repo owner/repo` |
| List taps | `hermes skills tap list` |
| Remove tap | `hermes skills tap remove owner/repo` |