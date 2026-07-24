"""Shared research-layer configuration constants.

Tách constants ra khỏi package root để tránh circular import khi các submodule
cần model/knob defaults trong lúc `research.__init__` vẫn đang khởi tạo.
"""

# Provider order matters: cheap+reliable first (arxiv, wikipedia), then web sources.
# `brave` is a FREE (2000 q/mo) substitute for tavily -- auto-skipped by
# available_providers() unless BRAVE_API_KEY is set, so listing it is a safe no-op
# until a key exists (get one at brave.com/search/api/).
PROVIDERS_DEFAULT = ("arxiv", "wikipedia", "tavily", "brave", "ddg")

# ---- v1 Retrieval Knobs ----
TOP_K_DEFAULT = 8
PRIMARY_FLOOR = 3
FULL_TEXT_TOP_N = 2
FULL_TEXT_MAX_WORDS = 350

# ---- v2 CRAG Knobs (CRAG tier) ----
GROUND_UPPER = 0.80
GROUND_LOWER = 0.40

# Gate thresholds live NEXT TO the logic that reads them, not here (single source, no drift):
#   TOP_K_RETRIEVE / TOP_K_FINAL / RELEVANCE_FLOOR  -> research/rerank.py
#   AUTO_SUPPORT_COS / AUTO_UNRELATED_COS           -> research/verify.py
#   HHEM_SUPPORT                                    -> research/faithfulness.py

# ---- Model Defaults ----
QUERY_GEN_MODEL = "gemma4:e4b"
JUDGE_MODEL = "gemma4:e4b"
DISCOVERY_MODEL = "gemma4:e4b"
OUTLINE_MODEL = "gemma4:e4b"
WRITER_MODEL = "batiai/qwen3.6-35b:iq3"
EMBED_MODEL = "bge-m3:latest"  # #3 unify with verify-side (was nomic: asymmetric, needs search_query/document prefix the code never passed)

# Iterative-research thresholds
MIN_GROUNDING = 0.55
MAX_RESEARCH_ROUNDS = 2

__all__ = [
    "PROVIDERS_DEFAULT",
    "TOP_K_DEFAULT",
    "PRIMARY_FLOOR", "FULL_TEXT_TOP_N", "FULL_TEXT_MAX_WORDS",
    "GROUND_UPPER", "GROUND_LOWER",
    "QUERY_GEN_MODEL", "JUDGE_MODEL", "DISCOVERY_MODEL", "OUTLINE_MODEL", "WRITER_MODEL", "EMBED_MODEL",
    "MIN_GROUNDING", "MAX_RESEARCH_ROUNDS",
]
