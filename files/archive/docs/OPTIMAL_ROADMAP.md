# Optimal Development Roadmap

## Current State Analysis

### Problem: Content Quality ≠ Structure Quality

```
┌─────────────────────────────────────────────────────────────┐
│                    llm_book_v35                             │
├─────────────────────────────────────────────────────────────┤
│  ✅ Writing Quality     │  ❌ Structure Quality            │
│  - Unique content       │  - Part N pattern: 56           │
│  - Good grounding       │  - Zero cross-refs              │
│  - Clean assembly       │  - Matrix overlap: 1643         │
├─────────────────────────────────────────────────────────────┤
│  📊 Score Breakdown                                          │
│  GATE-0 (Outline):     0.00  ❌ FAIL                      │
│  GATE-2 (Content):      1.00  ✅ PASS                      │
│  GATE-6 (Coherence):    0.35  ❌ FAIL                      │
│  GATE-7 (Hygiene):     1.00  ✅ PASS                      │
├─────────────────────────────────────────────────────────────┤
│  💰 Root Cause: Outline Generator is the BOTTLENECK        │
└─────────────────────────────────────────────────────────────┘
```

---

## Strategic Priorities

### Why Fix Outline First?

```
BEFORE (Current Pipeline):
Discovery → Outline [BAD] → Research → Writing → Verify → Book
                                  ↑
                            Expensive writing
                            happens on bad outline

AFTER (Optimized Pipeline):
Discovery → Outline [GATE-0] → Research → Writing → Verify → Book
                 ↑
           BLOCK bad outline BEFORE expensive writing
```

**Cost Analysis:**
- Outline generation: ~1K tokens
- Research per section: ~5K tokens
- Writing per section: ~3K tokens
- **Fix outline = Save 80% of wasted tokens**

---

## Phase 1: Critical Fixes (Week 1)

### 1.1 Block Part N Pattern

```python
# files/research/outline_from_research.py

def generate_outline(topic: TopicProfile) -> Outline:
    outline = llm_generate_outline(topic)
    
    # GATE-0: Block Part N pattern
    part_pattern = re.compile(r"\(Part\s+\d+\)")
    for section in outline.sections:
        if part_pattern.search(section.title):
            raise OutlineValidationError(
                f"Part N pattern not allowed: {section.title}"
            )
    
    return outline
```

### 1.2 Enforce Title Uniqueness

```python
# GATE-0: Jaccard < 0.30 between all titles
def validate_outline_titles(outline: Outline) -> None:
    titles = [s.title for s in outline.sections]
    
    for i, t1 in enumerate(titles):
        for j, t2 in enumerate(titles[i+1:], i+1):
            jaccard = compute_jaccard(t1, t2)
            if jaccard > 0.30:
                raise OutlineValidationError(
                    f"High overlap ({jaccard:.2f}): '{t1}' vs '{t2}'"
                )
```

### 1.3 Remove Matrix Pattern

```
❌ BAD Pattern:
├── Foundations: Theory
├── Foundations: Methods
├── Foundations: Applications
├── Math: Theory
├── Math: Methods
├── Math: Applications
└── ...

✅ GOOD Pattern:
├── Historical Origins of Language Models
├── The Transformer Architecture
├── Attention Mechanisms Deep Dive
├── Training Objectives and Losses
├── Scaling Laws and Compute
└── ...
```

---

## Phase 2: Coherence (Week 2)

### 2.1 Cross-Reference Requirement

```python
# Each section MUST reference at least 1 prior section
def validate_section(section: Section, prior_sections: List[Section]) -> None:
    content = section.content.lower()
    
    # Find references to prior sections
    refs = []
    for prior in prior_sections:
        if prior.title.lower() in content:
            refs.append(prior.id)
    
    if len(refs) == 0:
        raise WritingQualityError(
            f"Section {section.id} has no cross-references"
        )
```

### 2.2 Depth Escalation Check

```python
# Outline must follow: basic → intermediate → advanced
def validate_depth_escalation(outline: Outline) -> None:
    depth_levels = classify_depth(outline.sections)
    
    # Must have increasing trend
    if not is_escalating(depth_levels):
        raise OutlineValidationError(
            "Outline must have depth escalation: basic → advanced"
        )
```

---

## Phase 3: Quality Gates Integration (Week 3)

