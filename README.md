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

## Try it

No real bank statement in hand? Generate a synthetic one:

```
uv run python make_sample_statement.py
```

Then parse it:

```
uv run python main.py sample_data/sample_statement.pdf
```

This prints the extracted transactions and writes them to `sample_data/sample_statement.csv`.

To test against a real statement, point `main.py` at any PDF:

```
uv run python main.py /path/to/your_statement.pdf
```

## Note on sample data

No real bank statements are included in this repo. `make_sample_statement.py` generates a synthetic statement with fabricated transactions purely for testing the parsing pipeline. Real statements should never be committed to version control.

## Next step

If table extraction quality holds up across a few real statement formats, port `parser.py`'s logic into `personal_finance_tracker/services/parser.py`, replacing the Document AI client call and removing the GCP dependency from that project's requirements.
