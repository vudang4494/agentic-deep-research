#!/usr/bin/env python3
"""
Render book.md to PDF using pandoc + tectonic (LaTeX).

Usage:
  python3 scripts/render_book.py --run llm_trends_2026_2027 [--weasy]
"""
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `research.mathfix` resolves when run standalone

from research.mathfix import normalize_math  # canonical math/special-char normalization (single source of truth)


def is_substantive_technical_diagram(code: str) -> bool:
    """Filter out trivial/generic 3-box mindmaps. Keep diagrams containing math formulas,
    tensor dimensions, algorithm steps, or detailed multi-node flows.
    """
    lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("graph") and not l.strip().startswith("flowchart")]
    if len(lines) < 3:
        return False
    tech_markers = (
        r"\b\d+d\b", r"\[.*?\b(?:batch|seq|dim|head|hidden|size|shape|loss|grad|step|layer|state)\b.*?\]",
        r"\b(?:dL/d|dW|d\theta|forward|backward|backprop|softmax|arg|loss|cross-entropy|projection|attention|ppo|reward|mcts|actor|critic)\b",
        # An operator FLANKED BY word chars = a real expression (x=y, a+b, dL/dW). The old
        # bare class `[\=+\-*/\\]` matched the '-' in every mermaid edge (-->, ---) and the '=' in
        # ==>, so it kept ANY diagram with edges -- defeating the trivial-mindmap filter. Excluding
        # a bare '-' also avoids matching hyphenated node labels (self-attention).
        r"\w\s*[=+*/^]\s*\w", r"\$\$.*?\$\$|\\\(.*?\\\)"
    )
    has_tech = any(re.search(pat, code, re.I) for pat in tech_markers)
    return has_tech or len(lines) >= 5


def render_mermaid_blocks(content: str, run_dir: Path) -> str:
    """Find ```mermaid ... ``` blocks, fetch compiled PNGs from Kroki API,
    save to run_dir/diagrams/, and replace with markdown image syntax ![Diagram](diagrams/diag_N.png).
    Filter out trivial mindmaps.
    """
    import zlib, base64, httpx
    diagrams_dir = run_dir / "diagrams"
    diagrams_dir.mkdir(exist_ok=True)

    pattern = re.compile(r"```mermaid\s*\n([\s\S]*?)\n```")
    count = [0]
    dropped = [0]
    failed = [0]

    def _repl(m):
        code = m.group(1).strip()
        if not is_substantive_technical_diagram(code):
            dropped[0] += 1
            return ""  # drop trivial generic mindmap
        count[0] += 1
        img_path = diagrams_dir / f"diagram_{count[0]}.png"
        compressed = zlib.compress(code.encode("utf-8"))
        encoded = base64.urlsafe_b64encode(compressed).decode("utf-8")
        url = f"https://kroki.io/mermaid/png/{encoded}"
        for attempt in range(3):  # transient Kroki/network hiccup -> retry before giving up
            try:
                r = httpx.get(url, timeout=20.0)
                if r.status_code == 200 and len(r.content) > 100:
                    img_path.write_bytes(r.content)
                    return f"\n\n![Algorithmic & Mathematical Flow](diagrams/diagram_{count[0]}.png)\n\n"
                print(f"  [mermaid-render] diagram {count[0]} attempt {attempt+1}: HTTP {r.status_code}")
            except Exception as e:
                print(f"  [mermaid-render] diagram {count[0]} attempt {attempt+1} failed: {e}")
        # FINAL failure -> DROP the block. Raw `graph TD ...` source dumped as a verbatim code
        # block reads as garbage in a finished book; a missing figure is strictly better.
        failed[0] += 1
        return ""

    new_content = pattern.sub(_repl, content)
    if count[0] or dropped[0] or failed[0]:
        print(f"  [mermaid-render] {count[0]} diagram(s) -> PNG; dropped {dropped[0]} trivial, "
              f"{failed[0]} unrenderable (removed, never left as raw source)")
    return new_content


