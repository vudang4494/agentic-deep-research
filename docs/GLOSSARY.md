# Glossary — Thuật ngữ hệ thống

> **Mục đích:** định nghĩa chuẩn thuật ngữ, dùng chung cho mọi file trong project. Đọc file này TRƯỚC.
> **File này định nghĩa TỪ, không giữ NGƯỠNG.** Mọi con số → `docs/RULES.md`, và cuối cùng là **code**. Không changelog, không số đo một lần, không số dòng code.

---

## A. Kiến trúc Pipeline

| Term | Viết tắt | Định nghĩa |
|------|----------|------------|
| **Discovery** | DSC | Stage 0: phân tích topic → `TopicProfile` |
| **Outline Generation** | OUT | Stage 1: tạo cấu trúc chương/section **TỪ evidence** (không pre-template) |
| **Deep Investigation** | DI | Stage 2: mỗi section chạy vòng lặp research → rank → gate → write → verify |
| **Topic Profile** | TP | Struct: title, description, canonical papers, canonical terms, must-cover, out-of-scope |
| **Outline Profile** | OP | Struct: title, `chapters[]`, `sections[]` |
| **Chapter / Section** | CH / SEC | Chương · phần trong chương (vd "1.1 Introduction") |
| **State File** | | `output/runs/<name>/state.json` — section đã viết, tổng words, `seen_counts`. Là **cơ chế resume**: re-run cùng `--out-name` sẽ bỏ qua section đã có |
| **Assemble** | | Stage 3: gộp section thành `book.md` + hygiene (math, heading, `decite`) |
| **Render** | | Stage 4 (`--render`): `book.md` → PDF/HTML qua pandoc + tectonic |
| **Smoke** | | Chế độ **MẶC ĐỊNH**: cắt outline còn vài chương để chạy nhanh. Muốn sách đầy đủ phải truyền `--no-smoke` |

## B. Kiểm soát chất lượng

| Term | Định nghĩa |
|------|------------|
| **Hard Block** | Check fail → DỪNG, không viết section. Đối lập **Soft Block** (vẫn ship nhưng hạ nhãn chất lượng) |
| **Quality label** | Giá trị trường `quality` trong `state.json`: **`ok`** = qua sạch mọi gate sống · **`degraded`** = có nội dung nhưng trượt một gate mềm · **`BLOCKED`** = bị gate cứng chặn, **không vào book** (bỏ cả heading). ⚠️ Nhãn này **KHÔNG so sánh được xuyên phiên bản gate** |
| **Orchestration-layer improvement (doctrine)** | Cải thiện chất lượng ở tầng **orchestration/inference** (retrieval · verify · revise-loop · prompt · evidence-selection) — **KHÔNG fine-tune model, KHÔNG build dataset** (giữ topic-agnostic, prompt-robust, auditable). Xem `CLAUDE.md §2` |
| **P0a — Domain Relevance Gate** | Kiểm evidence pool có đúng domain **TRƯỚC khi viết**, qua `notes.check_evidence_domain()` = keyword-overlap + gemma judge (không phải LLM-judge thuần). **Gate cứng, PRE-writer.** Ngưỡng → `RULES.md` |
| **P0b — Canonical Injection** | Ép paper nền tảng của topic vào pool ngay từ Discovery (`--canonical-arxiv-ids`, `canonical_seeds.py`): force-fetch + đánh dấu protected |
| **P0c — Seen Penalty** | Phạt nguồn đã dùng ở nhiều section trước (trong RRF) để một paper không dominate cả sách. Canonical + pool-rescued được **EXEMPT** |
| **Protected source** | Nguồn canonical: **bypass** cosine prefilter + **exempt** khỏi P0c. Phá exemption này → canonical recall sụp về 0 |
| **Evidence Gate** | Trước writer: (1) pool không rỗng, else HARD BLOCK; (2) domain-relevance ≥ `ev_threshold` (P0a). KHÔNG có gate "đủ terms" riêng |
| **Evidence-pool rescue** | Khi sau prefilter còn quá ít nguồn on-topic → mượn nguồn của **section anh em** trong cùng run (vẫn qua prefilter), và **exempt P0c**. Chống block vì thiếu retrieval chứ không phải vì sai topic |
| **StageD / StageE** | Chốt kiểm cuối vòng lặp: **StageD** = word-count/cross-ref tối thiểu · **StageE** = HARD BLOCK khi best-topic dưới ngưỡng sau khi hết round (độc lập grounding) |
| **ReAct re-dispatch** | Section bị block được **retry MỘT lần** với nhiều round hơn + full provider set, trước khi stub `[BLOCKED]`. → block-rate trong `state.json` là số **sau** retry |
| **Grounding Score** | Điểm HHEM v2 (NLI). **G3 = log-only/advisory**, đã bỏ khỏi gate: strict-NLI under-score prose tổng hợp → **không phải metric chất lượng** |
| **Topic Relevance Score** | Mức đúng chủ đề của nội dung. **G4 = blend** `answer_relevance` (gemma LOCAL) + term-overlap, có floor bảo vệ khi term đủ và không drift. **ENFORCED** |
| **Citation Precision** | **G2**: tỉ lệ marker `[N]` mà evidence tương ứng thật sự support claim, chấm per-`[N]` bằng gemma. `supports` tính cả **paraphrase trung thực**; `contradicts`/`unrelated` giữ strict. **Gate sống** |
| **Citation Count** | Số lần nguồn được trích trong text. Zero citation = section không có evidence |
| **Cross-reference** | Câu dẫn chiếu section trước (đếm bằng regex). Yêu cầu tăng theo số section đã viết |
| **Verifier ≠ Writer** | Bất biến chống self-preference: grounding = HHEM · topic/citation = gemma · writer = Qwen. Không để writer tự chấm văn mình |
| **Decite** | Stage-F cleaner: writer hay name-drop **TITLE của section anh em** như thể paper ngoài → gỡ deterministic, chỉ xoá khi khớp đúng một section title, giữ nguyên `[N]`/cite ngoài |
| **Claim-aware excerpt** | Chọn đoạn trích của nguồn theo **argmax cosine với section prompt** (window chồng lấp) thay vì cắt phần đầu tài liệu — phần đầu thường không chứa fact cần cite |
| **Matrix pattern** | Anti-pattern: outline sinh theo tích `chapters × concepts` → hàng loạt section `{base}: {aspect}` gần trùng nhau. Bị `enforce_outline_structure()` collapse |

