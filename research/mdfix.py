"""Assemble-time markdown STRUCTURAL hygiene (Stage-F, formatting-only).

These defects pass every content gate because they change no word of prose -- they only change
how the markdown PARSES, so the damage is invisible until the book is rendered:

  * **list glued to the paragraph above it** (no blank line). CommonMark/pandoc do not let a
    list interrupt a paragraph, so the whole list collapses into running prose: a 4-step PPO
    algorithm prints as one run-on sentence with stray "1." "2." markers mid-line. This
    destroys exactly the step-by-step structure `explain.py` credits -- and `explain.py`
    scores the MARKDOWN, so the signal reports the section teaches while the PDF shows it
    does not. Measured on a real run: 9/15 sections.
  * **reference numbering with gaps**. `_section_references` emits only the sources actually
    cited, so the block is legitimately `1.` `3.` `4.` -- and markdown's ordered list renumbers
    it to `1.` `2.` `3.` on render. The prose then cites `[3]` while the printed entry says
    "2.": attribution silently broken in the one artifact a reader audits. 8/15 sections.
  * **`[[N]]` doubled citation brackets** -- print literally as "[[1]]". Harmless to G2
    (its `\\[(\\d+)\\]` matches the inner pair) but visibly wrong.
  * **a trailing `[N]` on the closing `$$` line**. pandoc ends display math at `$$`, orphaning
    the citation into a paragraph of its own that floats mid-page, detached from the claim.

Every fix here is FORMATTING-ONLY and IDEMPOTENT -- no word is added, removed or reordered, and
re-running on already-clean markdown is a no-op. That idempotence is what lets the RENDERER call
this as well as the assembler: books written before this module existed get repaired at render
time without the fixes double-applying. Same single-source discipline as `mathfix` -- one
implementation, two call sites, never a local copy.

Code fences are masked out first: indented pseudo-code and `[[...]]` inside a snippet are
content, not markup.
"""
import re

_CODE_FENCE = re.compile(r"```[\s\S]*?```")

# A list item start: <=3 spaces of indent, a bullet or ordered marker, then real content.
# The ordered marker is capped at TWO digits on purpose: `2024. Something` is a sentence
# opening with a year, and promoting it to a list would start the list at 2024.
_LIST_ITEM = re.compile(r"^ {0,3}(?:[*+-]|\d{1,2}[.)])\s+\S")
# Openers a list may legally follow without a blank line (they already close their own block),
# plus rows where inserting a break would corrupt the structure.
_NO_INSERT_BEFORE = re.compile(r"^\s*(?:#{1,6}\s|\||>|\$\$)")
_DOUBLE_CITE = re.compile(r"\[\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]\]")
# One or more citations trailing a math line, e.g. `$$ x = y $$ [1]` or a bare closing `$$ [1]`.
_MATH_TRAILING_CITE = re.compile(r"^(\s*\$\$.*?\$\$|\s*\$\$)\s*((?:\[\d+\]\s*[,;]?\s*)+)$")
# The assembler writes `**References**`; the renderer's heading promotion may have already
# turned it into `### References`, so accept both -- this runs on live and on rendered markdown.
_REF_HEADING = re.compile(r"^\s*(?:\*\*References\*\*|#{2,4}\s+References)\s*$")
_LEGACY_REF_ENTRY = re.compile(r"^(\d{1,3})\.\s+(\S.*)$")


def _mask_fences(text):
    holes = []

    def _grab(m):
        holes.append(m.group(0))
        return f"\x00F{len(holes) - 1}\x00"

    return _CODE_FENCE.sub(_grab, text), holes


def _unmask_fences(text, holes):
    for i, block in enumerate(holes):
        text = text.replace(f"\x00F{i}\x00", block)
    return text


def fix_double_citations(text):
    """`[[3]]` -> `[3]`, `[[1, 2]]` -> `[1, 2]`. Digits only, so a genuine `[[bracketed]]`
    phrase is never touched. Returns (text, n_fixed)."""
    n = [0]

    def _repl(m):
        n[0] += 1
        return "[" + m.group(1) + "]"

    return _DOUBLE_CITE.sub(_repl, text), n[0]


