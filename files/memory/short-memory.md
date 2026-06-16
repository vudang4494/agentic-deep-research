# Short Memory — Product Base (snapshot)

> Snapshot ngắn (≤50 dòng) của **TRẠNG THÁI BASE hiện tại**. Đọc: 1.`GLOSSARY.md` 2.file này 3.`long-memory.md`. Ngưỡng đầy đủ → `RULES.md`. Kiến trúc → `CLAUDE.md`. Lịch sử run/version → `long-memory.md` (KHÔNG để ở đây).

## Base (2026-06-16)
- **Orchestrator DUY NHẤT:** `files/deep_research_v3.py` + stage logic `files/research/*.py`. Launcher `./run_full.sh`. Resume qua `files/output/runs/<name>/state.json`.
- **Legacy (KHÔNG phải base — đừng sửa như live):** `files/deep_research.py` (v2, còn bị monitor/run_eval/runner import) + `files/archive/*` (v1).
- **100% model LOCAL:** gemma4:e4b (discovery/outline/QGN/judge) · qwen3.6-35b:iq3 (writer) · bge-m3 (embed) · bge-reranker-v2-m3 · HHEM. **TUYỆT ĐỐI không gọi Claude/external lúc runtime.**

## Verify layer (tối ưu + validated)
- LIVE: P0a domain (gemma) · G3 grounding (HHEM per-source + citation-aware **logged**) · G4 topic (gemma blend, **liên tục**) · G2 citation-integrity (verify_section, **PHÂN BIỆT được**) · cross-ref · StageE.
- **Verifier ≠ Writer** (bất biến): grounding=HHEM, topic/citation=gemma — KHÔNG để Qwen tự chấm prose.
- Tín hiệu phân biệt thật = **G2 cite_prec + G4 topic** (G3 grounding bão hòa trên content sạch → G2 đã lấp).

## Ngưỡng vận hành (chuẩn → RULES.md)
- P0a ≈0.40 · accept: grounding≥0.70 ∧ topic≥0.50 ∧ cites>0 ∧ **cite_prec≥0.45** ∧ cross-ref đủ.
- StageE: g-pass+topic<0.50. P0c floor 0.05 (canonical exempt). Prefilter 0.45/0.65 (bge-m3). Min 120 từ. max_rounds CLI 3.

## Base này đã gồm (đã ship + push, branch chore/normalize-docs-cleanup)
- #1 outline anti-matrix (title term-centric) · G6 bge-m3 dedup warn · #3 embed unify bge-m3 · **#5 anchoring SAFE** (anchor chỉ vào rank/rerank; prefilter giữ query gốc → KHÔNG mất nguồn) · #4 citation-aware grounding warn-first · G2 fail-closed · R7 + chapter-title fix.
- Unit test verify: `python3 files/eval/test_verify_optim.py` (16/16). Docs chuẩn hóa khớp code.

## Open (tuỳ chọn, cần thêm data)
- Bật #4 citation-aware làm gate (ưu tiên thấp — G2 đã lấp) · re-tune ngưỡng nếu cần · recall-floor backfill cho topic hiếm (pool thưa).

## Lệnh nhanh
```bash
./run_full.sh                              # hoặc: python3 files/deep_research_v3.py --topic "<T>" --out-name <n> --no-smoke
python3 files/eval/test_verify_optim.py    # unit test verify
python3 files/monitor.py
```
