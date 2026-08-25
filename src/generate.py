"""Turn retrieved wiki chunks into an answer via Ollama."""

from __future__ import annotations

import os
from collections.abc import Iterator

MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
MAX_CHUNK_CHARS = 1200
NUM_PREDICT = 250
SYSTEM = """You answer Europa Universalis IV questions using ONLY the provided wiki excerpts.
If the excerpts do not contain the answer, say you do not know from the indexed wiki.
Cite the page and section names you used. Be concise (4-8 sentences) and keep numbers and formulas exact."""


def _prompt(question: str, hits: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i}] {hit['title']} — {hit['section']}\n{hit['text'][:MAX_CHUNK_CHARS]}"
        for i, hit in enumerate(hits, 1)
    )
    return f"{SYSTEM}\n\nWiki excerpts:\n{context}\n\nQuestion: {question}\nAnswer:"


def generate_stream(question: str, hits: list[dict]) -> Iterator[str]:
    import ollama

    stream = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": _prompt(question, hits)}],
        stream=True,
        options={"num_predict": NUM_PREDICT},
    )
    for part in stream:
        piece = part.get("message", {}).get("content", "")
        if piece:
            yield piece


def generate_answer(question: str, hits: list[dict]) -> str:
    return "".join(generate_stream(question, hits))
