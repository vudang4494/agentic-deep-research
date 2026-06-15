"""
Generate a References / Bibliography section for llm_book_v36.

Reads sources from each section's `sources` field in state.json, plus the
canonical papers from topic_profile.json, and emits a Markdown references
section with arXiv hyperlinks.

Output: appends a "## References" section to book.clean.md (with
arxiv.org hyperlinks), and writes book.references.md (standalone).
"""
import json
import re
from collections import OrderedDict
from pathlib import Path

OUT_DIR = Path("/Users/vudang/PythonLab/AgentDeepLearning/files/output/runs/llm_book_v36")
STATE_PATH = OUT_DIR / "state.json"
TOPIC_PATH = OUT_DIR / "topic_profile.json"
BOOK_PATH = OUT_DIR / "book.clean.md"
OUT_BOOK = OUT_DIR / "book.references.md"

ARXIV_RE = re.compile(r"(?:arxiv[:\s]+|arXiv:?\s*)(\d{4}\.\d{4,5})", re.IGNORECASE)
ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})")
ARXIV_BARE = re.compile(r"(\d{4}\.\d{4,5})")
WIKI_RE = re.compile(r"wikipedia\.org/wiki/([^/\s\)\"#]+)")


def extract_id_from_source(src):
    """Pull a canonical arxiv id (YYYY.NNNNN) or wikipedia slug from a source dict or str.
    Returns (parsed_key_or_None, title, url, provider).
    """
    if isinstance(src, dict):
        # The Source object stores id, url, title, provider
        sid = src.get("id", "") or ""
        url = src.get("url", "") or ""
        title = src.get("title", "") or ""
        provider = src.get("provider", "") or ""
        # Parse from id first
        parsed = _parse_id_string(sid)
        if not parsed:
            parsed = _parse_id_string(url)
        return (parsed, title, url, provider)

    if not isinstance(src, str):
        return (None, "", "", "")
    parsed = _parse_id_string(src)
    return (parsed, "", "", "")


def _parse_id_string(s: str):
    """Return (kind, id) tuple or None."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    m = ARXIV_RE.search(s) or ARXIV_URL.search(s) or ARXIV_BARE.search(s)
    if m:
        return ("arxiv", m.group(1))
    m = WIKI_RE.search(s)
    if m:
        return ("wiki", m.group(1))
    if s.startswith("http"):
        return ("url", s)
    return None


def collect_all_sources(state, topic):
    """Walk state.sections[*].sources plus topic canonical papers."""
    refs = OrderedDict()  # key: (kind, id) -> (url, title)

    # Topic profile canonical papers (dict form)
    for cp in topic.get("canonical_papers", []):
        if isinstance(cp, dict):
            arxiv_id = cp.get("arxiv_id") or cp.get("id") or ""
            title = cp.get("title", "")
            url = cp.get("url", "")
            if arxiv_id:
                # Try to extract clean arxiv id
                m = ARXIV_BARE.search(str(arxiv_id))
                clean_id = m.group(1) if m else str(arxiv_id)
                key = ("arxiv", clean_id)
                if not url or "arxiv" not in url:
                    url = f"https://arxiv.org/abs/{clean_id}"
                refs[key] = (url, title or f"arXiv:{clean_id}")
        elif isinstance(cp, str):
            parsed = extract_id_from_source(cp)
            if parsed:
                kind, id_ = parsed
                url = f"https://arxiv.org/abs/{id_}" if kind == "arxiv" else cp
                refs.setdefault(parsed, (url, f"arXiv:{id_}"))

    # Section sources (list of dicts)
    for key, sec in state.get("sections", {}).items():
        for src in sec.get("sources", []) or []:
            parsed_tuple = extract_id_from_source(src)
            if not parsed_tuple:
                continue
            parsed, title, url, provider = parsed_tuple
            if not parsed:
                continue
            if parsed in refs:
                # Update title if we have a better one
                existing_url, existing_title = refs[parsed]
                if not existing_title and title:
                    refs[parsed] = (existing_url, title)
                continue
            kind, id_ = parsed
            if not url:
                if kind == "arxiv":
                    url = f"https://arxiv.org/abs/{id_}"
                elif kind == "wiki":
                    url = f"https://en.wikipedia.org/wiki/{id_}"
            if not title:
                title = f"{kind}:{id_}"
            refs[parsed] = (url, title)
    return refs


def main():
    state = json.load(open(STATE_PATH))
    topic = json.load(open(TOPIC_PATH))

    refs = collect_all_sources(state, topic)
    print(f"Collected {len(refs)} unique references")

    # Bucket by kind
    arxiv = [(k, v) for k, v in refs.items() if k[0] == "arxiv"]
    wiki = [(k, v) for k, v in refs.items() if k[0] == "wiki"]
    other = [(k, v) for k, v in refs.items() if k[0] not in ("arxiv", "wiki")]

    # Sort arxiv by id (year then number)
    arxiv.sort(key=lambda x: x[0][1])
    wiki.sort(key=lambda x: x[0][1].lower())
    other.sort(key=lambda x: x[0][1])

    # Emit markdown
    lines = ["\n---\n", "# References\n",
             f"\nThis book draws on **{len(arxiv)}** arXiv papers, "
             f"**{len(wiki)}** Wikipedia articles, and other primary sources.\n"]

    if arxiv:
        lines.append("\n## arXiv Papers\n")
        for (kind, aid), (url, title) in arxiv:
            display = title if title and title != f"arXiv:{aid}" else f"arXiv:{aid}"
            lines.append(f"- [{display}]({url}) — arXiv:{aid}\n")

    if wiki:
        lines.append("\n## Wikipedia\n")
        for (kind, slug), (url, title) in wiki:
            display = title if title and title != f"wiki:{slug}" else slug.replace("_", " ")
            lines.append(f"- [{display}]({url})\n")

    if other:
        lines.append("\n## Other Sources\n")
        for (kind, id_), (url, title) in other:
            lines.append(f"- [{id_}]({url})\n")

    references_md = "".join(lines)

    # Standalone references file
    with open(OUT_BOOK, "w") as f:
        f.write("# LLM Agents & Advanced AI Reasoning — References\n")
        f.write(f"_Generated from sources across {len(state.get('sections', {}))} sections._\n")
        f.write(references_md)
    print(f"Wrote {OUT_BOOK}")

    # Append to book.clean.md (without overwriting it)
    # Strip any previous "## References" / "# References" sections first to avoid dupes
    if BOOK_PATH.exists():
        existing = BOOK_PATH.read_text()
        # Find last # References or ## References
        for marker in ["\n---\n# References", "\n# References", "## References"]:
            idx = existing.rfind(marker)
            if idx > 0:
                existing = existing[:idx].rstrip() + "\n"
                break
        existing = existing + references_md
        BOOK_PATH.write_text(existing)
    else:
        BOOK_PATH.write_text(references_md)
    print(f"Appended references to {BOOK_PATH}")


if __name__ == "__main__":
    main()
