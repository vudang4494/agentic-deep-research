"""Explanatory-depth signal: does a section TEACH, or does it only assert?

Every live gate is defensive -- P0a asks "is the evidence on-domain", G2 "does each [N] support its
claim", G4 "is the prose on-topic". None of them asks whether the reader could actually LEARN the
mechanism, so that axis is unmeasured and drifts to the writer's default register: correct,
well-cited, and shallow.

This measures it deterministically (no model, no network, so it costs nothing and never varies).
It is ADVISORY on purpose -- the same discipline HHEM grounding earned: measure across real runs
first, calibrate, and only then consider a gate. Do NOT wire it into `gate_ok` before there is a
distribution to calibrate against.

The signals are structural traces of explanation, not of quality:
  derivation  -- display math the prose walks through
  symbols     -- "where x denotes ...", i.e. notation actually defined rather than dropped
  steps       -- an ordered procedure the reader can follow
  code        -- pseudocode/implementation
  example     -- a concrete instance, not just the general claim
  causal      -- because / therefore / which means: reasoning connectives, not just assertions
"""
import re

_DISPLAY_MATH = re.compile(r"\$\$.+?\$\$", re.DOTALL)
_CODE_FENCE = re.compile(r"```[\s\S]*?```")
_SYMBOL_DEF = re.compile(
    r"\b(?:where|here|with|let)\b[^.]{0,80}?\b(?:is|are|denotes?|represents?|be|defined as)\b", re.I)
# `\d+\.` must NOT be followed by \b -- after "." the next char is a space, and neither is a
# word char, so the boundary never matches and every numbered step was missed.
_STEP = re.compile(r"(?m)^\s*(?:\d+[.)]\s|Step\s+\d+\b|(?:First|Second|Third|Next|Finally)\b)", re.I)
_EXAMPLE = re.compile(r"\b(?:for example|for instance|consider (?:a|an|the)|suppose|e\.g\.)\b", re.I)
_CAUSAL = re.compile(
    r"\b(?:because|therefore|which means|this implies|as a result|intuitively|the reason|"
    r"consequently|so that|in other words)\b", re.I)

# Weights: a derivation the prose defines symbols for teaches more than a stray connective.
_WEIGHTS = {"derivation": 0.25, "symbols": 0.20, "steps": 0.20,
            "code": 0.10, "example": 0.10, "causal": 0.15}


def explanation_depth(content: str) -> dict:
    """Return {signal: bool/count} plus a 0..1 `score`. Deterministic; advisory only."""
    text = content or ""
    prose = _CODE_FENCE.sub(" ", text)
    counts = {
        "derivation": len(_DISPLAY_MATH.findall(text)),
        "symbols": len(_SYMBOL_DEF.findall(prose)),
        "steps": len(_STEP.findall(prose)),
        "code": len(_CODE_FENCE.findall(text)),
        "example": len(_EXAMPLE.findall(prose)),
        "causal": len(_CAUSAL.findall(prose)),
    }
    # Saturating credit: the second worked example teaches far less than the first, so cap each
    # signal's contribution instead of rewarding a section that spams one device.
    caps = {"derivation": 2, "symbols": 3, "steps": 4, "code": 1, "example": 2, "causal": 4}
    score = sum(_WEIGHTS[k] * min(counts[k], caps[k]) / caps[k] for k in _WEIGHTS)
    return {**counts, "score": round(score, 3)}
