# Glossary -- Thuật ngữ hệ thống

> **Mục đích:** Định nghĩa chuẩn tất cả thuật ngữ. Dùng cho mọi file trong project.

---

## A. Kiến trúc Pipeline

| Term | Viết tắt | Định nghĩa |
|------|-----------|-------------|
| **Deep Investigation** | DI | Giai đoạn 2: với mỗi section, thực hiện research (tìm nguồn) -> write (viết) -> verify (kiểm tra) |
| **Discovery** | | Giai đoạn 0: phân tích topic, tạo TopicProfile |
| **Outline Generation** | | Giai đoạn 1: tạo cấu trúc chương/phần từ evidence |
| **Topic Profile** | TP | Data structure chứa: title, description, canonical papers, key concepts, search queries |
| **Outline Profile** | OP | Data structure chứa: title, chapters[], sections[] |
| **Chapter** | CH | Một chương trong sách |
| **Section** | SEC | Một phần trong chương, ví dụ "1.1 Introduction" |
| **State File** | | `state.json` -- lưu trạng thái run: sections đã viết, tổng words, seen_counts |

## B. Kiểm soát chất lượng

| Term | Định nghĩa |
|------|-------------|
| **Hard Block** | Khi kiểm tra fail, DỪNG và báo lỗi. Không viết section. Đối lập với Soft Block. |
| **Soft Block** | Khi kiểm tra fail, vẫn tiếp tục nhưng đánh dấu chất lượng giảm. |
| **Domain Relevance Gate (P0a)** | Kiểm tra evidence pool đúng domain trước khi viết, qua `notes.check_evidence_domain()` = keyword-overlap + optional gemma judge (KHÔNG phải LLM-judge thuần). Threshold THẬT ≈ 0.40 (`deep_investigate.py:479`), KHÔNG phải 0.60. Accept-topic (writer) = 0.50. Ngưỡng chuẩn: RULES.md |
| **Evidence Gate (P0a/B)** | Trước writer: (1) pool không rỗng (else HARD BLOCK); (2) domain-relevance ≥ ev_threshold≈0.40. KHÔNG có gate "đủ terms" riêng. |
| **Grounding Score** | Điểm hallucination detection (0-1), model HHEM v2. ⚠️ Trên run v36 g=1.0 BÃO HÒA toàn bộ 280 section → non-discriminating; KHÔNG dùng làm tín hiệu chất lượng (xem CLAUDE.md Guardrail 2). |
| **Topic Relevance Score** | Điểm content đúng chủ đề (0-1). ⚠️ Tính bằng HEURISTIC term-presence + word-overlap (`verify.py:342`, KHÔNG LLM) → quantized {0.5, 0.75, 1.0}, không phải judge ngữ nghĩa. |
| **Citation Count** | Số lần nguồn được trích dẫn trong text. Zero citation = section không có evidence |

## C. Retrieval (Tìm kiếm nguồn)

| Term | Viết tắt | Định nghĩa |
|------|-----------|-------------|
| **Source** | | Một nguồn tìm được: có id, title, url, excerpt |
| **Canonical Paper** | | Paper nền tảng bắt buộc phải có (ví dụ "Attention Is All You Need") |
| **BM25** | | Sparse retrieval: tìm theo keyword matching. Không cần embedding |
| **Cosine Similarity** | | Dense retrieval: tìm theo embedding vector similarity |
| **Reciprocal Rank Fusion** | RRF | Gộp nhiều rankers (BM25 + Cosine) bằng công thức 1/(k+rank) |
| **Reranker / Cross-Encoder** | RRK | Mô hình re-rank kết quả retrieval. Model: BAAI/bge-reranker-v2-m3 |
| **Embedding Model** | | SPLIT: retrieval (notes.rank/prefilter) + query_router chạy `nomic-embed-text` lúc runtime; `bge-m3:latest` CHỈ ở verify-side (`verify.py:35`) + default embeddings.py. Hai model, hai path. |
| **Primary Source** | | arxiv.org hoặc wikipedia -- nguồn đáng tin cậy |
| **Secondary Source** | | Blog, medium, substack -- nguồn phụ |
| **Grey Domain** | | Domain có thể kém tin cậy (đã được whitelist) |

## D. Mô hình AI

| Term | Model | Vai trò |
|------|-------|---------|
| **Writer** | `batiai/qwen3.6-35b:iq3` | Viết nội dung section |
| **Query Generator** | QGN | Sinh search queries từ section title |
| **Judge / Verifier** | | Grounding = HHEM (model). Topic relevance = HEURISTIC (KHÔNG LLM). P0a domain = check_evidence_domain (gemma). |
| **Discovery Model** | | Phân tích topic, tạo TopicProfile |
| **Outline Model** | | Tạo outline từ evidence |

## E. Các lỗi đã biết

| Term | Định nghĩa | Root cause |
|------|-------------|------------|
| **Domain Mismatch** | Evidence tìm từ domain sai (ví dụ: RAG paper cho RLHF section) | Query generator gửi nhầm archetype |
| **Evidence Domination** | Một paper xuất hiện trong >50% sections | Không có penalty cho nguồn trùng lặp |
| **Canonical Miss** | Paper nền tảng không được retrieve | Search API ưu tiên paper mới |
| **Zero Citation** | Section không trích dẫn nguồn nào | Evidence rỗng hoặc writer không cite |

## F. Ký hiệu Logging

| Ký hiệu | Viết đầy | Ý nghĩa |
|---------|-----------|----------|
| `RSR` | Research | Thu thập nguồn |
| `QGN` | Query Gen | Sinh truy vấn |
| `WRT` | Write | Viết section |
| `VFY` | Verify | Kiểm tra grounding |
| `RVW` | Review | Đánh giá chất lượng |
| `RRK` | Rerank | Re-rank kết quả retrieval |
| `RRF` | Rank Fusion | Gộp BM25 + Cosine |
| `DI` | Deep Investigation | Toàn bộ stage 2 |

## G. Experiment Labels

| Label | Ý nghĩa |
|-------|----------|
| **Experiment A** | Benchmark 7 topics trước khi có fixes |
| **Experiment B** | Benchmark 7 topics sau khi có P0a/b/c fixes |
| **Smoke Test** | Test nhanh 1 section để verify fixes hoạt động |
| **Run** | Một lần chạy pipeline trên một topic |

## H. Acronyms thường gặp

| Acronym | Giải nghĩa |
|---------|-------------|
| RRF | Reciprocal Rank Fusion |
| RRK | Reranker / Cross-encoder rerank |
| LLM | Large Language Model |
| QGN | Query Generator |
| VFY | Verifier |
| WRT | Writer |
| DI | Deep Investigation |
| TP | Topic Profile |
| OP | Outline Profile |
| arxiv | arxiv.org -- kho paper học thuật |
| wiki | Wikipedia |
| ddg | DuckDuckGo web search |
| CoT | Chain-of-Thought |
| DPO | Direct Preference Optimization |
| RLHF | Reinforcement Learning from Human Feedback |
| RoPE | Rotary Position Embedding |
| HHEM | Hallucination Evaluation Model |
