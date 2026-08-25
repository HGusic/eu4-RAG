"""HTTP API + static HTML UI. Uses retrieve.py and generate.py."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from generate import generate_answer, generate_stream
from retrieve import retrieve

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="EU4 Wiki RAG")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class AskBody(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=8)


def _sources(hits: list[dict]) -> list[dict]:
    return [
        {
            "title": hit["title"],
            "section": hit["section"],
            "url": hit["url"],
            "distance": round(float(hit["distance"]), 3),
            "text": hit["text"][:2000],
        }
        for hit in hits
    ]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/ask")
def ask(body: AskBody):
    question = body.question.strip()
    try:
        hits = retrieve(question, k=body.k)
    except SystemExit as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        answer = generate_answer(question, hits)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama failed. Is it running? ({exc})",
        ) from exc
    return {"answer": answer, "sources": _sources(hits)}


@app.post("/api/ask/stream")
def ask_stream(body: AskBody):
    question = body.question.strip()
    try:
        hits = retrieve(question, k=body.k)
    except SystemExit as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def events():
        yield f"data: {json.dumps({'type': 'sources', 'sources': _sources(hits)})}\n\n"
        try:
            for token in generate_stream(question, hits):
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
            return
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
