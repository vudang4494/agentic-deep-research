"""Unit/acceptance test for research.outline_from_research.enforce_outline_structure
(deterministic anti-matrix / anti-redundancy outline enforcement, Guardrail 3+4).

Asserts the invariants that make the enforcement SAFE to run on EVERY outline path:
  1. A '{base}: {aspect}' suffix-matrix (>3 members) is collapsed to the cap, and the
     audit's `aspect_matrix` issue is cleared afterwards (discrimination: matrix caught).
  2. A CLEAN outline is left untouched -- no false-positive section removal.
  3. Cross-chapter near-duplicate section titles are dropped.
  4. Coverage is preserved: dropped aspects' `must_cover_terms` are merged, not lost.
  5. Section numbers stay contiguous (1..N) per chapter after removals.

Real `assert` statements (fail loud). Run: python3 eval/test_outline_enforce.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.outline_from_research import (
    OutlineProfile, enforce_outline_structure, audit_outline,
    _aspect_matrix_families, _ASPECT_MATRIX_CAP,
)

_ASPECTS = ["Core Mechanisms", "Design and Trade-offs", "Practical Methods",
            "Evaluation", "Failure Modes and Limitations", "Recent Advances",
            "Case Studies", "Open Problems"]


def _sec(n, title, terms=None):
    return {"n": n, "t": title, "pr": f"Write on {title}.",
            "must_cover_terms": terms if terms is not None else [title]}


def _outline(chapters):
    return OutlineProfile(title="Test Book", chapters=chapters, evidence_map=[])


def test_matrix_collapsed_and_audit_cleared():
    base = "Policy Optimization Strategies: A Comparative Analysis of PPO and DPO"
    secs = [_sec(i + 1, f"{base}: {a}", terms=[f"term_{i}"]) for i, a in enumerate(_ASPECTS)]
    o = _outline([{"n": 1, "t": "Optimization", "sections": secs}])

    before = audit_outline({"chapters": o.chapters, "title": o.title}, None, [])
    assert "aspect_matrix" in before["issues"], "8x base:aspect family must be flagged"

    log = enforce_outline_structure(o)
    kept = o.chapters[0]["sections"]
    assert len(kept) == _ASPECT_MATRIX_CAP, f"family capped to {_ASPECT_MATRIX_CAP}, got {len(kept)}"
    assert log["aspect_matrix_removed"] == len(_ASPECTS) - _ASPECT_MATRIX_CAP

    after = audit_outline({"chapters": o.chapters, "title": o.title}, None, [])
    assert "aspect_matrix" not in after["issues"], "collapse must clear the aspect_matrix issue"
    assert _aspect_matrix_families(o.chapters) == [], "no matrix family may remain"


def test_clean_outline_untouched():
    # Distinct, groundable titles -- must be a no-op (no false-positive removal).
    secs = [
        _sec(1, "The Bradley-Terry Preference Model"),
        _sec(2, "Reward Model Training Objectives"),
        _sec(3, "PPO for Policy Optimization"),
        _sec(4, "KL Regularization and Reference Policies"),
    ]
    o = _outline([{"n": 1, "t": "Foundations", "sections": secs}])
    log = enforce_outline_structure(o)
    assert log["aspect_matrix_removed"] == 0, "clean outline must not lose matrix sections"
    assert log["cross_chapter_removed"] == 0, "clean outline must not lose cross-chapter sections"
    assert len(o.chapters[0]["sections"]) == 4, "clean outline section count must be unchanged"


def test_cross_chapter_near_dup_dropped():
    dup_title = "Policy Optimization Strategies: A Comparative Analysis of PPO and DPO"
    o = _outline([
        {"n": 1, "t": "Methods", "sections": [_sec(1, dup_title), _sec(2, "Reward Modeling Basics")]},
        {"n": 2, "t": "Applications", "sections": [_sec(1, dup_title), _sec(2, "Deployment Patterns")]},
    ])
    n0 = sum(len(c["sections"]) for c in o.chapters)
    log = enforce_outline_structure(o)
    n1 = sum(len(c["sections"]) for c in o.chapters)
    assert log["cross_chapter_removed"] >= 1, "identical title across chapters must be dropped once"
    assert n1 == n0 - 1, "exactly one cross-chapter duplicate removed"
    # the first occurrence is kept
    assert any(s["t"] == dup_title for s in o.chapters[0]["sections"])
    assert all(s["t"] != dup_title for s in o.chapters[1]["sections"])


def test_coverage_merged_not_lost():
    base = "Advanced Optimization Techniques: Enhancing Sample Efficiency in RLHF Loops"
    secs = [_sec(i + 1, f"{base}: {a}", terms=[f"cover_{i}"]) for i, a in enumerate(_ASPECTS)]
    o = _outline([{"n": 1, "t": "Optimization", "sections": secs}])
    enforce_outline_structure(o)
    kept = o.chapters[0]["sections"]
    all_terms = {t for s in kept for t in s.get("must_cover_terms", [])}
    # surplus aspects' coverage terms (cover_3..cover_7) must survive on a kept section
    for i in range(_ASPECT_MATRIX_CAP, len(_ASPECTS)):
        assert f"cover_{i}" in all_terms, f"coverage term cover_{i} was lost, not merged"


def test_sections_renumbered_contiguously():
    base = "Controlling Drift: The Role of KL Divergence in Policy Regularization"
    secs = [_sec(i + 1, f"{base}: {a}") for i, a in enumerate(_ASPECTS)]
    o = _outline([{"n": 1, "t": "Regularization", "sections": secs}])
    enforce_outline_structure(o)
    nums = [s["n"] for s in o.chapters[0]["sections"]]
    assert nums == list(range(1, len(nums) + 1)), f"section numbers must be contiguous, got {nums}"


if __name__ == "__main__":
    tests = [
        test_matrix_collapsed_and_audit_cleared,
        test_clean_outline_untouched,
        test_cross_chapter_near_dup_dropped,
        test_coverage_merged_not_lost,
        test_sections_renumbered_contiguously,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
