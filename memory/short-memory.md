# Short Memory — snapshot trạng thái HIỆN TẠI

> **Chỉ snapshot hiện tại (≤50 dòng). KHÔNG changelog · KHÔNG số dòng code.**
> Lịch sử & quyết định → `long-memory.md`. Roadmap → `docs/plan.md`. Pipeline & ngưỡng → `CLAUDE.md` (§3/§5), cuối cùng là **CODE**.
> Thứ tự đọc: `docs/GLOSSARY.md` → file này → `CLAUDE.md`.

## Base đang chạy
- **Orchestrator DUY NHẤT:** `pipeline/deep_research_v3.py` + stage logic `research/*.py`. Launcher `./run_full.sh`, mặt tiền `agentic.py`. **Resume tự động** qua `output/runs/<name>/state.json` (cùng `--out-name` = resume; không có flag).
- **Legacy — đừng sửa như live:** `legacy/deep_research.py` (v2). `research/planner.py` đã **XOÁ** (v3 chưa bao giờ import).
- **100% model LOCAL:** `gemma4:e4b` (discovery/outline/QGN/judge) · `qwen3.6-35b:iq3` (writer) · `bge-m3:latest` (embed) · `bge-reranker-v2-m3` · HHEM. **Verifier ≠ Writer** (bất biến).
- Cổng ship: `python3 eval/verify_all.py` — hiện **17/17** (10 static A–J + 7 acceptance).

## Gate đang sống (giá trị → `CLAUDE.md §5` → grep code)
- **Cứng:** P0a domain-evidence (PRE-writer) · **G2** cite_precision ≥0.45 · **G4** topic ≥0.50 · StageD word-count/cross-ref · empty-pool.
- **Advisory:** **G3** grounding (HHEM) log-only · `explain.py` explanation_depth.
- P0c seen-penalty fire thật; canonical + pool-rescued **EXEMPT**.

## ⛔ ĐÃ THỬ VÀ THẤT BẠI — đừng làm lại nếu không có bằng chứng mới
Ba lần liên tiếp nhắm vào "hình phạt dành cho tổng hợp", **không lần nào gỡ được**. Chi tiết + số → khối `TRIED AND REVERTED` trong `deep_investigate.py`.
1. **CitationAgent** (gắn lại `[N]` sau khi viết, prose bất biến): 95 lần gọi, ΔG2 **+0.028** (20 tốt/14 tệ) = nhiễu. Code đã xoá.
2. **G2 chấm theo CLAIM** (hợp các nguồn được trích + miễn câu suy diễn): chấm lại 66 section thật → **0.352 → 0.323**, ít hơn 3 section qua gate. **Siết chứ không nới.** `verify.py` đã revert nguyên trạng.
3. Suy ra: hình phạt tổng hợp có vẻ **nội tại** ở việc chấm prose tổng hợp với excerpt truy xuất — **không phải** lỗi của đơn vị chấm.

## Baseline hiện hành: `gen_ai_900p` (665 trang, 334 section, 18,5h)
Run tốt nhất tới nay. **block 1,5% · topic 0,902 · expl 0,631 · cite_prec 0,356.**
- **`cite_precision` BẤT ĐỘNG xuyên 3 run** (0,352–0,385) bất kể chủ đề/quy mô/retrieval, trong khi block-rate đi từ 23,3% → 1,5% và topic 0,715 → 0,902. Bảng đầy đủ → `CLAUDE.md §7`.
- **`--n-chapters` là HINT**: xin 60×10=600 → nhận 39 chương/334 section, 8 chương bị lấp bằng khuôn aspect-matrix vì chỉ có ~49 nguồn. Muốn sách dài hơn → mở rộng **NGUỒN** ở Discovery, đừng tăng `--n-chapters`.
- Quy đổi: **~1 section ≈ 2 trang · ~3,3 phút/section** (đừng lấy giờ đầu tiên chia đều — nó gồm Discovery+Outline ~50 phút overhead một lần).

## Đánh đổi đang bật (biết giá của nó)
- `_CANONICAL_EXCERPT_WORDS = 2200` (đoạn liền mạch dày công thức cho canonical, thay cửa sổ 550 bám claim): `explanation_depth` **0.503→0.599**, `cite_precision` **0.385→0.345**. Sách dạy nhiều hơn, quy nguồn kém hơn. Section `degraded` **vẫn vào sách** (chỉ `BLOCKED` bị bỏ). Về `550` là khôi phục y cũ.
- **Mọi thứ đụng G2 đều là đánh đổi, không có cái nào miễn phí.**

## Đã có trong base (merged main)
Outline **anti-matrix ENFORCED** · embed unify bge-m3 · **G2 fail-CLOSED** · evidence-pool rescue · MMR diversity (`select_diverse`) · Stage-F `decite`/`dedup`/`mathfix`/**`mdfix`** (list bẹp, `[[N]]`, ref renumber, orphan cite) · **`arxiv_by_id` có fallback** (timeout 25s + retry + Tavily-theo-ID) · **`notes.normalize_source_id`** single-source · ReAct re-dispatch · render tectonic robust · provenance + atomic state write.

## Cảnh báo vận hành
- **Tavily ĐANG SỐNG** (key mới, 2026-07). Ghi chép cũ nói "billing-dead 402" là **SAI**.
- `export.arxiv.org` **chập chờn thật** (timeout 7s/20s, HTTP 429 ở 40s). Canonical mất → **không có lỗi nào được ném** vì canonical miễn prefilter+P0c. Kiểm bằng log `arxiv_by_id returned N papers`.
- Canonical **không** được miễn `rerank.RELEVANCE_FLOOR = 0.25` — chúng vẫn có thể bị cắt sau prefilter. Chưa xác minh cắt oan hay cắt đúng.
- **`embed()` PHẢI chia batch** (`_MAX_BATCH=64`): Ollama từ chối theo SỐ LƯỢNG text (128 ok / 192 fail), và `[]` bị mọi caller hiểu là "degrade cho êm" → vượt trần **tắt âm thầm** thứ mà embedding phục vụ. Đã từng giết cả bước gỡ-trùng-xuyên-chương của outline 35 chương. Enforce bởi `verify_all` check K.
- **Đừng chạy `--target-section X` kèm `--no-smoke` trên run smoke**: resume sẽ sinh luôn mọi chương còn thiếu (16 → 86 section).

## Lệnh nhanh
```bash
python3 agentic.py doctor | run | verify | report <run>
python3 eval/verify_all.py            # cổng ship, 17/17 (--static = vài giây, không cần Ollama)
python3 tools/report.py output/runs/<n>
```
