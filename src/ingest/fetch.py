"""Download article JSON for each page in data/catalog.json into data/raw/."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from wiki import DATA_DIR, api_get, polite_sleep

LOG = DATA_DIR / "logs" / "crawl.log"


def setup_log() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[logging.FileHandler(LOG, encoding="utf-8"), logging.StreamHandler()],
    )


def load_catalog() -> list[dict]:
    path = DATA_DIR / "catalog.json"
    if not path.exists():
        raise SystemExit(f"No catalog at {path}. Run catalog.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_page(pageid: int) -> dict:
    return api_get(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvslots": "main",
            "pageids": str(pageid),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill data/raw with wiki JSON from the catalog")
    parser.add_argument("--limit", type=int, default=None, help="Download at most N new pages")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    parser.add_argument("--force", action="store_true", help="Re-download pages that already exist")
    args = parser.parse_args()

    setup_log()
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog()
    downloaded = 0
    skipped = 0
    failed = 0

    for entry in catalog:
        pageid = entry["pageid"]
        title = entry["title"]
        out = raw_dir / f"{pageid}.json"
        if out.exists() and not args.force:
            skipped += 1
            continue
        if args.limit is not None and downloaded >= args.limit:
            break
        try:
            data = fetch_page(pageid)
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            downloaded += 1
            logging.info("saved %s (%s)", pageid, title)
        except SystemExit as exc:
            logging.error("stop: %s", exc)
            raise
        except Exception as exc:
            failed += 1
            logging.error("fail %s (%s): %s", pageid, title, exc)
        polite_sleep(args.delay)

    print(f"Downloaded {downloaded}, skipped {skipped}, failed {failed}")
    print(f"Raw files: {raw_dir}")
    print(f"Log: {LOG}")


if __name__ == "__main__":
    main()
