# Long Memory — nhật ký nén theo phiên

> **Đây là NHẬT KÝ, không phải trạng thái hiện tại.** Mỗi entry đúng **tại thời điểm của nó** và có thể đã bị supersede bởi entry mới hơn. Muốn biết hệ thống hôm nay ra sao → `short-memory.md`; ngưỡng thật → **code**.
> Quy tắc viết: mới nhất trước · 1–3 dòng mỗi mục · không lặp `short-memory.md` · **không chép số dòng code** (chúng trôi) · khi một kết luận cũ bị bác thì **sửa gọn tại entry cũ**, đừng để hai phiên bản cùng sống · nén entry cũ khi qua milestone.

---

## Session log (mới nhất trước)

### [2026-07-01] PR#25 anti-matrix ENFORCE · PR#26 brave provider
- **PR#25:** `enforce_outline_structure()` chạy trong `_postprocess_outline` **mọi path** (chunked/LLM/fallback) → collapse suffix aspect-matrix + drop cross-chapter near-dup, rồi re-audit. Đóng gap "outline `ok=false` vẫn ship nguyên xi". Guard: `eval/test_outline_enforce.py`.
- **PR#26:** thêm `brave` vào `PROVIDERS_DEFAULT` — thay thế FREE cho Tavily đã billing-dead (HTTP 402; 402≠401 → đổi key không chữa được). Thiếu key = no-op an toàn.
- **Bài học vận hành:** block-rate là hàm của **retrieval base**, không phải của code gate — đừng "sửa gate" khi thấy tỉ lệ block cao.

### [2026-06-25 → 06-29] Canonical 4-tier layout · anti-dup · Stage-F decite
- Flatten repo về **4-tier chuẩn** `pipeline/ research/ eval/ scripts/ legacy/ tools/ docs/`.
- Anti-duplicate: canonical-URL dedup + cross-encoder relevance gate · cross-chapter semantic dedup + seed-grounded canonical anchor · enforced content dedup + writer verify-revise (bản thô) + **ReAct re-dispatch** (retry 1 lần với nhiều round + full provider trước khi stub `[BLOCKED]`) · verifier `eval/check_dedup.py`.
- **Stage-F `decite`:** writer name-drop TITLE section anh em như thể paper ngoài → gỡ deterministic, chỉ xoá khi khớp đúng một section title, giữ nguyên `[N]`/cite ngoài. Guard: `eval/test_decite.py`.
- Retrieval reliability: arxiv fail-fast + takeover khi timeout. Tooling: `tools/monitor_run.py`.

### [2026-06-25] DOCTRINE chốt: cải thiện AGENTIC, KHÔNG train — + P0.5→P0.8
- **DOCTRINE (user affirmed, BẤT BIẾN):** chất lượng lên ở tầng **orchestration/inference** (retrieval · verify · revise-loop · prompt · evidence-select), **KHÔNG train model & KHÔNG build dataset** → giữ topic-agnostic, prompt-robust, auditable. Codify: `CLAUDE.md §2/§6.9`, `docs/RULES.md`, `docs/plan.md`.
- **P0.5** best-round pin: accept break ở round qua-G2 nhưng return `best_content` (topic-first) → ship body của round KHÁC với `quality="ok"`. Fix: khoá `best_*` (content + sources + n_cites + cite_markers + cross_refs) vào đúng round. Kèm: `assemble_book` skip section vắng trong `state.json` → hết hollow heading.
- **P0.6** G2 là **bug ĐO, không phải quality**: gemma emit 1 mảng JSON mỗi dòng, parser chỉ bắt mảng đầu → fail-closed pad phần còn lại → floor giả. Fix parser đa-mảng + chunk + retry + tăng timeout + nâng `AUTO_SUPPORT_COS` (paraphrase phải qua judge). Discrimination sau fix **bất đối xứng** (GOOD lên, BAD xuống) → judge không rubber-stamp.
- **P0.7** claim-aware excerpt: head-slice đầu tài liệu thường không chứa fact → `notes._best_passage` (window chồng 50%, argmax cosine bge-m3). Giúp CẢ writer lẫn judge.
- **P0.8** `.env` KHÔNG được orchestrator đọc → tavily im lặng OFF ở mọi run trước đó. Fix `_load_dotenv()`. **Mọi số retrieval đo trước mốc này đều thiếu tavily.**
- **Lever cuối = P1.5 verify-revise surgical:** feed `cite_res["verdicts"]` per-`[N]` ngược writer làm retry-hint. Không weight.

