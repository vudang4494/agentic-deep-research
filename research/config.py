"""Shared research-layer configuration constants.

Tách constants ra khỏi package root để tránh circular import khi các submodule
cần model/knob defaults trong lúc `research.__init__` vẫn đang khởi tạo.

ĐỌC KỸ TRƯỚC KHI TIN MỘT HẰNG Ở ĐÂY: file này từng chứa knob của v1/v2 mà v3 KHÔNG đọc,
nên người đọc tưởng chúng điều khiển pipeline. Mỗi hằng bên dưới giờ được gắn nhãn phạm vi:

  [LIVE]        v3 (pipeline/deep_research_v3.py + research/*) thực sự đọc.
  [LEGACY-ONLY] chỉ legacy/ (deep_research v2, bench_pipeline) đọc -- KHÔNG chi phối v3.

Ngưỡng gate sống CẠNH logic đọc nó, không nằm ở đây (single source, chống drift):
  TOP_K_RETRIEVE / TOP_K_FINAL / RELEVANCE_FLOOR -> research/rerank.py
  AUTO_SUPPORT_COS / AUTO_UNRELATED_COS          -> research/verify.py
  HHEM_SUPPORT                                   -> research/faithfulness.py
  min_topic_relevance / min_cite_precision / max_rounds / dedup_cosine_max
                                                 -> chữ ký investigate_section()
"""

# [LIVE] Provider order matters: cheap+reliable first (arxiv, wikipedia), then web sources.
# `brave` is a FREE (2000 q/mo) substitute for tavily -- auto-skipped by
# available_providers() unless BRAVE_API_KEY is set, so listing it is a safe no-op
# until a key exists (get one at brave.com/search/api/).
PROVIDERS_DEFAULT = ("arxiv", "wikipedia", "tavily", "brave", "ddg")

# [LIVE] reserved arxiv/wikipedia slots in the ranked pool (read by deep_research_v3).
PRIMARY_FLOOR = 3

# [LIVE] Model defaults -- the ONLY place model names may be written (verify_all check F).
QUERY_GEN_MODEL = "gemma4:e4b"
JUDGE_MODEL = "gemma4:e4b"
DISCOVERY_MODEL = "gemma4:e4b"
OUTLINE_MODEL = "gemma4:e4b"
WRITER_MODEL = "batiai/qwen3.6-35b:iq3"
EMBED_MODEL = "bge-m3:latest"  # unified with the verify side (nomic was asymmetric: it needs
                               # search_query:/search_document: prefixes the code never passed)

# ---------------------------------------------------------------------------
# [LEGACY-ONLY] read by legacy/deep_research.py + legacy/bench_pipeline.py ONLY.
# v3 does NOT consult these: full-text enrichment is called as
# notes.enrich_top_sources(top_n=4, max_words_per=550) at the deep_investigate call site,
# and grounding is advisory in v3 (no MIN_GROUNDING gate exists there).
# Do not "tune" them expecting a v3 behaviour change.
# ---------------------------------------------------------------------------
FULL_TEXT_TOP_N = 2
FULL_TEXT_MAX_WORDS = 350
MIN_GROUNDING = 0.55
MAX_RESEARCH_ROUNDS = 2

__all__ = [
    "PROVIDERS_DEFAULT", "PRIMARY_FLOOR",
    "QUERY_GEN_MODEL", "JUDGE_MODEL", "DISCOVERY_MODEL", "OUTLINE_MODEL", "WRITER_MODEL", "EMBED_MODEL",
    # legacy-only, kept for legacy/ imports:
    "FULL_TEXT_TOP_N", "FULL_TEXT_MAX_WORDS", "MIN_GROUNDING", "MAX_RESEARCH_ROUNDS",
]
