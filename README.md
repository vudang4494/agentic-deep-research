# agentic — Local-first Agentic Deep Research

> Hand it a topic. It **discovers** the scope, drafts an evidence-driven **outline**, then runs a
> per-section **research → rank → gate → write → verify** loop and assembles a LaTeX-typeset technical
> book — **100% on local models, no API key, every claim gated and auditable.**

<p align="left">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="python"  src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="runtime" src="https://img.shields.io/badge/runtime-Ollama%20(local)-black.svg">
  <img alt="demo"    src="https://img.shields.io/badge/demo-995--page%20book-success.svg">
  <img alt="dedup"   src="https://img.shields.io/badge/duplicate%20content-0-success.svg">
</p>

It is **not** a text generator. The goal is an on-topic, grounded, **auditable** book: drift, repetition,
and ungrounded claims are blocked at gates, not patched in the writer. **All quality comes from the
orchestration layer** — retrieval, verification, the revise loop, prompting, evidence selection — **never
from training the models.** That keeps it topic-agnostic, prompt-robust, and auditable.

---

## See it run — 995-page book, downloadable

A full end-to-end output is published so you can judge it by the artifact, not the claims:

### ▸ [**Download `book.pdf` — RLHF, 995 pages**](https://github.com/vudang4494/agentic-deep-research/releases/tag/book900-rlhf-demo)  *(GitHub Release)*

| Metric | Value | How verified |
|---|---|---|
| Length | **995 pages** · 504 sections · ~475k words | `pdfinfo` |
| **Duplicate content** | **0 sections, 0 paragraphs** | `eval/check_dedup.py` (cosine ≥0.85 / ≥0.92, bge-m3) |
| Technical depth | ~6,200 inline formulas · ~1,165 equation blocks | counted from `book.md` |
| Citations | ~16 per section, 100% of sections cited | from `state.json` |
| Topic purity (G4) | mean **0.922**, 100% ≥0.50 | gemma judge, per section |
| Completeness | **2.6%** sections blocked off-topic | down from 34% in early runs |

A second example is browsable in-repo (no download): [`output/runs/agentic_2025_full/`](output/runs/agentic_2025_full/) — 605 pages.

---

## Results that hold up to scrutiny

