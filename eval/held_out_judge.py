#!/usr/bin/env python3
"""P1-5 held-out judge: de-circle the eval by cross-checking the pipeline's gemma citation
judge against an INDEPENDENT local model family.

The pipeline judges citation integrity (G2), topic (G4) and domain (P0a) all with gemma. An
eval that also trusts gemma is circular. This tool re-judges the SAME labeled probe set
(reused verbatim from bench_cite_discrimination.py -- GOOD / BAD_UNRELATED / BAD_CONTRADICT,
ground-truth known) with BOTH the pipeline judge (JUDGE_MODEL, gemma) and a held-out model of a
DIFFERENT family, then reports:

  * per-judge ACCURACY vs the a-priori ground truth (supports vs not-support),
  * inter-judge AGREEMENT % and Cohen's kappa on the gate-relevant binary decision.

High kappa + both judges tracking ground truth => gemma's verdicts are corroborated by an
independent family, so the eval is not just gemma agreeing with itself. Low kappa => the judge
choice is load-bearing and should be revisited.

Run:
    python3 eval/held_out_judge.py                      # auto-pick a non-gemma local model
    python3 eval/held_out_judge.py --held-out llama3.2  # pin the held-out model

LOCAL-only: both models run on the local Ollama daemon. Gracefully skips (exit 0) if no
independent model is available -- it is a diagnostic, never a blocking gate.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # repo root

from research import verify as V
from research.config import JUDGE_MODEL, WRITER_MODEL
from research._ollama import OLLAMA_BASE
from research.types import Source
from bench_cite_discrimination import (
    GOOD_CONTENT, GOOD_EXCERPTS, UNRELATED_EXCERPTS, CONTRADICT_EXCERPTS,
)

# Ground truth per probe variant: is each [N] a genuine support?
PROBES = [
    ("GOOD", GOOD_EXCERPTS, True),        # faithful paraphrase -> supports
    ("BAD_UNRELATED", UNRELATED_EXCERPTS, False),
    ("BAD_CONTRADICT", CONTRADICT_EXCERPTS, False),
]
_SUPPORT_VERDICTS = {"supports"}          # gate-relevant binary: supports vs everything else


def _mk_sources(excerpts):
    return [Source(id=f"test:{i}", title=f"Test source {i}", url=f"https://example.org/{i}",
                   excerpt=ex, provider="arxiv") for i, ex in enumerate(excerpts, start=1)]


def _local_models():
    import httpx
    try:
        data = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5).json()
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _pick_held_out(available):
    """Choose a local model of a DIFFERENT family than the gemma judge (and not an embed model).
    Prefer a neutral instruct model; fall back to the writer family with a caveat."""
    judge_fam = JUDGE_MODEL.split(":")[0].split("/")[-1].lower()  # 'gemma4'
    def fam(n):
        return n.split(":")[0].split("/")[-1].lower()
    embed_like = ("bge", "nomic", "embed", "rerank")
    cands = [n for n in available
             if judge_fam[:4] not in fam(n) and not any(e in n.lower() for e in embed_like)]
    if not cands:
        return None
    preferred = ("llama", "qwen3:", "phi", "mistral", "deepseek", "granite", "olmo", "command")
    for p in preferred:
        for n in cands:
            if p in n.lower() and n != WRITER_MODEL:
                return n
    non_writer = [n for n in cands if n != WRITER_MODEL]
    return non_writer[0] if non_writer else cands[0]


def _judge(content, excerpts, model):
    """Return {n: verdict} for one probe under one model."""
    res = V.verify_section(content, _mk_sources(excerpts), model=model)
    return {v["n"]: v["verdict"] for v in res["verdicts"]}


def _cohens_kappa(a, b):
    """Cohen's kappa on two aligned label lists (binary here). Returns None if degenerate."""
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    labels = set(a) | set(b)
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--held-out", default=os.environ.get("HELD_OUT_JUDGE"),
                    help="held-out model name (default: auto-pick a non-gemma local model)")
    args = ap.parse_args()

    available = _local_models()
    if not available:
        print("[held-out] Ollama not reachable / no local models -- SKIP (diagnostic only).")
        return 0
    held = args.held_out or _pick_held_out(available)
    if not held:
        print(f"[held-out] no independent (non-gemma, non-embed) model found locally.\n"
              f"           pull one and re-run, e.g.:  ollama pull llama3.2 && "
              f"python3 eval/held_out_judge.py --held-out llama3.2\n"
              f"           available: {', '.join(available) or '(none)'}")
        return 0
    if held not in available:
        print(f"[held-out] requested model '{held}' not present locally. available: {', '.join(available)}")
        return 0
    if held == WRITER_MODEL:
        print(f"[held-out] NOTE: only the writer family was available; using it as an OFFLINE "
              f"cross-check judge (not in-pipeline, so verifier!=writer still holds at runtime).")

    print("=" * 78)
    print(f"HELD-OUT JUDGE CROSS-CHECK   pipeline judge = {JUDGE_MODEL}   held-out = {held}")
    print("=" * 78)

    truth, g_bin, h_bin = [], [], []
    try:
        for label, excerpts, is_support in PROBES:
            gv = _judge(GOOD_CONTENT, excerpts, JUDGE_MODEL)
            hv = _judge(GOOD_CONTENT, excerpts, held)
            print(f"\n[{label}]  (ground truth: {'supports' if is_support else 'not-support'})")
            for n in sorted(set(gv) | set(hv)):
                g, h = gv.get(n, "?"), hv.get(n, "?")
                mark = "" if (g in _SUPPORT_VERDICTS) == (h in _SUPPORT_VERDICTS) else "  <-- disagree"
                print(f"    [{n}] gemma={g:<12} held-out={h:<12}{mark}")
                truth.append(is_support)
                g_bin.append(g in _SUPPORT_VERDICTS)
                h_bin.append(h in _SUPPORT_VERDICTS)
    except Exception as e:
        print(f"\n[held-out] judge call failed ({e}). Is Ollama up with both models?")
        return 0

    n = len(truth)
    g_acc = sum(1 for t, g in zip(truth, g_bin) if t == g) / n
    h_acc = sum(1 for t, h in zip(truth, h_bin) if t == h) / n
    agree = sum(1 for g, h in zip(g_bin, h_bin) if g == h) / n
    kappa = _cohens_kappa(g_bin, h_bin)

    print("\n" + "-" * 78)
    print(f"samples (citations judged) : {n}")
    print(f"gemma   accuracy vs truth  : {g_acc:.0%}")
    print(f"held-out accuracy vs truth : {h_acc:.0%}")
    print(f"inter-judge agreement      : {agree:.0%}")
    print(f"Cohen's kappa (support/not): {kappa:.3f}" if kappa is not None else "Cohen's kappa: n/a")
    print("-" * 78)
    _proxy = ("  NOTE: the held-out model is the WRITER family, used offline as a proxy -- it "
              "still cross-checks the gemma JUDGE (different family), but a fully third-party "
              "model would be a stronger, fully-independent check." if held == WRITER_MODEL else "")
    if kappa is None:
        verdict = "DEGENERATE (one judge gave a constant label) -- inspect above."
    elif kappa >= 0.6 and g_acc >= 0.8:
        verdict = ("CORROBORATED -- a different model family agrees substantially with gemma AND "
                   "gemma tracks ground truth. The eval is not gemma-circular." + _proxy)
    elif g_acc < 0.8:
        verdict = ("GEMMA OFF GROUND TRUTH on this probe -- the pipeline judge itself is "
                   "mis-calling labeled cases; investigate before trusting G2.")
    else:
        verdict = ("LOW AGREEMENT (kappa<0.6) -- the judge-family choice is load-bearing; a "
                   "different family disagrees. Treat single-judge G2 numbers with caution.")
    print("VERDICT:", verdict)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
