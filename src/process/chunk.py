"""Split cleaned pages into heading-aware chunks with size limits."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "data" / "cleaned"
OUT_DIR = ROOT / "data" / "chunks"

MIN_CHARS = 200
MAX_CHARS = 3000
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.MULTILINE)
SKIP_EXACT = {"references", "see also", "external links", "notes"}
SKIP_SUBSTRING = ("portrait", "gallery")
FORMULA_HINT = re.compile(r"(\\text\{|\\frac\{|\\cdot|\\left|\\right)")


def _slug(value: str) -> str:
    slug = re.sub(r"[^\w]+", "_", value, flags=re.UNICODE).strip("_")
    return slug or "section"


def _should_skip(section_title: str) -> bool:
    lower = section_title.lower().strip()
    if lower in SKIP_EXACT:
        return True
    return any(part in lower for part in SKIP_SUBSTRING)


def _is_formula_line(line: str) -> bool:
    return bool(FORMULA_HINT.search(line))


def parse_sections(text: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(text))
    sections: list[dict] = []

    def add(level: int, heading: str, path: str, body: str) -> None:
        body = body.strip()
        if not body:
            return
        sections.append({"level": level, "heading": heading, "path": path, "text": body})

    intro = text[: matches[0].start()] if matches else text
    add(1, "Introduction", "Introduction", intro)

    h2 = h3 = None
    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        heading = re.sub(r"^[= ]+|[= ]+$", "", heading)
        if level == 2:
            h2, h3 = heading, None
            path = heading
        elif level == 3:
            h3 = heading
            path = f"{h2} / {heading}" if h2 else heading
        else:
            parts = [p for p in (h2, h3, heading) if p]
            path = " / ".join(parts)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        add(level, heading, path, text[start:end])
    return sections


def merge_small_sections(sections: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for section in sections:
        if (
            merged
            and section["level"] > merged[-1]["level"]
            and len(section["text"]) < MIN_CHARS
            and not _should_skip(section["heading"])
        ):
            parent = merged[-1]
            parent["text"] = (
                f"{parent['text']}\n\n{section['heading']}\n{section['text']}"
            )
            continue
        merged.append(section)
    return merged


def split_oversized(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    paragraphs = re.split(r"\n\s*\n", text)
    parts: list[str] = []
    buf: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buf, size
        if buf:
            parts.append("\n\n".join(buf).strip())
            buf, size = [], 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) > MAX_CHARS:
            flush()
            parts.extend(_split_long_paragraph(para))
            continue
        extra = len(para) + (2 if buf else 0)
        if buf and size + extra > MAX_CHARS:
            flush()
        buf.append(para)
        size += extra
    flush()
    return [p for p in parts if p]


def _split_long_paragraph(para: str) -> list[str]:
    lines = para.splitlines()
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        block = [line]
        j = i + 1
        if _is_formula_line(line):
            while j < len(lines) and _is_formula_line(lines[j]):
                block.append(lines[j])
                j += 1
        piece = "\n".join(block)
        extra = len(piece) + (1 if buf else 0)
        if buf and size + extra > MAX_CHARS:
            parts.append("\n".join(buf))
            buf, size = [], 0
        buf.append(piece)
        size += extra
        i = j
    if buf:
        parts.append("\n".join(buf))
    return parts


def unique_id(pageid: int, path: str, used: set[str]) -> str:
    base = f"{pageid}::{_slug(path)}"
    chunk_id = base
    n = 2
    while chunk_id in used:
        chunk_id = f"{base}_{n}"
        n += 1
    used.add(chunk_id)
    return chunk_id


def chunk_page(record: dict) -> tuple[list[dict], int]:
    title = record["title"]
    url = record["url"]
    pageid = record["pageid"]
    used: set[str] = set()
    chunks: list[dict] = []
    skipped = 0

    for section in merge_small_sections(parse_sections(record["text"])):
        if _should_skip(section["heading"]):
            skipped += 1
            continue
        pieces = split_oversized(section["text"])
        for i, piece in enumerate(pieces):
            path = section["path"] if len(pieces) == 1 else f"{section['path']} ({i + 1})"
            body = f"{title} > {path}\n\n{piece}"
            chunks.append(
                {
                    "id": unique_id(pageid, path, used),
                    "pageid": pageid,
                    "revid": record.get("revid"),
                    "title": title,
                    "section": path,
                    "url": f"{url}#{section['heading'].replace(' ', '_')}",
                    "text": body,
                }
            )
    return chunks, skipped


def main() -> None:
    files = sorted(IN_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No cleaned JSON in {IN_DIR}. Run clean.py first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    skipped_total = 0
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        chunks, skipped = chunk_page(record)
        skipped_total += skipped
        out = OUT_DIR / path.name
        out.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        total += len(chunks)
        print(f"{record['title']}: {len(chunks)} chunks")

    print(f"Wrote {total} chunks from {len(files)} pages to {OUT_DIR}")
    print(f"Skipped sections (references/portraits/gallery): {skipped_total}")
    print(f"Limits: min={MIN_CHARS} chars merge, max={MAX_CHARS} chars split")


if __name__ == "__main__":
    main()
