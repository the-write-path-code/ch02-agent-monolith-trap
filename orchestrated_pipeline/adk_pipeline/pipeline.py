"""Wires the deterministic Docling parse step and the two ADK agents
into one pipeline.

Run from the repo root:
    uv run python -m orchestrated_pipeline.adk_pipeline.pipeline <path_to_statement.pdf>

Writes two output files next to the input PDF:
    <name>_categorized.csv  - the categorized transactions
    <name>_report.md        - the final Markdown report

Note on ADK API stability: this is written against the commonly
documented Agent / SequentialAgent / Runner / session-service pattern
as of when this was built. ADK's exact method signatures (sync vs
async session creation, runner method names) have moved between
releases in the past. If something here doesn't match your installed
version, check `python -c "import google.adk; print(google.adk.__version__)"`
and the current docs at [https://adk.dev](https://adk.dev), rather than assuming this
code is wrong outright.

On the SequentialAgent deprecation warning: newer ADK versions are
introducing a 'Workflow' construct to eventually replace it, but as of
writing, Workflow can't yet be used as an LlmAgent sub-agent, which is
exactly what this pipeline needs, so SequentialAgent remains the
correct choice here despite the warning. Revisit this once Workflow
supports sub-agent composition.
"""
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from orchestrated_pipeline.adk_pipeline.agents import categorizer_agent, reporter_agent
from orchestrated_pipeline.adk_pipeline.tools import parse_bank_statement

APP_NAME = "finance_pipeline"
USER_ID = "local_user"

pipeline = SequentialAgent(
    name="categorize_and_report_pipeline",
    sub_agents=[categorizer_agent, reporter_agent],
)


def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json") or text.startswith("markdown"):
            text = text.split("\n", 1)[1] if "\n" in text else text
    return text.strip()


def _coerce_to_list(parsed_json):
    """Unwrap a dict-wrapped list if the model ignored the bare-array
    instruction, e.g. it returned {"transactions": [...]} instead of
    [...] directly. Falls back to the first list-valued field found.
    """
    if isinstance(parsed_json, list):
        return parsed_json
    if isinstance(parsed_json, dict):
        for value in parsed_json.values():
            if isinstance(value, list):
                return value
    raise ValueError(f"Expected a JSON list of transactions, got: {type(parsed_json).__name__}")


async def run_pipeline(pdf_path: str) -> dict:
    """Parse deterministically, then run the two-agent pipeline on the result.

    The parsed data is embedded directly in the initial message sent to
    the agents, rather than referenced through session state, so the
    model always sees the real data instead of a broken text reference.
    """
    parsed = parse_bank_statement(pdf_path)

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    initial_message_text = (
        "Here is the parsed bank statement data as JSON:\n\n"
        f"{json.dumps(parsed, indent=2)}\n\n"
        "Categorize these transactions, then write a summary report."
    )
    message = types.Content(role="user", parts=[types.Part(text=initial_message_text)])

    runner = Runner(agent=pipeline, app_name=APP_NAME, session_service=session_service)

    categorized_text, report_text = "", ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if event.author == "categorizer_agent":
                categorized_text = text
            elif event.author == "reporter_agent":
                report_text = text

    return {
        "parsed": parsed,
        "categorized_text": _strip_code_fences(categorized_text),
        "report_text": _strip_code_fences(report_text),
    }


def _save_outputs(pdf_path: Path, result: dict):
    csv_path = pdf_path.with_name(pdf_path.stem + "_categorized.csv")
    md_path = pdf_path.with_name(pdf_path.stem + "_report.md")

    try:
        parsed_json = json.loads(result["categorized_text"])
        categorized = _coerce_to_list(parsed_json)
        pd.DataFrame(categorized).to_csv(csv_path, index=False)
        print(f"Saved categorized transactions to {csv_path}")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"WARNING: couldn't parse categorizer output as a transaction list ({e}), skipping CSV.")
        print(f"Raw categorizer output:\n{result['categorized_text'][:500]}")

    md_path.write_text(result["report_text"])
    print(f"Saved report to {md_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python -m orchestrated_pipeline.adk_pipeline.pipeline <path_to_bank_statement.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    result = asyncio.run(run_pipeline(str(pdf_path)))

    if result["parsed"]["warning"]:
        print(f"\nWARNING from parser: {result['parsed']['warning']}")

    print("\n=== Final Report ===\n")
    print(result["report_text"])

    _save_outputs(pdf_path, result)


if __name__ == "__main__":
    main()
