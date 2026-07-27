#!/usr/bin/env python3
"""PostToolUse hook: run the static ship gate after an edit to pipeline-critical code.

CLAUDE.md tells you to run eval/verify_all.py before shipping, but nothing enforced it -- the
gate was invoked by hand. This closes that loop: any Edit/Write under research/ or pipeline/
(plus the gate itself) re-runs the static checks (~1s, no Ollama needed) and, on failure, exits 2
so the report is fed straight back to Claude as feedback instead of surfacing three runs later.

Exit codes (Claude Code hook contract):
  0 -> pass / not a watched file (silent)
  2 -> gate FAILED; stderr goes to Claude
"""
import json
import re
import subprocess
import sys
from pathlib import Path

WATCHED = re.compile(r"(?:research|pipeline)/[^/]*\.py$|eval/verify_all\.py$")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # malformed payload must never block the session

    path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    if not WATCHED.search(path.replace("\\", "/")):
        return 0

    root = Path(payload.get("cwd") or ".")
    gate = root / "eval" / "verify_all.py"
    if not gate.exists():
        return 0

    try:
        r = subprocess.run([sys.executable, str(gate), "--static"],
                           cwd=root, capture_output=True, text=True, timeout=150)
    except Exception as e:
        print(f"[verify-gate] could not run the gate: {e}", file=sys.stderr)
        return 0  # a broken hook must not masquerade as a failing gate

    if r.returncode == 0:
        return 0

    failures = [ln for ln in r.stdout.splitlines() if "FAIL" in ln]
    print("[verify-gate] STATIC GATE FAILED after editing "
          f"{path} -- fix before continuing:", file=sys.stderr)
    print("\n".join(failures or r.stdout.splitlines()[-12:]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
