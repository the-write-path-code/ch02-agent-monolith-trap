# Docling Finance Parser POC

A minimal proof of concept for replacing Google Document AI with [Docling](https://github.com/docling-project/docling) (open-source, local, no API key) in the bank statement parsing step of [personal_finance_tracker](https://github.com/mohitagr18/personal_finance_tracker). It also includes a companion experiment showing why single-model designs get brittle as input complexity increases, the "before" case for the same chapter.

## Part 1: Docling parsing POC

This tests only the parsing layer: PDF in, transaction table out. It intentionally leaves out the Streamlit UI, categorizer agent, and analysis team so the Docling swap can be validated on its own before it gets ported back into the main app.

### Why this exists

`personal_finance_tracker` calls Google Document AI to extract transaction tables from bank statement PDFs. Document AI works well but costs money past a small free tier and needs a GCP project, billing, and a configured processor. Docling is MIT-licensed, runs fully locally, and needs no account or API key. This repo checks whether it holds up well enough on real statements before swapping it into the main app.

### Setup

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
```

If you're on a headless Linux container (Codespaces, Docker, CI), also install the system graphics library Docling's OCR dependencies need:

```
sudo apt-get update && sudo apt-get install -y libgl1 libglib2.0-0
```

### Try it

```
uv run python make_sample_statement.py
uv run python main.py sample_data/sample_statement.pdf
```

Or point `main.py` at a real statement PDF.

### How parsing works

See `docs/pipeline.md` for a diagram of the full flow. In short: Docling detects tables, column names get deduplicated, the largest table is treated as the likely ledger, rows without both a date-shaped and dollar-shaped cell get dropped, and an independent `pypdf`-based date-marker count cross-checks the row count and warns on a mismatch.

### Known limitations

Tested against a real Citi credit card statement, the pipeline correctly extracted 13 of 14 transactions. One row was dropped entirely and one row's description was corrupted, both from Docling's table-structure model merging a two-line column header with the ledger and the surrounding fee/interest section into one detected table. See `docs/pipeline.md` for the full breakdown.

### CI

`.github/workflows/test.yml` runs the pipeline against the synthetic sample statement on every push, as a regression smoke test.

## Part 2: monolith complexity experiment

This is the "before" case: a single model, no agent framework, asked to write Python code that parses a statement, run that code, and fix its own code on failure, tested against four synthetic statements of increasing layout complexity while holding the same 10 transactions constant. This mirrors the actual mechanism that broke in the original hackathon project (a Data Analyzer agent writing parsing code, a Code Executor running it), not a simpler direct-extraction task, which an earlier version of this experiment tested and found too easy to show any brittleness at all. See `docs/monolith_experiment.md` for that finding and the full design.

### Setup

```
cp .env.example .env
# add your GOOGLE_API_KEY, optionally adjust MODEL_NAME and MAX_CODEGEN_ATTEMPTS
```

### Run it

```
uv run python run_complexity_experiment.py
```

This makes up to 15 API calls per level (5 runs x up to 3 attempts each) and writes `results/complexity_results.csv` (raw per-run data) and `results/complexity_results.md` (the summary table). Generated code runs in a subprocess with a timeout, not a hardened sandbox, fine for synthetic statements you generated yourself, not for untrusted input.

## Next step

If table extraction quality holds up across a few more real statement formats, port `parser.py`'s logic into `personal_finance_tracker/services/parser.py`, replacing the Document AI client call and removing the GCP dependency from that project's requirements. The monolith experiment's results feed directly into the chapter's 2.1-2.2 material; 2.3 reuses the Docling pipeline above as the "decompose, then match each node to the right tool" evidence.
