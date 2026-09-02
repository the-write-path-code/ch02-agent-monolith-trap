# Chapter 2: Why Your Agent Keeps Breaking

Companion code for *Building Safe Agentic AI for Enterprise Systems* by Mohit Aggarwal.

This repository compares three approaches to bank-statement processing. It starts with a single-model loop that writes, runs, and repairs its own parser. It then moves document ingestion into a deterministic Docling pipeline and uses Google Agent Development Kit (ADK) only after parsing has produced structured transaction records.

The chapter's argument is architectural. A model should not be responsible for document interpretation, code generation, code recovery, correctness assessment, and downstream reporting in one context window. Each responsibility needs a boundary that can be inspected and tested independently.

## What You Will Run

| Chapter sections | Implementation | What it demonstrates |
| --- | --- | --- |
| 2.1 and 2.2 | Monolith complexity experiment | One model writes a parser, executes it in a subprocess, receives its own error, and tries to repair it. The benchmark holds ten transactions constant while statement layout complexity increases. |
| 2.3 | Deterministic Docling pipeline | Plain Python converts a statement, selects a likely ledger, filters rows, and compares extracted rows with an independent date-marker count. No agent decides which rows are transactions. |
| 2.4 | ADK workflow | The deterministic parser runs before the workflow. Two agents then categorize already-structured transactions and produce a report. |

## Production Warning

The monolith experiment executes model-generated Python in a subprocess with a timeout. That boundary is suitable only for the repository's synthetic statements and local demonstration environment. It is not a hardened sandbox. Do not run generated code against untrusted PDFs or on a machine you do not control.

The deterministic pipeline is safer because it does not ask a model to write or execute parsing code. It still has limits. The Chapter 2 case study documents a dense statement layout where Docling extracted 13 of 14 transactions, dropped one row, and corrupted another description. The independent row-count check reports a mismatch. It cannot restore the missing record.

## Prerequisites

