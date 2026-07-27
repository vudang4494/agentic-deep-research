#!/usr/bin/env python3
"""Test notes.select_diverse — MMR evidence selection (Carbonell & Goldstein, 1998).

Standalone (no pytest). From repo root: python3 eval/test_mmr_diversity.py  (exit != 0 on failure)

Embeddings are STUBBED with deterministic hand-built vectors, so the test asserts the ALGORITHM
(does it trade relevance against redundancy, does it protect canonicals, does it fail open) rather
than the behaviour of bge-m3. No Ollama needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research.notes as N  # noqa: E402
from research.types import Source  # noqa: E402

_fail = 0


def check(name, cond, detail=""):
    global _fail
    if not cond:
        _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not cond else ""))


def mk(sid, title, excerpt="", rerank=None):
    s = Source(id=sid, title=title, url=f"https://example.org/{sid}", excerpt=excerpt, provider="arxiv")
    if rerank is not None:
        s.rerank_score = rerank
    return s


def with_stub_embed(vec_map, fn):
    """Run fn() with notes.embed stubbed to return vectors keyed by the '<title>. <excerpt>' text."""
    orig = N.embed
    def stub(texts, model=None):
        return [vec_map.get(t, [0.0, 0.0, 0.0]) for t in texts]
    N.embed = stub
    try:
        return fn()
    finally:
        N.embed = orig


def test_picks_diverse_over_near_duplicate():
    """Three near-identical high-relevance sources + one distinct: MMR must reach for the
    distinct facet instead of filling the set with restatements."""
    q = "policy optimization"
    dupes = [mk(f"d{i}", f"Dup {i}", "same point restated", rerank=0.90 + i * 0.001) for i in range(3)]
    other = mk("x1", "Other", "a different facet entirely", rerank=0.60)
    srcs = dupes + [other]
    vecs = {q: [1.0, 0.0, 0.0]}
    for d in dupes:
        vecs[f"{d.title}. {d.excerpt}"] = [1.0, 0.02, 0.0]      # mutually near-identical
    vecs[f"{other.title}. {other.excerpt}"] = [0.0, 1.0, 0.0]   # orthogonal

    out = with_stub_embed(vecs, lambda: N.select_diverse(srcs, q, top_k=2))
    ids = [s.id for s in out]
    check("returns exactly top_k", len(out) == 2, str(ids))
    check("keeps the strongest source", "d2" in ids or "d1" in ids or "d0" in ids, str(ids))
    check("reaches for the DISTINCT facet over a near-duplicate", "x1" in ids, str(ids))


def test_pure_relevance_would_have_taken_two_dupes():
    """Guard the premise: with lambda=1 (relevance only, i.e. today's behaviour) the same input
    yields two near-duplicates -- proving the diversity term is what changes the outcome."""
    q = "policy optimization"
    dupes = [mk(f"d{i}", f"Dup {i}", "same point restated", rerank=0.90 + i * 0.001) for i in range(3)]
    other = mk("x1", "Other", "a different facet entirely", rerank=0.60)
    srcs = dupes + [other]
    vecs = {q: [1.0, 0.0, 0.0]}
    for d in dupes:
        vecs[f"{d.title}. {d.excerpt}"] = [1.0, 0.02, 0.0]
    vecs[f"{other.title}. {other.excerpt}"] = [0.0, 1.0, 0.0]

    out = with_stub_embed(vecs, lambda: N.select_diverse(srcs, q, top_k=2, lambda_=1.0))
    ids = [s.id for s in out]
    check("lambda=1 (relevance-only) fills with duplicates", "x1" not in ids, str(ids))


def test_canonical_is_never_evicted():
    """A canonical paper with LOW relevance must survive: guardrail 5 (protected, never penalised)."""
    q = "topic"
    canon = mk("arxiv:1706.03762", "Canonical", "low similarity to the query", rerank=0.01)
    strong = [mk(f"s{i}", f"Strong {i}", "highly relevant", rerank=0.95) for i in range(4)]
    vecs = {q: [1.0, 0.0, 0.0], f"{canon.title}. {canon.excerpt}": [0.0, 0.0, 1.0]}
    for s in strong:
        vecs[f"{s.title}. {s.excerpt}"] = [1.0, 0.01, 0.0]

    out = with_stub_embed(vecs, lambda: N.select_diverse(
        [canon] + strong, q, top_k=2, protected_ids=["arxiv:1706.03762"]))
    check("canonical kept despite lowest relevance", "arxiv:1706.03762" in [s.id for s in out],
          str([s.id for s in out]))


def test_no_op_when_pool_not_larger_than_k():
    srcs = [mk("a", "A"), mk("b", "B")]
    out = N.select_diverse(srcs, "q", top_k=8)   # must not even embed
    check("pool <= top_k returned untouched", out == srcs)


def test_fails_open_when_embedding_unavailable():
    srcs = [mk(f"s{i}", f"S{i}", "x", rerank=0.5) for i in range(5)]
    out = with_stub_embed({}, lambda: N.select_diverse(srcs, "q", top_k=3))
    # stub returns constant zero vectors of the wrong count? -> it returns right count, all zeros,
    # so MMR still runs; assert it degrades gracefully rather than crashing or dropping below k.
    check("degenerate vectors -> still returns top_k, no crash", len(out) == 3, str(len(out)))

    orig = N.embed
    N.embed = lambda texts, model=None: []      # hard embed failure
    try:
        out2 = N.select_diverse(srcs, "q", top_k=3)
    finally:
        N.embed = orig
    check("embed failure -> preserves rerank order, truncated", [s.id for s in out2] == ["s0", "s1", "s2"],
          str([s.id for s in out2]))


def test_deterministic():
    q = "q"
    srcs = [mk(f"s{i}", f"S{i}", f"body {i}", rerank=0.5 + i * 0.01) for i in range(6)]
    vecs = {q: [1.0, 0.0, 0.0]}
    for i, s in enumerate(srcs):
        vecs[f"{s.title}. {s.excerpt}"] = [1.0 - i * 0.1, i * 0.1, 0.0]
    a = with_stub_embed(vecs, lambda: [s.id for s in N.select_diverse(srcs, q, top_k=3)])
    b = with_stub_embed(vecs, lambda: [s.id for s in N.select_diverse(srcs, q, top_k=3)])
    check("same input -> same selection", a == b, f"{a} vs {b}")


if __name__ == "__main__":
    print("test_mmr_diversity:")
    for fn in (test_picks_diverse_over_near_duplicate,
               test_pure_relevance_would_have_taken_two_dupes,
               test_canonical_is_never_evicted,
               test_no_op_when_pool_not_larger_than_k,
               test_fails_open_when_embedding_unavailable,
               test_deterministic):
        print(f"\n{fn.__name__}:")
        fn()
    print()
    if _fail:
        print(f"RESULT: {_fail} check(s) FAILED")
        sys.exit(1)
    print("RESULT: all checks PASSED")
