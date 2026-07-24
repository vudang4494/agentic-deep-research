# RULES.md — Product Guardrails + Bảng Ngưỡng + Agent Efficiency

> **Vai trò:** nguồn ngưỡng chuẩn duy nhất trong docs. Phân biệt rõ **OPERATIVE** (code enforce thật) vs **TARGET** (aspirational, CHƯA enforce).
> **Không changelog · không số đo một lần · không số dòng code** (chúng trôi — dùng grep anchor). Lịch sử → `memory/long-memory.md`. Trạng thái hôm nay → `memory/short-memory.md`. Mục tiêu academic chi tiết → `eval/PRODUCT_QUALITY_CRITERIA.md`.
> **Cuối cùng, CODE mới là chuẩn.** Bảng dưới là ảnh chụp để định hướng — trước khi dựa vào một con số, grep symbol tương ứng.

## Mục tiêu tối thượng
Product này **KHÔNG** phải hệ thống sinh chữ dài. Đây là hệ thống tạo **technical book / research artifact đúng topic, đúng evidence, có logic học thuật, auditable**.
**Run dài nhưng sai topic / drift / lặp = FAIL.**

## 7 câu hỏi bắt buộc trước khi chấp nhận run
1. Book có đúng topic không?
2. Canonical papers của topic có thực sự xuất hiện (evidence + prose) không?
3. Có adjacent-domain contamination không?
4. Có paper nào dominate bất thường (>50% sections) không?
5. Các chapter có thực sự nói điều khác nhau không?
6. Sách đọc như một cuốn coherent book chưa?
7. Nếu bỏ chỉ số `g` (grounding), còn dám gọi đây là output tốt không?

**Bất kỳ câu nào = "không chắc" → FAIL.**

## Thứ tự ưu tiên quyết định
1. Đúng topic → 2. Đúng evidence/canonical → 3. Không lặp/drift → 4. Logic học thuật toàn sách → 5. Grounding/citation correctness → 6. Độ dài/số section → 7. Văn phong.

## Product-level FAIL (bất kỳ điều nào)
1. `must_cite_recall = 0%` cho topic có canonical rõ ràng.
2. Adjacent domain chi phối narrative nhiều sections.
3. Một paper dominate >50% sections.
4. Lặp semantic nghiêm trọng giữa chapter/section.
5. Heading inflation / assembly corruption.
6. Section viết ra dù evidence topic gate fail.
7. **"Nâng chất lượng" bằng fine-tune/train model pipeline hoặc build training dataset** (thay vì sửa retrieval/verify/revise/prompt) — vi phạm doctrine agentic-loop, phá topic-agnosticism + auditability. (Distill-để-SPEED hoặc SWAP base hỏng KHÔNG tính.)

---

## ⭐ BẢNG NGƯỠNG: OPERATIVE (code) vs TARGET (aspirational)

> **Quy tắc vàng:** khi viết/sửa code hay đánh giá run, dùng cột OPERATIVE. Cột TARGET là đích cần đạt, **KHÔNG phản ánh hành vi hiện tại**.