### [2026-06-22 → 06-23] Verify post-writer INERT → P0 → P0-2b: faithfulness gate sống lại
- **Phát hiện (audit grounded 22-agent):** grounding per-source-max không bao giờ chạm ngưỡng `base_ok` → (a) clean-accept không fire; (b) `verify_section` (G2) nằm trong `if base_ok` nên **KHÔNG BAO GIỜ chạy** → `cite_precision=1.0` chỉ là giá trị init, từng bị đọc nhầm thành "G2 REAL"; (c) StageE topic-block không fire. → **gate cứng sống duy nhất lúc đó = P0a pre-writer**; mọi verify post-writer chỉ LOG.
- **P0 (06-22):** bỏ grounding khỏi gate (G3 log-only) · G2 chạy độc lập grounding → cite_precision **đo thật** · `cite_precision=None` khi không đo (hết default 1.0) · best-round topic-first · StageE chuyển sau-loop theo best-topic · fix P0c aliasing (`run_seen_counts` từ no-op → fire thật).
- **Lộ P0-2b:** prompt judge "direct match only, not topical overlap" khiến prose synthesized bị chấm no_evidence/unrelated → cite_precision floor ~0.3-0.4 (**cùng bệnh strict-NLI như HHEM**), clean-accept vẫn = 0.
- **P0-2b (06-23):** soften judge — `supports` = evidence states/implies/**faithfully paraphrases** claim; topical-overlap-không-support vẫn KHÔNG phải supports; contradicts/unrelated giữ strict. `min_cite_precision` + `no_evidence` **GIỮ NGUYÊN** (không hạ mù). Guard chống "nới-để-qua": `eval/bench_cite_discrimination.py` chạy THẬT `verify_section` trên labeled GOOD/BAD_unrelated/BAD_contradict, assert GOOD qua ngưỡng ∧ gap đủ rộng.
- **Kết:** faithfulness gate hết INERT — trên prose thật, section faithful ACCEPT, section yếu bị retry rồi degraded. Gate SỐNG và discriminate.

### [2026-06-21] Chuẩn hoá docs; grounding = ADVISORY; embed UNIFIED
- **Grounding có HAI số** — `grounding` (per-source-max, từng là soft conjunct của `base_ok`) và `grounding_cited` (strict cited, rất thấp trên prose). Chốt: **advisory**. *(Kết luận "faithfulness thật = G2 cite_prec" viết ở entry này SAI tại thời điểm đó — 06-22 chứng minh G2 chưa từng chạy; đúng trở lại sau P0.)*
- **Embed UNIFIED `bge-m3:latest` mọi path** — supersede mọi note "embed SPLIT nomic/bge-m3" ở entry 06-15/06-16. Lý do bỏ nomic: nó cần prefix `search_query:`/`search_document:` mà code không truyền → asymmetric. 0 ref nomic sống.
- Docs-only, 0 đổi hành vi pipeline. Còn lại: eval semantic/LLM-judge (BAER chỉ cơ học); retriever cho topic ngách.

### [2026-06-16] Xây tầng Verify: G2/G3/G4/G5/G6 + anti-matrix #1 + anchoring an toàn
- **Audit lộ nhiễu:** P0a in message sai ngưỡng so với cái enforce · `topic_relevance_check` nhận `model=` nhưng không gọi LLM (heuristic quantize {0.5,0.75,1.0}) · grounding bão hoà do gộp mega-premise · 6/8 hàm `verify.py` chỉ legacy gọi.
- **Implement (LOCAL-only):** **G3** grounding de-saturate (per-source max) · **G4** topic judge gemma-local (blend `answer_relevance` + StageE floor) · **G2** citation-integrity `verify_section` → sau đó chuyển **fail-CLOSED** (lỗi verify = 0.0, retry/best-effort, không mất content) · **G5** fix bug ngưỡng cross-ref + gộp gate chồng · **G6** bge-m3 dedup warn-first.
- **#1 outline anti-matrix** (title term-centric) + **#5 anchoring AN TOÀN**: anchor chỉ vào rank/rerank (ordering), **prefilter — chỗ hard-drop duy nhất — giữ `section_prompt` gốc** → không bao giờ thu nhỏ pool. Guard: `eval/test_verify_optim.py`.

### [2026-06-15] Đánh giá `llm_book_v36` → nguồn gốc của 8 guardrails
- **HHEM bão hoà** (g=1.0 toàn bộ section) → vô nghĩa làm tín hiệu; tín hiệu thật lúc đó = `topic_relevance`.
- **Matrix pattern còn sống:** outline templated `anchor × section`, `outline_audit ok=false` nhưng **chỉ advisory** → redundancy lọt. (Doc cũ claim "fixed=0" là OVER-CLAIM.) → về sau thành PR#25.
- **Reference off-topic tỉ lệ cao** do prefilter + domain gate quá lỏng cho chapter theme-generic → guardrail "enforce reference relevance theo SECTION".
- **Doc drift nặng** (version, số section, đường dẫn module, ngưỡng đều sai so với code) → guardrail "ngưỡng sống trong CODE, doc là advisory". Viết lại `CLAUDE.md` + `docs/RULES.md` + memory từ mốc này.

---

## Lịch sử nén (≤ 2026-06-08)

- **[06-08]** Eval 7 run v3 + rubric 5 tiêu chí: g=1.0 & topic=1.0 mọi run · **arxiv recall 0%** (foundational paper không retrieve được) · một paper dominate 50-75% nguồn. → ship **P0a** (LLM domain-gate trước writer), **P0b** (canonical injection + `--canonical-arxiv-ids`, force-fetch + protect), **P0c** (seen-count penalty trong RRF, protected exempt).
- **[06-07]** P3 outline repair + R7 canonical-URL hygiene: dup sections → 0, generic title → 0; lỗi nằm ở post-processing chứ không phải model. Tái cấu trúc 3 file memory: **CLAUDE = luật · short = snapshot · long = journal**.
- **[06-04]** **True Deep Research v3 redesign** — outline phải emerge từ evidence, không pre-fix. Tạo `discovery.py` / `outline_from_research.py` / `deep_investigate.py` / `deep_research_v3.py`.
- **[06-03]** Writer chuyển sang `batiai/qwen3.6-35b:iq3` (MoE IQ3 hợp quality/cost local).
- **[05-27 → 05-29]** Honest audit đầu tiên (4 structural gap) + batch fix cấu trúc render; tectonic còn lỗi ký tự đặc biệt → về sau thành `mathfix.py` single-source.
