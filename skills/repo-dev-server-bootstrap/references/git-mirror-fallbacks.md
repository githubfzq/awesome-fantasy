# GitHub clone fallbacks

Use only when a plain HTTPS clone fails. Work top-down; stop at the first that
works.

## 1. HTTPS (default)

```bash
git clone https://github.com/<owner>/<repo>.git
```

Check first whether a global rewrite already routes this:

```bash
git config --global --get-regexp 'insteadof'
```

If it prints something like
`url.https://v6.gh-proxy.org/https://github.com/.insteadof=https://github.com/`
then HTTPS already goes through the mirror and no change is needed.

## 2. SSH

```bash
git clone git@github.com:<owner>/<repo>.git
```

Requires an SSH key registered on the account and port 22 reachable.

## 3. Explicit mirror URL

Prefix the plain HTTPS URL with the mirror host:

```bash
git clone https://gh-proxy.org/https://github.com/<owner>/<repo>.git
```

Common mirrors: `gh-proxy.org`, `v6.gh-proxy.org`, `ghfast.top` (exact prefix
style varies; verify with `curl -sI` before committing to a long clone).

## 4. Tarball fallback (no git history)

```bash
curl -L -o repo.tar.gz https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main
tar xzf repo.tar.gz
```

Use only when the user asked for the code, not for git history or a
contributable checkout.

## Notes

- A clone that prints `Cloning into '...'...` and then hangs is a network stall,
  not a permission problem; retry with a mirror rather than waiting.
- Never clone into a directory that already has content without checking
  whether the user wanted a fresh checkout there.
