# Plan — Roadmap nâng cấp

> **Vai trò:** nơi DUY NHẤT trả lời *"còn phải làm gì, theo thứ tự nào"*.
> **Không changelog** (việc đã xong để lại đúng 1 dòng; post-mortem → `memory/long-memory.md`) · **không số dòng code** (dùng grep anchor) · **không số đo một lần** (đo lại rồi hãy tin).
> Ngưỡng & gate hiện hành → `docs/RULES.md` → cuối cùng là **code**. Doctrine → `CLAUDE.md §2`.
> Bản thiết kế v3 gốc + khung eval tháng 6 (đã supersede) → `docs/archive/plan-v3-design-2026-06.md`.

## Bất biến — áp cho MỌI item dưới đây
**LOCAL-only** · **Verifier ≠ Writer** · **fix ở GATE, không ở writer** · **outline emerge từ evidence** · **KHÔNG fine-tune & KHÔNG build dataset** (mọi lever là retrieval/verify/revise-loop/prompt/evidence-selection).
Mỗi item phải có **validation run đo Acceptance** trước khi tin là xong.

## ✅ Đã xong (chi tiết → `memory/long-memory.md`)
P0 + P0-2b (faithfulness gate sống lại: G2 chạy thật, grounding log-only, P0c fire) · P0.5 (best-round pin, hết hollow heading) · P0.6 (G2 parse fix — discrimination bất đối xứng) · P0.7 (claim-aware excerpt) · P0.8 (`.env` auto-load) · **P1-1 matrix HARD gate — PR#25** (`enforce_outline_structure` + suffix-detector đã wire vào `audit_outline`, grep `MATRIX_PATTERN_BLOCK`) · brave provider — PR#26.

---

# Việc còn mở

## 1. P1-3 — Math validation gate · **[RANK 1] impact MED · readiness HIGH · risk 0**

Zero-risk, thuần Python, không đụng writer/verifier, test harness đã có sẵn.

- **Vấn đề — 4 bug, reproduce lại 2026-07-24 (đều CÒN THẬT):**

  | Probe | Kết quả | Mong đợi | Loại |
  |---|---|---|---|
  | `r_i \leftarrow r_i + 1` | `False` | `True` | **false-POSITIVE** — check `\left` bằng substring nên đụng `\leftarrow` |
  | `a \rightarrow b` | `False` | `True` | **false-POSITIVE** — tương tự với `\right` |
  | `\exp(a + b` | `True` | `False` | **false-NEGATIVE** — brace cân nhưng **không hề check paren** → ship math SAI |
  | `x \coloneqq y` | `False` | `True` | thiếu macro trong allowlist |

  Hệ quả false-positive: math hợp lệ bị neutralize thành literal `$$…$$` trong backtick — **"$$-in-backticks leak" chính là output của neutralizer, KHÔNG phải writer leak.**
- **Fix-site:** `research/mathfix.py` — grep `def _math_span_valid` (whole-word regex `\\left(?![A-Za-z])` thay substring) + `_MACRO_ALLOWLIST`.
- **Acceptance:** 4 probe trên đảo đúng chiều · `python3 eval/test_math_char_safety.py` không regress.
- **DON'T:** đụng writer/verifier · nới brace-balance (đang đúng).

## 2. P1.5 — Verify-revise surgical · **lever ĐÚNG doctrine, đánh vào residual thật**

- **Vấn đề:** pipeline đã có multi-round retry và G2 **đã trả verdict per-`[N]`** (`cite_res["verdicts"]` — `{n, verdict, reason}`), nhưng retry-hint hiện **gom chung**, không chỉ cho writer ĐÚNG citation nào hỏng và vì sao → section `degraded` đi hết số round vẫn nằm dưới ngưỡng. Đây là residual cuối: **writer grounding**, không phải retrieval.
- **Fix-site:** `research/deep_investigate.py` vùng retry-hint (grep `verdicts`) — dựng hint per-citation: *"[5] no_evidence — excerpt không nêu X → đổi nguồn HOẶC bỏ claim; [8] unrelated — citation sai → thay"*. Round sau writer revise **trúng chỗ trượt**, không viết lại mù.
- **Acceptance:** tỉ lệ `degraded → ok` tăng (near-miss ngay dưới ngưỡng vượt được sau revise có-hướng), **đồng thời** discrimination test không đổi.
- **TRIPWIRE:** không nới gate để lấy thành tích · không để writer tự chấm (Verifier≠Writer).

