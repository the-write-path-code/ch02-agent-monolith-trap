# ch2-agent-monolith-trap

Companion repo for Chapter 2 of *The Write Path*, "Why your agent keeps breaking: the monolith trap and the path out." It walks through three implementations of the same bank-statement-parsing task, moving from a fragile monolithic design to a deterministic hand-wired pipeline to the same pipeline properly orchestrated in an agent framework, to make the chapter's argument concrete rather than theoretical.

## What's here

- **Section 2.1-2.2**: a single model writes and debugs its own Python parsing code in a loop, tested against four synthetic statements of increasing layout complexity. This is the monolith the chapter title refers to.
- **Section 2.3**: the same parsing task rebuilt as a deterministic pipeline using Docling for table extraction, with an independent cross-check against the raw text to catch silent extraction failures.
- **Section 2.4**: the same architecture from 2.3, rebuilt inside Google's Agent Development Kit (ADK), to show that better orchestration, not more parsing cleverness, is the actual fix.

## Section 2.1-2.2: monolith complexity experiment

The "before" case: no agent framework, no orchestration, just a single model asked to write Python code that parses a statement, run that code, and fix its own code on failure. Tested against four synthetic statements of increasing layout complexity while holding the same 10 transactions constant. See `docs/monolith_experiment.md` for the full design and the 15-run results table.

### Setup

```
cp .env.example .env
# add your GOOGLE_API_KEY, optionally adjust MODEL_NAME and MAX_CODEGEN_ATTEMPTS
```

### Run it

```
uv run python run_complexity_experiment.py
```

## Section 2.3: Docling parsing pipeline

This tests the parsing layer in isolation: PDF in, transaction table out, as a plain deterministic Python pipeline with no agent involved at all.

### Why Docling

Google Document AI extracts transaction tables from bank statement PDFs well, but it costs money past a small free tier and needs a GCP project, billing, and a configured processor. Docling is MIT-licensed, runs fully locally, and needs no account or API key. This section tests whether it holds up well enough on real statements to be a credible deterministic alternative.

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

Or point `main.py` at a real statement PDF, or the sanitized replica from `make_citi_replica.py` (see below).

### How parsing works

See `docs/pipeline.md` for a diagram of the full flow. In short: Docling detects tables, column names get deduplicated, the largest table is treated as the likely ledger, rows without both a date-shaped and dollar-shaped cell get dropped, and an independent `pypdf`-based date-marker count cross-checks the row count and warns on a mismatch.

### Known limitations

Tested against a real Citi credit card statement, the pipeline correctly extracted 13 of 14 transactions. One row was dropped entirely and one row's description was corrupted, both from Docling's table-structure model merging a two-line column header with the ledger and the surrounding fee/interest section into one detected table. See `docs/pipeline.md` for the full breakdown, and `make_citi_replica.py` for a sanitized, shareable version of the statement built to explore this failure.

### CI

`.github/workflows/test.yml` runs the pipeline against the synthetic sample statement on every push, as a regression smoke test.

## Section 2.4: ADK pipeline

The same mixed architecture as Section 2.3, a deterministic parse step feeding categorizer and reporter agents, rebuilt in Google's Agent Development Kit instead of hand-wired Python function calls. See `docs/adk_pipeline.md` for the design, why parsing still isn't an agent even here, and a note on ADK's API volatility.

### Run it

```
uv run python make_citi_replica.py
uv run python -m adk_pipeline.pipeline sample_data/citi_replica_statement.pdf
```

`make_citi_replica.py` generates a sanitized replica of the dense statement layout that originally exposed Docling's table-structure bug: fictional name, address, and account numbers, real merchants/dates/amounts preserved. It illustrates the structural pattern involved, a variable-height date column, but does not reliably reproduce the exact same misparse on every run; see `docs/adk_pipeline.md` for why.

## Next step

The Section 2.1-2.2 results are the concrete evidence behind the chapter's claim that monolithic, single-model designs get brittle as input complexity increases. Section 2.3 shows a deterministic alternative built without any agent framework. Section 2.4 shows the same architecture under proper orchestration. Together they trace the chapter's full progression from "why agents break" to "the path out."
