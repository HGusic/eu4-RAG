"""Query the local Chroma index and print the nearest wiki chunks."""

from __future__ import annotations

import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "eu4_wiki"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
            raise SystemExit(f"No index at {CHROMA_DIR}. Run src/index/build.py first.")
        embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection(name=COLLECTION, embedding_function=embed_fn)
    return _collection


def retrieve(question: str, k: int = 5) -> list[dict]:
    result = _get_collection().query(
        query_texts=[question],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append(
            {
                "text": doc,
                "title": meta["title"],
                "section": meta["section"],
                "url": meta["url"],
                "pageid": meta.get("pageid", ""),
                "distance": dist,
            }
        )
    return hits


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "How is advisor hiring cost calculated?"
    k = 5
    hits = retrieve(question, k=k)
    print(f"Question: {question}\n")
    for i, hit in enumerate(hits, 1):
        print(f"[{i}] {hit['title']} — {hit['section']}  (distance={hit['distance']:.3f})")
        print(f"    {hit['url']}")
        preview = hit["text"][:500].replace("\n", "\n    ")
        print(f"    {preview}\n")


if __name__ == "__main__":
    main()