def promote_bold_headings(content: str) -> str:
    """The writer emits many sub-section labels as a stand-alone **Bold line** instead of a
    markdown heading, so a section renders as a flat wall of paragraphs with no visible
    sub-structure. Promote a line that is ENTIRELY bold and heading-like (capitalized start,
    no terminal punctuation, <= 14 words) to an H3. toc-depth=2 keeps these out of the TOC,
    so this adds in-page structure without bloating the contents page."""
    out = []
    for ln in content.split("\n"):
        s = ln.strip()
        m = re.fullmatch(r"\*\*(.+?)\*\*", s)
        if m:
            t = m.group(1).strip()
            if (t and t[0].isupper() and t[-1] not in ".:,;?!" and "**" not in t
                    and not t.startswith("[") and 1 <= len(t.split()) <= 14):
                out.append(f"### {t}")
                continue
        out.append(ln)
    return "\n".join(out)


def _extract_and_strip_title(content: str, default: str = "Technical Book"):
    """Pull the book title from the leading non-numbered '# ...' H1 (assemble writes it as
    '# <outline.title>') and REMOVE that line from the body. pandoc renders the title via
    \\maketitle from metadata; leaving the H1 in the body would duplicate it as an opening
    chapter. Numbered '# N. ...' chapter headings are left intact. Returns (title, body).
    This replaces the two hardcoded, topic-mismatched title constants the render paths used."""
    lines = content.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        m = re.match(r"^#\s+(.+)$", ln.strip())
        if m and not re.match(r"^\d+\.", m.group(1).strip()):
            title = m.group(1).strip()
            del lines[i]
            return title, "\n".join(lines)
        break  # first non-empty line is not a title H1 -> leave body unchanged
    return default, content


def clean_md(content: str, run_dir: Path = None) -> str:
    """Apply math fixes and markdown hygiene to the full book markdown."""
    lines = content.split("\n")
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                content = "\n".join(lines[i+1:])
                break
    content = re.sub(r"\n---\n", "\n\n***\n\n", content)
    content = promote_bold_headings(content)
    content = normalize_math(content)
    if run_dir:
        content = render_mermaid_blocks(content, run_dir)
    return content


# LaTeX preamble: professional Springer/MIT Press style book typography & callout styling.
_PREAMBLE = r"""
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{charter}
\usepackage{fancyhdr}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage[many]{tcolorbox}

% Curated Color Palette
\definecolor{primary}{HTML}{0F172A}
\definecolor{accent}{HTML}{0284C7}
\definecolor{boxbg}{HTML}{F8FAFC}
\definecolor{boxborder}{HTML}{0284C7}

% Styled Callout & Quote Boxes
\renewenvironment{quote}{%
  \vspace{0.4em}%
  \begin{tcolorbox}[breakable, colback=boxbg, colframe=boxborder, arc=3pt, boxrule=1.2pt, left=10pt, right=10pt, top=6pt, bottom=6pt]%
}{%
  \end{tcolorbox}%
  \vspace{0.4em}%
}

% Running Headers & Footers
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\color{primary}\scshape \leftmark}
\fancyhead[R]{\small\color{accent}\bfseries \thepage}
\renewcommand{\headrulewidth}{0.4pt}

% Math Macros
\providecommand{\softmax}{\operatorname{softmax}}
\providecommand{\argmax}{\operatorname*{arg\,max}}
\providecommand{\argmin}{\operatorname*{arg\,min}}
\providecommand{\sign}{\operatorname{sign}}
\providecommand{\symbb}{\mathbb}
\providecommand{\symbf}{\mathbf}
\providecommand{\symcal}{\mathcal}
\providecommand{\mathds}{\mathbb}
\providecommand{\mathbbm}{\mathbb}
\providecommand{\bm}{\boldsymbol}
% \lt \gt are in mathfix's allowlist (so they survive validation) but are not core TeX --
% define them here so the writer's x_{\lt i} notation renders instead of erroring.
\providecommand{\lt}{<}
\providecommand{\gt}{>}
"""


