"""Single verification gate. Everything must pass through this before it ships.

    python3 eval/verify_all.py           # static checks + acceptance tests
    python3 eval/verify_all.py --static  # static checks only (no Ollama needed)

Exit 0 = green, 1 = at least one FAIL. WARN never fails the gate.

Static checks are pure source/AST analysis -- no models, no network, seconds to run.
They encode the invariants that CLAUDE.md calls bat bien, so a refactor that silently
breaks one is caught here instead of three runs later:

  A. every module imports cleanly
  B. LOCAL-only            -- no external LLM API host reachable from research/ or pipeline/
  C. Verifier != Writer    -- the writer model must never appear in the verify layer
  D. embed unified         -- bge-m3 everywhere, zero live nomic references
  E. no constant drift     -- a constant defined in two modules with two values
  F. no model literals     -- model names live in config.py, not sprinkled at call sites
  G. mathfix single-source -- no local re-implementation of math normalization
  H. providers well-formed -- PROVIDERS_DEFAULT holds only known provider names
  I. Ollama single-source  -- the endpoint literal lives only in research/_ollama.py
"""
import argparse
import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = ("research", "pipeline")
CONFIG = ROOT / "research" / "config.py"

# Verify-layer modules: the writer model must never appear here (self-preference guard).
VERIFY_LAYER = ("research/verify.py", "research/faithfulness.py")

EXTERNAL_LLM_HOSTS = (
    "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com",
    "api.cohere.ai", "api.mistral.ai",
)
KNOWN_PROVIDERS = {"arxiv", "wikipedia", "tavily", "brave", "ddg"}
MODEL_LITERAL_RE = re.compile(r"[\"'](?:gemma[\w.]*:[\w.-]+|batiai/[\w.\-]+:[\w.]+|bge-m3[\w:.-]*)[\"']")
NOMIC_RE = re.compile(r"\bnomic\b|nomic-embed")  # 'economic' must not match
OLLAMA_HOST_RE = re.compile(r"(?:localhost|127\.0\.0\.1):11434")
OLLAMA_MODULE = "research/_ollama.py"  # the single source of the Ollama endpoint

# Acceptance tests: standalone scripts (this repo does not use pytest). Each must exit 0.
ACCEPTANCE = [
    ("eval/test_outline_enforce.py", "outline anti-matrix enforcement", False),
    ("eval/test_decite.py", "intra-book citation cleaner", False),
    ("eval/test_math_char_safety.py", "math/special-char safety", False),
    ("eval/test_verify_optim.py", "verify layer", True),  # needs_ollama
]

results = []  # (level, check, detail)


def ok(check, detail=""):
    results.append(("PASS", check, detail))


def warn(check, detail):
    results.append(("WARN", check, detail))


def fail(check, detail):
    results.append(("FAIL", check, detail))


def py_files():
    for d in SRC_DIRS:
        yield from sorted((ROOT / d).glob("*.py"))


def rel(p):
    return str(Path(p).relative_to(ROOT))


