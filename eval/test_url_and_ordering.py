#!/usr/bin/env python3
"""Standalone tests for two silent defects found by reading the printed book.

1. `_canonical_url` must unwrap search-engine redirects. A DuckDuckGo href reaches the
   bibliography verbatim, so a reader clicking a citation lands on DuckDuckGo instead of the
   paper -- one observed case wrapped a real arxiv.org/abs URL. This breaks the single property
   the book sells: a citation you can check.
2. `_section_sort_key` must order "10.1" after "2.1". Plain `sorted()` is lexicographic, and
   the writer reads only `prior_sections[-2:]` for continuation context, so from chapter 10
   onward it was being handed chapter 9's material as "what came just before".

Both are pure functions: no model, no network.
Run from repo root:  python3 eval/test_url_and_ordering.py   (exit != 0 on any failure)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.search import _canonical_url, _url_id  # noqa: E402
from pipeline.deep_research_v3 import _section_sort_key  # noqa: E402

_fail = 0


def check(name, cond, detail=""):
    global _fail
    if not cond:
        _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail!r}" if detail and not cond else ""))


# ------------------------------------------------------------------ redirect unwrapping
def test_ddg_wrapper_unwrapped():
    # exact shape found in the shipped book (note `&amp;` survived the HTML scrape)
    wrapped = ("https://duckduckgo.com/l?uddg=https%3A%2F%2Farxiv.org%2Fabs%2F2503.01807"
               "&amp%3Brut=6c6c0a68a951fa226a94bc6b6e04288f")
    check("wrapped arxiv resolves to the paper",
          _canonical_url(wrapped) == "https://arxiv.org/abs/2503.01807", _canonical_url(wrapped))


def test_protocol_relative_wrapper():
    w = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fapxml.com%2Fcourses%2Frlhf&amp;rut=abc"
    check("protocol-relative wrapper unwrapped",
          _canonical_url(w) == "https://apxml.com/courses/rlhf", _canonical_url(w))


def test_wrapped_and_bare_share_one_id():
    """Dedup identity must collapse too, or the same paper counts twice for P0c seen-penalty."""
    a = _url_id("https://duckduckgo.com/l?uddg=https%3A%2F%2Farxiv.org%2Fabs%2F2503.01807&amp%3Brut=x")
    b = _url_id("https://arxiv.org/abs/2503.01807")
    check("wrapped and bare arxiv share one id", a == b, f"{a} vs {b}")


def test_non_wrapper_ddg_url_untouched():
    """A real DuckDuckGo page is not a redirect -- only `uddg` makes it one."""
    u = "https://duckduckgo.com/?q=rlhf"
    check("ddg search page is not unwrapped", "duckduckgo.com" in _canonical_url(u), _canonical_url(u))


def test_non_http_target_rejected():
    """A wrapper whose target is not http(s) must not be trusted."""
    u = "https://duckduckgo.com/l?uddg=javascript%3Aalert(1)"
    out = _canonical_url(u)
    check("non-http redirect target rejected", not out.startswith("javascript"), out)


def test_ordinary_urls_unaffected():
    for src, want in [
        ("https://arxiv.org/abs/1706.03762v7", "https://arxiv.org/abs/1706.03762"),
        ("https://en.wikipedia.org/wiki/RLHF", "https://en.wikipedia.org/wiki/RLHF"),
    ]:
        check(f"unchanged: {src[:44]}", _canonical_url(src) == want, _canonical_url(src))
    check("empty input safe", _canonical_url("") == "")
    check("None-ish input safe", _canonical_url(None) is None)


# ------------------------------------------------------------------ section ordering
def test_chapter_ten_sorts_after_chapter_two():
    keys = [f"{c}.{s}" for c in range(1, 12) for s in range(1, 9)]
    srt = sorted(keys, key=_section_sort_key)
    check("the two most recent sections are from chapter 11, not 9",
          srt[-2:] == ["11.7", "11.8"], srt[-2:])
    check("'2.1' precedes '10.1'", srt.index("2.1") < srt.index("10.1"))


def test_cross_ref_hint_window_is_recent():
    keys = [f"{c}.{s}" for c in range(1, 12) for s in range(1, 9)]
    srt = sorted(keys, key=_section_sort_key)
    check("cross-ref hint offers the previous chapter",
          all(k.startswith("11.") for k in srt[-5:]), srt[-5:])


def test_malformed_keys_do_not_raise():
    out = sorted(["2.1", "abc", "10.1", "", "3"], key=_section_sort_key)
    check("non-numeric keys sort last instead of raising",
          out[:3] == ["2.1", "3", "10.1"], out)


if __name__ == "__main__":
    print("URL redirect unwrapping + numeric section ordering")
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        print(f"\n{fn.__name__}:")
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
