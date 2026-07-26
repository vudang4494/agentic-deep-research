# Plan — Roadmap nâng cấp

> **Vai trò:** nơi DUY NHẤT trả lời *"còn phải làm gì, theo thứ tự nào"*.
> **Không changelog** (việc đã xong để lại đúng 1 dòng; post-mortem → `memory/long-memory.md`) · **không số dòng code** (dùng grep anchor) · **không số đo một lần** (đo lại rồi hãy tin).
> Ngưỡng & gate hiện hành → `docs/RULES.md` → cuối cùng là **code**. Doctrine → `CLAUDE.md §2`.
> Lịch sử thiết kế v3 gốc + khung eval tháng 6 (đã supersede) → `git log` / `memory/long-memory.md`.

## Bất biến — áp cho MỌI item dưới đây
**LOCAL-only** · **Verifier ≠ Writer** · **fix ở GATE, không ở writer** · **outline emerge từ evidence** · **KHÔNG fine-tune & KHÔNG build dataset** (mọi lever là retrieval/verify/revise-loop/prompt/evidence-selection).
Mỗi item phải có **validation run đo Acceptance** trước khi tin là xong.

## ✅ Đã xong (chi tiết → `memory/long-memory.md`)
P0 + P0-2b (faithfulness gate sống lại: G2 chạy thật, grounding log-only, P0c fire) · P0.5 (best-round pin, hết hollow heading) · P0.6 (G2 parse fix — discrimination bất đối xứng) · P0.7 (claim-aware excerpt) · P0.8 (`.env` auto-load) · **P1-1 matrix HARD gate — PR#25** (`enforce_outline_structure` + suffix-detector đã wire vào `audit_outline`, grep `MATRIX_PATTERN_BLOCK`) · brave provider — PR#26.
**P1 batch (PR#28–#32)** · **P1-3** math validation (whole-word `\left/\right`, paren-balance, `coloneqq` — grep `_math_span_valid`) · **P1.5** verify-revise surgical per-`[N]` fix-list vào REVISE MODE (grep `revise_fixlist`) · **P1-4** near-miss re-query rescue (grep `_near_miss_used`) · **P1-2** sentence dedup lúc assemble (`dedup.drop_duplicate_sentences`) · **P1-5** held-out judge độc lập (`eval/held_out_judge.py`, kappa vs model khác họ). · **Product audit fixes** (best-round sentinel, P0a arxiv-penalty, atomic state write, render title/mermaid — grep `_have_best` / `_atomic_write_text`).

---

# Việc còn mở

> P1-2..P1-5 đã ship (xem "✅ Đã xong"). Riêng **P1-4** & **P1-5** vẫn cần **validation run** để định lượng (block-rate giảm mà cite_precision giữ; kappa held-out trên model khác họ thật, không phải qwen-writer-proxy) — chưa đo trên full run.

## 1. P2 — Năng lực agentic sâu hơn (sau khi P1 xong)

- **P2-1 · Citation-graph 2nd-hop:** pool thưa cho sub-topic ngách → follow reference của top paper (arxiv refs / semantic-scholar) để lấy nguồn 2nd-hop on-topic, nạp qua **cùng prefilter** + P0c-exempt như evidence-pool. Acceptance: pool-depth tăng cho topic ngách, đếm được số lần rescue fire.
- **P2-2 · Primary-source routing:** marker `[N]` ở dòng định nghĩa/phương trình đôi khi trỏ aggregator thứ cấp thay vì paper gốc → ưu tiên primary khi cite block định nghĩa/equation (match canonical arxiv ID nếu có trong pool). Acceptance: % primary-cite trên equation line tăng.

---

## Ghi chú thứ tự
**P1-3 đứng đầu** vì risk 0 và bug vừa reproduce lại hôm nay — làm xong không cần validation run tốn kém. **P1.5 xếp thứ 2** vì nó đánh đúng residual cuối (writer grounding) bằng đúng lever doctrine, và dữ liệu feedback (`verdicts` per-`[N]`) **đã có sẵn** — không phải xây mới. P1-4 và P1-2 đều cần validation run / là polish. P1-5 chốt cuối vì đang BLOCKED trên việc chọn model.
