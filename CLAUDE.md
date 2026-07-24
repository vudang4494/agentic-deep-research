# CLAUDE.md — Agentic Deep Research Platform

> **Nguồn sự thật vận hành cho agent.** Ngưỡng & hành vi THẬT nằm trong CODE (`research/*.py`, `pipeline/`), KHÔNG phải trong doc. Nghi ngờ một con số → **grep code**, đừng trích doc làm fact.
>
> **File này KHÔNG chứa changelog và KHÔNG chứa số đo một lần.** Trạng thái hôm nay → `memory/short-memory.md`. Lịch sử/quyết định → `memory/long-memory.md` + `git log`. Roadmap → `docs/plan.md`. Bảng ngưỡng đầy đủ → `docs/RULES.md`. Số của một run → đo lại bằng `tools/report.py`, đừng quote lại từ doc.

## 0. Quy tắc phản hồi
- Trả lời = **tiếng Việt có dấu** + English term khi cần.

## 1. Thứ tự đọc mỗi phiên
1. `docs/GLOSSARY.md` — thuật ngữ chuẩn (ĐỌC TRƯỚC).
2. `memory/short-memory.md` — snapshot trạng thái hiện tại.
3. File này — doctrine, pipeline, model stack, guardrails.
4. `docs/RULES.md` — bảng ngưỡng & gate (khi đụng quality gate / debug drift).

## 2. Doctrine (CỐ ĐỊNH — không đổi)
**Hệ thống KHÔNG được biết trước kịch bản.** Outline phải **emerge từ evidence**, tuyệt đối không pre-template `chapters × concepts` (đó là *matrix pattern* gây trùng lặp — xem Guardrail 3).

**Cải thiện ở tầng ORCHESTRATION/INFERENCE (BẤT BIẾN).** Mọi nâng cấp chất lượng đến từ **retrieval · verify · revise-loop · prompting · evidence-selection** — **KHÔNG fine-tune model, KHÔNG build dataset** (giữ topic-agnostic · prompt-robust · auditable). Bottleneck writer-grounding → fix bằng **verify-revise loop** (feed G2 per-`[N]` verdict ngược writer) + claim-aware excerpt, KHÔNG bằng weight.

```
Prompt thô → Discovery (TopicProfile) → Outline (từ evidence)
   → Deep Investigation mỗi Section: QGN → Search → Rerank → Gate(P0a) → Write → Verify
   → Assemble → (Render PDF)
```

## 3. Pipeline THẬT
> Bản đồ kiến trúc tầng-cao: `docs/agentic-deep-research-architecture.md Phần A`. Mục này = chi tiết code-level (nguồn sự thật vận hành).
> **Không có số dòng trong mục này — chỉ symbol để grep.** Số dòng trôi liên tục; luôn `grep -n "<symbol>" <file>` thay vì nhảy thẳng tới dòng.

- **Orchestrator LIVE:** `pipeline/deep_research_v3.py :: run_v3()`. Launcher: `run_full.sh`.
- **Legacy v2 (ĐỪNG sửa như đang live):** `legacy/deep_research.py` + `runner.py` + `run.sh` + `watch.sh`. Vẫn bị `tools/monitor.py` / `eval/run_eval.py` import → còn sống nhưng KHÔNG phải đường chính.
- **Resume KHÔNG có flag:** re-run cùng `--out-name` là resume tự động (nạp `state.json` + `run_seen_counts` từ `output/runs/<name>/`). **Không bao giờ viết lại Section đã có trong `state.json`** → muốn chạy sạch phải đổi `--out-name` hoặc xoá run-dir.

