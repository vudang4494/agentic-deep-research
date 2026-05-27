"""Planner agent: turn a topic string into a research-informed CHAPTERS outline.

This is Stage 3 of the Agentic Deep Research roadmap. When the pipeline is
launched with `--topic "..."`, the planner:

  1. Does a brief scoping research pass over the topic (3 broad queries -> ~10 sources).
  2. Asks an LLM to produce a 12-chapter / 8-section-per-chapter outline (96
     total sections), each section with a 1-2 line generation prompt.
  3. Returns a CHAPTERS list compatible with deep_research.py's existing format.

Output schema matches the hardcoded CHAPTERS:
    [{"n": int, "t": str, "passes": [{"p": int, "t": str, "w": int, "pr": str}, ...]}, ...]

The planner is best-effort: if generation fails or parses poorly, the caller
falls back to the hardcoded CHAPTERS list.
"""
import json
import re
from typing import List, Optional

import httpx

from . import search as _search
from .query_gen import _strip_think
from .types import Query

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_PLANNER_MODEL = "qwen3.5:4b"
# 132-section JSON outlines push ~6000 output tokens; qwen3.5:4b ~30 tok/s -> ~200s.
# Pad to 480s so 200-section outlines and CPU-only fallbacks still fit.
DEFAULT_TIMEOUT = 480.0

DEFAULT_N_CHAPTERS = 12
DEFAULT_N_PASSES = 8
DEFAULT_WORD_BUDGET = 4200

PLANNER_SYS = (
    "You are a research book planner. Given a topic and a short scoping summary "
    "of recent literature, produce a comprehensive outline for a technical book.\n\n"
    "Output ONLY a JSON object with this exact schema (no prose, no markdown fences):\n"
    "{\n"
    '  "title":    "<book title>",\n'
    '  "chapters": [\n'
    "    {\n"
    '      "n": 1,\n'
    '      "t": "<chapter title>",\n'
    '      "passes": [\n'
    '        {"p": 1, "t": "<section title>", "pr": "<1-2 sentence generation directive>"},\n'
    "        ...\n"
    "      ]\n"
    "    },\n"
    "    ...\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Produce exactly the requested number of chapters and passes per chapter.\n"
    "- Each chapter must cover a distinct, non-overlapping sub-area of the topic.\n"
    "- Each section title should be specific enough that a writer knows what to cover.\n"
    "- The `pr` field is the prompt the writer sees. Make it concrete: list key sub-topics, "
    "formulas, methods, or case studies to include.\n"
    "- Order chapters from foundational -> intermediate -> advanced -> applications -> frontiers."
)


def _scope_topic(topic: str, providers=("tavily", "arxiv", "wikipedia")) -> str:
    """Run a brief research pass to give the planner real context.

    Returns a compact bullet list of titles + 1-line summaries from up to 10
    sources across 3 broad scoping queries. Empty string if everything fails.
    """
    scoping_queries = [
        Query(q=f"{topic} survey overview"),
        Query(q=f"{topic} fundamentals introduction"),
        Query(q=f"{topic} state of the art 2024 2025"),
    ]
    sources = _search.gather(scoping_queries, providers=providers, per_provider_k=3)
    if not sources:
        return ""
    # Dedup by URL
    seen = set()
    uniq = []
    for s in sources:
        if s.url in seen:
            continue
        seen.add(s.url)
        uniq.append(s)
        if len(uniq) >= 10:
            break
    lines = ["Recent literature scoped during planning:"]
    for s in uniq:
        year = f" ({s.year})" if s.year else ""
        snippet = (s.excerpt or "").split(". ")[0][:160]
        lines.append(f"  - {s.title}{year}: {snippet}")
    return "\n".join(lines)


