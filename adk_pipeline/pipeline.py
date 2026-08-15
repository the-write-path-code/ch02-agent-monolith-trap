"""Wires the deterministic Docling parse step and the two ADK agents
into one pipeline.

Run from the repo root:
    uv run python -m adk_pipeline.pipeline <path_to_statement.pdf>

Note on ADK API stability: this is written against the commonly
documented Agent / SequentialAgent / Runner / session-service pattern
as of when this was built. ADK's exact method signatures (sync vs
async session creation, runner method names) have moved between
releases in the past. If something here doesn't match your installed
version, check `python -c "import google.adk; print(google.adk.__version__)"`
and the current docs at https://adk.dev, rather than assuming this
code is wrong outright.
"""
import asyncio
import sys
from pathlib import Path

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_pipeline.agents import categorizer_agent, reporter_agent
from adk_pipeline.tools import parse_bank_statement

APP_NAME = "finance_pipeline"
USER_ID = "local_user"

pipeline = SequentialAgent(
    name="categorize_and_report_pipeline",
    sub_agents=[categorizer_agent, reporter_agent],
)


async def run_pipeline(pdf_path: str) -> str:
    """Parse deterministically, then run the two-agent pipeline on the result."""
    parsed = parse_bank_statement(pdf_path)

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"parsed_statement": parsed},
    )

    runner = Runner(agent=pipeline, app_name=APP_NAME, session_service=session_service)
    message = types.Content(
        role="user",
        parts=[types.Part(text="Categorize these transactions and write a summary report.")],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or final_text

    return final_text


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python -m adk_pipeline.pipeline <path_to_bank_statement.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    report = asyncio.run(run_pipeline(pdf_path))
    print("\n=== Final Report ===\n")
    print(report)


if __name__ == "__main__":
    main()