Every number below was **re-measured independently** (not taken from the run's own logs):

- **Zero duplicate content at 995 pages.** Section- and paragraph-level cosine dedup both pass with 0 hits — the anti-duplication levers hold at full scale, not just on smoke tests.
- **The faithfulness gate discriminates — it does not rubber-stamp.** Re-running the citation judge (G2) on a stratified sample: sections the pipeline labelled `ok` score **0.55** mean citation-precision vs **0.30** for `degraded` (gap **+0.25**) — the gate genuinely separates faithful from weak prose.
- **Citation-hygiene cleanup, −97.6% noise.** The writer used to name-drop the book's own section titles inline as if they were external papers (~1,250 phrases, 98% of sections). A deterministic Stage-F pass ([`research/decite.py`](research/decite.py)) strips them while preserving every real `[N]` and external reference — verified by [`eval/test_decite.py`](eval/test_decite.py).
- **Honest gates.** Grounding (HHEM) is advisory (strict-NLI under-scores synthesized prose); the *enforced* checks are domain (P0a, pre-writer) + topic (G4) + citation-precision (G2). Thresholds live in **code**, not docs.

---

## Architecture

```
Topic ─▶ Discovery ─▶ Outline (evidence-driven) ─▶ Deep Investigation (per section) ─▶ Assemble ─▶ Render
```

| # | Stage | Model | What happens |
|---|-------|-------|--------------|
| 0 | **Discovery** | gemma4:e4b | scoping queries → `TopicProfile` (canonical terms, must-cover, out-of-scope) + canonical-paper injection (P0b) |
| 1 | **Outline** | gemma4:e4b | chunked drafting — chapter skeleton, then per-chapter sections drawn from that chapter's evidence |
| 2 | **Deep Investigation** (loop / section) | gemma + qwen | query-gen → search (arXiv/Tavily/Wiki/DDG) → cosine prefilter → RRF rank + cross-encoder rerank → **gates** → write → **verify → revise** |
| 3 | **Assemble** | — | `book.md` + math hygiene + intra-book citation hygiene + per-section references |
| 4 | **Render** (`--render`) | — | pandoc → **tectonic** (LaTeX, continue-on-errors); WeasyPrint fallback |

### Model stack — all local (Ollama + transformers)

| Role | Model |
|------|-------|
| Discovery / Outline / Query-gen / **Judge** | `gemma4:e4b` |
| **Writer** | `batiai/qwen3.6-35b:iq3` |
| Embedding (retrieval + verify + dedup) | `bge-m3:latest` |
| Rerank | `BAAI/bge-reranker-v2-m3` (cross-encoder) |
| Grounding | `vectara/hallucination_evaluation_model` (HHEM v2, advisory) |

> **Verifier ≠ Writer:** the writer is **qwen**; grounding is scored by **HHEM**, topic/citation by **gemma**.
> The writer never grades its own prose. **LOCAL-ONLY** — no Claude/OpenAI/external API at runtime.

### The gates — what actually enforces

- **P0a domain gate** — primary live hard gate: blocks a section whose *evidence* is off-domain (≈0.40, **pre-writer**).
- **P0b / P0c** — canonical papers are protected (exempt from prefilter + dedup); over-represented sources penalized.
- **Prefilter** — drop sources below cosine 0.48 to the section (grey domains 0.65); canonical exempt.
- **Verify (post-writer)** — topic (G4) enforced + topic-drift block; citation-precision (G2) is a live gate (faithful prose clears 0.45, weak/off-source floors below → `degraded`); grounding (G3) advisory.

---

## Quick start

```bash
# 1. Local models (Ollama)
brew install ollama && ollama serve &
ollama pull gemma4:e4b
ollama pull batiai/qwen3.6-35b:iq3
ollama pull bge-m3:latest

# 2. Python deps + render toolchain
pip install -r requirements.txt
brew install pandoc tectonic

# 3. (optional) extra web search — degrades gracefully without
cp .env.example .env                  # add TAVILY_API_KEY if you have one

# 4. Run (smoke = first 2 chapters; --no-smoke = full book)
python3 pipeline/deep_research_v3.py --topic "RLHF" --out-name rlhf_v4 \
  --canonical-arxiv-ids "2203.02155,2305.18290,1706.03762" --no-smoke --render
#   or: ./run_full.sh

# 5. Inspect / verify the result
python3 tools/report.py output/runs/rlhf_v4   # per-section metrics from state.json
python3 eval/check_dedup.py output/runs/rlhf_v4   # zero-duplicate acceptance test
```

Each run lands in `output/runs/<out-name>/` (`book.{md,pdf}`, `state.json`, `topic_profile.json`,
`outline_profile.json`). Runs are **resume-safe** — re-running continues from `state.json` and never
rewrites an accepted section.

### CLI (orchestrator v3)

| Flag | Default | Effect |
|------|---------|--------|
| `--topic` | required | Research topic |
| `--out-name` | from topic | Output folder |
| `--n-chapters N` / `--sections-per-chapter N` | from discovery | Outline size hints |
| `--canonical-arxiv-ids "id,id"` | none | Force-inject + protect foundational papers (P0b) |
| `--max-rounds N` | 3 | Max research rounds per section |
| `--no-smoke` | smoke (2 ch) | Run the full book |
| `--render` | off | Render PDF |

---

## Repo layout

```
AgentDeepLearning/
├── pipeline/deep_research_v3.py    # orchestrator (LIVE) — run_v3()
├── research/                       # stage layer (relative-import package)
│   ├── discovery.py                # Stage 0 — TopicProfile + canonical inject
│   ├── outline_from_research.py    # Stage 1 — evidence-driven outline
│   ├── deep_investigate.py         # Stage 2 — per-section research/gate/write/verify loop
│   ├── search.py · rerank.py · notes.py        # retrieval + RRF rank + P0a/P0c gates + prefilter
│   ├── verify.py · faithfulness.py             # G4 topic + G2 citation (gemma) · G3 grounding (HHEM)
│   ├── mathfix.py · decite.py                  # render-safe math + intra-book citation hygiene
│   └── config.py · types.py · embeddings.py · fetch.py · canonical_seeds.py
├── eval/                           # quality harness — check_dedup.py · test_decite.py · benchmark_book.py · ...
├── scripts/render_book.py          # Stage 4 — pandoc + tectonic / weasyprint
├── tools/                          # monitor.py · report.py · mcp_server.py
├── docs/                           # RULES.md (gate/threshold table) · GLOSSARY.md · architecture
├── output/runs/<name>/             # per-run output (gitignored; committed example: agentic_2025_full)
└── CLAUDE.md · README.md · requirements.txt
```

Operational doctrine: [CLAUDE.md](CLAUDE.md) · gate/threshold table: [docs/RULES.md](docs/RULES.md) · terms: [docs/GLOSSARY.md](docs/GLOSSARY.md).

---

## License

[MIT](LICENSE). Generated book content is yours.
