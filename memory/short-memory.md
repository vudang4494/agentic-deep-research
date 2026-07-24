# Short Memory — snapshot trạng thái HIỆN TẠI

> **Chỉ snapshot hiện tại (≤50 dòng). KHÔNG changelog · KHÔNG số đo một lần · KHÔNG số dòng code.**
> Lịch sử & quyết định → `long-memory.md`. Roadmap → `docs/plan.md`. Pipeline & ngưỡng → `CLAUDE.md` (§3/§5), cuối cùng là **CODE**.
> Thứ tự đọc: `docs/GLOSSARY.md` → file này → `CLAUDE.md`.

## Base đang chạy
- **Orchestrator DUY NHẤT:** `pipeline/deep_research_v3.py` + stage logic `research/*.py`. Launcher `./run_full.sh`. **Resume tự động** qua `output/runs/<name>/state.json` (không có flag — cùng `--out-name` = resume).
- **Legacy — KHÔNG phải base, đừng sửa như live:** `legacy/deep_research.py` (v2; còn bị `tools/monitor.py` / `eval/run_eval.py` import). v1 đã retire.
- **100% model LOCAL:** `gemma4:e4b` (discovery/outline/QGN/judge) · `qwen3.6-35b:iq3` (writer) · `bge-m3:latest` (embed, UNIFIED mọi path) · `bge-reranker-v2-m3` · HHEM. **Không gọi Claude/external model lúc runtime** (search provider ngoài như brave/tavily thì được — LOCAL-only nói về *model inference*).
- **Verifier ≠ Writer** (bất biến): grounding = HHEM · topic/cite = gemma · writer = Qwen.

## Gate đang sống (giá trị cụ thể → `CLAUDE.md §5` → grep code)
- **Cứng:** P0a domain-evidence (PRE-writer) · **G2** cite_precision · **G4** topic · StageD word-count/cross-ref · empty-pool.
- **Advisory:** **G3** grounding (HHEM) — log-only, đã bỏ khỏi gate (strict-NLI under-score prose tổng hợp; không phải tín hiệu chất lượng).
- P0c seen-penalty fire thật; canonical + pool-rescued **EXEMPT**.

## Đã có trong base (merged main)
Outline **anti-matrix ENFORCED** (`enforce_outline_structure` chạy mọi path) · embed unify bge-m3 · anchoring safe (không thu nhỏ pool) · **G2 fail-CLOSED** · evidence-pool rescue (mượn sibling, P0c-exempt) · claim-aware excerpt (`_best_passage`) · Stage-F `decite` + `mathfix` single-source · `.env` auto-load · brave provider · ReAct re-dispatch trước khi stub BLOCKED · render tectonic robust.

## Trần chất lượng & hướng đi
- **Retrieval base là biến chi phối block-rate**, không phải code gate. Tavily billing-dead (402) → base free mỏng hơn → block nhiều hơn. Thêm `BRAVE_API_KEY` (free) là lever rẻ nhất; **ĐỪNG prune outline bằng keyword**.
- **Residual = writer grounding:** phần lớn section ship `degraded` vì cite_precision dưới ngưỡng, không phải vì lệch topic.
- **Lever kế (đúng doctrine, KHÔNG train): surgical verify-revise** — feed `cite_res["verdicts"]` per-`[N]` ngược writer làm retry-hint để sửa đúng citation hỏng. Thứ tự ưu tiên đầy đủ → `docs/plan.md`.
- **DOCTRINE (bất biến):** cải thiện ở tầng orchestration/inference (retrieval · verify · revise-loop · prompt · evidence-select) — **KHÔNG train model, KHÔNG build dataset**. → `CLAUDE.md §2` + `§6.9`.

## Lệnh nhanh
```bash
./run_full.sh                                # hoặc: python3 pipeline/deep_research_v3.py --topic "<T>" --out-name <n> --no-smoke
python3 tools/monitor.py                     # tiến độ khi đang chạy
python3 tools/report.py output/runs/<n>      # đếm quality ok/degraded/BLOCKED sau run
python3 eval/test_verify_optim.py            # unit test verify (mỗi file test là script độc lập, KHÔNG pytest)
```
