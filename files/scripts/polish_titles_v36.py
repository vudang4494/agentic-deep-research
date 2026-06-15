"""
Polish chapter and section titles to remove matrix pattern (e.g. "X: Subtitle, and X").

The original outline generator emitted "TopicA: Subtitle, and TopicA" which has
the same keyword on both sides of the colon. This script:

  1. Strips the trailing " and <topic>" tail when the topic name repeats.
  2. Keeps the descriptive subtitle intact.
  3. Updates outline_profile.json + state.json + book.clean.md.
"""
import json
import re
from pathlib import Path

OUT_DIR = Path("/Users/vudang/PythonLab/AgentDeepLearning/files/output/runs/llm_book_v36")
OUTLINE_PATH = OUT_DIR / "outline_profile.json"
STATE_PATH = OUT_DIR / "state.json"
BOOK_PATH = OUT_DIR / "book.clean.md"


def polish_title(title: str) -> str:
    """Strip trailing ', and <topic>' if it duplicates the leading topic."""
    if not title:
        return title
    # Pattern: "<TOPIC>: <subtitle>, and <TOPIC>" (case-insensitive on the trailing repetition)
    m = re.match(r"^([\w\s\(\)\-]+):\s*(.+?),\s*and\s+(.+?)\s*$", title)
    if m:
        topic, subtitle, tail = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        # Compare lowercase, ignoring parens content
        topic_norm = re.sub(r"[^a-z0-9]", "", topic.lower())
        tail_norm = re.sub(r"[^a-z0-9]", "", tail.lower())
        if topic_norm == tail_norm:
            # Drop tail, keep just "Topic: Subtitle"
            return f"{topic}: {subtitle}"
        # Also check if the leading part is X and the tail contains X
        # e.g. "Transformer block: ..., and Transformer block"
    # Simpler pattern: ", and <something>"  if it's the same word
    parts = title.rsplit(", and ", 1)
    if len(parts) == 2:
        left, tail = parts
        # extract topic (before colon)
        if ":" in left:
            topic, subtitle = left.split(":", 1)
            topic_norm = re.sub(r"[^a-z0-9]", "", topic.lower())
            tail_norm = re.sub(r"[^a-z0-9]", "", tail.lower())
            if topic_norm == tail_norm:
                return f"{topic.strip()}: {subtitle.strip()}"
    return title


def main():
    outline = json.load(open(OUTLINE_PATH))
    state = json.load(open(STATE_PATH))

    n_ch_changed = 0
    n_sec_changed = 0

    for ch in outline.get("chapters", []):
        old_t = ch.get("t", "")
        new_t = polish_title(old_t)
        if new_t != old_t:
            ch["t"] = new_t
            n_ch_changed += 1
        for sec in ch.get("sections", []):
            old_st = sec.get("t", "")
            new_st = polish_title(old_st)
            if new_st != old_st:
                sec["t"] = new_st
                n_sec_changed += 1

    print(f"Polished {n_ch_changed} chapter titles, {n_sec_changed} section titles")

    # Save outline
    with open(OUTLINE_PATH, "w") as f:
        json.dump(outline, f, indent=2)
    print(f"Saved {OUTLINE_PATH}")

    # Update state.json section titles to match
    for k, sec in state.get("sections", {}).items():
        old_title = sec.get("title", "")
        new_title = polish_title(old_title)
        if new_title != old_title:
            sec["title"] = new_title
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved {STATE_PATH}")

    # Update book.clean.md H1 / H2 headings
    if BOOK_PATH.exists():
        book = BOOK_PATH.read_text()
        new_book_lines = []
        for line in book.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith("# ") or stripped.startswith("## "):
                # Extract heading level and content
                level, content = stripped.split(" ", 1)
                new_content = polish_title(content)
                # Preserve leading whitespace
                prefix = line[:len(line) - len(stripped)]
                new_book_lines.append(f"{prefix}{level} {new_content}")
            else:
                new_book_lines.append(line)
        BOOK_PATH.write_text("\n".join(new_book_lines))
        print(f"Updated headings in {BOOK_PATH}")


if __name__ == "__main__":
    main()
