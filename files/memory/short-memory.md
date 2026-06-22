# Short Memory — Product Base (snapshot)

> Snapshot ngắn (≤50 dòng) của **TRẠNG THÁI BASE hiện tại**. Đọc: 1.`GLOSSARY.md` 2.file này 3.`long-memory.md`. Ngưỡng đầy đủ → `RULES.md`. Kiến trúc → `CLAUDE.md`. Lịch sử run/version → `long-memory.md` (KHÔNG để ở đây).

## Base (2026-06-21)
- **Orchestrator DUY NHẤT:** `files/deep_research_v3.py` + stage logic `files/research/*.py`. Launcher `./run_full.sh`. Resume qua `files/output/runs/<name>/state.json`.
- **Legacy (KHÔNG phải base — đừng sửa như live):** `files/deep_research.py` (v2, còn bị monitor/run_eval/runner import) + `files/archive/*` (v1).
- **100% model LOCAL:** gemma4:e4b (discovery/outline/QGN/judge) · qwen3.6-35b:iq3 (writer) · **bge-m3:latest (embed UNIFIED mọi path #3)** · bge-reranker-v2-m3 · HHEM. **TUYỆT ĐỐI không gọi Claude/external lúc runtime.**

## Verify layer — ⚠️ THỰC TRẠNG (eval 2026-06-22, verified 4-topic 390 sec)
- **Gate cứng SỐNG duy nhất = P0a domain-evidence (~0.40, PRE-writer)** + StageD word-count 120 + empty-pool.
- **Mọi verify POST-writer là LOG-ONLY, KHÔNG enforce:** per-source-max grounding max **0.458 < 0.70** → `base_ok` luôn false → (a) clean-accept không fire, mọi section ship `quality='degraded'`; (b) G2 `verify_section` (trong `if base_ok`) **KHÔNG BAO GIỜ chạy** → `cite_precision=1.0` là **DEFAULT** (BAER parse nhầm từ log retry-hint); (c) StageE topic-block (cần g≥0.70) **không fire**.
- G3 grounding = INERT · G4 topic = chạy + discriminate nhưng **không enforce** · G2 = không chạy.
- **Verifier ≠ Writer** (bất biến, đúng ở cấp model): grounding=HHEM, topic/cite=gemma, writer=Qwen.
- 🔧 Fix (decouple G2 + re-baseline grounding + fix P0c aliasing) → `plan.md` §Upgrade P0.

## Ngưỡng vận hành (chuẩn → RULES.md)
- **P0a ≈0.40 (gate cứng SỐNG duy nhất, pre-writer).** Min word 120 (HARD). Prefilter **0.48/0.65** (bge-m3). max_rounds CLI 3 / run_v3 nội bộ 2.
- ⚠️ accept-clean (topic 0.50 ∧ cite_prec 0.45 ∧ grounding 0.70) + StageE + P0c-cross-section: **định nghĩa có trong code nhưng INERT** (base_ok không bao giờ pass; P0c aliasing bug → no-op trong 1 run). KHÔNG tin chúng đang bảo vệ run.

## Base này đã gồm (đã merge main + push)
- #1 outline anti-matrix (chunked) · G6 bge-m3 dedup warn · **#3 embed unify bge-m3** · #5 anchoring SAFE (không mất nguồn) · #4 citation-aware grounding warn-first · **G2 fail-CLOSED→0.0**.
- **HHEM re-tie** (hết degenerate 0.502; nay advisory) · **agentic evidence-pool rescue** (post-prefilter on-topic<5 → mượn sibling, P0c-exempt; block −21%, faithfulness giữ) · **mathfix single-source** + render tectonic robust · **4-topic benchmark** (accept 0.724±0.058; cite_prec/canonical/near-dup std=0) + **HF dataset** `vudang449/agentic-deep-research-eval`.
- Unit test verify: `python3 files/eval/test_verify_optim.py`. Docs + HF card khớp code; **eval 2026-06-22 phát hiện verify post-writer INERT** (đã clean docs về đúng sự thật).

## Open → ROADMAP UPGRADE (`plan.md` §Upgrade)
- **P0 (faithfulness rỗng):** decouple G2 khỏi grounding bar (chạy `verify_section` bất kể grounding, đo cite_precision thật) · re-baseline/bỏ grounding khỏi `base_ok` · fix bug aliasing P0c (`run_seen_counts = x or {}` → `if x is None`).
- **P1 (cấu trúc):** matrix thành HARD gate (suffix/skeleton detector) · paragraph-dedup lúc assemble · math-validation gate (balance + chống LaTeX leak) · near-miss rescue (0.35–0.40).
- **P1 (eval):** held-out judge từ model khác họ / gold set (chống self-eval vòng tròn).
- **P2 (agentic sâu hơn):** citation-graph 2nd-hop cho topic ngách · primary-source routing cho citation định nghĩa/phương trình.

## Lệnh nhanh
```bash
./run_full.sh                              # hoặc: python3 files/deep_research_v3.py --topic "<T>" --out-name <n> --no-smoke
python3 files/eval/test_verify_optim.py    # unit test verify
python3 files/monitor.py
```
