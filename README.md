# Docling Finance Parser POC

A minimal proof of concept for replacing Google Document AI with [Docling](https://github.com/docling-project/docling) (open-source, local, no API key) in the bank statement parsing step of [personal_finance_tracker](https://github.com/mohitagr18/personal_finance_tracker).

This repo tests only the parsing layer: PDF in, transaction table out. It intentionally leaves out the Streamlit UI, categorizer agent, and analysis team so the Docling swap can be validated on its own before it gets ported back into the main app.

## Why this exists

`personal_finance_tracker` calls Google Document AI to extract transaction tables from bank statement PDFs. Document AI works well but costs money past a small free tier and needs a GCP project, billing, and a configured processor. Docling is MIT-licensed, runs fully locally, and needs no account or API key. This repo checks whether it holds up well enough on real statements before swapping it into the main app.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
```

If you're on a headless Linux container (Codespaces, Docker, CI), also install the system graphics library Docling's OCR dependencies need:

```
sudo apt-get update && sudo apt-get install -y libgl1 libglib2.0-0
```

## Try it

No real bank statement in hand? Generate a synthetic one:

```
uv run python make_sample_statement.py
```

Then parse it:

```
uv run python main.py sample_data/sample_statement.pdf
```

This prints every table Docling detected, the likely transaction rows, and writes them to `sample_data/sample_statement.csv`.

To test against a real statement, point `main.py` at any PDF:

```
uv run python main.py /path/to/your_statement.pdf
```

## How parsing works

See `docs/pipeline.md` for a diagram of the full flow. In short:

1. Docling converts the PDF and detects every table on the page.
2. Column names get deduplicated, since multi-line headers otherwise produce blank or repeated labels.
3. The table with the most rows is treated as the likely transaction ledger.
4. Rows without a dollar-amount cell get dropped, which filters out section labels and leftover header fragments.
5. An independent check counts `MM/DD` date markers in the PDF's raw text layer, bypassing Docling's table model entirely, and compares that count to the number of extracted rows. A mismatch prints a warning.

## Known limitations

Tested against a real Citi credit card statement (`MA_Test_bank_statement.pdf`), the pipeline correctly extracted 13 of 14 transactions. One row was dropped entirely and one row's description was corrupted, both because Docling's table-structure model merged a two-line column header with the ledger and the surrounding fee and interest sections into a single detected table. This is a table-structure misread on a dense, multi-section page, not a text-extraction failure. The row-count warning described above exists specifically to catch this class of silent error. Treat this parser's output as a first pass worth spot-checking, not a guaranteed-correct source of truth. See `docs/pipeline.md` for the full breakdown.

## CI

`.github/workflows/test.yml` runs the pipeline against the synthetic sample statement on every push, as a regression smoke test. It doesn't replace testing against real statement formats, which stays a manual step since no real statements are checked into this repo.

## Next step

If table extraction quality holds up across a few more real statement formats, port `parser.py`'s logic into `personal_finance_tracker/services/parser.py`, replacing the Document AI client call and removing the GCP dependency from that project's requirements.
