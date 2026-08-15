# Docling Finance Parser POC

A minimal proof of concept for replacing Google Document AI with [Docling](https://github.com/docling-project/docling) (open-source, local, no API key) in the bank statement parsing step of [personal_finance_tracker](https://github.com/mohitagr18/personal_finance_tracker). It also includes a companion experiment showing why single-model designs get brittle as input complexity increases, and an ADK rebuild of the full pipeline, the "before," "after," and "properly orchestrated" cases for the same chapter.

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

Or point `main.py` at a real statement PDF, or the sanitized replica from `make_citi_replica.py` (see Part 3).

### How parsing works

See `docs/pipeline.md` for a diagram of the full flow. In short: Docling detects tables, column names get deduplicated, the largest table is treated as the likely ledger, rows without both a date-shaped and dollar-shaped cell get dropped, and an independent `pypdf`-based date-marker count cross-checks the row count and warns on a mismatch.

### Known limitations

Tested against a real Citi credit card statement, the pipeline correctly extracted 13 of 14 transactions. One row was dropped entirely and one row's description was corrupted, both from Docling's table-structure model merging a two-line column header with the ledger and the surrounding fee/interest section into one detected table. See `docs/pipeline.md` for the full breakdown, and `make_citi_replica.py` (Part 3) for a sanitized, shareable version of the statement that reproduces this same failure.

### CI

`.github/workflows/test.yml` runs the pipeline against the synthetic sample statement on every push, as a regression smoke test.

## Part 2: monolith complexity experiment

This is the "before" case: a single model, no agent framework, asked to write Python code that parses a statement, run that code, and fix its own code on failure, tested against four synthetic statements of increasing layout complexity while holding the same 10 transactions constant. See `docs/monolith_experiment.md` for the full design and the 15-run results table.

### Setup

```
cp .env.example .env
# add your GOOGLE_API_KEY, optionally adjust MODEL_NAME and MAX_CODEGEN_ATTEMPTS
```

### Run it

```
uv run python run_complexity_experiment.py
```

## Part 3: ADK pipeline (2.4)

The same mixed architecture as Part 1, a deterministic parse step feeding categorizer and reporter agents, rebuilt in Google's Agent Development Kit instead of hand-wired Python function calls. See `docs/adk_pipeline.md` for the design, why parsing still isn't an agent even here, and a note on ADK's API volatility.

### Run it

```
uv run python make_citi_replica.py
uv run python -m adk_pipeline.pipeline sample_data/citi_replica_statement.pdf
```

`make_citi_replica.py` generates a sanitized replica of the real dense statement layout that exposed Docling's table-structure bug, fictional name, address, and account numbers, real merchants/dates/amounts preserved, so the same known failure can be reproduced and shared safely.

## Next step

If table extraction quality holds up across a few more real statement formats, port `parser.py`'s logic into `personal_finance_tracker/services/parser.py`, replacing the Document AI client call and removing the GCP dependency from that project's requirements. The monolith experiment's results feed directly into the chapter's 2.1-2.2 material; Part 1 (Docling) covers 2.3; Part 3 (ADK) covers 2.4.