def _parse_outline(raw: str, n_chapters: int, n_passes: int,
                   word_budget: int) -> Optional[List[dict]]:
    """Extract the JSON outline from a model response. Returns CHAPTERS-format list
    or None on parse failure. Pads/truncates to exact (n_chapters, n_passes) so the
    runner/state code never has to deal with off-shape outlines."""
    raw = _strip_think(raw or "")
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None

    chapters_in = data.get("chapters") or []
    if not isinstance(chapters_in, list) or not chapters_in:
        return None

    out: List[dict] = []
    for i, ch in enumerate(chapters_in[:n_chapters], start=1):
        if not isinstance(ch, dict):
            continue
        ct = str(ch.get("t") or ch.get("title") or f"Chapter {i}").strip()
        passes_in = ch.get("passes") or []
        passes_out = []
        for j, pp in enumerate(passes_in[:n_passes], start=1):
            if isinstance(pp, dict):
                pt = str(pp.get("t") or pp.get("title") or f"Section {i}.{j}").strip()
                pr = str(pp.get("pr") or pp.get("prompt") or pt).strip()
            elif isinstance(pp, str):
                pt, pr = pp[:80], pp
            else:
                continue
            passes_out.append({"p": j, "t": pt, "w": word_budget, "pr": pr})
        if not passes_out:
            continue
        # Pad to n_passes if model under-produced
        while len(passes_out) < n_passes:
            j = len(passes_out) + 1
            passes_out.append({
                "p": j, "t": f"{ct} -- additional aspect {j}", "w": word_budget,
                "pr": f"Continue the {ct.lower()} discussion with an additional important sub-topic not yet covered in earlier passes.",
            })
        out.append({"n": i, "t": ct, "passes": passes_out})

    if not out:
        return None
    # Pad chapters if needed
    while len(out) < n_chapters:
        i = len(out) + 1
        out.append({
            "n": i, "t": f"Additional Chapter {i}",
            "passes": [{"p": j, "t": f"Aspect {j}", "w": word_budget,
                        "pr": f"Discuss aspect {j} of the broader topic."}
                       for j in range(1, n_passes + 1)],
        })
    return out


def plan_outline(topic: str,
                 n_chapters: int = DEFAULT_N_CHAPTERS,
                 n_passes: int = DEFAULT_N_PASSES,
                 word_budget: int = DEFAULT_WORD_BUDGET,
                 model: str = DEFAULT_PLANNER_MODEL,
                 timeout: float = DEFAULT_TIMEOUT) -> Optional[List[dict]]:
    """Plan a CHAPTERS outline for the given topic.

    Returns a list compatible with deep_research.CHAPTERS, or None if planning
    fails (caller should fall back to the hardcoded outline).
    """
    print(f"[planner] scoping research for topic: {topic!r}", flush=True)
    scope = _scope_topic(topic)
    if scope:
        print(f"[planner] scoped {scope.count(chr(10))} sources", flush=True)
    else:
        print(f"[planner] WARN: scoping returned no sources -- proceeding without context", flush=True)

    user_prompt = (
        f"TOPIC: {topic}\n"
        f"REQUIRED OUTLINE SHAPE: {n_chapters} chapters x {n_passes} sections each\n\n"
        f"{scope}\n\n"
        "Return the JSON outline now."
    )
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": PLANNER_SYS},
            {"role": "user",   "content": user_prompt},
        ],
        "options": {"temperature": 0.4, "num_predict": 6000, "top_p": 0.9},
        "think": False,
    }
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
            raw = (r.json().get("message") or {}).get("content", "")
    except Exception as e:
        print(f"[planner] ERROR: model call failed: {e}", flush=True)
        return None

    outline = _parse_outline(raw, n_chapters, n_passes, word_budget)
    if outline is None:
        print(f"[planner] ERROR: outline parse failed (model returned {len(raw)} chars)", flush=True)
        return None

    outline = _self_correct(outline)
    print(f"[planner] outline OK: {len(outline)} chapters x {len(outline[0]['passes'])} passes", flush=True)
    return outline


