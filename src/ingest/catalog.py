"""Download the list of main-namespace EU4 wiki pages (no article text)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wiki import DATA_DIR, api_get, polite_sleep


def catalog_pages(limit: int | None, delay: float) -> list[dict]:
    pages: list[dict] = []
    continue_token = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": "0",
            "apfilterredir": "nonredirects",
            "aplimit": "500",
        }
        if continue_token:
            params["apcontinue"] = continue_token
        data = api_get(params)
        batch = data.get("query", {}).get("allpages", [])
        for item in batch:
            pages.append({"pageid": item["pageid"], "title": item["title"]})
            if limit is not None and len(pages) >= limit:
                return pages
        continue_token = data.get("continue", {}).get("apcontinue")
        if not continue_token:
            return pages
        polite_sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="List EU4 wiki articles into data/catalog.json")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N pages (for a test run)")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between API calls")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pages = catalog_pages(limit=args.limit, delay=args.delay)
    out = DATA_DIR / "catalog.json"
    out.write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(pages)} pages to {out}")


if __name__ == "__main__":
    main()
