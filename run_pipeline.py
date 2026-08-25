"""Run PIPELINE.md steps 1–6 with no page limits (full wiki catalog + fetch).

Skips pip install, retrieve smoke test, Ollama, and the web UI.
Fetch skips files that already exist. Re-run safely if it stops.

Usage (repo root):
    python run_pipeline.py
    python run_pipeline.py --limit 50
    python run_pipeline.py --from fetch
    python run_pipeline.py --from extract
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# name, script relative to ROOT, cwd relative to ROOT, extra argv
STEPS: list[tuple[str, str, str, list[str]]] = [
    ("catalog", "src/ingest/catalog.py", "src/ingest", []),
    ("fetch", "src/ingest/fetch.py", "src/ingest", []),
    ("extract", "src/process/extract.py", "src/process", []),
    ("clean", "src/process/clean.py", "src/process", []),
    ("chunk", "src/process/chunk.py", "src/process", []),
    ("index", "src/index/build.py", "src/index", []),
]


def run_step(name: str, script: str, cwd: str, extra: list[str]) -> None:
    path = ROOT / script
    if not path.exists():
        raise SystemExit(
            f"Missing {path}. Check out feature/1-initial (main has no src/)."
        )
    print(f"\n=== {name}: {script} ===\n", flush=True)
    result = subprocess.run(
        [sys.executable, str(path), *extra],
        cwd=str(ROOT / cwd),
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Step '{name}' failed with exit code {result.returncode}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full-wiki ingest: catalog → fetch → extract → clean → chunk → index"
    )
    parser.add_argument(
        "--from",
        dest="start",
        choices=[s[0] for s in STEPS],
        default="catalog",
        help="Resume from this step (default: catalog)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Demo cap: pass --limit N to catalog and fetch (omit for the full wiki)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Override fetch delay in seconds (passed to fetch.py only)",
    )
    args = parser.parse_args()

    start_i = next(i for i, s in enumerate(STEPS) if s[0] == args.start)
    if args.limit is None:
        print(
            "Full wiki: no --limit on catalog or fetch.\n"
            "This can take many hours. Cloudflare may interrupt fetch; re-run with --from fetch.\n"
            "Does not start Ollama or the web UI.",
            flush=True,
        )
    else:
        print(
            f"Demo mode: catalog and fetch --limit {args.limit}.\n"
            "Does not start Ollama or the web UI.",
            flush=True,
        )
    for name, script, cwd, extra in STEPS[start_i:]:
        extra = list(extra)
        if name in ("catalog", "fetch") and args.limit is not None:
            extra.extend(["--limit", str(args.limit)])
        if name == "fetch" and args.delay is not None:
            extra.extend(["--delay", str(args.delay)])
        run_step(name, script, cwd, extra)
    print("\nPipeline finished. Start Ollama, then from src/:")
    print("  python -m uvicorn api:app --reload --port 8000 --app-dir .")


if __name__ == "__main__":
    main()