| # | Stage | File | Vai trò |
|---|-------|------|---------|
| 0 | Discovery (DSC) | `research/discovery.py` | TopicProfile (canonical papers/terms, out_of_scope) + **P0b** canonical injection |
| 1 | Outline (OUT) | `research/outline_from_research.py` | chapters/sections TỪ evidence; `outline_audit` (advisory) + **`enforce_outline_structure()` ENFORCED** (gọi trong `_postprocess_outline` → chạy MỌI path chunked/LLM/fallback): collapse suffix aspect-matrix `{base}: {aspect}` quá `_ASPECT_MATRIX_CAP` (merge `must_cover_terms`, chỉ bỏ section thừa) + drop cross-chapter near-dup theo title-jaccard, rồi **re-audit**. Đây là lý do `ok=false` không còn ship outline bad nguyên xi |
| 2 | Deep Investigation | `research/deep_investigate.py` | vòng lặp per-section `max_rounds` — **3 default khác nhau**: CLI `--max-rounds`=3 · `run_v3()`=2 · `run_full.sh N_ROUNDS`=2 |
| 2a | Query Gen (QGN) | `research/query_gen.py` + `query_router.py` | LLM khi có `domain_context`, else archetype |
| 2b | Search (RSR) | `research/search.py` | `PROVIDERS_DEFAULT` ở `config.py` = arxiv · wikipedia · tavily · brave · ddg. `available_providers()` tự lọc: **tavily** cần `TAVILY_API_KEY`, **brave** cần `BRAVE_API_KEY` (free ~2000 q/mo) → liệt kê mà thiếu key = no-op an toàn. ⚠️ **Tavily billing-dead (HTTP 402, 402≠401 → đổi key KHÔNG chữa; kiểm lại trước khi kết luận)** → thực tế còn arxiv+wiki+ddg(+brave nếu có key) |
| 2c | Rerank (RRK) | `research/rerank.py` | `bge-reranker-v2-m3` (transformers, KHÔNG Ollama) |
| 2d | Rank + Gate | `research/notes.py` | RRF(BM25+cosine) + **P0a** domain gate + **P0c** seen-penalty + prefilter + **evidence-pool rescue** (post-prefilter on-topic quá ít → mượn sibling sources, P0c-EXEMPT; grep `_pool_rescue_ids`) |
| 2e | Writer (WRT) | `deep_investigate.py` (inline) | `qwen3.6-35b:iq3` |
| 2f | Grounding (VFY) | `research/faithfulness.py` | HHEM v2 — **ADVISORY/log-only**, không hard-block |
| 2g | Topic / Cross-ref | `research/verify.py` | topic = **G4** blend term-heuristic + `answer_relevance` gemma LOCAL (grep `def topic_relevance_check`) + StageE floor; cross-ref = regex string match |
| 3 | Assemble | `deep_research_v3.py` | book.md + math/heading hygiene (Stage F) + **`decite.clean_intrabook_citations`** (trong `_sanitize_section_content`): gỡ name-drop nội-sách (writer trích TITLE section anh em như thể paper ngoài), CHỈ xoá khi khớp đúng một section title — `[N]`/cite ngoài được GIỮ + **`dedup.drop_duplicate_sentences`** (Stage-F, deletion-only): bỏ câu boilerplate lặp y hệt xuyên chương, GIỮ lần đầu; byte-conservative (paragraph không dup = nguyên si), bảo vệ code/math/heading/reference. `state.json` ghi **`provenance`** (git SHA + seed=42 + model digest) cho reproducibility |
| 4 | Render `--render` | `scripts/render_book.py` | book.pdf / book.html |

Module phụ trợ (load-bearing): `config.py` (hằng số + `PROVIDERS_DEFAULT`), **`_ollama.py`** (single-source Ollama transport: `OLLAMA_BASE` + `chat()` — mọi module talk-to-Ollama import từ đây, ĐỪNG hardcode lại `localhost:11434`; enforce bởi `verify_all.py` check I), `canonical_seeds.py` (P0b seeds), `embeddings.py`, `fetch.py`, `planner.py`, `types.py`, **`decite.py`** (Stage-F citation cleaner), **`dedup.py`** (Stage-F exact-duplicate sentence remover, deletion-only — single source; test `eval/test_dedup_sentences.py`), **`mathfix.py`** (single-source math/special-char normalization — ĐỪNG tạo bản copy cục bộ, nó sẽ drift).

**Hai hành vi orchestrator dễ hiểu nhầm khi đọc log/state:**
- **ReAct re-dispatch** (`deep_research_v3.py`, grep `ReAct re-dispatch`): section ném `RuntimeError` (P0a/StageE block) được **retry MỘT lần** với `max_rounds+2` + union provider set *trước khi* stub `[BLOCKED]`. → block-rate trong `state.json` là số **sau** retry; và đây là lý do một section chạy hai lượt.
- **BLOCKED không bao giờ vào book** (grep `quality") == "BLOCKED"` trong `assemble_book`): section blocked bị bỏ cả heading, chapter rỗng bị bỏ, và regex chặn chuỗi moderation nội bộ leak vào prose. → block-rate cao KHÔNG tạo trang rỗng, nó làm sách **ngắn đi**.

