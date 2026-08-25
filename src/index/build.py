"""Embed chunk JSON files into a local Chroma collection."""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_DIR = ROOT / "data" / "chunks"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "eu4_wiki"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 256


def load_chunks() -> tuple[list[str], list[str], list[dict]]:
    files = sorted(CHUNKS_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No chunk JSON in {CHUNKS_DIR}. Run chunk.py first.")
    ids, docs, metas = [], [], []
    seen: set[str] = set()
    for path in files:
        chunks = json.loads(path.read_text(encoding="utf-8"))
        for chunk in chunks:
            chunk_id = chunk["id"]
            if chunk_id in seen:
                raise SystemExit(f"Duplicate chunk id: {chunk_id}")
            seen.add(chunk_id)
            ids.append(chunk_id)
            docs.append(chunk["text"])
            metas.append(
                {
                    "pageid": str(chunk["pageid"]),
                    "revid": str(chunk.get("revid") or ""),
                    "title": chunk["title"],
                    "section": chunk["section"],
                    "url": chunk["url"],
                }
            )
    return ids, docs, metas


def batched(seq, size: int):
    for i in range(0, len(seq), size):
        yield i, seq[i : i + size]


def main() -> None:
    ids, docs, metas = load_chunks()
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    for start, _ in batched(ids, BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.add(
            ids=ids[start:end],
            documents=docs[start:end],
            metadatas=metas[start:end],
        )
        print(f"Indexed {min(end, len(ids))}/{len(ids)}")

    print(f"Done. {len(ids)} chunks in {CHROMA_DIR} ({COLLECTION})")
    print(f"Embedding model: {EMBED_MODEL}")


if __name__ == "__main__":
    main()
