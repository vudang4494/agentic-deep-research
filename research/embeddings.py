"""bge-m3 embeddings via Ollama /api/embed, used by notes.rank()."""
import math
from typing import List

import httpx

from .config import EMBED_MODEL
from ._ollama import OLLAMA_BASE

DEFAULT_MODEL = EMBED_MODEL
TIMEOUT = 60.0

# Ollama's /api/embed rejects large batches with HTTP 400 -- and the limit is on the NUMBER of
# texts, not the payload size: measured against bge-m3, 20 texts x 5000 words (586 KB) succeeds
# while 350 texts x 50 words (104 KB) fails with `Post ".../tokenize": read tcp ...`. The break
# point sits between 128 and 192 items, so 64 leaves a 2x margin.
#
# This mattered far more than one failed call. `embed()` returns [] on failure and every caller
# treats [] as "embedding unavailable, degrade gracefully", so a batch over the limit did not
# raise -- it silently disabled whatever the caller wanted the embedding FOR. Observed on a
# 35-chapter outline: `relate/dedup skipped: embed unavailable`, i.e. the cross-chapter
# near-duplicate pass and the depends_on wiring were both skipped, and the outline shipped with
# 7 surviving overlap pairs. Because batch size scales with book size, the anti-repetition pass
# switched itself off exactly when the book got big enough to need it.
_MAX_BATCH = 64


def _embed_batch(client, texts, model):
    r = client.post(f"{OLLAMA_BASE}/api/embed", json={"model": model, "input": texts})
    r.raise_for_status()
    vecs = r.json().get("embeddings") or []
    # Newer Ollama returns {"embeddings": [[...], [...]]}; older may return {"embedding": [...]} for single.
    if isinstance(vecs, list) and vecs and not isinstance(vecs[0], list):
        vecs = [vecs]
    return vecs


def embed(texts: List[str], model: str = DEFAULT_MODEL) -> List[List[float]]:
    """Batch-embed a list of texts. Returns one vector per input, preserving order.

    Splits into `_MAX_BATCH` chunks so a large call cannot exceed Ollama's per-request item
    limit. Returns an empty list on any failure -- callers must handle the empty case
    (typically by falling back to lexical ranking), so a PARTIAL result must never be returned:
    a short list would pass some callers' truthiness check and silently mis-align vectors
    against inputs.
    """
    if not texts:
        return []
    out: List[List[float]] = []
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            for i in range(0, len(texts), _MAX_BATCH):
                chunk = texts[i:i + _MAX_BATCH]
                try:
                    vecs = _embed_batch(c, chunk, model)
                except Exception:
                    vecs = _embed_batch(c, chunk, model)   # one retry: transient 500/timeout
                if len(vecs) != len(chunk):
                    print(f"[research/embeddings] WARN: got {len(vecs)} vectors for "
                          f"{len(chunk)} inputs in one chunk", flush=True)
                    return []
                out.extend(vecs)
    except Exception as e:
        print(f"[research/embeddings] WARN: embed call failed: {e}", flush=True)
        return []
    return out


def cosine(a: List[float], b: List[float]) -> float:
    """Plain-Python cosine similarity. Returns 0.0 if either vector is empty/degenerate."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
