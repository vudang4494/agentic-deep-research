# agentic

> **Local-first Agentic Deep Research platform.** Hand it a topic; it discovers the
> outline from research, runs ~100 atomic *research → write → verify* rounds, and
> assembles a 300-400+ page, LaTeX-typeset technical book with a single deduplicated
> References page — all on your laptop, no API key required.

<p align="left">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="python"  src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
  <img alt="runtime" src="https://img.shields.io/badge/runtime-Ollama-black.svg">
  <img alt="render"  src="https://img.shields.io/badge/render-tectonic%20%2F%20WeasyPrint-orange.svg">
  <img alt="status"  src="https://img.shields.io/badge/status-v3%20smoke--tested-success.svg">
</p>

**Tiered model stack:**

| Tier | Role | Model | Why |
|------|------|-------|-----|
| **Fast (research)** | QGN, VFY, RSR | `gemma4:e4b` | 12B dense, 6.4 GB, fast inference |
| **Quality (writing)** | WRT, PLN, RVW | `batiai/qwen3.6-35b:iq3` | MoE 35B/3B, best prose quality |
| Embedding | RSR rank | `bge-m3:latest` | dense retrieval |

Providers: arXiv + Wikipedia + DDG. Provider-agnostic — swap in any OpenAI-compatible endpoint.

---

## Highlights

| Capability | What ships today |
|---|---|
| **True Deep Research (v3)** | Outline emerges from evidence, not pre-planned |
| **Local-first** | Ollama-served LLMs only (tiered: gemma-4 research + qwen3.6 writer) |
| **Multi-provider retrieval** | arXiv + Wikipedia + DDG, all gated by env vars |
| **Full-text grounding** | top-2 sources per section get a 350-word body extract |
| **Self-critique** | HHEM-as-judge scores per-`[N]` citation grounding and triggers re-search |
| **Iterative loop** | low-grounding sections re-query with hint, capped at 2 rounds |
| **Concept discovery** | every section discovers new concepts; outline can grow dynamically |
| **LaTeX-quality PDF** | renders via `tectonic` with WeasyPrint fallback |
| **Resume-safe** | per-section state checkpoint, autonomous watchdog with Ollama health checks |

See [WORKPLAN.md](WORKPLAN.md) for roadmap and architecture notes.

---

## Quick start

```bash
# 1. Install Ollama + pull models
brew install ollama
ollama serve &
ollama pull gemma4:e4b     # fast research model (QGN, VFY)
ollama pull batiai/qwen3.6-35b:iq3  # best prose model (WRT, PLN)
ollama pull bge-m3:latest            # embedder

# 2. Python deps
pip install -r files/requirements.txt
brew install pandoc tectonic    # tectonic for paper-quality LaTeX PDF render

# 3. (optional) web-search keys
cp .env.example .env
# fill in TAVILY_API_KEY -- pipeline degrades gracefully without

# 4. Run v3 (outline-from-research, smoke test: 2 chapters)
python3 files/deep_research_v3.py --topic "Diffusion Models" --out-name diffusion_v3

#    or full run (all chapters)
python3 files/deep_research_v3.py --topic "Diffusion Models" \
  --out-name diffusion_v3 --no-smoke

#    or v2 (pre-planned outline, shipped)
./run.sh

# 5. Kill
pkill -f files/runner.py && pkill -f files/deep_research.py
```

Each run lands in `files/output/runs/<out-name>/` as `book.{md,pdf}` (plus `state.json`,
`topic_profile.json`, `outline_profile.json`, and logs).

---

## Pipeline v3 (outline-from-research)

```
Topic
  │
  v
.------------------------------------------------------.
| Stage 0: DISCOVER  (gemma-4-12b)                     |
|   3 broad scoping queries -> ~20 sources              |
|   -> LLM synthesizes TopicProfile                   |
'------------------------------------------------------'
  │
  v
.------------------------------------------------------.
| Stage 1: OUTLINE FROM RESEARCH                        |
|   LLM reads gathered sources -> hierarchical outline |
|   (outline is an OUTPUT, not INPUT)                  |
'------------------------------------------------------'
  │
  v
.------------------------------------------------------.
| Stage 2: INVESTIGATE  (per section)                 |
|   (1) QGN -> 3-5 search queries                      |
|   (2) RSR gather (arxiv/wiki/ddg)                   |
|   (3) Rank top-k (RRF + RRK)                        |
|   (4) Full-text enrich (top-2, 350w)                |
|   (5) WRT -> markdown with [N] citations            |
|   (6) VFY (HHEM grounding)                          |
|   (7) if g < 0.55: retry with refined queries       |
'------------------------------------------------------'
  │
  v
.------------------------------------------------------.
| Stage 3: ASSEMBLE -> book.md -> PDF                  |
'------------------------------------------------------'
```

---

## Pipeline v2 (pre-planned outline)

