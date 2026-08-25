"""Pull title + raw wikitext from MediaWiki JSON. Does not strip markup, numbers, or math."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "extracted"
WIKI_URL = "https://eu4.paradoxwikis.com/{title}"

MATH_RE = re.compile(r"<math[\s>]", re.IGNORECASE)


def extract_record(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ValueError(f"No query.pages in {path.name}")
    page = next(iter(pages.values()))
    if "missing" in page or "revisions" not in page:
        raise ValueError(f"No revision content in {path.name}")

    title = page["title"]
    revision = page["revisions"][0]
    slot = revision["slots"]["main"]
    wikitext = slot.get("*") or slot.get("content") or ""
    if not isinstance(wikitext, str):
        raise ValueError(f"Wikitext is not a string in {path.name}")

    return {
        "pageid": page["pageid"],
        "revid": revision.get("revid"),
        "title": title,
        "url": WIKI_URL.format(title=title.replace(" ", "_")),
        "wikitext": wikitext,
    }


def main() -> None:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No JSON in {RAW_DIR}. Run fetch.py first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    failed = 0
    with_math = 0

    for path in files:
        try:
            record = extract_record(path)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: {exc}")
            failed += 1
            continue
        out = OUT_DIR / f"{record['pageid']}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        ok += 1
        if MATH_RE.search(record["wikitext"]):
            with_math += 1

    print(f"Extracted {ok} pages to {OUT_DIR} ({failed} failed)")
    print(f"Pages containing <math> equations: {with_math}")
    print("Wikitext is stored unchanged (numbers, {{green|…}}, and <math> kept).")


if __name__ == "__main__":
    main()