| Check | OPERATIVE (enforce thật) | Grep | TARGET |
|-------|--------------------------|------|--------|
| **P0a domain gate** | `ev_threshold = min(0.40, max(0.30, min_topic_rel−0.10))` → **HARD BLOCK** round cuối, PRE-writer | `ev_threshold =` | ≥0.80 topic purity |
| **Topic relevance (G4)** | **ENFORCED**: điều kiện của `gate_ok` + StageE chặn best-topic <0.50. Blend `0.6·answer_relevance(gemma) + 0.4·term-overlap`, có floor bảo vệ khi term đủ & không drift | `def topic_relevance_check` | ✅ đã enforce |
| **Citation precision (G2)** | **GATE SỐNG**: `≥ min_cite_precision` để clean-accept; đo thật per-`[N]` bằng gemma. Judge tính paraphrase-trung-thực = supports; contradicts/unrelated giữ strict | `min_cite_precision` (`deep_investigate.py`) · `def verify_section` (`verify.py`) | discriminate, không floor |
| **Grounding (HHEM/G3)** | **LOG-only / advisory** — đã bỏ khỏi gate. Strict-NLI under-score prose tổng hợp → KHÔNG phải metric chất lượng | `min_grounding=` (in ra kèm "NOT enforced") | — |
| **StageE hard block** | best-topic <0.50 (sau-loop, độc lập grounding) → BLOCK | `StageE HARD BLOCK` | (giữ) |
| **Citation count** | `n_cites > 0` (điều kiện `gate_ok`) | `gate_ok =` | diversity ≥10 unique |
| **Cross-refs** | 2 nếu ≥2 prior section · 1 nếu 1 prior · 0 nếu section đầu | `has_min_cross_refs` | ≥2/section |
| **Min word count** | HARD: dưới ngưỡng → retry, round cuối BLOCK (StageD) | `word_count=` (`deep_investigate.py`) | — |
| **P0c seen-penalty** | `max(0.05, (1 − seen/max_seen)²)`; canonical + pool-rescued **EXEMPT** | `seen_counts` (`notes.py`) | <50%/paper |
| **Prefilter cosine** | drop dưới `min_relevance`; grey-domain ngưỡng cao hơn | `min_relevance` (`notes.py`) | — |
| **Outline semantic overlap** | audit **flag advisory** theo title-jaccard (không block)… | `jaccard >=` (`outline_from_research.py`) | … |
| **Outline anti-matrix** | …nhưng `enforce_outline_structure()` **ENFORCED**: collapse suffix aspect-matrix quá cap + drop cross-chapter near-dup, chạy **mọi path**, rồi re-audit | `def enforce_outline_structure` | jaccard thấp, 0 matrix |
| **Heading hygiene (assemble)** | dup/orphan → **WARN only**; section vắng `state.json` hoặc `quality=BLOCKED` bị **bỏ hẳn** khỏi book | `if key not in sections` | FAIL nếu dup |
| **max_rounds** | **3 default khác nhau**: CLI `--max-rounds`=3 · `run_v3()`=2 · `run_full.sh N_ROUNDS`=2 | `max_rounds` | — |
| **Embed model** | **UNIFIED** `bge-m3:latest` mọi path (retrieval RRF/prefilter, query_router, verify-side) | `EMBED_MODEL` | — |

