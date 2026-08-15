import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash")

PROMPT_TEMPLATE = """You are a financial data analyst. Read the bank statement text below and, \
in a single pass, do all three of these things:

1. Extract every transaction as a list of objects with fields: date (MM/DD), \
description (string), amount (number, negative for debits/purchases, positive \
for deposits/credits).
2. Assign a short spending category to each transaction (e.g. "Groceries", \
"Dining", "Transfer", "Income", "Utilities", "Subscription", "Other").
3. Write a two-sentence natural-language summary of the statement.

Return ONLY valid JSON with this exact shape, no markdown fences, no commentary:
{{
  "transactions": [
    {{"date": "MM/DD", "description": "...", "amount": 0.00, "category": "..."}}
  ],
  "summary": "..."
}}

Statement text:
---
{statement_text}
---
"""


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def run_monolith(pdf_path: Path, model_name: str = None) -> dict:
    """Run the single-prompt, do-everything-at-once design on one statement.

    Returns a dict with the raw model text, whether it parsed as valid
    JSON, and the parsed transactions/summary if it did. Temperature is
    intentionally left at 0.7, not pinned to 0, to reflect how a
    single-prompt agent is actually deployed in practice rather than
    artificially forcing determinism to make the demo look cleaner.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Copy .env.example to .env and add your key.")

    client = genai.Client(api_key=api_key)
    statement_text = _extract_text(pdf_path)
    prompt = PROMPT_TEMPLATE.format(statement_text=statement_text)

    response = client.models.generate_content(
        model=model_name or MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )

    raw_text = response.text or ""
    cleaned = _strip_code_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
        return {
            "raw_text": raw_text,
            "valid_json": True,
            "transactions": parsed.get("transactions", []),
            "summary": parsed.get("summary", ""),
            "error": None,
        }
    except json.JSONDecodeError as e:
        return {
            "raw_text": raw_text,
            "valid_json": False,
            "transactions": [],
            "summary": "",
            "error": str(e),
        }
