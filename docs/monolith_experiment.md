# Monolith Complexity Experiment (Section 2.1-2.2)

This documents the demo behind chapter section 2.1-2.2 ("The failure of the single-prompt agent" / "Why overconfident orchestration collapses in production"). It uses no agent framework at all, no AutoGen, no ADK, just plain Python control flow and a direct Gemini API call, because the claim being tested ("a single-model design becomes brittle at scale") doesn't depend on any orchestration framework. The framework comparison is reserved for section 2.4.

## Why this isn't a direct-extraction test

The first version of this experiment asked the model to read already-extracted statement text and return structured JSON directly, no code generation involved. That version scored 100% across all four complexity levels, every run, with identical output every time. That's a legitimate result, but it tested the wrong task: reading clean text and reformatting it as JSON is not what actually broke in the original monolithic design. The original failure was in a Data Analyzer agent *writing Python code* to parse raw statement text, and a Code Executor *running* that code, a mechanically fragile loop where the model has to get column assumptions, string matching, and control flow exactly right, or the code throws an exception. This version reproduces that mechanism instead.

## The design being tested

A single model writes a Python function that parses the statement text into transactions. That code gets executed in a subprocess. If it fails, either it throws an exception, times out, returns something that isn't valid JSON, or returns an empty list (an empty result counts as a failure here, since every test statement genuinely contains 10 transactions), the same model gets the error message and its own previous code, and tries again, up to a configurable number of attempts (`MAX_CODEGEN_ATTEMPTS` in `.env`, default 3). This is still a single, undifferentiated model doing everything, writing and implicitly debugging, with no separate specialized agents and no orchestration framework, which is what makes it "monolithic" in the chapter's sense.

```mermaid
flowchart TD
    A[Bank statement PDF] --> B[Extract raw text with pypdf]
    B --> C[Model writes a Python
parsing function]
    C --> D[Run the function in a subprocess]
    D --> E{Ran successfully,
valid JSON,
non-empty result?}
    E -- No, attempts remain --> F[Feed the error and
previous code back to the model]
    F --> C
    E -- No, out of attempts --> G[Run counts as a failure]
    E -- Yes --> H[Score against known ground truth]
    H --> I[Compare across 15 runs
and across 4 complexity levels]
```

## The four complexity levels

All four levels hold the exact same 10 transactions constant, only the page layout changes.

| Level | Name | What changes |
|---|---|---|
| 1 | Clean | One table, one header row, nothing else on the page |
| 2 | Sectioned | Adds an account summary block and section labels interleaved between rows |
| 3 | Dual dates + split header | Column header splits across two lines, some rows show two stacked dates |
| 4 | Dense / multi-section | Combines levels 2 and 3, plus a trailing fees/interest/APR block after the ledger |

## Scoring

Each run is scored against the fixed 10-transaction ground truth by matching on `(date, amount)` pairs, plus two metrics specific to the code-gen loop:

- **attempts**: how many write-execute-fix cycles it took to get working code (or the max if it never succeeded)
- **code_hash**: a fingerprint of the generated code, used to check whether independent runs on identical input converge on the same implementation or produce genuinely different code each time

## Results

Run against `gemini-3.1-flash-lite`, temperature 0.7, 15 runs per level, max 3 attempts per run. This supersedes an earlier 5-run pass that showed the same directional pattern with wider, less trustworthy confidence intervals.

| Level | Description | Success rate | Avg attempts used | Avg matched / 10 | Avg hallucinated | Distinct code versions |
|---|---|---|---|---|---|---|
| 1 | Clean | 100% | 1.0 | 10.0 | 0.0 | 10 of 15 |
| 2 | Sectioned | 100% | 1.0 | 10.0 | 0.0 | 12 of 15 |
| 3 | Dual dates + split header | 87% | 1.6 | 8.3 | 0.0 | 15 of 15 |
| 4 | Dense / multi-section | 47% | 2.6 | 2.7 | 0.3 | 15 of 15 |

Success rate, attempts required, and matched-transaction count all degrade as layout complexity increases, on identical underlying data. Only the page layout changed between levels.

Level 4 is the clearest evidence for the chapter's claim. Success dropped to under half (47%), average attempts climbed to 2.6 out of a maximum of 3, average matched transactions fell to 2.7 out of 10, and hallucinated rows appeared for the first time (0.3 average), meaning the model started inventing transactions that don't exist in the source document, not just missing real ones. A parser that runs without crashing and returns non-empty JSON is not the same thing as a parser that's correct; "success" by the crash/valid-JSON bar and "success" by the matched-transaction bar diverge sharply at this complexity level.

Code-hash diversity climbs alongside the failure rate: level 1 saw 10 distinct implementations across 15 runs, level 4 saw 15 distinct implementations across 15 runs, meaning no two runs converged on the same code at all at the highest complexity level. That's the concrete form of "identical input, different output": not just different wording, but a different program written each time, with correctness becoming a coin flip rather than a guarantee.

Raw per-run data is available by rerunning the experiment; this repo doesn't commit the raw CSV by default since it regenerates on each run.

## Running it yourself

```
cp .env.example .env
# edit .env: add GOOGLE_API_KEY, optionally adjust MODEL_NAME and MAX_CODEGEN_ATTEMPTS
uv sync
uv run python run_complexity_experiment.py
```

Generated code executes in a subprocess with a timeout, not in a hardened sandbox. This is fine for a local demo against synthetic statements you generated yourself; don't run it against untrusted PDFs or on a machine you don't control.

Results land in `results/complexity_results.csv` (raw per-run) and `results/complexity_results.md` (the summary table). Neither is committed to this repo by default; the numbers above are the specific run referenced in the chapter, preserved directly in this file.