**Verify layer — LIVE vs LEGACY (đừng sửa nhầm):**
- **LIVE (gọi mỗi round):** `faithfulness.grounding_score` (**G3, log-only/advisory** — KHÔNG trong gate) + `verify.topic_relevance_check` (**G4 — ENFORCED**: điều kiện `gate_ok` + StageE best-topic) + `verify.verify_section` (**G2 — ENFORCED**, cite_precision đo thật) + `verify.verify_cross_references_v2` (regex đếm).
- **LEGACY-only** (chỉ `legacy/deep_research.py` / scripts / eval gọi — ĐỪNG sửa như live): `verify_section_v2`, `crag_decision`, `strip_refine`, `scrub_unsupported_citations`.
- Đổi accept/grounding → sửa vùng verify→gate trong `deep_investigate.py` (grep `gate_ok =`), **KHÔNG** sửa `crag_decision`/`verify_section_v2` (no-op với run thật).
- **Verifier ≠ Writer (bất biến — chống self-preference):** grounding = **HHEM**, topic/citation = **gemma**, writer = **Qwen**. ĐỪNG để Qwen tự chấm prose của chính nó.

## 4. Model stack (THẬT)
| Vai trò | Model |
|---------|-------|
| Discovery / Outline / Query-Gen / Judge | `gemma4:e4b` |
| Writer | `batiai/qwen3.6-35b:iq3` |
| Embed | **`bge-m3:latest` THỐNG NHẤT**: retrieval (`notes` RRF/prefilter) + `query_router` + verify-side đều bge-m3 (grep `EMBED_MODEL` / `DEFAULT_MODEL`). **0 ref nomic sống** — nomic cần prefix `search_query:`/`search_document:` mà code không truyền → asymmetric, đã bỏ. |
| Rerank | `BAAI/bge-reranker-v2-m3` (transformers) |
| Grounding | `vectara/hallucination_evaluation_model` (HHEM v2) |

> **LOCAL-ONLY (bất biến):** mọi model trong pipeline chạy cục bộ (Ollama `localhost:11434` + transformers). Mọi judge — P0a domain, G4 topic, G2 citation — đều **gemma4:e4b LOCAL**; grounding **HHEM local**; embed **bge-m3 local**. **TUYỆT ĐỐI KHÔNG gọi Claude/OpenAI/external API lúc runtime.** Claude (tôi) chỉ review + chuẩn hoá docs + thiết kế cấu trúc verify, KHÔNG phải một model trong pipeline. (Search provider ngoài như tavily/brave KHÔNG vi phạm điều này — LOCAL-only nói về *model inference*.)

## 5. Gate đang SỐNG (code = chuẩn; chi tiết → `docs/RULES.md`)
> Giá trị dưới đây là **ảnh chụp để định hướng** — trước khi dựa vào bất kỳ số nào, `grep` symbol tương ứng để xác nhận.

| Gate | Hành vi | Grep |
|------|---------|------|
| **P0a domain gate** | `ev_threshold = min(0.40, max(0.30, min_topic_relevance−0.10))` — **HARD BLOCK** ở round cuối, PRE-writer. **Near-miss rescue (P1-4):** nếu `ev_topic_rel` chỉ dưới bar trong `_NEAR_MISS_DELTA` (0.10) → cấp **1 bonus round** re-query focused vào `must_cover` TRƯỚC khi BLOCK (fire 1 lần; section vẫn phải clear bar — không hạ ngưỡng) | `ev_threshold =` / `_near_miss_used` trong `deep_investigate.py` |
| **Accept Section** | `topic≥0.50 (G4) AND n_cites>0 AND cross-ref AND cite_precision≥0.45 (G2)`; grounding KHÔNG tham gia | `gate_ok =` trong `deep_investigate.py` |
| **StageE HARD BLOCK** | fire khi `not accepted AND best_topic_relevance<0.50` (sau-loop, độc lập grounding) | `StageE HARD BLOCK` |
| **P0c seen-penalty** | `max(0.05, (1 − seen/max_seen)²)`; canonical + pool-rescued **EXEMPT** | `seen_counts` trong `notes.py` |
| **Prefilter cosine** | `min_relevance` (grey-domain cao hơn) | `min_relevance` trong `notes.py` |
| **StageD word-count / cross-ref** | min words + số cross-ref theo số prior sections | `deep_investigate.py` |

→ **Gate cứng SỐNG = P0a (pre-writer) + G2 cite_precision + G4 topic + StageD word-count.** Grounding (HHEM) là advisory.

⚠️ Các số `0.80 grounding`, `0.80 topic_purity`, `jaccard 0.30/0.70` trong tài liệu cũ là **ASPIRATIONAL (target), KHÔNG được enforce**. Đừng trích chúng làm hành vi thật.