def render_tectonic(clean_md_path: Path, output_pdf: Path, title: str = "Technical Book") -> bool:
    """Render via pandoc -> LaTeX -> tectonic, in TWO steps so we can pass tectonic's
    `-Z continue-on-errors`: in a 250k-word LLM-generated book a single residual TeX error
    (an undefined macro, a malformed \\frac) would otherwise abort the WHOLE render and drop us
    to the math-blind weasyprint fallback. continue-on-errors keeps tectonic-quality math
    everywhere and only mangles the few broken spots locally. Success = a PDF was produced
    (tectonic may return non-zero yet still emit the PDF)."""
    header_path = clean_md_path.with_name("header.tex")
    header_path.write_text(_PREAMBLE, encoding="utf-8")
    tex_path = output_pdf.with_suffix(".tex")  # -> book.tex, so tectonic emits book.pdf
    # 1) markdown -> standalone LaTeX
    r1 = subprocess.run(
        ["pandoc", str(clean_md_path), "-o", str(tex_path), "--standalone", "--wrap=none",
         "-H", str(header_path), "--toc", "--toc-depth=2",
         "-V", "documentclass=report",
         "-V", "geometry:margin=0.85in", "-V", "fontsize=10.5pt", "-V", "papersize=a4",
         "-V", "colorlinks=true", "-V", "linkcolor=accent", "-V", "urlcolor=accent",
         "--metadata", f"title={title}"],
        capture_output=True, text=True,
    )
    if r1.returncode != 0:
        print(f"  [pandoc->tex] {r1.stderr[-500:]}")
        return False
    # Remove any stale PDF so the success check can't be fooled by a previous (e.g. weasy) render.
    try:
        output_pdf.unlink()
    except FileNotFoundError:
        pass
    # 2) LaTeX -> PDF, continuing past severe errors
    r2 = subprocess.run(
        ["tectonic", "-Z", "continue-on-errors", "--outfmt", "pdf",
         "--outdir", str(output_pdf.parent), str(tex_path)],
        capture_output=True, text=True,
    )
    log_path = clean_md_path.with_name("tectonic.err.log")
    try:
        log_path.write_text(r2.stderr or "", encoding="utf-8")
    except Exception:
        pass
    # Success is judged by the artifact, not the return code (continue-on-errors -> rc may be != 0).
    if output_pdf.exists() and output_pdf.stat().st_size > 50_000:
        if r2.returncode != 0:
            print(f"  [tectonic] produced PDF with recoverable errors (rc={r2.returncode}); log -> {log_path}")
        return True
    print(f"  [tectonic] no PDF produced (rc={r2.returncode}); full log -> {log_path}")
    print(f"  [tectonic] {r2.stderr[-1200:]}")
    return False


def render_weasy(clean_md_path: Path, output_pdf: Path, title: str = "Technical Book") -> bool:
    """Render via pandoc --html + weasyprint."""
    html_path = output_pdf.with_suffix(".html")
    r = subprocess.run(
        ["pandoc", str(clean_md_path), "-o", str(html_path),
         "--standalone", "--toc", "--toc-depth=3", "--mathml",
         "--metadata", f"title={title}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  [pandoc html] {r.stderr[-300:]}")
        return False
    try:
        import weasyprint, warnings
        warnings.filterwarnings("ignore")
        weasyprint.HTML(filename=str(html_path)).write_pdf(str(output_pdf))
        return True
    except Exception as e:
        print(f"  [weasyprint] {e}")
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--weasy", action="store_true", help="Force weasyprint")
    args = p.parse_args()

    run_dir = ROOT / "output/runs" / args.run
    book_md = run_dir / "book.md"
    clean_md_out = run_dir / "book.clean.md"
    output_pdf = run_dir / "book.pdf"

    print(f"Reading: {book_md}")
    content = book_md.read_text(encoding="utf-8")
    title, content = _extract_and_strip_title(content)
    wc = len(content.split())
    lines = content.count("\n") + 1
    print(f"  {wc} words, {lines} lines | title: {title}")

    print("Cleaning math & rendering diagrams...")
    cleaned = clean_md(content, run_dir)
    clean_md_out.write_text(cleaned, encoding="utf-8")
    sz_clean = clean_md_out.stat().st_size
    print(f"  clean.md: {sz_clean} bytes")

    if args.weasy:
        print("Rendering via weasyprint...")
        ok = render_weasy(clean_md_out, output_pdf, title)
    else:
        print("Rendering via tectonic...")
        ok = render_tectonic(clean_md_out, output_pdf, title)
        if not ok:
            print("  fallback: weasyprint...")
            ok = render_weasy(clean_md_out, output_pdf, title)

    if ok:
        sz = output_pdf.stat().st_size
        print(f"  Done: {output_pdf} ({sz/1024/1024:.2f} MB)")
    else:
        print("  [ERROR] Render failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