✅ **Ngưỡng single-source (drift đã diệt, PR#28):** gate threshold sống MỘT chỗ cạnh logic — `AUTO_SUPPORT_COS`/`AUTO_UNRELATED_COS` → `verify.py`; `RELEVANCE_FLOOR`/`TOP_K_*` → `rerank.py`; `HHEM_SUPPORT` → `faithfulness.py`. `config.py` chỉ giữ model name + provider. `eval/verify_all.py` (check E) chặn tái phát drift.

⚠️ Các số `0.80 grounding`, `0.80 topic_purity`, `jaccard 0.30/0.70` xuất hiện trong tài liệu cũ là **TARGET**, KHÔNG được enforce. Đừng trích làm hành vi thật.

---

## Gate A–F (map về code thật)

| Gate | Tên | Enforcement thật | File |
|------|-----|------------------|------|
| **A** Structure | Outline audit + anti-matrix | Generator sinh outline theo **chunked** (chapter skeleton → sections per chapter, JSON nhỏ hợp lệ, section emerge từ evidence chương). Audit là advisory, NHƯNG `enforce_outline_structure()` **ENFORCED** trên mọi path → outline `ok=false` không còn ship nguyên xi | `outline_from_research.py` |
| **B** Evidence | P0a domain gate · P0b canonical inject · P0c seen-penalty · prefilter | **HARD BLOCK** (P0a round cuối). **Evidence-pool rescue**: post-prefilter on-topic quá ít → mượn sibling sources (qua cùng prefilter), **P0c-EXEMPT** | `deep_investigate.py`, `notes.py`, `discovery.py` |
| **C** Writing | min word count, citation cleanup | **HARD BLOCK** word-count; dedup chưa wire vào writer → PARTIAL | `deep_investigate.py` |
| **D** Verify | clean-accept = topic (G4) + `n_cites>0` + cross-ref + cite_precision (G2); grounding log-only | **ENFORCED** — G2 chạy thật, StageE chặn best-topic sau-loop | `deep_investigate.py`, `verify.py` |
| **E** Coherence/Assembly | dup/orphan heading | **WARN only** → PARTIAL. Stage-F `decite` gỡ name-drop nội-sách (deterministic) | `deep_research_v3.py`, `decite.py` |

> GATE-0..6 / DR3-Eval / DREAM trong `eval/PRODUCT_QUALITY_CRITERIA.md` + `eval/product_quality_verifiers.py`: **KHÔNG được import vào runtime** → **eval-only, không chạy lúc generate**. Đừng giả định chúng đang bảo vệ run.

---

## Verify layer — LIVE vs LEGACY

- **LIVE (gọi mỗi round):** `grounding_score` (HHEM — **G3 log-only/advisory**) · `topic_relevance_check` (**G4 ENFORCED**) · `verify_section` (**G2 cite_precision — GATE SỐNG**, đo thật) · `verify_cross_references_v2` (regex đếm).
- **LEGACY-only** (chỉ `legacy/deep_research.py`/scripts/eval gọi — ĐỪNG sửa như live): `verify_section_v2`, `crag_decision`, `strip_refine`, `scrub_unsupported_citations`.
- **Gate cứng SỐNG = P0a (pre-writer) + G2 cite_precision + G4 topic + StageD word-count.**
- **Invariant:** mọi message HARD in ngưỡng **thật** (biến, không literal) · 1 định nghĩa grounding + 1 định nghĩa topic · 1 embed model · **mọi judge = model LOCAL (gemma / HHEM / bge)**, KHÔNG Claude/external lúc runtime · **Verifier ≠ Writer** (grounding=HHEM, topic/cite=gemma, writer=Qwen).
- Guard chống rubber-stamp: `eval/bench_cite_discrimination.py` chạy THẬT `verify_section` trên labeled GOOD / BAD_unrelated / BAD_contradict, assert GOOD qua ngưỡng ∧ gap đủ rộng. Unit test verify: `eval/test_verify_optim.py`.
- ⏳ Roadmap (chưa có): G5b resolve "Section N.M" vs outline thật (HARD) · G6 redundancy cosine vs prior (hiện soft/warn). Thứ tự ưu tiên → `docs/plan.md`.

---

## Hardcoded Agent Rules (đồng bộ Guardrails ở `CLAUDE.md §6`)
1. Không tối ưu completion rate / word count trước quality.
2. **Grounding pass ≠ success** — grounding là advisory. Tín hiệu sống = G4 topic + G2 cite_precision. StageE fire theo best-topic sau-loop, độc lập grounding.
3. Outline sai logic → sửa outline trước, không đắp prompt writer.
4. Drift phát hiện → chặn ở gate, không để writer "viết xong rồi tính".
5. Canonical = protected + P0c-exempt — không phá exemption.
6. Root-cause fix > patch bề mặt.
7. Sau mỗi stage: trim context + archive intermediates + cập nhật `short-memory.md`.
8. **Cải thiện ở AGENTIC LOOP** (retrieval/verify/revise/prompt/evidence-selection), **KHÔNG fine-tune & KHÔNG build dataset**. Bottleneck writer-grounding → verify-revise loop (feed G2 per-`[N]` verdict ngược writer), không phải weight.

## Agent Efficiency — Token & Memory
- **State file thay vì inline context:** pipeline state → `state.json`; outline/section body ghi file, truyền path. Không re-send full conversation giữa các stage.
- **Trim sau mỗi stage:** giữ TopicProfile/outline/verdict, bỏ scratch + evidence không dùng.
- **Compact prompt:** query-gen template-based · verify rubric cố định · writer chỉ nhận section goal + evidence path + tóm tắt prior sections.
- **Memory gọn:** `short-memory.md` ≤50 dòng (snapshot, không lịch sử) · `long-memory.md` <200 dòng (journal, 1–3 dòng/mục, nén khi qua milestone).
- **Cache:** LLM output → file (không giữ RAM) · embeddings → vector store · search results → disk, chỉ giữ top-K.

## Compact Notation
```
DSC Discovery · OUT Outline · RSR Research[q,src] · QGN QueryGen · RRK Rerank · RRF RankFusion
EVG[rel=0.41] P0a gate · P0b(canon=N) · P0c(pen=0.20x) · WRT[g=0.85,wc=760] · VFY[topic=0.75]
FAIL hard block · PASS all gates green
```

## Claim Policy
Không claim "book-quality / research-grade / benchmark-ready" khi chưa có nhiều run liên tiếp chứng minh: canonical recall, topic purity, evidence-domination control, book coherence. Khi trích số của một run: **luôn kèm ngày + trạng thái gate lúc đó** — nhãn `quality` KHÔNG so sánh được xuyên phiên bản gate.
