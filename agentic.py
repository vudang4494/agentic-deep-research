#!/usr/bin/env python3
"""Agentic Deep Research -- single entry point for the whole product.

The stages already exist as separate scripts (pipeline/, scripts/, eval/, tools/); each has its
own flags and its own conventions, so running the product meant remembering which script to call
in which order -- and calling `pipeline/deep_research_v3.py` directly silently skipped the
preflight that `run_full.sh` performs, so a missing model surfaced as a mid-run crash.

This wraps them in ONE flow. It DELEGATES -- no stage logic is reimplemented here, so
`research/*.py` stays the single source of truth (CLAUDE.md guardrail 8).

    python3 agentic.py doctor                      # preflight: ollama + models + deps + render tools
    python3 agentic.py run    --topic "RLHF" --out-name rlhf_v4 --no-smoke [--render]
    python3 agentic.py all    --topic "RLHF" --out-name rlhf_v4 --no-smoke   # run -> render -> report
    python3 agentic.py render <run>
    python3 agentic.py report <run>
    python3 agentic.py verify [--static]           # the ship gate
    python3 agentic.py dedup  <run>                # near-dup audit
    python3 agentic.py outline <run> --topic "..." # outline audit
    python3 agentic.py judge  [--held-out MODEL]   # de-circle eval (kappa vs held-out judge)
    python3 agentic.py monitor

`run` preflights first unless --skip-preflight. Exit code is the delegated tool's own.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "output" / "runs"
PY = sys.executable


def _run(argv, **kw):
    """Delegate to a stage script, streaming its output. Returns its exit code."""
    print(f"\033[2m$ {' '.join(str(a) for a in argv)}\033[0m", flush=True)
    return subprocess.run([str(a) for a in argv], cwd=ROOT, **kw).returncode


def _run_dir(name: str) -> Path:
    """Accept a run NAME or a path to a run dir."""
    p = Path(name)
    return p if p.is_dir() else RUNS / name


# ------------------------------------------------------------------ doctor
def cmd_doctor(args) -> int:
    """Preflight. Model names come from research/config.py -- the single source -- rather than
    being retyped here (run_full.sh hardcodes them, which is how model drift starts)."""
    ok = True

    def line(label, good, detail=""):
        nonlocal ok
        ok &= good
        print(f"[{'  ok  ' if good else ' FAIL '}] {label:<26} {detail}")

    try:
        sys.path.insert(0, str(ROOT))
        from research.config import WRITER_MODEL, JUDGE_MODEL, EMBED_MODEL
        from research._ollama import OLLAMA_BASE
    except Exception as e:
        print(f"[ FAIL ] imports                    cannot import research/: {e}")
        return 1

    try:
        import httpx
        tags = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5).json()
        local = {m.get("name", "") for m in tags.get("models", [])}
        line("ollama", True, OLLAMA_BASE)
    except Exception as e:
        line("ollama", False, f"not reachable at {OLLAMA_BASE} -- start it: ollama serve  ({e})")
        return 1

    for role, model in (("writer", WRITER_MODEL), ("judge", JUDGE_MODEL), ("embed", EMBED_MODEL)):
        line(f"model {role}", model in local, model if model in local else f"MISSING -- ollama pull {model}")

    for mod in ("httpx", "torch", "transformers"):
        try:
            __import__(mod)
            line(f"python {mod}", True)
        except ImportError:
            line(f"python {mod}", False, "pip install -r requirements.txt")

    import shutil
    for tool in ("pandoc", "tectonic"):
        have = shutil.which(tool) is not None
        # render-only: absence costs the PDF, not the book
        print(f"[{'  ok  ' if have else ' warn '}] {'render ' + tool:<26} "
              f"{'' if have else 'missing -- book.md still renders, PDF will not (brew install ' + tool + ')'}")

    print("-" * 70)
    print("preflight OK" if ok else "preflight FAILED -- fix the FAIL lines above before running")
    return 0 if ok else 1


# --------------------------------------------------------------------- run
def cmd_run(args) -> int:
    if not args.skip_preflight:
        print("=== preflight ===")
        if cmd_doctor(args) != 0:
            print("\nAborting: preflight failed (use --skip-preflight to override).", file=sys.stderr)
            return 1
        print()

    argv = [PY, ROOT / "pipeline" / "deep_research_v3.py", "--topic", args.topic]
    if args.out_name:
        argv += ["--out-name", args.out_name]
    if args.canonical_ids:
        argv += ["--canonical-arxiv-ids", args.canonical_ids]
    if args.max_rounds:
        argv += ["--max-rounds", str(args.max_rounds)]
    if args.providers:
        argv += ["--providers", args.providers]
    if args.n_chapters:
        argv += ["--n-chapters", str(args.n_chapters)]
    if args.sections_per_chapter:
        argv += ["--sections-per-chapter", str(args.sections_per_chapter)]
    if args.no_smoke:
        argv += ["--no-smoke"]
    if args.render:
        argv += ["--render"]
    return _run(argv)


def cmd_all(args) -> int:
    """The end-to-end product flow: research -> render -> report, stopping on the first failure."""
    rc = cmd_run(args)
    if rc != 0:
        return rc
    name = args.out_name
    if not name:
        print("[all] --out-name not given; skipping render/report (cannot locate the run dir).")
        return 0
    if not args.render:  # --render already rendered inside the pipeline
        rc = _run([PY, ROOT / "scripts" / "render_book.py", "--run", name])
        if rc != 0:
            print("[all] render failed -- book.md is still valid; continuing to report.", file=sys.stderr)
    return _run([PY, ROOT / "tools" / "report.py", str(_run_dir(name))])


# ------------------------------------------------------------- thin wrappers
def cmd_render(args):
    return _run([PY, ROOT / "scripts" / "render_book.py", "--run", args.run] + (["--weasy"] if args.weasy else []))


def cmd_report(args):
    return _run([PY, ROOT / "tools" / "report.py", str(_run_dir(args.run))])


def cmd_verify(args):
    return _run([PY, ROOT / "eval" / "verify_all.py"] + (["--static"] if args.static else []))


def cmd_dedup(args):
    return _run([PY, ROOT / "eval" / "check_dedup.py", args.run])


def cmd_outline(args):
    state = _run_dir(args.run) / "state.json"
    return _run([PY, ROOT / "eval" / "audit_outline.py", "--state", str(state), "--topic", args.topic])


def cmd_judge(args):
    return _run([PY, ROOT / "eval" / "held_out_judge.py"] + (["--held-out", args.held_out] if args.held_out else []))


def cmd_monitor(args):
    return _run([PY, ROOT / "tools" / "monitor.py"])


def build_parser():
    p = argparse.ArgumentParser(prog="agentic.py", description=__doc__.split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_run_flags(sp):
        sp.add_argument("--topic", required=True)
        sp.add_argument("--out-name")
        sp.add_argument("--canonical-ids", help="comma-separated arxiv IDs to protect (P0b)")
        sp.add_argument("--max-rounds", type=int)
        sp.add_argument("--providers")
        sp.add_argument("--n-chapters", type=int)
        sp.add_argument("--sections-per-chapter", type=int)
        sp.add_argument("--no-smoke", action="store_true",
                        help="FULL book. Without it the run is a smoke test (chapters[:2]) -- that is the default.")
        sp.add_argument("--render", action="store_true", help="render the PDF inside the pipeline")
        sp.add_argument("--skip-preflight", action="store_true")

    add_run_flags(sub.add_parser("run", help="research + assemble a book"))
    add_run_flags(sub.add_parser("all", help="run -> render -> report, end to end"))

    sub.add_parser("doctor", help="preflight: ollama, models, python deps, render tools")

    sp = sub.add_parser("render", help="render an existing run to PDF")
    sp.add_argument("run"); sp.add_argument("--weasy", action="store_true")

    sub.add_parser("report", help="analyse a run's state.json").add_argument("run")

    sub.add_parser("verify", help="the ship gate").add_argument("--static", action="store_true")

    sub.add_parser("dedup", help="near-duplicate audit of a run").add_argument("run")

    sp = sub.add_parser("outline", help="outline audit of a run")
    sp.add_argument("run"); sp.add_argument("--topic", required=True)

    sub.add_parser("judge", help="held-out judge cross-check (kappa)").add_argument("--held-out")

    sub.add_parser("monitor", help="watch run progress")
    return p


def main():
    args = build_parser().parse_args()
    return globals()[f"cmd_{args.cmd}"](args)


if __name__ == "__main__":
    sys.exit(main())
