---
name: audit
description: Multi-dimension product audit — sweep the pipeline for real defects, adversarially verify every finding, report only what survives.
disable-model-invocation: true
argument-hint: "[optional: a dimension or path to focus on]"
context: fork
---

Audit this product for real defects. The mechanical gate (`eval/verify_all.py`) already covers the
regex-checkable invariants; a previous run of this audit found **24 confirmed defects (1 HIGH)
while that gate reported 9/9 PASS**, so aim at what regex cannot see.

Read `CLAUDE.md` first — §2 doctrine, §5 live gates, §6 guardrails — it defines what is a defect
versus what is deliberate.

## Dimensions to sweep

Cover these unless the user narrowed the scope:

1. **research core correctness** — `deep_investigate.py`, `notes.py`, `verify.py`, `discovery.py`,
   `outline_from_research.py`, `rerank.py`: gate conditions, round-loop control, best-round
   selection, fail-open/closed paths.
2. **orchestrator / render / Stage-F** — `pipeline/deep_research_v3.py`, `scripts/render_book.py`,
   `mathfix.py`, `decite.py`, `dedup.py`: assemble, resume, provenance, Stage-F ordering.
3. **doctrine (semantic)** — delegate to the `doctrine-reviewer` subagent.
4. **dead code / duplication** — prove a symbol is unreferenced with grep before reporting it;
   remember a CLI entry-point with zero importers is NOT dead.
5. **eval/test integrity** — does each test actually assert? Any test that passes vacuously
   (empty loop body, network-dependent), any gate that reads a frozen artifact instead of code?
6. **docs ↔ code consistency** — grep every documented symbol/threshold/anchor; docs that lie are
   the recurring failure mode here.
7. **efficiency** — redundant recomputation across rounds, needless network calls, O(n²) where
   O(n) works. Behavior-preserving changes only.
8. **error handling** — bare `except: pass`, missing timeouts, non-atomic writes on
   resume-critical files, crash-on-malformed-input.

## Verify before you believe

Every candidate finding must survive an adversarial pass: try to REFUTE it by reading the actual
code. Ask "can this failure really occur, or is it guarded elsewhere?" and "would fixing it break
an intentional invariant?" Drop anything you cannot confirm at `file:line`. **Prefer few confirmed
findings over many plausible ones** — a false finding costs more than a missed one, because acting
on it damages working code.

## Report

Rank by severity. For each: `file:line`, the defect in one sentence, a concrete failure scenario,
and the minimal fix. Separate "confirmed" from "rejected during verification" and say briefly why
the rejected ones were dropped. Do not fix anything unless the user asks — this skill reports.