✅ **Ngưỡng single-source (drift đã diệt):** mỗi ngưỡng chỉ định nghĩa MỘT chỗ — model name → `config.py`; gate threshold (`AUTO_SUPPORT_COS`, `RELEVANCE_FLOOR`, `HHEM_SUPPORT`…) → cạnh logic ở `verify.py`/`rerank.py`/`faithfulness.py`. Bất-biến này do `eval/verify_all.py` (check E/F) enforce — **chạy nó trước khi ship.**

## 6. Guardrails — tránh đi sai hướng product/process
1. **Output goal > volume.** Đây là technical book đúng-topic, grounded, auditable — KHÔNG phải máy sinh chữ. Run 700 trang mà drift/lặp = **FAIL**. Đừng tối ưu section/word/completion trước topic purity & non-redundancy.
2. **Grounding KHÔNG phải chất lượng.** HHEM strict-NLI under-score prose tổng hợp → đã bỏ khỏi gate, chỉ log. Tín hiệu SỐNG = **G4 topic** + **G2 cite_precision**. Đừng green-light run chỉ vì grounding; cũng đừng "sửa" nó.
3. **Outline EMERGE từ evidence — GIẾT matrix pattern.** Không pre-template chapters×concepts. `outline_audit ok=false` → **sửa OUTLINE trước Stage 2**, không vá ở writer. *Matrix/overlap giờ ĐÃ tự động* qua `enforce_outline_structure()`. Còn LẠI thủ công = `coherence_low` + `missing_canonical_terms` (outline over-reach vào title hẹp/frontier) — chưa có lever tự động.
4. **Fix ở GATE, không ở writer.** Drift / off-topic evidence / canonical thiếu / nguồn dominate phải chặn ở P0a/P0b/P0c/prefilter (`notes.py`, `deep_investigate.py`). Không cho writer "cứ viết rồi tính".
5. **Canonical papers được PROTECT, không penalize.** `protected_source_ids` bypass cosine prefilter + EXEMPT khỏi P0c. Mọi thay đổi retrieval/dedup phải giữ exemption này (mất → canonical recall sụp về 0).
6. **Enforce reference relevance theo SECTION.** Canonical recall cao che giấu sourcing kém per-section. Siết prefilter/domain gate; không accept section chỉ vì nó có nhiều citation.
7. **Ngưỡng sống trong CODE, doc là advisory.** Đừng quote số trong doc làm fact — grep `config.py` / `deep_investigate.py` / `notes.py` / `verify.py`. **Đừng thêm số dòng vào doc** (chúng trôi mỗi lần refactor) — dùng symbol. *Lưu ý:* `eval/product_quality_verifiers.py` là eval-time-only, KHÔNG chạy trong pipeline; đừng coi GATE-0..6 trong đó là đang bảo vệ run.
8. **Một nguồn sự thật pipeline.** Orchestrator = `deep_research_v3.py`; mọi stage logic = `research/*.py`. `legacy/deep_research.py` là legacy v2 — đừng sửa như đang live. Memory gọn (short ≤50 dòng, long <200).
9. **Cải thiện ở AGENTIC LOOP, KHÔNG train model.** Lever = retrieval/verify/revise-loop/prompt/evidence-selection — KHÔNG fine-tune & KHÔNG build dataset. Bottleneck (writer grounding) → verify-revise loop (feed G2 per-`[N]` verdict ngược writer), không phải weight. (Xem mục 2.)

