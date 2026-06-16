#!/usr/bin/env python3
"""
Render book.md to PDF using pandoc + tectonic (LaTeX).

Usage:
  python3 files/scripts/render_book.py --run llm_trends_2026_2027 [--weasy]
"""
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "files"))  # so `research.mathfix` resolves when run standalone

from research.mathfix import normalize_math  # canonical math/special-char normalization (single source of truth)


def clean_md(content: str) -> str:
    """Apply math fixes and markdown hygiene to the full book markdown."""
    # Strip YAML frontmatter (lines between leading --- and the next ---)
    # This prevents pandoc from misinterpreting --- section dividers as YAML
    lines = content.split("\n")
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                content = "\n".join(lines[i+1:])
                break
    # Convert bare --- section dividers in the body to *** (LaTeX-safe)
    # Pandoc interprets --- as YAML at line 1, so we already removed the frontmatter.
    # But lone --- lines in the body also trigger YAML parsing; replace them.
    content = re.sub(r"\n---\n", "\n\n***\n\n", content)
    content = normalize_math(content)  # split glued -> balance $$ -> escape Unicode -> validate+neutralize
    return content


# LaTeX preamble: define the operators/macros the local writer commonly emits but that
# are NOT built-in (\softmax, \argmax, \symbb...). \providecommand = no clash if pandoc
# or amsmath already defines one. Without these, a single \softmax crashes the whole book.
_PREAMBLE = r"""\usepackage{amsmath}
\usepackage{amssymb}
\providecommand{\softmax}{\operatorname{softmax}}
\providecommand{\argmax}{\operatorname*{arg\,max}}
\providecommand{\argmin}{\operatorname*{arg\,min}}
\providecommand{\sign}{\operatorname{sign}}
\providecommand{\symbb}{\mathbb}
\providecommand{\symbf}{\mathbf}
\providecommand{\symcal}{\mathcal}
"""


def render_tectonic(clean_md_path: Path, output_pdf: Path) -> bool:
    """Render via pandoc + tectonic."""
    header_path = clean_md_path.with_name("header.tex")
    header_path.write_text(_PREAMBLE, encoding="utf-8")
    cmd = [
        "pandoc", str(clean_md_path),
        "-o", str(output_pdf),
        "--pdf-engine=tectonic",
        "-H", str(header_path),
        "--toc", "--toc-depth=3",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
        "-V", "papersize=a4",
        "-V", "linkcolor=blue",
        "-V", "urlcolor=blue",
        "--metadata", "title=Large Language Models: A Comprehensive Handbook",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Persist the FULL stderr so a render failure is diagnosable (not just the tail).
        log_path = clean_md_path.with_name("tectonic.err.log")
        try:
            log_path.write_text(r.stderr or "", encoding="utf-8")
        except Exception:
            pass
        print(f"  [tectonic] rc={r.returncode}; full log -> {log_path}")
        print(f"  [tectonic] {r.stderr[-1200:]}")
        return False
    return True


def render_weasy(clean_md_path: Path, output_pdf: Path) -> bool:
    """Render via pandoc --html + weasyprint."""
    html_path = output_pdf.with_suffix(".html")
    r = subprocess.run(
        ["pandoc", str(clean_md_path), "-o", str(html_path),
         "--standalone", "--toc", "--toc-depth=3", "--mathml",
         "--metadata", "title=Large Language Models: A Comprehensive Handbook"],
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

    run_dir = ROOT / "files/output/runs" / args.run
    book_md = run_dir / "book.md"
    clean_md_out = run_dir / "book.clean.md"
    output_pdf = run_dir / "book.pdf"

    print(f"Reading: {book_md}")
    content = book_md.read_text(encoding="utf-8")
    wc = len(content.split())
    lines = content.count("\n") + 1
    print(f"  {wc} words, {lines} lines")

    print("Cleaning math...")
    cleaned = clean_md(content)
    clean_md_out.write_text(cleaned, encoding="utf-8")
    sz_clean = clean_md_out.stat().st_size
    print(f"  clean.md: {sz_clean} bytes")

    if args.weasy:
        print("Rendering via weasyprint...")
        ok = render_weasy(clean_md_out, output_pdf)
    else:
        print("Rendering via tectonic...")
        ok = render_tectonic(clean_md_out, output_pdf)
        if not ok:
            print("  fallback: weasyprint...")
            ok = render_weasy(clean_md_out, output_pdf)

    if ok:
        sz = output_pdf.stat().st_size
        print(f"  Done: {output_pdf} ({sz/1024/1024:.2f} MB)")
    else:
        print("  [ERROR] Render failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
