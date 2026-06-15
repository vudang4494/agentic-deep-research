# WORKPLAN.md -- Agentic Deep Research Pipeline

**Mission:** local-first deep research tu prompt thuon, tao sach ky thuat co nguon trich dan, co tu-danh gia, co vong lap.

**Doctrine:** Khong biet truoc kich ban. Lam cung chi co the. Do hard-code quality contracts, khong hard-code answers.

---

## Trang thai hien tai (2026-06-08)

| Khu vuc | Trang thai | Ghi chu |
|---------|-----------|---------|
| v3 discovery-first pipeline | shipped | Discovery -> Outline -> Investigate -> Write -> Verify |
| P3a outline repair | shipped + verified | non-destructive, 0 dups, 0 R0 |
| P3b canonical URL hygiene | shipped + verified | 100% primary sources |
| P0a domain gate | **SHIPPED** | `check_evidence_domain()` before writer |
| P0b canonical injection | **SHIPPED** | `--canonical-arxiv-ids` CLI flag |
| P0c seen-count penalty | **SHIPPED** | RRF penalty cho over-represented sources |
| Experiment A | COMPLETE (6/6) | spec=1.00, dups=0, R0=0, primary>=98.7% |
| rlhf_v4 run | in progress | testing P0a/b/c on RLHF topic |
| P1, P2, P4 | pending | can be done in parallel |

---

## Hien trang nhu luc

### Nhung gi CO

- Pipeline sequential local chay tu prompt thuon
- Discovery-first: retrieve roi moi sinh TopicProfile, outline, section research
- Quality gates 5 tang (A: structure, B: evidence, C: writing, D: verification, E: coherence)
- P0a: chan evidence sai domain truoc khi writer bat dau
- P0b: force-inject canonical arxiv papers de tranh 0% recall
- P0c: giam domination cua mot paper trong nhieu sections
- Grounding tot (g=1.000 tren tat ca runs)
- Primary source coverage 100%
- arxiv coverage 100%

### Nhung gi CHUA CO

- Khong co multi-agent parallelism (tat ca sequential)
- Khong co citation graph / second-hop retrieval
- Khong co production-proven full-book validation cua v3
- P1 (retry diversity), P2 (best-round scoring), P4 (partial-run eval) con pending

---

## Model stack

| Vai tro | Model | Ghi chu |
|--------|-------|---------|
| Discovery / Outline / Judge | `gemma4:e4b` | Phan tich, danh gia |
| Writer | `batiai/qwen3.6-35b:iq3` | Chi viet sau gates |
| Embed | `bge-m3:latest` | Dense retrieval |
| Rerank | `BAAI/bge-reranker-v2-m3` | Cross-encoder |
| Grounding | `vectara/hallucination_evaluation_model` | HHEM |

---

## Cong viec can lam tiep

### P1 -- Retry diversity
Chong lam lai cung query/source giua cac vong. Theo doi query signatures va source IDs. Neu overlap > nguong, dung som hoac ep diversification.

### P2 -- Best-round scoring
Thay the so sanh brittle additive bang tuple ranking (grounding, topic_relevance, citation_presence). Dam bao vong sau chi thang khi thuc su tot hon.

### P4 -- Partial-run eval
Ho tro che do partial-run: relax breadth-sensitive metrics (should_cite_recall, subtopic_coverage) nhung giu intrinsic unchanged (grounding, loops, zero_cite, word_count).

### Experiment B -- Smoke comparison
Sau P1: so sanh v2 vs v3 tren 2 chapters moi topic.

### Experiment C -- Full-run
Sau P1/P2/P4: full run tren 1-2 topics, paper eval, human review.

---

## Cong viec da xong

- v2 shipped (outline dinh truoc)
- v3 discovery-first (shipped, smoke tested)
- P3a outline repair (shipped + verified)
- P3b canonical URL hygiene (shipped + verified)
- P3c coverage-note preservation (shipped + verified)
- P0a domain gate (shipped)
- P0b canonical injection (shipped)
- P0c seen-count penalty (shipped)
- Experiment A COMPLETE (6/6)

---

## Pipeline files

| File | Trang thai | Mo ta |
|------|-----------|-------|
| `deep_research_v3.py` | shipped | Orchestrator v3, discovery-first |
| `research/discovery.py` | shipped | Stage 0: TopicProfile. Co P0b. |
| `research/outline_from_research.py` | shipped | Stage 1: outline tu evidence |
| `research/deep_investigate.py` | shipped | Stage 2: per-section research. Co P0a. |
| `research/notes.py` | shipped | rank + format evidence. Co P0a + P0c. |
| `research/verify.py` | shipped | grounding + topic relevance |
| `research/rerank.py` | shipped | cross-encoder rerank |
| `research/faithfulness.py` | shipped | HHEM grounding |
| `research/search.py` | shipped | provider adapters + arxiv two-phase |
| `research/query_router.py` | shipped | semantic archetype routing |
| `eval/paper_eval.py` | shipped | paper-quality eval |
| `eval/run_eval.py` | shipped | eval harness |
