#!/usr/bin/env python3
"""Standalone test for research/embeddings.embed chunking.

Ollama's /api/embed rejects a request by ITEM COUNT (measured: 128 ok, 192 fails; payload size
is irrelevant -- 586 KB in 20 items succeeds). `embed()` returns [] on failure and every caller
reads [] as "embeddings unavailable, degrade gracefully", so an over-sized batch did not raise:
it silently switched off whatever the embedding was for. That is how a 35-chapter outline
shipped with `relate/dedup skipped` -- the cross-chapter near-duplicate pass disabled itself
precisely because the book was large.

So the invariants under test are about the CONTRACT, not the math: never return a partial list,
never reorder, never exceed the chunk size. `_embed_batch` is stubbed, so no Ollama is needed.

Run from repo root:  python3 eval/test_embed_batching.py   (exit != 0 on any failure)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import research.embeddings as E  # noqa: E402

_fail = 0


def check(name, cond, detail=""):
    global _fail
    if not cond:
        _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail!r}" if detail and not cond else ""))


def stub(fail_on=None, short_on=None, fail_once=None):
    """Record chunk sizes; optionally make the Nth CHUNK misbehave.

    The chunk is identified by its CONTENT ("t<i>" -> i // _MAX_BATCH), not by the call
    counter -- a retry re-sends the same chunk, so a counter-keyed stub would let the retry
    land on a different ordinal and silently mask a real all-or-nothing violation.
    Vector = [global index] so ordering is verifiable end to end.
    """
    calls = {"sizes": [], "n": 0, "raised": 0}

    def _fn(client, texts, model):
        calls["n"] += 1
        calls["sizes"].append(len(texts))
        first = int(texts[0][1:])                 # "t137" -> 137
        idx = first // E._MAX_BATCH               # stable across retries of the same chunk
        if fail_once is not None and idx == fail_once and calls["raised"] == 0:
            calls["raised"] += 1
            raise RuntimeError("transient 500")
        if fail_on is not None and idx == fail_on:
            raise RuntimeError("hard failure")
        if short_on is not None and idx == short_on:
            return [[0.0]] * (len(texts) - 1)      # server dropped one
        return [[float(first + k)] for k in range(len(texts))]

    return _fn, calls


def run(n, **kw):
    fn, calls = stub(**kw)
    orig = E._embed_batch
    E._embed_batch = fn
    try:
        return E.embed([f"t{i}" for i in range(n)]), calls
    finally:
        E._embed_batch = orig


def test_chunks_never_exceed_the_limit():
    out, calls = run(322)
    check("all 322 vectors returned", len(out) == 322, len(out))
    check("no chunk exceeds _MAX_BATCH", max(calls["sizes"]) <= E._MAX_BATCH, calls["sizes"])
    check("chunk count is ceil(n/limit)",
          calls["n"] == -(-322 // E._MAX_BATCH), calls["n"])


def test_order_is_preserved_across_chunks():
    out, _ = run(200)
    check("vectors come back in input order",
          [v[0] for v in out] == [float(i) for i in range(200)], out[:3])


def test_small_input_is_a_single_call():
    out, calls = run(5)
    check("one call for a small list", calls["n"] == 1 and len(out) == 5, calls["sizes"])


def test_hard_failure_returns_empty_not_partial():
    """A short list would pass a caller's truthiness check and mis-align vectors to inputs."""
    out, _ = run(200, fail_on=1)
    check("mid-batch failure -> [] (never partial)", out == [], len(out))


def test_short_chunk_returns_empty():
    out, _ = run(200, short_on=1)
    check("server returning fewer vectors than inputs -> []", out == [], len(out))


def test_transient_failure_is_retried_once():
    out, calls = run(128, fail_once=0)
    check("one retry recovers a transient error", len(out) == 128, len(out))
    check("retry cost is one extra call", calls["n"] == 3, calls["n"])


def test_empty_input():
    fn, _ = stub()
    orig, E._embed_batch = E._embed_batch, fn
    try:
        check("empty input returns [] without calling the server", E.embed([]) == [])
    finally:
        E._embed_batch = orig


def test_limit_is_below_the_measured_break_point():
    check("_MAX_BATCH keeps a margin under the observed 192-item failure",
          E._MAX_BATCH <= 128, E._MAX_BATCH)


if __name__ == "__main__":
    print("embed batching -- chunk size, ordering, all-or-nothing contract")
    for f in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        print(f"\n{f.__name__}:")
        f()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
