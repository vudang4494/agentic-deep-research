#!/usr/bin/env python3
"""
Render book.md to PDF using pandoc + tectonic (LaTeX).

Usage:
  python3 files/scripts/render_book.py --run llm_trends_2026_2027 [--weasy]
"""
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _balance_display_math(content: str) -> str:
    """Balance $$ pairs so LaTeX doesn't crash with 'Missing $ inserted'."""
    # Skip fenced code blocks
    in_code = False
    lines = content.split("\n")
    result_lines = []
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
        result_lines.append(line)

    text = "\n".join(result_lines)
    count = text.count("$$")
    if count % 2 == 0:
        return text

    # Odd count: find the last unpaired $$
    lines = text.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].count("$$") % 2 == 1:
            lines[i] += "$$"
            break
    return "\n".join(lines)


_ESCAPE_MAP = {
    "ℝ": r"$\mathbb{R}$", "∈": r"$\in$", "∉": r"$\notin$",
    "∞": r"$\infty$", "α": r"$\alpha$", "β": r"$\beta$", "γ": r"$\gamma$",
    "δ": r"$\delta$", "ε": r"$\epsilon$", "θ": r"$\theta$", "λ": r"$\lambda$",
    "μ": r"$\mu$", "π": r"$\pi$", "σ": r"$\sigma$", "φ": r"$\phi$",
    "ω": r"$\omega$", "Γ": r"$\Gamma$", "Δ": r"$\Delta$", "Θ": r"$\Theta$",
    "Λ": r"$\Lambda$", "Π": r"$\Pi$", "Σ": r"$\Sigma$", "Φ": r"$\Phi$",
    "Ψ": r"$\Psi$", "Ω": r"$\Omega$",
    "≤": r"$\leq$", "≥": r"$\geq$", "≠": r"$\neq$", "≈": r"$\approx$",
    "×": r"$\times$", "÷": r"$\div$", "±": r"$\pm$",
    "∇": r"$\nabla$", "∂": r"$\partial$",
    "∀": r"$\forall$", "∃": r"$\exists$",
    "⊂": r"$\subset$", "⊃": r"$\supset$", "∩": r"$\cap$", "∪": r"$\cup$",
    "ℕ": r"$\mathbb{N}$", "ℤ": r"$\mathbb{Z}$", "ℂ": r"$\mathbb{C}$",
    "𝕀": r"$\mathbb{I}$",
    "ℹ": r"$\mathbb{I}$",
}


def _escape_unicode_math(content: str) -> str:
    """Escape Unicode math symbols for LaTeX compatibility."""
    # NFKC normalize first
    import unicodedata
    try:
        content = unicodedata.normalize("NFKC", content)
    except Exception:
        pass

    # Escape math symbols in text (outside $...$)
    result = []
    i = 0
    in_math = False
    while i < len(content):
        c = content[i]
        if c == "$" and (i == 0 or content[i-1] != "\\"):
            in_math = not in_math
            result.append(c)
            i += 1
            continue

        if not in_math and c in _ESCAPE_MAP:
            result.append(_ESCAPE_MAP[c])
        else:
            result.append(c)
        i += 1

    return "".join(result)


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
    content = _balance_display_math(content)
    content = _escape_unicode_math(content)
    return content


def render_tectonic(clean_md_path: Path, output_pdf: Path) -> bool:
    """Render via pandoc + tectonic."""
    cmd = [
        "pandoc", str(clean_md_path),
        "-o", str(output_pdf),
        "--pdf-engine=tectonic",
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
        print(f"  [tectonic] {r.stderr[-500:]}")
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
