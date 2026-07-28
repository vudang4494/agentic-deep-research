#!/usr/bin/env python3
"""Standalone test for research/mdfix.py (Stage-F markdown structural hygiene).

These fixes are formatting-only, so the invariants under test are conservatism ones: no prose
word may change, code fences must survive byte-identical, and running twice must equal running
once (the renderer applies the same module to books the assembler already cleaned).

Run from repo root:  python3 eval/test_mdfix.py   (exit != 0 on any failure)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.mdfix import (  # noqa: E402
    fix_double_citations, fix_glued_lists, fix_orphan_math_citations,
    fix_reference_numbering, normalize_markdown,
)

_fail = 0


def check(name, cond, detail=""):
    global _fail
    if not cond:
        _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail!r}" if detail and not cond else ""))


def words(text):
    """Prose words with markdown punctuation stripped -- used to prove nothing was rewritten."""
    return re.findall(r"[A-Za-z]+", text)


# --------------------------------------------------------------- glued lists (defect B)
def test_glued_list_gets_blank_line():
    # verbatim shape from a real run: the PPO loop printed as one run-on paragraph
    text = ("The PPO algorithm operates through an iterative loop:\n"
            "1. **Sampling:** Generate responses from the current policy.\n"
            "2. **Scoring:** Evaluate these responses using the Reward Model.\n")
    out, n = fix_glued_lists(text)
    check("blank line inserted before glued list", n == 1, out)
    check("list now parses (blank line precedes marker)",
          "iterative loop:\n\n1. **Sampling:**" in out, out)
    check("no word changed", words(out) == words(text), out)


def test_separated_list_untouched():
    text = ("Key evaluation strategies include:\n\n"
            "* **Human Preference Accuracy:** side-by-side comparisons.\n"
            "* **Safety Benchmarks:** harmful content testing.\n")
    out, n = fix_glued_lists(text)
    check("already-correct list is byte-identical", out == text and n == 0, out)


def test_lazy_continuation_not_split():
    """A wrapped line inside a list item is non-blank and not a marker -- splitting there
    would cut one list into two. The in-list flag must suppress the insert."""
    text = ("- first item that wraps onto\n"
            "  a continuation line\n"
            "- second item\n")
    out, n = fix_glued_lists(text)
    check("continuation line does not trigger a split", out == text and n == 0, out)


def test_year_sentence_not_promoted():
    text = ("Preference optimization matured quickly.\n"
            "2024. was the year DPO overtook PPO in published ablations.\n")
    out, n = fix_glued_lists(text)
    check("`2024.` sentence is not treated as a list", out == text and n == 0, out)


def test_heading_before_list_untouched():
    text = "### Evaluation Dimensions\n- reward accuracy\n- consistency\n"
    out, n = fix_glued_lists(text)
    check("list right after a heading needs no insert", out == text and n == 0, out)


# ------------------------------------------------------------ double citations (defect C)
def test_double_citation_collapsed():
    text = "RLHF bridges this gap [[1]]. Reward modeling follows [[3]], then PPO [[1, 2]]."
    out, n = fix_double_citations(text)
    check("three doubled citations collapsed", n == 3, f"n={n}")
    check("single brackets remain", "[1]." in out and "[3]," in out and "[1, 2]" in out, out)
    check("no doubled bracket survives", "[[" not in out, out)


def test_non_numeric_double_bracket_kept():
    text = "The notation [[matrix]] is defined in the appendix."
    out, n = fix_double_citations(text)
    check("non-numeric [[...]] is untouched", out == text and n == 0, out)


# --------------------------------------------------- orphan math citations (defect D)
def test_orphan_citation_moved_from_oneline_math():
    text = ("the total reward is decomposed into extrinsic and intrinsic components:\n"
            "$$ r_{total} = r_{ext} + \\beta r_{int} $$ [1]\n"
            "\nWhere r_ext is the environment reward.\n")
    out, n = fix_orphan_math_citations(text)
    check("one orphan citation relocated", n == 1, out)
    check("citation now sits on the prose line, before the colon",
          "intrinsic components [1]:" in out, out)
    check("math line ends at $$", "$$ [1]" not in out and "\\beta r_{int} $$" in out, out)


def test_orphan_citation_moved_from_multiline_math():
    text = ("The generalization error bound is given by:\n"
            "$$\n"
            "gen(\\mu) \\leq \\sqrt{2\\sigma^2/n}\n"
            "$$ [2]\n")
    out, n = fix_orphan_math_citations(text)
    check("multi-line block: citation relocated", n == 1, out)
    check("anchor is the prose BEFORE the block, not the math body",
          "given by [2]:" in out, out)
    check("closing delimiter left bare", out.rstrip().endswith("$$"), out)


def test_orphan_citation_without_prose_is_left_alone():
    text = "$$ x = y $$ [1]\n"
    out, n = fix_orphan_math_citations(text)
    check("no prose to anchor to -> unchanged (fail-safe)", out == text and n == 0, out)


# ------------------------------------------------------ reference numbering (defect A)
def test_gapped_reference_list_migrated():
    text = ("**References**\n\n"
            "1. Next Token Prediction — Liang Chen (2024). <https://arxiv.org/abs/2412.18619>\n"
            "3. DPO vs PPO: How To Align LLM. <https://labellerr.com/blog/dpo-vs-ppo>\n")
    out, n = fix_reference_numbering(text)
    check("both entries migrated", n == 2, out)
    check("gap preserved as literal markers",
          "- [1] Next Token" in out and "- [3] DPO vs PPO" in out, out)
    check("no ordered-list marker left for markdown to renumber",
          not re.search(r"(?m)^\d+\.\s", out), out)


def test_reference_migration_is_noop_on_new_format():
    text = "**References**\n\n- [1] Already migrated. <https://example.org>\n"
    out, n = fix_reference_numbering(text)
    check("already-migrated block untouched", out == text and n == 0, out)


def test_numbered_list_outside_reference_block_untouched():
    text = ("The loop has two steps:\n\n"
            "1. Sample from the policy.\n"
            "2. Score with the reward model.\n\n"
            "**References**\n\n"
            "1. A Survey of DPO. <https://arxiv.org/abs/2503.11701>\n")
    out, n = fix_reference_numbering(text)
    check("only the reference block is migrated", n == 1, out)
    check("body numbered list stays a list",
          "1. Sample from the policy." in out and "- [1] A Survey of DPO." in out, out)


# ------------------------------------------------------------------ whole-module invariants
FENCE = """Here is the implementation:
```python
# steps below must NOT be reflowed
1. not a list, it is a comment
citations = "[[1]]"
```
Text after the fence."""


def test_code_fence_survives_verbatim():
    out, counts = normalize_markdown(FENCE)
    check("fence content byte-identical (no fixes applied inside)",
          '1. not a list, it is a comment' in out and 'citations = "[[1]]"' in out, out)
    check("no fix fired on fenced content", sum(counts.values()) == 0, str(counts))


DIRTY = ("RLHF layers human judgment onto a base model [[1]]. The objective is:\n"
         "$$ \\mathcal{L}_{RM} = -\\log \\sigma(r_w - r_l) $$ [3]\n"
         "The pipeline has three stages:\n"
         "1. Preference collection.\n"
         "2. Reward modeling.\n"
         "3. Policy optimization.\n"
         "\n**References**\n\n"
         "1. InstructGPT. <https://arxiv.org/abs/2203.02155>\n"
         "3. DPO. <https://arxiv.org/abs/2305.18290>\n")


def test_all_fixes_compose():
    out, counts = normalize_markdown(DIRTY)
    check("every defect class fired once or more",
          all(counts[k] >= 1 for k in
              ("double_citations", "orphan_math_citations", "reference_numbering", "glued_lists")),
          str(counts))
    check("prose words unchanged by the whole pass", words(out) == words(DIRTY), out)


def test_idempotent():
    once, c1 = normalize_markdown(DIRTY)
    twice, c2 = normalize_markdown(once)
    check("second pass is a no-op (renderer may re-apply)", twice == once, twice)
    check("second pass reports zero fixes", sum(c2.values()) == 0, str(c2))


def test_empty_and_clean_input():
    check("empty input safe", normalize_markdown("")[0] == "")
    clean = "A plain paragraph with a citation [1].\n\n- one\n- two\n"
    out, counts = normalize_markdown(clean)
    check("clean markdown is byte-identical", out == clean and sum(counts.values()) == 0, out)


if __name__ == "__main__":
    print("mdfix -- Stage-F markdown structural hygiene")
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        print(f"\n{fn.__name__}:")
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