## 3. P1-4 — Near-miss rescue thay vì drop cứng · impact HIGH · readiness MED

- **Vấn đề:** `ev_topic_rel` tính **một lần**, dưới `ev_threshold` là round cuối raise thẳng — **0 nhánh re-query**. Evidence-pool rescue không cứu được ca này vì nó trigger theo **pool mỏng** (score-agnostic) và chạy **TRƯỚC** gate. Phần lớn section bị block nằm sát ngay dưới ngưỡng chứ không phải off-domain thật.
- **Fix-site:** `research/deep_investigate.py` — grep `ev_threshold =`; chèn **1 round re-query** nhắm `must_cover` + re-gate TRƯỚC khi raise (tái dùng query_gen + search + `check_evidence_domain`).
- **Acceptance:** block-rate giảm **mà cite_precision không tụt**. Cần **validation run** chứng minh re-query thật sự nâng điểm pool qua ngưỡng (lý do readiness MED).
- **TRIPWIRE (Guardrail 6):** re-retrieve/re-gate THẬT — **KHÔNG hạ `ev_threshold`** (nhóm off-domain thật vẫn phải drop); giữ hard-block làm fallback cuối.

## 4. P1-2 — Paragraph/sentence dedup lúc assemble · impact MED · polish

- **Vấn đề:** assemble chỉ dedup **heading-title**, không dedup câu/đoạn → câu boilerplate lặp nhiều lần xuyên chapter mà section-level Jaccard **không thấy** (mỗi section vẫn khác nhau tổng thể).
- **Fix-site:** `pipeline/deep_research_v3.py` — pass dedup sau khi join, TRƯỚC `normalize_math`; kèm scrub numeric-ref bịa trong `_sanitize_section_content`.
- **Acceptance:** số câu trùng giảm · 0 numeric-ref trỏ section không tồn tại · `eval/check_dedup.py` vẫn PASS.
- **TRIPWIRE:** **deletion-only** — xoá bản lặp, **giữ nguyên lần xuất hiện đầu**, không orphan `[N]`, **không rewrite prose** (đây là presentation-scrub, không phải sửa nội dung); embed phải LOCAL.

## 5. P1-5 — Held-out judge độc lập · impact HIGH · **BLOCKED (cần model)**

- **Vấn đề (vòng tròn eval):** BAER đọc `topic_relevance` do chính pipeline ghi từ G4, và ref-on-topic dùng **cùng scorer cosine** với prefilter/P0a → `topic_pass` gần như **đồng nhất** với `accept_rate` về cấu trúc. Không có judge độc lập nào trong `eval/`.
- **Fix-site:** `eval/benchmark_book.py` (thêm pass judge độc lập trên sample accepted sections) + `eval/aggregate_benchmark.py` (SIGNALS).
- **Acceptance:** có ít nhất 1 số chất lượng **decorrelated** với accept_rate (đo agreement/kappa vs G4).
- **BLOCKER:** phải **chọn + pull (SWAP, KHÔNG train)** một model LOCAL **khác họ** (không gemma-G4, không qwen-writer). Cô lập thành pass optional để giữ tính determinism "no-model" của BAER. Eval-side only.

## 6. P2 — Năng lực agentic sâu hơn (sau khi P1 xong)

- **P2-1 · Citation-graph 2nd-hop:** pool thưa cho sub-topic ngách → follow reference của top paper (arxiv refs / semantic-scholar) để lấy nguồn 2nd-hop on-topic, nạp qua **cùng prefilter** + P0c-exempt như evidence-pool. Acceptance: pool-depth tăng cho topic ngách, đếm được số lần rescue fire.
- **P2-2 · Primary-source routing:** marker `[N]` ở dòng định nghĩa/phương trình đôi khi trỏ aggregator thứ cấp thay vì paper gốc → ưu tiên primary khi cite block định nghĩa/equation (match canonical arxiv ID nếu có trong pool). Acceptance: % primary-cite trên equation line tăng.

---

## Ghi chú thứ tự
**P1-3 đứng đầu** vì risk 0 và bug vừa reproduce lại hôm nay — làm xong không cần validation run tốn kém. **P1.5 xếp thứ 2** vì nó đánh đúng residual cuối (writer grounding) bằng đúng lever doctrine, và dữ liệu feedback (`verdicts` per-`[N]`) **đã có sẵn** — không phải xây mới. P1-4 và P1-2 đều cần validation run / là polish. P1-5 chốt cuối vì đang BLOCKED trên việc chọn model.