def _self_correct(outline: List[dict]) -> List[dict]:
    """Cheap deterministic self-correction over a freshly-planned outline:

    1. Disambiguate any literally-duplicated section titles.
    2. Disambiguate NEAR-duplicates via bge-m3 cosine on titles (catches
       cases like "Tokenization Strategies" vs "Tokenizer Methods" which
       the literal-match pass misses but the writer will duplicate).
    3. Audit for cross-chapter concept overlap; report it to the caller.

    Concept-overlap removal is deferred to the runtime dedupe_outline() pass in
    deep_research.run() -- that pass needs runtime access to the full key-term
    list and is idempotent, so we don't duplicate the logic here.
    """
    # 1. Literal-duplicate disambiguation
    seen_titles = {}
    for ch in outline:
        for pp in ch["passes"]:
            t = pp["t"].strip()
            key = t.lower()
            if key in seen_titles:
                pp["t"] = f"{t} (Ch{ch['n']}.{pp['p']} -- {ch['t'].split()[0]} perspective)"
            else:
                seen_titles[key] = (ch["n"], pp["p"])

    # 2. Near-duplicate detection via bge-m3 cosine. Annotate the LATER
    # section with a "DISTINCT FROM Ch X.Y" directive so the writer is
    # primed to differentiate from the earlier coverage. Cheap (1 batch
    # embedding call, ~150 titles -> ~2s on M-series).
    try:
        from .embeddings import embed, cosine  # local import: planner runs without it on Ollama failures
        all_pps = [(ch["n"], pp["p"], pp) for ch in outline for pp in ch["passes"]]
        titles = [pp["t"] for _, _, pp in all_pps]
        vecs = embed(titles, model="bge-m3:latest") if len(titles) > 1 else []
        if len(vecs) == len(titles):
            NEAR_DUP_THRESHOLD = 0.85
            for i in range(1, len(vecs)):
                for j in range(i):
                    sim = cosine(vecs[i], vecs[j])
                    if sim < NEAR_DUP_THRESHOLD:
                        continue
                    later_n, later_p, later = all_pps[i]
                    earlier_n, earlier_p, earlier = all_pps[j]
                    directive = (
                        f"\n\n[OUTLINE-DEDUPE] This section title is near-duplicate "
                        f"(cosine={sim:.2f}) of Ch{earlier_n}.{earlier_p} "
                        f"'{earlier['t']}'. Write THIS section from a clearly "
                        f"distinct angle -- do NOT re-derive the same content. "
                        f"Reference the earlier section if you must touch the "
                        f"overlapping concept."
                    )
                    if "[OUTLINE-DEDUPE]" not in later["pr"]:
                        later["pr"] = later["pr"].rstrip() + directive
                    break  # one near-dup callout per later-section is enough
            n_near = sum(1 for _, _, pp in all_pps if "[OUTLINE-DEDUPE]" in pp["pr"])
            if n_near:
                print(f"[planner] near-duplicate audit: {n_near} sections flagged "
                      f"with bge-m3 cosine >= {NEAR_DUP_THRESHOLD}", flush=True)
    except Exception as e:
        print(f"[planner] near-dup audit skipped ({type(e).__name__}: {e})", flush=True)

    # 3. Audit concept overlap (informational)
    from collections import Counter
    key_terms = ["attention", "embedding", "scaling laws", "fine-tuning", "transformer",
                 "RAG", "quantization", "LoRA", "RLHF", "DPO", "tokeniz"]
    counts = Counter()
    for ch in outline:
        for pp in ch["passes"]:
            blob = (pp["t"] + " " + pp["pr"]).lower()
            for t in key_terms:
                if t.lower() in blob:
                    counts[t] += 1
    repeats = [(t, n) for t, n in counts.items() if n >= 3]
    if repeats:
        print(f"[planner] outline concept-overlap audit: " +
              ", ".join(f"{t}x{n}" for t, n in repeats) +
              " -- runtime dedupe_outline() will inject 'already covered' directives.",
              flush=True)
    return outline
