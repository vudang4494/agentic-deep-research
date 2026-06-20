# Short Memory — Product Base (snapshot)

> Snapshot ngắn (≤50 dòng) của **TRẠNG THÁI BASE hiện tại**. Đọc: 1.`GLOSSARY.md` 2.file này 3.`long-memory.md`. Ngưỡng đầy đủ → `RULES.md`. Kiến trúc → `CLAUDE.md`. Lịch sử run/version → `long-memory.md` (KHÔNG để ở đây).

## Base (2026-06-21)
- **Orchestrator DUY NHẤT:** `files/deep_research_v3.py` + stage logic `files/research/*.py`. Launcher `./run_full.sh`. Resume qua `files/output/runs/<name>/state.json`.
- **Legacy (KHÔNG phải base — đừng sửa như live):** `files/deep_research.py` (v2, còn bị monitor/run_eval/runner import) + `files/archive/*` (v1).
- **100% model LOCAL:** gemma4:e4b (discovery/outline/QGN/judge) · qwen3.6-35b:iq3 (writer) · **bge-m3:latest (embed UNIFIED mọi path #3)** · bge-reranker-v2-m3 · HHEM. **TUYỆT ĐỐI không gọi Claude/external lúc runtime.**

## Verify layer (LOCAL-only, Verifier ≠ Writer)
- LIVE: P0a domain (gemma) · G3 grounding (HHEM per-source, **ADVISORY/log-only**) · G4 topic (gemma blend, **liên tục**) · G2 citation-integrity (`verify_section`, gemma) · cross-ref · StageE.
- **Verifier ≠ Writer** (bất biến): grounding=HHEM, topic/citation=gemma — KHÔNG để Qwen tự chấm prose của chính nó.
- **Tín hiệu phân biệt chất lượng LIVE = G4 topic.** G3 grounding **ADVISORY** (strict-NLI ~0.05–0.10 trên prose faithful → KHÔNG phải metric). G2 cite_prec = faithfulness signal nhưng **saturate 1.0 trên 4-topic benchmark** → non-discriminating ở đó.

## Ngưỡng vận hành (chuẩn → RULES.md)
- P0a ≈0.40 (HARD). Accept clean: topic≥0.50 ∧ cites>0 ∧ **cite_prec≥0.45** ∧ cross-ref đủ ∧ grounding≥0.70 (**advisory** — thiếu grounding → ship `quality='degraded'`, KHÔNG hard-block một mình).
- StageE: g-pass + topic<0.50 (block do **topic**). P0c floor 0.05 (canonical + pool-rescued exempt). **Prefilter 0.48/0.65** (bge-m3). Min 120 từ. max_rounds CLI 3 / run_v3 nội bộ 2.

## Base này đã gồm (đã merge main + push)
- #1 outline anti-matrix (chunked) · G6 bge-m3 dedup warn · **#3 embed unify bge-m3** · #5 anchoring SAFE (không mất nguồn) · #4 citation-aware grounding warn-first · **G2 fail-CLOSED→0.0**.
- **HHEM re-tie** (hết degenerate 0.502; nay advisory) · **agentic evidence-pool rescue** (post-prefilter on-topic<5 → mượn sibling, P0c-exempt; block −21%, faithfulness giữ) · **mathfix single-source** + render tectonic robust · **4-topic benchmark** (accept 0.724±0.058; cite_prec/canonical/near-dup std=0) + **HF dataset** `vudang449/agentic-deep-research-eval`.
- Unit test verify: `python3 files/eval/test_verify_optim.py`. Docs (RULES/CLAUDE/GLOSSARY/README) + HF card chuẩn hóa khớp code (2026-06-21).

## Open (tuỳ chọn, cần thêm data)
- **Semantic/LLM-judge eval** (gap lớn nhất — BAER chỉ đo cơ học) · bật #4 làm gate (ưu tiên thấp — G2 đã lấp) · deeper retriever cho topic ngách (pool thưa).

## Lệnh nhanh
```bash
./run_full.sh                              # hoặc: python3 files/deep_research_v3.py --topic "<T>" --out-name <n> --no-smoke
python3 files/eval/test_verify_optim.py    # unit test verify
python3 files/monitor.py
```
