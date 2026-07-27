#!/usr/bin/env python3
"""PreToolUse hook: refuse to write the owner's private working notes.

`dg.md` and `research.md` are personal scratch files that live untracked in the repo root and
must never be edited or committed by an agent. Guarding this by memory alone failed repeatedly
(it had to be re-checked before every single commit), so it is enforced here instead.

Emits the documented deny decision (exit 0 + JSON) rather than a bare exit 2, so Claude sees a
clean, explained refusal instead of an error.
"""
import json
import sys

PRIVATE = ("dg.md", "research.md")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    path = ((payload.get("tool_input") or {}).get("file_path", "") or "").replace("\\", "/")
    if not path.split("/")[-1] in PRIVATE:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{path.split('/')[-1]} is the owner's private notes -- never edit or commit it. "
                "Put working notes in the scratchpad instead."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