def fix_glued_lists(text):
    """Insert the blank line a list needs to parse as a list. Only fires when the preceding
    line is ordinary prose OUTSIDE any list -- a lazy continuation line inside a list item is
    left alone, because splitting there would break one list into two. Returns (text, n)."""
    lines = text.split("\n")
    out, n = [], 0
    in_list = False      # a list block is open (cleared by a blank line)
    in_math = False      # inside a multi-line $$ ... $$ block
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("$$"):
            # a one-line `$$ ... $$` opens and closes; a bare `$$` toggles.
            if not (len(stripped) > 2 and stripped.endswith("$$")):
                in_math = not in_math
            out.append(ln)
            in_list = False
            continue
        if in_math:
            out.append(ln)
            continue
        if not stripped:
            out.append(ln)
            in_list = False
            continue
        if _LIST_ITEM.match(ln):
            prev = out[-1] if out else ""
            if (prev.strip() and not in_list and not _LIST_ITEM.match(prev)
                    and not _NO_INSERT_BEFORE.match(prev)):
                out.append("")
                n += 1
            out.append(ln)
            in_list = True
            continue
        out.append(ln)
    return "\n".join(out), n


def fix_orphan_math_citations(text):
    """Move a `[N]` trailing a display-math line onto the prose sentence that introduces the
    formula, where it belongs. pandoc would otherwise orphan it into its own paragraph.
    Skipped (line left verbatim) when no prose line precedes the block. Returns (text, n)."""
    lines = text.split("\n")
    n = 0
    block_start = None   # index of the line that opened an unterminated $$ block
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped.startswith("$$"):
            continue
        m = _MATH_TRAILING_CITE.match(ln)
        # Decide open-vs-close on the MATH part only: `$$ x $$ [1]` is self-closing even
        # though the raw line ends in `]`, and mis-reading it would desync block_start.
        core = m.group(1).strip() if m else stripped
        self_closing = len(core) > 2 and core.endswith("$$")
        if m:
            anchor = i if (self_closing or block_start is None) else block_start
            target = None
            for j in range(anchor - 1, -1, -1):
                cand = lines[j].strip()
                if not cand:
                    continue
                if cand.startswith("$$") or cand.startswith("#") or not re.search(r"[A-Za-z]", cand):
                    break
                target = j
                break
            cites = m.group(2).strip()
            if target is not None:
                lines[i] = core
                body = lines[target].rstrip()
                if not body.endswith(cites):
                    # "...decomposed into components:" reads better as "...components [1]:"
                    lines[target] = (body[:-1].rstrip() + " " + cites + ":") if body.endswith(":") \
                        else (body + " " + cites)
                n += 1
        if not self_closing:
            block_start = None if block_start is not None else i
    return "\n".join(lines), n


def fix_reference_numbering(text):
    """Migrate a legacy `**References**` block written as an ordered list (`1.` `3.` `4.`) to
    `- [N] ...`, so markdown can no longer renumber it and the printed marker keeps matching the
    `[N]` in the prose. The assembler emits the `- [N]` form directly; this repairs books
    assembled before that, and is a no-op on them. Returns (text, n_entries_migrated)."""
    lines = text.split("\n")
    n, in_block = 0, False
    for i, ln in enumerate(lines):
        if _REF_HEADING.match(ln):
            in_block = True
            continue
        if not in_block:
            continue
        if not ln.strip():
            continue
        m = _LEGACY_REF_ENTRY.match(ln)
        if m:
            lines[i] = f"- [{m.group(1)}] {m.group(2)}"
            n += 1
        else:
            in_block = False   # first non-entry line ends the reference block
    return "\n".join(lines), n


def normalize_markdown(text):
    """Single entry point: all structural fixes, code fences preserved verbatim.
    Returns (text, {fix_name: count}). Idempotent -- safe to run at assemble AND at render."""
    if not text:
        return text or "", {}
    masked, holes = _mask_fences(text)
    counts = {}
    masked, counts["double_citations"] = fix_double_citations(masked)
    masked, counts["orphan_math_citations"] = fix_orphan_math_citations(masked)
    masked, counts["reference_numbering"] = fix_reference_numbering(masked)
    masked, counts["glued_lists"] = fix_glued_lists(masked)
    return _unmask_fences(masked, holes), counts