## C. Retrieval

| Term | Viết tắt | Định nghĩa |
|------|----------|------------|
| **Source** | | Một nguồn: id, title, url, excerpt |
| **Canonical Paper** | | Paper nền tảng bắt buộc phải có của topic (vd "Attention Is All You Need") |
| **Provider** | | Backend tìm kiếm: arxiv · wikipedia · tavily · brave · ddg. Provider thiếu API key = **no-op an toàn**, không lỗi |
| **BM25** | | Sparse retrieval: khớp keyword, không cần embedding |
| **Cosine Similarity** | | Dense retrieval: khớp theo embedding vector |
| **Reciprocal Rank Fusion** | RRF | Gộp nhiều ranker (BM25 + cosine) bằng `1/(k+rank)` |
| **Reranker / Cross-Encoder** | RRK | Re-rank kết quả retrieval — `BAAI/bge-reranker-v2-m3` (transformers, không qua Ollama) |
| **Prefilter** | | Chỗ **hard-drop duy nhất** của pool: loại nguồn dưới ngưỡng cosine (grey-domain khắt khe hơn). Protected source bypass |
| **Embedding Model** | | **UNIFIED** `bge-m3:latest` mọi path: retrieval (RRF/prefilter), query_router, verify-side |
| **Primary / Secondary Source** | | arxiv, wikipedia = primary · blog/medium/substack = secondary |
| **Grey Domain** | | Domain độ tin thấp hơn, đã whitelist — áp ngưỡng prefilter cao hơn |

## D. Mô hình (tất cả LOCAL)

| Vai trò | Model |
|---------|-------|
| **Discovery / Outline / Query-Gen / Judge** | `gemma4:e4b` |
| **Writer** | `batiai/qwen3.6-35b:iq3` |
| **Embed** | `bge-m3:latest` |
| **Rerank** | `BAAI/bge-reranker-v2-m3` |
| **Grounding** | `vectara/hallucination_evaluation_model` (HHEM v2) |

> **LOCAL-ONLY:** mọi model inference chạy cục bộ (Ollama + transformers). **KHÔNG gọi Claude/OpenAI/external API lúc runtime.** Search provider ngoài (tavily/brave/ddg) KHÔNG vi phạm — LOCAL-only nói về *model inference*.

## E. Lỗi đã biết

| Term | Định nghĩa | Root cause |
|------|------------|------------|
| **Domain Mismatch** | Evidence lấy từ domain sai (vd paper RAG cho section RLHF) | Query generator gửi nhầm archetype |
| **Evidence Domination** | Một paper xuất hiện ở >50% section | Thiếu penalty cho nguồn trùng (→ P0c) |
| **Canonical Miss** | Paper nền tảng không retrieve được | Search API ưu tiên paper mới (→ P0b) |
| **Zero Citation** | Section không trích nguồn nào | Evidence rỗng hoặc writer không cite |
| **Hollow heading** | Heading có trong book nhưng không có nội dung | Assemble duyệt full outline thay vì chỉ section có trong `state.json` (đã fix) |

## F. Ký hiệu Logging

| Ký hiệu | Viết đầy | Ý nghĩa |
|---------|----------|---------|
| `DSC` | Discovery | Phân tích topic |
| `OUT` | Outline | Sinh cấu trúc sách |
| `RSR` | Research | Thu thập nguồn |
| `QGN` | Query Gen | Sinh truy vấn |
| `RRK` / `RRF` | Rerank / Rank Fusion | Re-rank · gộp BM25+cosine |
| `WRT` | Write | Viết section |
| `VFY` | Verify | Kiểm grounding/topic/citation |
| `DI` | Deep Investigation | Toàn bộ stage 2 |

## G. Nhãn thực nghiệm

| Label | Ý nghĩa |
|-------|---------|
| **Run** | Một lần chạy pipeline trên một topic (một run-dir) |
| **Smoke test** | Chạy rút gọn để verify fix hoạt động, không phải để đánh giá chất lượng |
| **Eval artifact** (BAER · `eval/product_quality_verifiers.py`) | Công cụ **ĐO** chất lượng run đã xong — **eval-only, không chạy trong pipeline**, và KHÔNG phải training data |

## H. Acronyms

| Acronym | Giải nghĩa |
|---------|------------|
| RRF · RRK | Reciprocal Rank Fusion · Reranker |
| QGN · WRT · VFY · DI | Query Generator · Writer · Verifier · Deep Investigation |
| TP · OP | Topic Profile · Outline Profile |
| HHEM | Hallucination Evaluation Model (Vectara) |
| NLI | Natural Language Inference |
| arxiv · wiki · ddg | arxiv.org · Wikipedia · DuckDuckGo |
| CoT · DPO · RLHF · RoPE | Chain-of-Thought · Direct Preference Optimization · RL from Human Feedback · Rotary Position Embedding |
