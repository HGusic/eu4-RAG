"""Shared MediaWiki API helper for EU4 wiki ingest."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://eu4.paradoxwikis.com/api.php"
USER_AGENT = "eu4-RAG/0.1 (local personal project; MediaWiki API ingest)"
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def api_get(params: dict, timeout: int = 60) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    url = f"{API_URL}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Wiki HTTP {exc.code} for {url}\n"
            "Cloudflare may be blocking scripts. Try again later or from a browser."
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach wiki API: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:300].replace("\n", " ")
        raise SystemExit(
            "Wiki did not return JSON (often a Cloudflare challenge).\n"
            f"Preview: {preview}"
        ) from exc
    return data


def polite_sleep(seconds: float) -> None:
    time.sleep(seconds)