def source_of(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_comments_and_strings(src):
    """Source with comments and string literals blanked, so a rule that greps for a
    pattern does not fire on a comment that merely *mentions* it."""
    out = []
    for tok_line in src.split("\n"):
        out.append(tok_line.split("#", 1)[0])
    no_comments = "\n".join(out)
    return re.sub(r"(['\"])(?:\\.|(?!\1).)*\1", "''", no_comments, flags=re.S)


# ---------------------------------------------------------------- A. imports
def check_imports():
    mods = []
    for p in py_files():
        if p.name == "__init__.py":
            continue
        mods.append(f"{p.parent.name}.{p.stem}")
    code = "import importlib,sys\n" + "".join(
        f"importlib.import_module({m!r})\n" for m in mods
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                       capture_output=True, text=True, timeout=180)
    if r.returncode == 0:
        ok("A. imports", f"{len(mods)} modules import cleanly")
    else:
        last = (r.stderr.strip().split("\n") or ["?"])[-1]
        fail("A. imports", last[:200])


# ------------------------------------------------------------- B. LOCAL-only
def check_local_only():
    hits = []
    for p in py_files():
        body = strip_comments_and_strings(source_of(p))
        raw = source_of(p)
        for host in EXTERNAL_LLM_HOSTS:
            # host appears in a real string literal (not just a comment)
            if host in raw and host in re.sub(r"^\s*#.*$", "", raw, flags=re.M):
                if host in body or f'"{host}' in raw or f"'{host}" in raw:
                    hits.append(f"{rel(p)} -> {host}")
    if hits:
        fail("B. LOCAL-only", "external LLM API referenced: " + "; ".join(hits[:3]))
    else:
        ok("B. LOCAL-only", "no external LLM API host in research/ or pipeline/")


# --------------------------------------------------- C. Verifier != Writer
def check_verifier_not_writer():
    writer = None
    m = re.search(r'^WRITER_MODEL\s*=\s*["\']([^"\']+)', source_of(CONFIG), re.M)
    if m:
        writer = m.group(1)
    if not writer:
        warn("C. Verifier!=Writer", "WRITER_MODEL not found in config.py -- skipped")
        return
    offenders = []
    for relp in VERIFY_LAYER:
        p = ROOT / relp
        if not p.exists():
            continue
        for i, line in enumerate(source_of(p).split("\n"), 1):
            if writer in line and not line.strip().startswith("#"):
                offenders.append(f"{relp}:{i}")
    if offenders:
        fail("C. Verifier!=Writer",
             f"writer model {writer!r} reachable in verify layer: {', '.join(offenders[:3])}")
    else:
        ok("C. Verifier!=Writer", f"writer {writer!r} absent from {len(VERIFY_LAYER)} verify modules")


# ------------------------------------------------------------ D. embed unified
def check_embed_unified():
    m = re.search(r'^EMBED_MODEL\s*=\s*["\']([^"\']+)', source_of(CONFIG), re.M)
    embed = m.group(1) if m else None
    if not embed or not embed.startswith("bge-m3"):
        fail("D. embed unified", f"config EMBED_MODEL is {embed!r}, expected bge-m3*")
        return
    live_nomic = []
    for p in py_files():
        for i, line in enumerate(source_of(p).split("\n"), 1):
            code = line.split("#", 1)[0]  # a trailing comment may legitimately say why nomic was dropped
            if NOMIC_RE.search(code):     # word-boundary: 'economic' must not read as the nomic model
                live_nomic.append(f"{rel(p)}:{i}")
    if live_nomic:
        fail("D. embed unified", f"live nomic reference(s): {', '.join(live_nomic[:3])}")
    else:
        ok("D. embed unified", f"{embed} everywhere, 0 live nomic refs")


# ----------------------------------------------------------- E. constant drift
def check_constant_drift():
    """A constant declared in config.py and REDEFINED elsewhere with a different value.

    Scoped to config.py deliberately: config is the declared single source, so a module
    disagreeing with it is real drift. Names that only ever live module-locally (TIMEOUT,
    DEFAULT_TIMEOUT -- each tuned to its own task) are not drift and are not flagged."""
    seen = defaultdict(dict)  # NAME -> {module: value_repr}
    for p in py_files():
        try:
            tree = ast.parse(source_of(p))
        except SyntaxError as e:
            fail("E. constant drift", f"{rel(p)} does not parse: {e}")
            return
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            tgt = node.targets[0]
            if not isinstance(tgt, ast.Name) or not tgt.id.isupper():
                continue
            if isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, (int, float, str, bool)):
                seen[tgt.id][rel(p)] = repr(node.value.value)
    cfg = rel(CONFIG)
    drift = {n: mv for n, mv in seen.items()
             if cfg in mv and len(mv) > 1 and len(set(mv.values())) > 1}
    if drift:
        detail = "; ".join(
            f"{n}: " + ", ".join(f"{m}={v}" for m, v in sorted(mv.items()))
            for n, mv in sorted(drift.items())
        )
        fail("E. constant drift", detail[:400])
    else:
        shared = sum(1 for n, mv in seen.items() if cfg in mv and len(mv) > 1)
        ok("E. constant drift", f"no module contradicts config.py ({shared} shared constants agree)")


# --------------------------------------------------------- F. model literals
def check_model_literals():
    offenders = defaultdict(list)
    for p in py_files():
        if p.resolve() == CONFIG.resolve():
            continue
        for i, line in enumerate(source_of(p).split("\n"), 1):
            if line.strip().startswith("#"):
                continue
            code = line.split("#", 1)[0]
            if MODEL_LITERAL_RE.search(code):
                offenders[rel(p)].append(i)
    if offenders:
        total = sum(len(v) for v in offenders.values())
        detail = "; ".join(f"{f}:{','.join(map(str, ls[:4]))}" for f, ls in sorted(offenders.items()))
        fail("F. model literals", f"{total} hardcoded model name(s) outside config.py -- {detail}"[:400])
    else:
        ok("F. model literals", "model names only in config.py")


