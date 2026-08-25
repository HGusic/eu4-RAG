# EU4 RAG — files and run order

Use this tomorrow. All commands assume Git Bash. Paths are relative to the repo root unless noted.

Repo: `C:\Users\Haris\Documents\DEV\eu4-RAG`

---

## Run order (pipeline)

Do these in order. You can skip a step if its output already exists and the input has not changed.

| Step | Command | Writes |
|---|---|---|
| 0 | `pip install -r requirements.txt` (once per machine/venv) | packages in the environment |
| 1 | `cd src/ingest` then `python catalog.py --limit 50` | `data/catalog.json` |
| 2 | `python fetch.py --limit 5` (or no `--limit` for everything in the catalog) | `data/raw/{pageid}.json` |
| 3 | `cd ../process` then `python extract.py` | `data/extracted/{pageid}.json` |
| 4 | `python clean.py` | `data/cleaned/{pageid}.json` |
| 5 | `python chunk.py` | `data/chunks/{pageid}.json` |
| 6 | `cd ../index` then `python build.py` | `data/chroma/` |
| 7 | `cd ..` then `python retrieve.py "your question"` | nothing (prints hits) |
| 8 | Ollama running (`ollama pull llama3.1`) | model on disk (Ollama, not this repo) |
| 9 | From `src/`: `python -m uvicorn api:app --reload --port 8000` then open http://127.0.0.1:8000 | HTML UI (Streamlit `app.py` still exists) |

**Full wiki in one go (no `--limit`):** from the repo root, on the branch that has `src/`:

```bash
python run_pipeline.py
python run_pipeline.py --limit 50
```

Resume after a failed crawl: `python run_pipeline.py --from fetch` (skips pages already in `data/raw`). Later stages: `--from extract` / `clean` / `chunk` / `index`. Does not install pip packages or start the UI.

**If you only change cleaning/chunking:** start at step 4 or 5, then rebuild the index (step 6). You do not recrawl.

**If retrieve looks wrong:** do not add pages. Fix chunk/clean, rebuild, test retrieve again.

---

## Directories

| Path | Role |
|---|---|
| `src/ingest/` | Talk to the live wiki |
| `src/process/` | Turn wiki JSON into RAG text |
| `src/index/` | Embed chunks into Chroma |
| `src/` (root of src) | Ask path: retrieve, generate, Streamlit |
| `tests/` | Checks that do not need the wiki |
| `eval/` | Empty for now; gold questions later |
| `data/` | **Gitignored runtime data.** Regenerable. Do not commit. |
| `data/raw/` | Downloaded MediaWiki JSON (source of truth) |
| `data/extracted/` | Title + raw wikitext (numbers and `<math>` unchanged) |
| `data/cleaned/` | Readable text, markup stripped, numbers/formulas kept |
| `data/chunks/` | Section-sized pieces that get embedded |
| `data/chroma/` | Vector index used at ask time |
| `data/logs/` | Crawl log from fetch |

---

## Files

### Root

**`README.md`**  
Short project blurb. Not the runbook.

**`requirements.txt`**  
Python deps: mwparserfromhell, chromadb, sentence-transformers, streamlit, ollama.

**`PIPELINE.md`**  
This file.

### Ingest (`src/ingest/`)

**`wiki.py`**  
Shared HTTP helper: EU4 wiki `api.php`, User-Agent, JSON parse, Cloudflare error message, sleep helper. Not run by itself.

**`catalog.py`**  
Downloads the **list** of main-namespace articles (title + pageid). No article body.  
`python catalog.py --limit 50`

**`fetch.py`**  
Reads `data/catalog.json`, downloads each article into `data/raw/`. Skips files that already exist unless `--force`.  
`python fetch.py --limit 5`

### Process (`src/process/`)

**`extract.py`**  
Reads `data/raw/*.json`, pulls title, pageid, revid, **full wikitext** (no stripping).  
`python extract.py`

**`clean.py`**  
Reads extracted JSON, strips File/refs/navboxes, keeps `{{green|…}}` values and `<math>` formulas, markdown headings.  
`python clean.py`  
After a run it reports leftover `[[wikilinks]]`.

**`chunk.py`**  
Reads cleaned JSON, splits on `##` / `###` / `####`, merges tiny child sections, splits long ones (~3000 chars), skips References/portraits/gallery. Writes lists of chunks per page.  
`python chunk.py`

### Index

**`src/index/build.py`**  
Embeds all chunks with `BAAI/bge-small-en-v1.5`, stores collection `eu4_wiki` in `data/chroma`. Rebuilds the collection each run. Batches of 256.  
`python build.py`

### Ask path (`src/`)

**`retrieve.py`**  
Embeds the question with the **same** model, prints top-k chunks. Used by the UI. Does not call Ollama.  
`python retrieve.py "How is advisor hiring cost calculated?"`

**`generate.py`**  
Builds the “answer only from excerpts” prompt and streams Ollama (`llama3.1` unless `OLLAMA_MODEL` is set). Used by the UI. Not usually run alone.

**`app.py`**  
Streamlit: search → stream answer → source expanders.  
Must be started **from the `src` folder**:

```bash
cd ~/Documents/DEV/eu4-RAG/src
python -m streamlit run app.py
```

### Tests

**`tests/test_clean.py`**  
Nested File-caption leftover and broken `[[` links. Run:

```bash
cd ~/Documents/DEV/eu4-RAG
python -c "import tests.test_clean as t; t.test_nested_file_caption_is_removed(); t.test_broken_wikilink_brackets_are_stripped(); print('ok')"
```

---

## Tomorrow checklist

1. Confirm Ollama is installed and `ollama run llama3.1 "hi"` works.  
2. From `src`: `python -m streamlit run app.py` and ask the advisor hiring-cost question.  
3. If the UI is fine, optional: catalog/fetch **without** `--limit` overnight, then extract → clean → chunk → build → retrieve smoke test.  
4. Do not put `data/` on git.

## Smoke test that already passed

```text
python retrieve.py "How is advisor hiring cost calculated"
→ [1] Advisor — Cost / Hiring cost (distance ~0.156)
```

That means search is good. Remaining work for a usable app is Ollama + Streamlit (steps 8–9), then a larger crawl when you want more than ~50 pages.
