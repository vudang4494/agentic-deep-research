# Long Memory — Nhật ký nén theo phiên

> **Mục đích:** Lưu lịch sử quyết định/phát hiện/kết quả, mới nhất trước. Không lặp `short-memory.md`. Mỗi entry 1–3 dòng/mục; archive khi milestone.

```text
### [YYYY-MM-DD] <tiêu đề>
- Bối cảnh: / Phát hiện: / Thay đổi: / Bằng chứng: / Còn lại:
```

---

## Session log (mới nhất trước)

### [2026-06-15] Đánh giá llm_book_v36 + chuẩn hóa docs/cleanup
- **Bối cảnh:** Hoàn thành book v36 (712 trang); audit chất lượng + chuẩn hóa CLAUDE/RULES/memory cho khớp code thật; dọn file lạc mục tiêu.
- **Phát hiện chính:**
  - **g=1.0 toàn bộ 280 section → HHEM bão hòa, vô nghĩa làm tín hiệu.** Tín hiệu thật = `topic_relevance` (mean 0.782; 23 section ở sàn 0.50).
  - **Matrix pattern còn sống:** outline templated (35 anchor × 8 section); RAG/CoT bị tách 2 anchor; jaccard ~0.80 giữa section gần-trùng. `outline_audit` `ok=false` nhưng chỉ advisory → redundancy lọt. (FIX_SUMMARY/DEVELOPMENT_SUMMARY claim "fixed=0" là OVER-CLAIM.)
  - **~45% reference off-topic** (laser/MHD/QFT...) do prefilter 0.45 + domain gate ~0.40 quá lỏng cho chapter theme-generic.
  - **Doc drift nặng:** CLAUDE/short-memory ghi v3.4/v3.5, "32 section/19K từ/4 canonical", module ở `files/*.py`, P0a=0.60/0.80 — ĐỀU SAI. Thật: deep_research_v3.py + `files/research/*.py`, 280 section, 12 canonical, P0a≈0.40, grounding accept 0.70, topic 0.50.
  - **Config drift:** `config.py EMBED_MODEL=nomic-embed-text` nhưng code thật dùng `bge-m3:latest`.
- **Thay đổi đã làm:**
  - Viết lại `CLAUDE.md` (pipeline 12-stage thật + 8 guardrails + ngưỡng code), `RULES.md` (bảng OPERATIVE vs TARGET), `short-memory.md` (snapshot v36), `long-memory.md` (de-dup entry 06-08).
  - Xoá cruft (~4MB): `cv_*_run.log`, `.DS_Store`, `danhgia/` rỗng, `*.bak`/`*.prepolish` (v36), tất cả `__pycache__`.
- **Bằng chứng:** ngưỡng verify trực tiếp tại `deep_investigate.py:218-220,479,671,702`, `notes.py:101,311`, `config.py`.
- **Còn lại:** (1) sửa outline generator khử matrix → audit `ok=true`; (2) siết per-section reference relevance; (3) **commit file core đang untracked** (deep_research_v3.py + research layer + GLOSSARY + memory + run_full.sh); (4) consolidate doc sprawl (eval/*SUMMARY*, WORKPLAN→plan, benchmark.md → archive).

---

### [2026-06-08] 7-run comprehensive eval + scoring rubric
- **Bối cảnh:** Sau 7 topics v3, cần phân loại run nào benchmark-được.
- **Phát hiện:** g=1.0 + topic=1.0 mọi run; arxiv recall **0%** (foundational papers không retrieve); paper `2510.22344` (FAIR-RAG) dominate 50-75% mọi run; rlhf_v3 §1.1=143w toàn RAG (evidence gate fail); diffusion_v3 3 zero-cite section; boilerplate tăng theo size.
- **Thay đổi:** `eval_v3_runs.py` + rubric 5 tiêu chí. Scoring: A=rag/longctx/agentic; B=transformer/llm_agentic_2026; C=rlhf/diffusion.
- **Còn lại:** fix P0a/P0b/P0c rồi rerun rlhf+diffusion. Báo cáo: `eval/reports/eval_v3_runs_20260608.md`.

### [2026-06-08] Shipped P0a/b/c fixes
- **P0a** (`notes.py`+`deep_investigate.py`): `check_evidence_domain()` LLM-gate trước writer, block/retry khi topic thấp. *(Lưu ý 06-15: ngưỡng thật về sau ≈0.40, không phải 0.60 như ghi lúc này.)*
- **P0b** (`discovery.py`+`deep_research_v3.py`): canonical injection, `--canonical-arxiv-ids`, force-fetch + protect.
- **P0c** (`notes.py`): seen-count penalty trong RRF; protected papers exempt. *(Formula sau cùng: `max(0.05,(1−f)²)`.)*
- **Bằng chứng:** syntax check pass. **Còn lại:** rerun verify.

### [2026-06-07] P3 verified + đồng bộ memory/product flow
- Fresh eval `attention_v3_p3` xác nhận P3a/b/c SHIPPED+VERIFIED: dup sections 32→0, R0 1→0, chapter specificity 0.15→1.0, primary coverage 83→100%, generic rate 100→0%.
- Tái cấu trúc 3 file: CLAUDE=luật, short=snapshot, long=journal.

### [2026-06-07] P3 outline repair + R7 canonical URL hygiene
- Lỗi ở post-processing, không phải model. Regex generic title, `_postprocess_outline` mọi return path, dedup section xuyên chương, loại DDG redirect khỏi canonical, R0 detection trong `discovery_eval.py`.

### [2026-06-04] True Deep Research v3 redesign
- Outline phải emerge từ evidence (không pre-fix). Tạo `discovery.py` / `outline_from_research.py` / `deep_investigate.py` / `deep_research_v3.py`. Smoke: 16 section, g=1.0, 365 cites, 31.6 min.

### [2026-06-04] Paper eval sprint + postprocess
- Tạo `paper_eval.py` + `postprocess_book.py` + arXiv boost. grounding 0.979, pass 98%, arXiv chỉ 7.6%.

### [2026-06-03] Migration writer → `batiai/qwen3.6-35b:iq3`
- MoE IQ3 tốt hơn cho quality/cost local; grounding tăng.

### [2026-05-29] bookv7 fix-batch
- 12 fix cấu trúc; WeasyPrint OK, tectonic còn lỗi `symbb`.

### [2026-05-27] Honest audit
- Xác định 4 structural gaps; W1 đã sửa; tạo baseline trung thực. Còn W2-W4.
