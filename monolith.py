import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite")
MAX_ATTEMPTS = int(os.environ.get("MAX_CODEGEN_ATTEMPTS", "3"))
EXEC_TIMEOUT_SECONDS = 10

CODEGEN_PROMPT = """You are writing Python code to parse a bank statement's raw text into \
structured transactions.

Write a single Python function with this exact signature:

def extract_transactions(text: str) -> list:
    ...

It must return a list of dicts, each with keys: "date" (string, "MM/DD"), \
"description" (string), "amount" (float, negative for debits/purchases, \
positive for deposits/credits).

Return ONLY the Python function definition. No markdown fences, no example \
usage, no commentary, no import of anything beyond the standard library.

Statement text this function will receive at runtime:
---
{statement_text}
---
"""

FIX_PROMPT_SUFFIX = """

Your previous attempt failed. Here is the code you wrote:
---
{previous_code}
---

Here is the error it raised when run against the statement text above:
---
{error}
---

Write a corrected version of the same function. Return ONLY the corrected \
Python function definition, same rules as before.
"""

HARNESS_TEMPLATE = """
{generated_code}

import sys, json
_text = sys.stdin.read()
_result = extract_transactions(_text)
print(json.dumps(_result))
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
        if text.startswith("python"):
            text = text[6:]
    return text.strip()


def _generate_code(statement_text: str, model_name: str, previous_code: str = None, error: str = None) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Copy .env.example to .env and add your key.")

    client = genai.Client(api_key=api_key)
    prompt = CODEGEN_PROMPT.format(statement_text=statement_text)
    if previous_code and error:
        prompt += FIX_PROMPT_SUFFIX.format(previous_code=previous_code, error=error)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7),
        )
    except Exception as e:
        if "404" in str(e) or "NOT_FOUND" in str(e):
            raise RuntimeError(
                f"Model '{model_name}' isn't reachable with this API key. Run "
                "`uv run python list_models.py` to see available models, then "
                "update MODEL_NAME in .env."
            ) from e
        raise

    return _strip_code_fences(response.text or "")


def _execute_code(code: str, statement_text: str) -> dict:
    """Run generated code in a subprocess (not sandboxed, local demo only).

    The generated function is embedded in a small harness that calls it
    with the statement text piped in on stdin, then prints the result as
    JSON on stdout. This isolates the generated code's own crashes,
    syntax errors, and infinite loops (via a timeout) from the parent
    process. Do not run this against untrusted PDFs or on a machine you
    don't control; there is no hardened sandbox here.
    """
    harness = HARNESS_TEMPLATE.format(generated_code=code)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(harness)
        script_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            input=statement_text,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False, "transactions": [],
            "error": f"Timed out after {EXEC_TIMEOUT_SECONDS}s (possible infinite loop)",
        }
    finally:
        os.unlink(script_path)

    if proc.returncode != 0:
        return {"success": False, "transactions": [], "error": proc.stderr.strip()[-2000:]}

    try:
        transactions = json.loads(proc.stdout.strip())
        return {"success": True, "transactions": transactions, "error": None}
    except json.JSONDecodeError as e:
        return {
            "success": False, "transactions": [],
            "error": f"Output wasn't valid JSON: {e}. Raw stdout: {proc.stdout[:500]}",
        }


def run_codegen_monolith(pdf_path: Path, model_name: str = None, max_attempts: int = None) -> dict:
    """Ask a single model to write parsing code, run it, and let the same
    model fix its own code on failure, up to max_attempts times.

    This mirrors the actual mechanism that broke in the original
    hackathon project: a Data Analyzer agent writing Python against raw
    statement text, and a Code Executor running it, not a direct
    read-and-reformat task. No framework is involved here, this is a
    plain Python retry loop calling the Gemini API directly.
    """
    model_name = model_name or MODEL_NAME
    max_attempts = max_attempts or MAX_ATTEMPTS
    statement_text = _extract_text(pdf_path)

    previous_code, error = None, None
    for attempt in range(1, max_attempts + 1):
        code = _generate_code(statement_text, model_name, previous_code, error)
        result = _execute_code(code, statement_text)

        if result["success"]:
            return {
                "success": True, "attempts": attempt, "code": code,
                "transactions": result["transactions"], "error": None,
            }

        previous_code, error = code, result["error"]

    return {
        "success": False, "attempts": max_attempts, "code": previous_code,
        "transactions": [], "error": error,
    }