# ------------------------------------------------------ G. mathfix single-source
def check_mathfix_single_source():
    mathfix = ROOT / "research" / "mathfix.py"
    if not mathfix.exists():
        warn("G. mathfix single-source", "research/mathfix.py missing -- skipped")
        return
    fns = set()
    for node in ast.parse(source_of(mathfix)).body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            fns.add(node.name)
    clones = []
    for p in py_files():
        if p.resolve() == mathfix.resolve():
            continue
        try:
            tree = ast.parse(source_of(p))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in fns:
                clones.append(f"{rel(p)}::{node.name}")
    if clones:
        fail("G. mathfix single-source", "local copy of math normalization: " + ", ".join(clones[:3]))
    else:
        ok("G. mathfix single-source", f"{len(fns)} public fns, no local re-implementations")


# --------------------------------------------------------------- H. providers
def check_providers():
    m = re.search(r"^PROVIDERS_DEFAULT\s*=\s*\(([^)]*)\)", source_of(CONFIG), re.M)
    if not m:
        fail("H. providers", "PROVIDERS_DEFAULT not found in config.py")
        return
    names = [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
    unknown = [n for n in names if n not in KNOWN_PROVIDERS]
    if unknown:
        fail("H. providers", f"unknown provider(s) in PROVIDERS_DEFAULT: {unknown}")
    elif not names:
        fail("H. providers", "PROVIDERS_DEFAULT is empty")
    else:
        ok("H. providers", f"{len(names)} known providers: {', '.join(names)}")


# ------------------------------------------------ I. Ollama single-source
def check_ollama_single_source():
    """The Ollama endpoint literal appears in exactly one module (research/_ollama.py);
    every other caller imports OLLAMA_BASE from there. Same drift guard as D/F -- one
    HTTP layer instead of the eight copy-pasted 'http://localhost:11434' literals that
    used to live across the research modules."""
    offenders = []
    for p in py_files():
        if rel(p) == OLLAMA_MODULE:
            continue
        for i, line in enumerate(source_of(p).split("\n"), 1):
            code = line.split("#", 1)[0]  # a trailing comment may mention the port
            if OLLAMA_HOST_RE.search(code):
                offenders.append(f"{rel(p)}:{i}")
    if offenders:
        fail("I. Ollama single-source",
             f"endpoint literal outside {OLLAMA_MODULE}: {', '.join(offenders[:4])}")
    else:
        ok("I. Ollama single-source",
           f"endpoint only in {OLLAMA_MODULE}; all callers import OLLAMA_BASE")


# ---------------------------------------------------------- acceptance tests
def ollama_up():
    try:
        import httpx
        httpx.get("http://localhost:11434/api/tags", timeout=3).raise_for_status()
        return True
    except Exception:
        return False


def run_acceptance():
    have_ollama = ollama_up()
    for relp, label, needs_ollama in ACCEPTANCE:
        p = ROOT / relp
        if not p.exists():
            warn(f"T. {label}", f"{relp} missing -- skipped")
            continue
        if needs_ollama and not have_ollama:
            warn(f"T. {label}", "Ollama not reachable -- skipped")
            continue
        try:
            r = subprocess.run([sys.executable, str(p)], cwd=ROOT,
                               capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            fail(f"T. {label}", f"{relp} timed out")
            continue
        if r.returncode == 0:
            tail = [l for l in r.stdout.strip().split("\n") if l.strip()]
            ok(f"T. {label}", tail[-1][:100] if tail else relp)
        else:
            tail = [l for l in (r.stdout + r.stderr).strip().split("\n") if l.strip()]
            fail(f"T. {label}", (tail[-1] if tail else f"exit {r.returncode}")[:200])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true",
                    help="static checks only -- skip acceptance tests")
    args = ap.parse_args()

    for fn in (check_imports, check_local_only, check_verifier_not_writer,
               check_embed_unified, check_constant_drift, check_model_literals,
               check_mathfix_single_source, check_providers,
               check_ollama_single_source):
        try:
            fn()
        except Exception as e:  # a broken check must not masquerade as a pass
            fail(fn.__name__, f"check itself errored: {type(e).__name__}: {e}")

    if not args.static:
        run_acceptance()

    width = max(len(c) for _, c, _ in results) + 2
    print("=" * 78)
    print("VERIFY GATE")
    print("=" * 78)
    for level, check, detail in results:
        mark = {"PASS": "  ok  ", "WARN": " warn ", "FAIL": " FAIL "}[level]
        print(f"[{mark}] {check:<{width}} {detail}")
    n_fail = sum(1 for l, _, _ in results if l == "FAIL")
    n_warn = sum(1 for l, _, _ in results if l == "WARN")
    n_pass = sum(1 for l, _, _ in results if l == "PASS")
    print("-" * 78)
    print(f"{n_pass} passed, {n_warn} warned, {n_fail} FAILED")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