## 7. Lệnh thường dùng
```bash
# Prereq (LOCAL-only → thiếu là chết giữa chừng, KHÔNG có fallback cloud)
ollama serve &                       # bắt buộc: localhost:11434
ollama pull gemma4:e4b && ollama pull batiai/qwen3.6-35b:iq3 && ollama pull bge-m3:latest
pip install -r requirements.txt      # torch/transformers/FlagEmbedding; rerank+HHEM weights tải từ HF lần đầu
brew install pandoc tectonic         # CHỈ cho `--render`; thiếu → book.md vẫn ra, chỉ mất PDF
cp .env.example .env                 # TAVILY_API_KEY / BRAVE_API_KEY (optional) — auto-load bởi
                                     # `deep_research_v3.py::_load_dotenv()`; thiếu key = provider no-op
# `./run_full.sh` có preflight ollama + 2 model; gọi thẳng `python3 pipeline/...` thì KHÔNG → tự kiểm trước.
# KHÔNG có pyproject/ruff/black/mypy/CI trong repo — đừng đi tìm linter.

# Full run (orchestrator v3)
python3 pipeline/deep_research_v3.py --topic "RLHF" --out-name rlhf_v4 \
  --canonical-arxiv-ids "2203.02155,2305.18290,1706.03762" --no-smoke
# ⚠️ SMOKE LÀ MẶC ĐỊNH (`smoke = not args.no_smoke`) và smoke cắt `chapters[:2]`.
#    Quên `--no-smoke` → book 2 chương; đó KHÔNG phải bug.
#    Flag: --no-smoke · --max-rounds · --providers · --n-chapters / --sections-per-chapter (hint outline) · --render
TOPIC="RLHF" OUT_NAME="rlhf_v5" CANONICAL_IDS="2203.02155" ./run_full.sh   # env-driven launcher

# Test — KHÔNG có pytest: mỗi file là script độc lập (`__main__` + tự `sys.path.insert` repo root),
# chạy TỪ repo root, exit≠0 khi fail. "Chạy 1 test" = chạy đúng file đó.
python3 eval/test_outline_enforce.py       # anti-matrix enforce: collapse/no-op/dedup/coverage/renumber
python3 eval/test_decite.py                # citation cleaner: gỡ name-drop, GIỮ cite ngoài
python3 eval/test_verify_optim.py          # verify layer
python3 eval/test_math_char_safety.py      # mathfix/BM25 char-safety (BẮT BUỘC khi đụng mathfix.py)
python3 eval/test_dedup_sentences.py       # Stage-F sentence dedup: xoá dup, GIỮ ref/code/math/heading
python3 eval/bench_cite_discrimination.py  # G2 judge có discriminate không (chống rubber-stamp)
python3 eval/held_out_judge.py             # de-circle eval: kappa gemma vs model khác họ (auto-pick / --held-out)
python3 eval/smoke_test_p0.py --topic "Transformer" --canonical-ids "1706.03762,1607.06450"

# Đo chất lượng (LOCAL, bge-m3) — LUÔN đo lại, đừng quote số cũ trong doc
python3 eval/check_dedup.py <run-name|run-dir>   # near-dup section/paragraph; PASS = 0
python3 eval/audit_outline.py --state output/runs/<n>/state.json --topic "<T>"
python3 tools/report.py <run_dir>        # phân tích state.json (đếm quality: ok/degraded/BLOCKED)
bash eval/run_benchmark.sh               # benchmark 4 topic (RLHF/Diffusion/RAG/MoE), tuần tự, resume-safe
python3 tools/monitor.py                 # theo dõi tiến độ
pkill -f pipeline/deep_research_v3.py    # dừng
```

**Cách đọc block-rate (quan trọng — đừng "sửa gate" nhầm):**
- **Block-rate là hàm của RETRIEVAL BASE, không phải của code gate.** Base free (arxiv/wiki/ddg) làm block-rate cao hơn hẳn base có tavily/brave. Số trong README được đo khi retrieval base khác → **không so trực tiếp với run hôm nay**; muốn biết số thật thì chạy `tools/report.py` trên chính run đó.
- Section bị block = gate từ chối bịa → **hành vi ĐÚNG**, không phải regression. Muốn hạ block-rate → **thêm `BRAVE_API_KEY`** (free), **ĐỪNG prune outline bằng keyword** (đã test trên label thật: precision chỉ ~59% → over-prune section tốt).
- **Nhãn `quality` KHÔNG so sánh được xuyên phiên bản gate.** Run cũ (trước khi G2 chạy thật) có `ok` theo nghĩa khác. Luôn kèm ngày + trạng thái gate khi trích số.

## 8. Trạng thái & bước kế
- **Trạng thái hôm nay → `memory/short-memory.md`** (snapshot, không changelog). **Lịch sử & quyết định → `memory/long-memory.md`** (journal, nơi DUY NHẤT giữ changelog). **Roadmap → `docs/plan.md`.** Ba file này không chép chéo nhau.
- **Base** = orchestrator `deep_research_v3.py` + research layer: LOCAL-only · Verifier≠Writer · outline anti-matrix enforced · embed `bge-m3` thống nhất · evidence-pool rescue · Stage-F decite/mathfix · render tectonic robust.
- **MCP server in-repo:** `.mcp.json` → `tools/mcp_server.py` (`get_pipeline_status`, `get_stage_info`, `estimate_pipeline`, `generate_run_command`, `get_checkpoint_content`). Hiện **tắt** trong `.claude/settings.local.json`.
- `output/runs/llm_book_v36` và các run cũ chỉ để tham khảo lịch sử — KHÔNG phải baseline hiện hành.
