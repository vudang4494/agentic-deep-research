---
name: ship
description: Gate, commit, PR and merge the current work — with the staging verification that a silent `git add` failure once defeated.
disable-model-invocation: true
argument-hint: "[short description of the change]"
allowed-tools: Bash, Read
---

Ship the current working-tree change. Follow these steps IN ORDER and stop at the first failure.

## 1. Gate first — never commit a red tree

```bash
python3 eval/verify_all.py        # full: static A–I + acceptance (needs Ollama)
```
Use `--static` only if Ollama is down, and say so in the report. **Any FAIL → stop and fix.**

## 2. Branch (never commit straight to main)

```bash
git branch --show-current           # if main -> create a topic branch
git checkout -b <type>/<slug>       # fix/ feat/ refactor/ chore/ docs/
```

## 3. Stage EXPLICITLY, then VERIFY the staging

This is the step that has actually failed before: `git add -A <dir>` where one pathspec was a
directory already removed by `git rm` made git abort the WHOLE add, `2>/dev/null` swallowed the
error, and the commit silently shipped only a fraction of the change — the fix had to be split
across two PRs.

```bash
git add <file1> <file2> ...         # explicit paths; no bare -A, never a deleted dir as pathspec
git status -s                       # VERIFY: column 1 must be M/A/D for every intended file
```
- Column 1 = staged, column 2 = unstaged. A file showing ` M` (space first) is **NOT staged**.
- Confirm the staged set matches what you intended, and that `dg.md` / `research.md` are absent.
- Never redirect `git add` stderr to /dev/null.

## 4. Commit

- Explain **why**, not just what; reference the concrete failure the change prevents.
- **Do NOT add a `Co-Authored-By` trailer** (owner's standing convention).
- Use a heredoc (`git commit -F -`) so the body keeps its formatting.

## 5. PR → merge → back to main

```bash
git push -u origin <branch>
gh pr create --title "..." --body "..."   # body ends with the Claude Code attribution line
gh pr merge <n> --merge --delete-branch
git checkout main && git pull --ff-only
```

## 6. Report

State the PR number, the merge commit on main, the gate result (e.g. `14/14`), and confirm the
working tree is clean apart from intentionally-untracked WIP. If anything was skipped, say so.