### 3.1 Gate Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    QUALITY GATE PIPELINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Discovery                                                    │
│     ↓                                                        │
│  Outline ───→ GATE-0 ───→ FAIL/BLOCK ───→ Fix Outline      │
│     ↓               ↓                                        │
│     ↓          PASS                                          │
│     ↓                                                        │
│  Research ───→ GATE-1 (P0a/b/c) ───→ FAIL/BLOCK            │
│     ↓                                                        │
│  Writing ───→ GATE-2 (Uniqueness) ──→ REWRITE              │
│     ↓                                                        │
│  Verify ────→ GATE-4 (Grounding) ───→ RETRY                │
│     ↓                                                        │
│  Assembly ───→ GATE-7 (Hygiene) ────→ CLEAN                │
│     ↓                                                        │
│  Book                                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Fail Fast Strategy

```python
# Don't waste tokens on bad outline
def run_pipeline(topic: str) -> Book:
    # Stage 1: Discovery
    topic_profile = discovery(topic)
    
    # Stage 2: Outline (with GATE-0)
    outline = generate_outline(topic_profile)
    
    # CRITICAL: Validate BEFORE expensive operations
    gate_0_results = {
        "part_duplication": verify_no_part_duplication(outline),
        "title_uniqueness": verify_outline_uniqueness(outline),
        "depth_escalation": verify_depth_escalation(outline),
    }
    
    if not all(r["pass"] for r in gate_0_results.values()):
        raise PipelineError(
            f"GATE-0 failed: {[k for k,v in gate_0_results.items() if not v['pass']]}"
        )
    
    # Only now proceed to expensive operations
    for section in outline.sections:
        section = research(section)
        section = write(section)
        section = verify(section)
    
    return assemble(outline)
```

---

## Phase 4: Metrics & Monitoring (Week 4)

### 4.1 Dashboard

```python
# Track quality over time
METRICS = {
    "gate_0_pass_rate": [],      # Should be 100%
    "avg_section_similarity": [], # Should be < 0.30
    "cross_ref_density": [],      # Should be >= 2/section
    "grounding_scores": [],       # Should be >= 0.80
    "book_scores": [],           # Should be >= 0.80
}
```

### 4.2 Alert Thresholds

```python
ALERTS = {
    "gate_0_pass_rate < 0.8": "PAGER: Outline generator broken",
    "avg_similarity > 0.5": "ALERT: Section overlap increasing",
    "grounding < 0.7": "PAGER: Writer quality degraded",
    "book_score < 0.6": "CRITICAL: Overall quality below threshold",
}
```

---

## Implementation Priority

```
WEEK 1: Fix Outline Generation
├── [ ] Block Part N pattern
├── [ ] Enforce Jaccard < 0.30
├── [ ] Remove matrix pattern
└── [ ] Test on sample topics

WEEK 2: Add Coherence
├── [ ] Cross-reference requirement
├── [ ] Depth escalation check
├── [ ] Concept dependency check
└── [ ] Smoke test

WEEK 3: Integrate Gates
├── [ ] GATE-0 blocking in pipeline
├── [ ] GATE-2 uniqueness check
├── [ ] GATE-6 coherence check
└── [ ] End-to-end test

WEEK 4: Monitor & Iterate
├── [ ] Quality dashboard
├── [ ] Alert system
├── [ ] Regression tests
└── [ ] Benchmark v3.6
```

---

## Expected Results

| Metric | v3.5 (Before) | v3.6 (After) |
|--------|----------------|---------------|
| Part N Pattern | 56 ❌ | 0 ✅ |
| Title Uniqueness | 49 dup ❌ | 0 dup ✅ |
| Cross-refs | 0/section ❌ | >= 2/section ✅ |
| Book Score | 0.625 ❌ | >= 0.80 ✅ |
| Grade | B | A |

---

## Success Criteria

```
✅ PASS = ALL of:
   - GATE-0 pass rate = 100%
   - GATE-2 uniqueness = 100%
   - Cross-refs >= 2/section
   - Book score >= 0.80
   - Grade >= A
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Over-blocking good outlines | Tune thresholds (Jaccard < 0.30, not 0.20) |
| Too slow pipeline | Parallelize research per section |
| False positives | Manual review for edge cases |
| Regression | Auto-tests on every PR |

---

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  OPTIMAL PATH FORWARD                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Fix OUTLINE GENERATOR (not writer)                     │
│     - Part N pattern is root cause                          │
│     - 80% of quality issues come from bad outline           │
│                                                              │
│  2. Fail FAST before expensive operations                    │
│     - Block bad outline BEFORE research/writing              │
│     - Save tokens and time                                  │
│                                                              │
│  3. Add Cross-References                                    │
│     - Required >= 2 refs/section                            │
│     - Transform isolated sections → coherent book          │
│                                                              │
│  4. Measure Everything                                       │
│     - Track metrics over time                               │
│     - Alert on degradation                                  │
│     - Benchmark every version                               │
│                                                              │
│  TARGET: A-grade book in 4 weeks                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
