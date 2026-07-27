#!/usr/bin/env python3
"""
Report Generator for Agentic Deep Research Pipeline
===================================================
Reads state.json from any pipeline run and produces a structured analysis report.

Usage:
    python3 tools/report.py output/runs/bookv7
    python3 tools/report.py output/runs/smoke_batiaiqwen36 --format markdown
    python3 tools/report.py --all  # report on all runs

Output formats: text (default), markdown, json
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import Optional

# ---- Report configurations ----
REPORT_MODELS = [
    "gemma3:4b",
    "batiai/qwen3.6-35b:iq3",
    "gemma4:e4b",
]

BASELINE_GROUNDING = {
    "gemma3:4b": 0.35,
    "batiai/qwen3.6-35b:iq3": 0.979,  # full run v2
}


def load_state(run_dir: Path) -> Optional[dict]:
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def load_report(run_dir: Path) -> Optional[dict]:
    report_file = run_dir / "report.json"
    if not report_file.exists():
        return None
    try:
        return json.loads(report_file.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def compute_stats(state: dict, min_grounding: float = 0.55) -> dict:
    passes = state.get("passes", {})
    done = {k: v for k, v in passes.items() if v.get("verify")}
    if not done:
        return _empty_stats()

    g_vals = [v["verify"]["grounding"] for v in done.values()]
    wc_vals = [v.get("wc", 0) for v in done.values()]
    rounds = [v.get("round", 1) for v in done.values()]

    # Citation breakdown — handle both v1 (per-citation) and v2 (per-claim) schema
    # v1: verify.supports / verify.partial / verify.unrelated / verify.no_evidence (counts)
    # v2: verify.n_supported / verify.n_partial / verify.n_unsupported (counts) + verify.n_claims
    s_vals = [v["verify"].get("supports", v["verify"].get("n_supported", 0)) for v in done.values()]
    p_vals = [v["verify"].get("partial", v["verify"].get("n_partial", 0)) for v in done.values()]
    u_vals = [v["verify"].get("unrelated", v["verify"].get("n_unsupported", 0)) for v in done.values()]
    ce_vals = [v["verify"].get("no_evidence", 0) for v in done.values()]

    # v2 cite_precision field
    cite_prec_vals = [
        v["verify"].get("cite_precision", 0) for v in done.values()
        if v["verify"].get("verify_version") == "v2"
    ]

    # v2 CRAG branch distribution
    crag_counts = {"accept": 0, "ambiguous": 0, "incorrect": 0}
    for v in done.values():
        crag = v["verify"].get("crag_decision")
        if crag in crag_counts:
            crag_counts[crag] += 1

    total_s = sum(s_vals)
    total_p = sum(p_vals)
    total_u = sum(u_vals)
    total_ce = sum(ce_vals)
    total_cite = total_s + total_p + total_u + total_ce
    grounding_rate = total_s / total_cite if total_cite else 0

    # Review scores
    has_review = any(v.get("review") for v in done.values())
    if has_review:
        rev_depth = [v["review"]["depth"] for v in done.values() if v.get("review")]
        rev_coh = [v["review"]["coherence"] for v in done.values() if v.get("review")]
        rev_fmt = [v["review"]["format"] for v in done.values() if v.get("review")]
        avg_depth = sum(rev_depth) / len(rev_depth) if rev_depth else 0
        avg_coh = sum(rev_coh) / len(rev_coh) if rev_coh else 0
        avg_fmt = sum(rev_fmt) / len(rev_fmt) if rev_fmt else 0
    else:
        avg_depth = avg_coh = avg_fmt = 0

    # Section breakdown
    by_bucket = {
        "excellent": sum(1 for g in g_vals if g >= 0.7),
        "good": sum(1 for g in g_vals if 0.55 <= g < 0.7),
        "fair": sum(1 for g in g_vals if 0.4 <= g < 0.55),
        "poor": sum(1 for g in g_vals if g < 0.4),
    }

    # CRAG branch distribution (v2)
    verify_version = "v1"
    if any(v["verify"].get("verify_version") == "v2" for v in done.values()):
        verify_version = "v2"

    return {
        "total_sections": len(passes),
        "completed_sections": len(done),
        "avg_grounding": sum(g_vals) / len(g_vals) if g_vals else 0,
        "min_grounding": min(g_vals) if g_vals else 0,
        "max_grounding": max(g_vals) if g_vals else 0,
        "std_grounding": _std(g_vals) if len(g_vals) > 1 else 0,
        "sections_above_threshold": sum(1 for g in g_vals if g >= min_grounding),
        "sections_below_threshold": sum(1 for g in g_vals if g < min_grounding),
        "pass_rate": sum(1 for g in g_vals if g >= min_grounding) / len(g_vals) if g_vals else 0,
        "avg_wc": sum(wc_vals) / len(wc_vals) if wc_vals else 0,
        "total_wc": sum(wc_vals),
        "avg_rounds": sum(rounds) / len(rounds) if rounds else 0,
        "total_rounds": sum(rounds),
        "reserach_loops_triggered": sum(1 for r in rounds if r > 1),
        "grounding_rate": grounding_rate,
        "cite_supports": total_s,
        "cite_partial": total_p,
        "cite_unrelated": total_u,
        "cite_no_evidence": total_ce,
        "cite_total": total_cite,
        "avg_review_depth": avg_depth,
        "avg_review_coherence": avg_coh,
        "avg_review_format": avg_fmt,
        "has_review": has_review,
        "by_bucket": by_bucket,
        "threshold": min_grounding,
        # v2 fields
        "verify_version": verify_version,
        "cite_precision_avg": sum(cite_prec_vals) / len(cite_prec_vals) if cite_prec_vals else None,
        "crag_branches": crag_counts if verify_version == "v2" else None,
    }


def _std(vals):
    mean = sum(vals) / len(vals)
    return (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5


def _empty_stats():
    return {
        "total_sections": 0, "completed_sections": 0,
        "avg_grounding": 0, "min_grounding": 0, "max_grounding": 0,
        "std_grounding": 0, "sections_above_threshold": 0,
        "sections_below_threshold": 0, "pass_rate": 0,
        "avg_wc": 0, "total_wc": 0, "avg_rounds": 1,
        "total_rounds": 0, "reserach_loops_triggered": 0,
        "grounding_rate": 0, "cite_supports": 0,
        "cite_partial": 0, "cite_unrelated": 0, "cite_no_evidence": 0,
        "cite_total": 0, "avg_review_depth": 0,
        "avg_review_coherence": 0, "avg_review_format": 0,
        "has_review": False, "by_bucket": {},
        "threshold": 0.55,
        "verify_version": "v1",
        "cite_precision_avg": None,
        "crag_branches": None,
    }


def format_text(stats: dict, run_name: str, model: str = "", run_dir: Path = None) -> str:
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  REPORT: {run_name}")
    if model:
        lines.append(f"  Model:  {model}")
    if run_dir:
        lines.append(f"  Path:   {run_dir}")
    lines.append(f"{'='*60}")
    lines.append("")

    pct = lambda v: f"{v * 100:.1f}%" if isinstance(v, float) else str(v)

    lines.append(f"{'Sections':<30} {stats['completed_sections']}/{stats['total_sections']}")
    lines.append("")
    lines.append("GROUNDING")
    lines.append(f"  {'Avg':<28} {stats['avg_grounding']:.3f}")
    lines.append(f"  {'Min':<28} {stats['min_grounding']:.3f}")
    lines.append(f"  {'Max':<28} {stats['max_grounding']:.3f}")
    lines.append(f"  {'Std':<28} {stats['std_grounding']:.3f}")
    lines.append(f"  {'Pass rate (>=0.55)':<28} {stats['pass_rate']*100:.1f}%  ({stats['sections_above_threshold']}/{stats['completed_sections']})")

    # Grounding vs baseline
    for bmodel, bval in BASELINE_GROUNDING.items():
        if model and bmodel in model:
            delta = (stats['avg_grounding'] - bval) / bval * 100
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {'vs baseline':<28} {sign}{delta:.0f}%  ({bmodel})")

    lines.append("")
    lines.append("GROUNDING DISTRIBUTION")
    buckets = stats["by_bucket"]
    labels = [("Excellent (>=0.70)", "excellent"),
               ("Good    (0.55-0.70)", "good"),
               ("Fair    (0.40-0.55)", "fair"),
               ("Poor    (<0.40)",     "poor")]
    for label, key in labels:
        n = buckets.get(key, 0)
        bar = "█" * n + "░" * (stats["completed_sections"] - n)
        lines.append(f"  {label:<24} {bar} {n}")

    lines.append("")
    lines.append("CONTENT")
    lines.append(f"  {'Avg words/section':<28} {stats['avg_wc']:.0f}")
    lines.append(f"  {'Total words':<28} {stats['total_wc']:,}")
    if stats["has_review"]:
        lines.append(f"  {'Avg review depth':<28} {stats['avg_review_depth']:.1f}/10")
        lines.append(f"  {'Avg review coherence':<28} {stats['avg_review_coherence']:.1f}/10")
        lines.append(f"  {'Avg review format':<28} {stats['avg_review_format']:.1f}/10")

    lines.append("")
    lines.append("ITERATION")
    lines.append(f"  {'Avg research rounds':<28} {stats['avg_rounds']:.1f}")
    lines.append(f"  {'Re-search triggered':<28} {stats['reserach_loops_triggered']} sections")

    lines.append("")
    lines.append("CITATION QUALITY")
    total = stats["cite_total"]
    if total > 0:
        lines.append(f"  {'Supports':<28} {stats['cite_supports']:>4}  {pct(stats['cite_supports']/total)}")
        lines.append(f"  {'Partial':<28} {stats['cite_partial']:>4}  {pct(stats['cite_partial']/total)}")
        lines.append(f"  {'Unrelated':<28} {stats['cite_unrelated']:>4}  {pct(stats['cite_unrelated']/total)}")
        lines.append(f"  {'No evidence':<28} {stats['cite_no_evidence']:>4}  {pct(stats['cite_no_evidence']/total)}")
        lines.append(f"  {'Grounding rate (s/total)':<28} {stats['grounding_rate']*100:.1f}%")
    lines.append("")
    return "\n".join(lines)


def format_markdown(stats: dict, run_name: str, model: str = "", run_dir: Path = None) -> str:
    lines = []
    lines.append(f"# Report: {run_name}")
    if model:
        lines.append(f"**Model:** `{model}`")
    if run_dir:
        lines.append(f"**Path:** `{run_dir}`")
    lines.append("")
    lines.append(f"_Generated: {datetime.now().isoformat()}_")
    lines.append("")

    lines.append("## Grounding Summary")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Avg grounding | **{stats['avg_grounding']:.3f}** |")
    lines.append(f"| Min grounding | {stats['min_grounding']:.3f} |")
    lines.append(f"| Max grounding | {stats['max_grounding']:.3f} |")
    lines.append(f"| Std deviation | {stats['std_grounding']:.3f} |")
    lines.append(f"| Pass rate (>=0.55) | **{stats['pass_rate']*100:.1f}%** ({stats['sections_above_threshold']}/{stats['completed_sections']}) |")

    # vs baseline
    for bmodel, bval in BASELINE_GROUNDING.items():
        if model and bmodel in model:
            delta = (stats['avg_grounding'] - bval) / bval * 100
            sign = "+" if delta >= 0 else ""
            lines.append(f"| vs {bmodel} baseline | {sign}{delta:.0f}% |")

    lines.append("")
    lines.append("## Grounding Distribution")
    buckets = stats["by_bucket"]
    total = stats["completed_sections"]
    for label, key in [("Excellent (>=0.70)", "excellent"), ("Good (0.55-0.70)", "good"),
                        ("Fair (0.40-0.55)", "fair"), ("Poor (<0.40)", "poor")]:
        n = buckets.get(key, 0)
        bar = "█" * n + "░" * (total - n)
        lines.append(f"- **{label}:** {bar} `{n}/{total}`")

    lines.append("")
    lines.append("## Content")
    lines.append(f"- Avg words/section: **{stats['avg_wc']:.0f}**")
    lines.append(f"- Total words: **{stats['total_wc']:,}**")
    if stats["has_review"]:
        lines.append(f"- Avg review (depth/coherence/format): {stats['avg_review_depth']:.1f} / {stats['avg_review_coherence']:.1f} / {stats['avg_review_format']:.1f}")

    lines.append("")
    lines.append("## Iteration")
    lines.append(f"- Avg research rounds: **{stats['avg_rounds']:.1f}**")
    lines.append(f"- Re-search triggered: **{stats['reserach_loops_triggered']}** sections")

    lines.append("")
    lines.append("## Citation Quality")
    total = stats["cite_total"]
    if total > 0:
        lines.append(f"| Category | Count | Rate |")
        lines.append(f"|----------|-------|------|")
        for label, key in [("Supports", "cite_supports"), ("Partial", "cite_partial"),
                            ("Unrelated", "cite_unrelated"), ("No evidence", "cite_no_evidence")]:
            n = stats[key]
            lines.append(f"| {label} | {n} | {n/total*100:.1f}% |")
        lines.append(f"| **Grounding rate** | | **{stats['grounding_rate']*100:.1f}%** |")

    lines.append("")
    lines.append("## Per-Section Detail")
    lines.append("| Section | Grounding | Words | Rounds | Supports | Partial | Unrelated |")
    lines.append("|---------|-----------|-------|--------|----------|---------|----------|")
    # Would need state to show this; note it
    lines.append("| _(requires state.json)_ | | | | | | |")
    lines.append("")
    return "\n".join(lines)


def format_json(stats: dict, run_name: str, model: str = "") -> str:
    output = {
        "run_name": run_name,
        "model": model,
        "generated_at": datetime.now().isoformat(),
        **stats,
    }
    return json.dumps(output, indent=2)


def _v3_stats(state: dict) -> dict:
    """Stats for the v3 orchestrator's FLAT `sections` schema.

    compute_stats() below reads the legacy v2 `passes` schema (`v["verify"]["grounding"]`,
    crag_decision, review...). run_v3 writes `sections[key] = {quality, topic_relevance,
    grounding, n_citations, cross_refs, content, ...}` instead, so every v3 run reported
    'no completed sections' -- the documented measurement tool was blind to the live pipeline.

    The headline signals here are the ones that are actually ENFORCED (CLAUDE.md guardrail 2):
    `quality` (ok/degraded/BLOCKED) and G4 `topic_relevance`. Grounding is reported but labelled
    advisory -- it is not a gate and must not be read as a quality score."""
    secs = state.get("sections") or {}
    rows = [v for v in secs.values() if isinstance(v, dict)]
    q = Counter(str(v.get("quality", "?")) for v in rows)
    topics = [float(v.get("topic_relevance", 0) or 0) for v in rows]
    grounds = [float(v.get("grounding", 0) or 0) for v in rows]
    words = [len((v.get("content") or "").split()) for v in rows]
    cites = [int(v.get("n_citations", 0) or 0) for v in rows]
    xrefs = [int(v.get("cross_refs", 0) or 0) for v in rows]
    cps = [float(v["cite_precision"]) for v in rows if v.get("cite_precision") is not None]
    n = len(rows) or 1
    return {
        "n_sections": len(rows),
        "quality": dict(q),
        "blocked_rate": q.get("BLOCKED", 0) / n,
        "topic_mean": sum(topics) / n,
        "topic_ge_050": sum(1 for t in topics if t >= 0.50) / n,
        "grounding_mean": sum(grounds) / n,
        "grounding_inert": len({round(g, 4) for g in grounds}) <= 1,
        "cite_precision_mean": (sum(cps) / len(cps)) if cps else None,
        "cite_precision_n": len(cps),
        "words": sum(words),
        "cites": sum(cites),
        "sections_no_cite": sum(1 for c in cites if c == 0),
        "xrefs": sum(xrefs),
        "provenance": state.get("provenance") or {},
    }


def _format_v3(s: dict, run_name: str, topic: str) -> str:
    L = [f"\n{'=' * 70}", f"RUN: {run_name}   (orchestrator v3)", f"topic: {topic}", "=" * 70]
    q = s["quality"]
    L.append(f"{'Sections':<26} {s['n_sections']}   " +
             "  ".join(f"{k}={v}" for k, v in sorted(q.items())))
    L.append(f"{'Blocked rate':<26} {s['blocked_rate']:.0%}   (gate refusing to fabricate = correct)")
    L.append(f"{'Topic G4 (ENFORCED)':<26} mean {s['topic_mean']:.3f} | >=0.50: {s['topic_ge_050']:.0%}")
    cp = s.get("cite_precision_mean")
    L.append(f"{'Cite-precision G2':<26} " + (
        f"mean {cp:.3f} (n={s['cite_precision_n']}) -- gate 0.45"
        if cp is not None else "not persisted (pre-fix run; grep the log for cite_prec=)"))
    L.append(f"{'Grounding (advisory)':<26} mean {s['grounding_mean']:.3f}" +
             ("   [INERT: constant -- not a quality signal]" if s["grounding_inert"] else ""))
    L.append(f"{'Words':<26} {s['words']:,}   (~{round(s['words'] / 450)} pages)")
    L.append(f"{'Citations':<26} {s['cites']}   ({s['sections_no_cite']} section(s) with 0 cites)")
    L.append(f"{'Cross-refs':<26} {s['xrefs']}")
    p = s["provenance"]
    if p:
        models = p.get("models") or {}
        w = (models.get("writer") or {}).get("name", "?")
        L.append(f"{'Provenance':<26} git {str(p.get('git_sha', '?'))[:8]}"
                 f"{'+dirty' if p.get('git_dirty') else ''} | seed {p.get('seed')} | writer {w}")
    L.append("=" * 70)
    return "\n".join(L)


def report_run(run_dir: Path, format: str = "text", model: str = "") -> str:
    state = load_state(run_dir)
    run_name = run_dir.name
    if not state:
        return f"  [skip] {run_name}: no state.json found"

    # v3 orchestrator writes `sections`; legacy v2 wrote `passes`. Route on the schema present.
    if state.get("sections") and not state.get("passes"):
        v3 = _v3_stats(state)
        if v3["n_sections"] == 0:
            return f"  [skip] {run_name}: no sections in state.json"
        if format == "json":
            return json.dumps({"run": run_name, **v3}, indent=2, ensure_ascii=False)
        return _format_v3(v3, run_name, state.get("topic", "?"))

    stats = compute_stats(state)
    if stats["completed_sections"] == 0:
        return f"  [skip] {run_name}: no completed sections"

    if format == "text":
        return format_text(stats, run_name, model, run_dir)
    elif format == "markdown":
        return format_markdown(stats, run_name, model, run_dir)
    elif format == "json":
        return format_json(stats, run_name, model)
    return format_text(stats, run_name, model, run_dir)


def list_runs(base: Path) -> list:
    runs = []
    runs_dir = base / "runs"
    if runs_dir.exists():
        for d in sorted(runs_dir.iterdir()):
            if d.is_dir() and (d / "state.json").exists():
                runs.append(d)
    baselines = base / "baselines"
    if baselines.exists():
        for d in sorted(baselines.iterdir()):
            if d.is_dir() and (d / "state.json").exists():
                runs.append(d)
    return runs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agentic Deep Research Report Generator")
    parser.add_argument("path", nargs="?", default="output",
                        help="Path to run dir or output root")
    parser.add_argument("--format", "-f", choices=["text", "markdown", "json"], default="text")
    parser.add_argument("--all", action="store_true", help="Report all runs")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all runs side-by-side")
    args = parser.parse_args()

    base = Path(args.path)
    if args.all or args.compare:
        runs = list_runs(base)
        if not runs:
            print("No runs with state.json found.")
            return
        print(f"Found {len(runs)} runs:\n")
        for r in runs:
            print(f"  {r.name}")
        print()

        if args.compare:
            rows = []
            for run_dir in runs:
                state = load_state(run_dir)
                if not state:
                    continue
                stats = compute_stats(state)
                rows.append({
                    "run": run_dir.name,
                    "avg_g": stats["avg_grounding"],
                    "min_g": stats["min_grounding"],
                    "pass%": stats["pass_rate"],
                    "n": stats["completed_sections"],
                    "wc": stats["avg_wc"],
                })

            print(f"{'Run':<30} {'Avg g':>8} {'Min g':>8} {'Pass%':>8} {'N':>5} {'Avg wc':>8}")
            print("-" * 75)
            for r in sorted(rows, key=lambda x: x["avg_g"], reverse=True):
                print(f"{r['run']:<30} {r['avg_g']:>8.3f} {r['min_g']:>8.3f} "
                      f"{r['pass%']*100:>7.1f}% {r['n']:>5} {r['wc']:>8.0f}")
        return

    # Single run
    if base.is_file():
        base = base.parent
    output = report_run(base, args.format)
    print(output)


if __name__ == "__main__":
    main()
