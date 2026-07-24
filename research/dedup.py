"""Assemble-time exact-duplicate sentence remover (Stage-F, deletion-only).

The writer runs per-section with no view of the whole book, so it re-emits the same
boilerplate sentence ("In this section we explore ...", a stock definition) across chapters.
Heading/paragraph dedup (enforce_outline_structure, the in-loop G6 near-dup gate) don't catch
a single duplicated SENTENCE embedded in otherwise-distinct paragraphs.

`drop_duplicate_sentences` removes an EXACT repeat of a SUBSTANTIAL sentence, keeping the first
occurrence. Design constraints (a bad dedup silently corrupts the book, so safety first):

  * deletion-only -- never rewrites or merges, only drops a verbatim repeat.
  * byte-conservative -- a paragraph with no duplicate is returned UNCHANGED (no re-split/rejoin).
  * block-aware -- code fences, display math ($$), headings, tables, blockquotes and reference
    lists are never touched (the same paper cited in two sections yields identical ref lines
    by design -- those must survive).
  * word-floor -- only sentences with >= _MIN_WORDS real words are deduped; two independent
    10+-word sentences being byte-identical is boilerplate, not coincidence. Short repeats
    ("This is important.") are left alone (low harm, high false-positive risk).

Sentences differing only by their citation marker ([5] vs [8]) are DISTINCT keys and both survive.
"""
import re

_MIN_WORDS = 10
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CODE_FENCE = re.compile(r"```[\s\S]*?```")
# A block whose FIRST line is one of these is structural, not prose -> left verbatim.
_PROTECTED = re.compile(r"^\s*(#{1,6}\s|\||>|\d+\.\s|\*\*References\*\*|\$\$|\[\d+\]\s|-\s|\*\s)")


def _norm(sentence):
    """Match key: whitespace-collapsed, trailing sentence punctuation stripped, lowercased.
    Citation markers ([5]) are kept, so differently-cited sentences stay distinct."""
    return re.sub(r"\s+", " ", sentence).strip().rstrip(".!?").lower()


def _dedup_block(block, seen):
    if _PROTECTED.match(block) or "$$" in block:
        return block, 0
    sents = _SENT_SPLIT.split(block)
    kept, removed = [], 0
    for s in sents:
        key = _norm(s)
        if len(key.split()) >= _MIN_WORDS and re.search(r"[A-Za-z]", s):
            if key in seen:
                removed += 1
                continue
            seen.add(key)
        kept.append(s)
    if removed == 0:
        return block, 0                      # untouched -> byte-identical
    return " ".join(k for k in kept if k).strip(), removed


def drop_duplicate_sentences(text):
    """Return (deduped_text, n_removed). First occurrence of each substantial sentence is kept;
    code fences are masked out and restored unchanged."""
    masks = []

    def _mask(m):
        masks.append(m.group(0))
        return f"\x00C{len(masks) - 1}\x00"

    masked = _CODE_FENCE.sub(_mask, text)
    seen, total = set(), 0
    blocks = re.split(r"(\n\s*\n)", masked)  # keep the blank-line separators (odd indices)
    for i in range(0, len(blocks), 2):
        blocks[i], n = _dedup_block(blocks[i], seen)
        total += n
    out = "".join(blocks)
    for j, mk in enumerate(masks):
        out = out.replace(f"\x00C{j}\x00", mk)
    return out, total
