# eu4-RAG

Ask questions about Europa Universalis 4 using the wiki — type a question in your browser instead of searching pages yourself.

---

## What you need first

Install these once on your computer (Linux):

- **Git** — to download the project
- **Python 3** — to prepare the wiki data (one-time)
- **Docker** — to run the app

On Debian/Ubuntu, as admin:

```bash
apt update
apt install -y git python3-venv python3-full docker.io docker-compose-plugin
systemctl enable --now docker
```

---

## First time setup (do this once)

Open a terminal. Copy and paste each block, press Enter, and wait for it to finish before the next one.

### Step 1 — Download the project

```bash
git clone https://github.com/HGusic/eu4-RAG.git
cd eu4-RAG
```

**What this does:** Copies the project onto your computer.

---

### Step 2 — Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**What this does:** Creates a private Python folder so the project can install its tools without touching your system.

You should see `(.venv)` at the start of your terminal line after `source .venv/bin/activate`.

---

### Step 3 — Download and prepare wiki pages

```bash
python run_pipeline.py --limit 10
```

**What this does:** Grabs 10 wiki pages, cleans them up, and builds a search index the app can use. Takes a few minutes.

For the full wiki (much longer):

```bash
python run_pipeline.py
```

When it finishes, turn off the Python folder:

```bash
deactivate
```

---

### Step 4 — Start the app

```bash
docker compose up --build
```

**What this does:** Starts the website and the AI brain. The first run takes a while (downloads large files). Leave this terminal open.

When you see logs scrolling and no errors, open a **second terminal** and go to the project folder:

```bash
cd eu4-RAG
```

---

### Step 5 — Download the AI model (once)

```bash
docker compose exec ollama ollama pull llama3.1
```

**What this does:** Downloads the language model (~5 GB). Only needed once per computer. Wait until it says success.

---

### Step 6 — Open the app

In your web browser, go to:

**http://localhost:8000**

Type a question and press Ask.

---

## Every time after that

You only need two commands:

```bash
cd eu4-RAG
docker compose up -d
```

**What this does:** Starts the app in the background.

Open **http://localhost:8000** in your browser.

When you're done:

```bash
docker compose down
```

**What this does:** Stops the app.

You do **not** need to run the Python steps or download the model again.

---

## Quick reference

| When | What to run |
|---|---|
| First time ever | Steps 1–6 above |
| Every normal use | `docker compose up -d` → open http://localhost:8000 |
| Stop the app | `docker compose down` |
| Refresh wiki data | `source .venv/bin/activate` → `python run_pipeline.py --limit 10` → `deactivate` |

---

## Something went wrong?

| Problem | What to try |
|---|---|
| `externally-managed-environment` | Use Step 2 (the venv). Don't run `pip install` without activating `.venv` first. |
| `model 'llama3.1' not found` | Run Step 5 again in a second terminal while Docker is running. |
| Page says no index / 503 error | Run Step 3 again — the wiki index is missing. |
| Website won't load | Make sure `docker compose up` is still running, or run `docker compose up -d` and wait a minute. |
| Port already in use | Something else is using port 8000. Stop that program or restart your computer. |

---

## For developers

Technical details about each file and pipeline stage: [PIPELINE.md](PIPELINE.md)