```
topic str ---> Planner agent (batiai/qwen3.6-35b:iq3 + scoping research)
                 -> 12-chapter outline JSON (self-corrected)
                 -------------------------------------------------------
per section -> (1) QGN -> 3-5 search queries (JSON)
               (2) Multi-provider search (arxiv/wiki/ddg)
               (3) Prefilter (bge-m3 cosine + domain noise)
               (4) Rank top-k (RRF + RRK cross-encoder)
               (5) Full-text enrich (top-2, 350w)
               (6) Writer (batiai/qwen3.6-35b:iq3)
               (7) Sanitize + math normalize + clean_citations
               (8) VFY (HHEM grounding)
               (9) if g < 0.55 AND round < 2: re-query -> back to (2)
                 -------------------------------------------------------
assemble -> book.md + dedup'd References -> PDF (tectonic)
```

---

## CLI reference

### v3 (outline-from-research)

```bash
python3 files/deep_research_v3.py [OPTIONS]
```

| Flag | Default | Effect |
|------|---------|--------|
| `--topic` | required | Research topic |
| `--out-name` | from topic | Output folder name |
| `--n-chapters N` | 12 | Number of chapters |
| `--sections-per-chapter N` | 8 | Sections per chapter |
| `--providers arxiv wikipedia ddg` | all 3 | Research providers |
| `--max-rounds N` | 2 | Max research rounds per section |
| `--no-smoke` | smoke (2 ch) | Run full pipeline |
| `--render` | off | Generate PDF |

### v2 (pre-planned outline)

```bash
python3 files/deep_research.py [OPTIONS]
```

| Flag | Default | Effect |
|------|---------|--------|
| `--topic "..."` | hardcoded LLM outline | Stage 3 planner generates outline |
| `--n-chapters N` | 12 | Number of chapters |
| `--n-passes N` | 8 | Sections per chapter |
| `--start-ch N` | 1 | Resume from chapter N |
| `--start-pp N` | 1 | Resume from section N |
| `--end-ch N` | none | Stop after chapter N |
| `--review` | off | LLM-as-judge prose review |
| `--no-render` | render on | Skip PDF |
| `--out-name X` | book | Run name |

---

## Environment variables

| Variable | Effect |
|---|---|
| `TAVILY_API_KEY` | Enable Tavily web search (free 1000/mo at tavily.com) |
| `DEEP_RESEARCH_WRITER_MODEL` | Override writer model |
| `DEEP_RESEARCH_REVIEW=1` | Enable review pass |
| `DEEP_RESEARCH_END_CH` | Stop after this chapter |

---

## File layout

```
files/
├── deep_research.py          # v2: pre-planned outline (shipped)
├── deep_research_v3.py      # v3: outline-from-research (smoke tested)
├── runner.py               # watchdog + auto-restart
├── monitor.py              # progress CLI
├── research/               # research layer
│   ├── discovery.py        # v3: topic scoping
│   ├── outline_from_research.py  # v3: outline from evidence
│   ├── deep_investigate.py      # v3: per-section research
│   ├── search.py          # provider adapters (arxiv/wiki/ddg/tavily)
│   ├── query_gen.py       # query generator
│   ├── notes.py           # RRF rank + format evidence
│   ├── embeddings.py      # bge-m3 batched + cosine
│   ├── fetch.py           # disk-cached HTTP fetcher
│   ├── verify.py          # VFY (grounding judge)
│   ├── faithfulness.py    # HHEM v2 grounding
│   ├── rerank.py          # RRK cross-encoder
│   ├── planner.py         # PLN (v2 outline generator)
│   └── types.py           # Source + Query dataclasses
├── eval/                  # evaluation
│   ├── paper_eval.py      # paper-quality eval
│   └── reports/           # eval outputs (gitignored)
├── memory/                # agent memory
│   ├── short-memory.md    # version changelog
│   └── long-memory.md     # session journal
└── output/
    └── runs/<name>/       # per-run output (gitignored)
```

---

## How it stays grounded

1. **Zero-citation penalty** — `grounding = 0.0` when evidence was provided but no `[N]`
   markers are emitted, forcing the writer to cite or hedge.
2. **HHEM v2 grounding** — each `[N]` claim fed to vectara/hallucination_evaluation_model
   (flan-t5-base); returns supports/partial/contradicts/unrelated.
3. **Source noise** — bge-m3 cosine prefilter drops anything below 0.30 similarity,
   stricter 0.55 for noisy-domain hits.
4. **RRF + RRK** — Reciprocal Rank Fusion (sparse BM25 + dense cosine) followed by
   cross-encoder reranking for top-8 candidates.
5. **Off-by-one citations** — `clean_citations()` strips `[N>max]` orphans post-write.

---

## Roadmap

| Stage | Description | Status |
|-------|-------------|--------|
| 0-1 | Atomic generator + continuity + reviewer | shipped |
| 2 | Researcher layer (search + retrieval + citations) | shipped |
| 2+ | Tavily + full-text + verifier + iterative loop | shipped |
| 3 | Planner agent + outline self-correction | shipped |
| **v3** | **True Deep Research (outline from evidence)** | **smoke tested** |
| 4 | Multi-agent split (parallel sections) | planned |
| 5 | Citation-graph + second-hop retrieval | planned |

---

## License

[MIT](LICENSE). Generated book content is yours.
