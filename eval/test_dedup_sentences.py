#!/usr/bin/env python3
"""Standalone test for research/dedup.py (assemble-time exact-duplicate sentence remover).

Run from repo root:  python3 eval/test_dedup_sentences.py   (exit != 0 on any failure)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.dedup import drop_duplicate_sentences  # noqa: E402

_fail = 0


def check(name, cond, detail=""):
    global _fail
    if not cond:
        _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not cond else ""))


BOILER = "The reward model assigns a scalar score to each candidate response during training."


def test_removes_exact_duplicate():
    text = (
        f"Chapter two opens here. {BOILER} It grounds the next step.\n\n"
        f"A later chapter. {BOILER} And it continues with new material afterward."
    )
    out, n = drop_duplicate_sentences(text)
    check("one duplicate removed", n == 1, f"n={n}")
    check("first occurrence kept", out.count(BOILER) == 1, out)
    check("surrounding prose survives", "grounds the next step" in out and "new material afterward" in out, out)


def test_byte_identical_when_no_dup():
    text = "First distinct sentence about attention heads and their scaling.\n\nA second, entirely different paragraph."
    out, n = drop_duplicate_sentences(text)
    check("no-dup text unchanged (byte-identical)", out == text and n == 0, out)


def test_reference_lines_protected():
    text = (
        "1. Attention Is All You Need — Vaswani et al. (2017). <http://arxiv.org/abs/1706.03762>\n\n"
        "1. Attention Is All You Need — Vaswani et al. (2017). <http://arxiv.org/abs/1706.03762>"
    )
    out, n = drop_duplicate_sentences(text)
    check("identical reference lines NOT removed", n == 0 and out.count("Attention Is All You Need") == 2, out)


def test_code_fence_protected():
    block = "```\nfor i in range(n): total += reward[i]  # identical loop line\n```"
    text = f"Prose intro line one about the loop below here now.\n\n{block}\n\n{block}"
    out, n = drop_duplicate_sentences(text)
    check("code fences untouched", out.count("total += reward[i]") == 2, out)


def test_heading_protected():
    text = "## 2. Policy Optimization\n\n## 5. Policy Optimization"
    out, n = drop_duplicate_sentences(text)
    check("duplicate headings NOT removed", n == 0 and out.count("Policy Optimization") == 2, out)


def test_short_sentence_below_floor():
    text = "It works well here.\n\nDifferent lead-in text. It works well here."
    out, n = drop_duplicate_sentences(text)
    check("short (<10w) duplicate NOT removed", n == 0, f"n={n}")


def test_citation_distinct():
    s5 = "The policy gradient estimator reduces variance when a learned baseline is subtracted from returns [5]."
    s8 = "The policy gradient estimator reduces variance when a learned baseline is subtracted from returns [8]."
    text = f"Intro alpha here now. {s5}\n\nIntro beta here now. {s8}"
    out, n = drop_duplicate_sentences(text)
    check("same sentence, different [N] -> both kept", n == 0 and "[5]" in out and "[8]" in out, out)


def test_display_math_protected():
    m = "$$\\nabla_\\theta J(\\theta) = \\mathbb{E}[\\nabla_\\theta \\log \\pi_\\theta(a|s) A(s,a)]$$"
    text = f"Lead sentence one about the gradient expression below now.\n\n{m}\n\n{m}"
    out, n = drop_duplicate_sentences(text)
    check("identical display-math blocks untouched", out.count("nabla_\\theta J") == 2, out)


if __name__ == "__main__":
    for fn in (test_removes_exact_duplicate, test_byte_identical_when_no_dup,
               test_reference_lines_protected, test_code_fence_protected,
               test_heading_protected, test_short_sentence_below_floor,
               test_citation_distinct, test_display_math_protected):
        print(f"\n{fn.__name__}:")
        fn()
    print()
    if _fail:
        print(f"RESULT: {_fail} check(s) FAILED")
        sys.exit(1)
    print("RESULT: all checks PASSED")
