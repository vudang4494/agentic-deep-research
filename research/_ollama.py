"""Single-source Ollama transport (endpoint + canonical chat round).

`OLLAMA_BASE` used to be a copy-pasted literal in 8+ modules -- the same
silent-drift trap PR#28 killed for model names. It lives HERE now; every module
that talks to Ollama imports it. `chat()` is the canonical /api/chat round that
discovery, outline_from_research and deep_investigate carried as byte-identical
`_ollama_chat` copies.

Modules with genuinely different call semantics (top_p, `_strip_think`, a reused
httpx.Client for connection pooling, custom fallbacks) keep their own call body
on purpose -- they only import OLLAMA_BASE from here. The single-source invariant
is enforced by eval/verify_all.py (check I): the endpoint literal and the
`_ollama_chat` definition may appear ONLY in this file.

LOCAL-only doctrine: the endpoint is the local Ollama daemon. This is model
inference, always localhost -- never a cloud LLM API.
"""
from __future__ import annotations

import httpx

OLLAMA_BASE = "http://localhost:11434"

# discovery / outline_from_research / deep_investigate all used TIMEOUT = 300.0
# as the default for their `_ollama_chat`; keep that as the shared default so the
# collapse is behavior-identical for callers that omit `timeout`.
DEFAULT_TIMEOUT = 300.0


def chat(model: str, messages: list, temperature: float = 0.3,
         num_predict: int = 2000, timeout: float = DEFAULT_TIMEOUT) -> str:
    """One /api/chat round (stream off, think off).

    Raises on transport failure (httpx / non-2xx). Falls back to the `thinking`
    field when `content` is empty -- the exact behavior the three collapsed
    `_ollama_chat` copies had.
    """
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": messages,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    with httpx.Client(timeout=timeout) as c:
        r = c.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        content = (data.get("message") or {}).get("thinking", "").strip()
    return content