- Git
- [uv](https://docs.astral.sh/uv/)
- Python 3.10 or later
- System graphics libraries for Docling when running on headless Linux, in a container, in Codespaces, or in CI
- A Gemini API key only for the monolith experiment and the ADK categorization-and-reporting workflow

The deterministic Docling pipeline in Section 2.3 uses local tooling and does not require a model key.

## Quick Start

### 1. Install uv

Install uv once if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and synchronize the repository

```bash
git clone https://github.com/the-write-path-code/ch02-agent-monolith-trap.git
cd ch02-agent-monolith-trap
uv sync
```

The repository includes `uv.lock`. Run `uv sync` after pulling changes so the local environment matches the committed dependency set.

### 3. Install headless Linux dependencies when needed

On macOS and most desktop Linux installations, skip this step unless Docling reports an OpenCV or graphics-library error. On Codespaces, Docker, CI, or a headless Linux host, run:

```bash
sudo apt-get update
sudo apt-get install -y libgl1 libglib2.0-0
```

## Configuration

The deterministic parsing path needs no environment variables.

The monolith experiment and ADK workflow call Gemini. Copy the template when you are ready to run either one:

```bash
cp .env.example .env
```

Set the values required by your checkout:

```dotenv
GOOGLE_API_KEY=your-api-key
MODEL_NAME=gemini-3.1-flash-lite
MAX_CODEGEN_ATTEMPTS=3
```

`MAX_CODEGEN_ATTEMPTS` defaults to three. The benchmark uses that cap so a failing model loop cannot retry indefinitely.

> **Tip**
>
> Use the deterministic parser before adding any API key. It establishes the document-ingestion boundary and gives you a known local path before you introduce model variability.

## Run the Chapter Demonstrations

### 1. Deterministic Parsing Pipeline, Section 2.3

Start with the deterministic path. It is the repository's default learning path and does not require a Gemini key.

Generate a synthetic statement:

```bash
uv run python make_sample_statement.py
```

Parse it:

```bash
uv run python main.py sample_data/sample_statement.pdf
```

The pipeline performs six fixed stages:

1. Docling detects tables in the PDF.
2. The largest detected table becomes the likely ledger.
3. Duplicate column names are made unique.
4. Rows are retained only when they contain date-shaped and dollar-amount values.
5. A separate `pypdf` pass counts date markers in the text layer.
6. The pipeline warns when the independent count and extracted-row count differ.

The row-count comparison is a warning signal, not a certificate of correctness. It can identify some silent failures, but it cannot restore a dropped row or repair a corrupted field.

### 2. Monolith Complexity Experiment, Sections 2.1 and 2.2

The monolith experiment requires a Gemini API key because the model writes the parsing function.

```bash
uv run python run_complexity_experiment.py
```

The experiment evaluates four layouts that contain the same ten synthetic transactions:

| Level | Layout change |
| --- | --- |
| 1 | One ledger with one header row |
| 2 | Account-summary material and section labels |
| 3 | Dual dates and a split header |
| 4 | The prior changes plus trailing fees, interest, and APR material |

Each trial records whether generated code completed and returned valid, nonempty JSON; the number of write-execute-repair attempts; the number of known `(date, amount)` transaction pairs matched; the number of rows absent from the reference set; and a hash of the generated parser.

### 3. ADK Post-Parse Workflow, Section 2.4

The ADK workflow begins only after deterministic parsing has returned structured transaction records. Parsing is not an agent tool.

Create the sanitized dense-layout replica:

```bash
uv run python make_citi_replica.py
```

Run the workflow:

```bash
uv run python -m adk_pipeline.pipeline sample_data/citi_replica_statement.pdf
```

The categorizer adds a category to each transaction without changing its source date, description, or amount. The reporter then produces a Markdown summary from those categorized records.

> **Architecture Note**
>
> ADK APIs change quickly, particularly around synchronous and asynchronous session patterns. If a session or runner method fails after a dependency upgrade, verify the installed ADK version against current documentation before changing the design. The parser should remain a direct deterministic function.

## Expected Results

### Deterministic pipeline

A synthetic sample statement should produce a transaction CSV and no row-count warning. This verifies a known input through the stated parsing stages. It does not show that the largest-table heuristic works for every statement layout.

### Monolith benchmark

The experiment writes one record per trial and a summary table. Results vary because the model generates code probabilistically. The Chapter 2 reference benchmark ran 15 trials per layout, using `gemini-3.1-flash-lite` at temperature 0.7 and a maximum of three attempts.

On the dense Level 4 layout, the loop reached its immediate success condition in 47 percent of runs, matched 2.7 of ten transactions on average, and produced 0.3 hallucinated rows per run. These figures describe the repository's controlled benchmark, model configuration, and layout conditions. They are not general accuracy claims about models or statement parsers.

Results are written under `results/`:

```text
results/complexity_results.csv
results/complexity_results.md
```

### ADK workflow

The workflow writes categorized data when the categorizer returns valid JSON and writes a Markdown report from the reporter's final response. A parser warning remains visible in the downstream report. Categorization and reporting do not repair data that parsing omitted or corrupted.

## Run the Tests

The GitHub Actions workflow generates a synthetic statement and runs the deterministic parser. Run the same smoke test locally:

```bash
uv run python deterministic_pipeline/make_sample_statement.py
uv run python deterministic_pipeline/main.py sample_data/sample_statement.pdf
```

The smoke test is deliberately narrow. It verifies that a known synthetic input still passes the deterministic path after a change.

Run the available unit and integration tests with:

```bash
uv run pytest
```

## Repository Layout

```text
.
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── run_complexity_experiment.py       # Sections 2.1 and 2.2
├── make_sample_statement.py           # Synthetic statement generator
├── make_citi_replica.py               # Sanitized dense-layout replica
├── main.py                            # Deterministic parser entry point
├── deterministic_pipeline/            # Section 2.3 implementation
├── adk_pipeline/                      # Section 2.4 workflow
├── docs/
│   ├── monolith_experiment.md         # Benchmark design and recorded results
│   ├── pipeline.md                    # Deterministic parsing flow and limits
│   └── adk_pipeline.md                # ADK architecture and API notes
├── sample_data/                       # Synthetic and sanitized statement inputs
├── results/                           # Generated benchmark output; not committed by default
├── tests/
└── .github/workflows/
    └── test.yml                       # Deterministic parser smoke test
```

## Architecture Diagrams and Supporting Documents

Read these documents alongside Chapter 2:

- `docs/monolith_experiment.md` explains the controlled benchmark, scoring criteria, and recorded 15-run results.
- `docs/pipeline.md` shows the deterministic parsing stages and documents the dense-statement failure.
- `docs/adk_pipeline.md` explains why parsing remains outside the agent workflow and how structured records move into categorization and reporting.

## Safety and Operational Limits

- The subprocess used in the monolith benchmark isolates the parent process from parser crashes and applies a timeout. It is not a secure execution sandbox.
- Use only the supplied synthetic statements or sanitized replica with the monolith experiment. Do not run generated parser code against untrusted documents.
- The deterministic parser uses heuristic table selection, row filtering, and date-marker counting. A warning indicates a possible mismatch; it does not establish complete or correct extraction.
- The sanitized replica demonstrates the layout pattern associated with the real statement failure. It does not reliably reproduce the exact Docling misparse on every run.
- The ADK workflow sequences model-driven categorization and reporting. It does not validate the full transaction schema or certify the correctness of the parser output.

## Troubleshooting

### `uv sync` fails during installation

Confirm that uv is current and that a compatible Python interpreter is available:

```bash
uv --version
uv python list
```

### Docling or OpenCV reports a missing shared library

Install the headless Linux dependencies:

```bash
sudo apt-get update
sudo apt-get install -y libgl1 libglib2.0-0
```

### The monolith experiment cannot call Gemini

Confirm that `.env` exists and that `GOOGLE_API_KEY` is set. The deterministic parser does not need this key.

### The parser warns that extracted rows do not match date markers

Treat the result as a potential extraction failure. Review the generated CSV against the source statement. Do not suppress the warning or ask a downstream agent to infer the missing transaction.

### The ADK workflow fails after a dependency update

Check the installed ADK version:

```bash
uv run python -c "import google.adk; print(google.adk.__version__)"
```

Compare the installed API with the current ADK documentation. Keep the architecture intact: deterministic parsing first, model-driven categorization and reporting second.

## Related Chapters

- Chapter 1 establishes why production systems need deterministic boundaries around irreversible decisions.
- Chapters 3 through 5 strengthen the retrieval and grounding layers that support later reasoning.
- Chapter 10 explains why process-local state fails after deployment to stateless cloud workers.
- Chapter 15 turns the controlled evaluation approach into merge gates and regression checks.

## License and Errata

See `LICENSE` for licensing terms. Report documentation or code issues through this repository's GitHub issue tracker.
