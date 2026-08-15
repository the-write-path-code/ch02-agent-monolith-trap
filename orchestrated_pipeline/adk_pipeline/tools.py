"""ADK tool wrapper around the existing Docling parser.

This is the deterministic boundary from section 2.3: parsing is a plain
Python function, never a model call, so it can't hallucinate a
transaction. It's called directly in pipeline.py, not wrapped in an
agent, deliberately, see pipeline.py's docstring for why.

The raw output of parser.extract_transactions() has whatever column
names Docling happened to detect on a given document ('Sale Date',
'Post Date', 'Description', 'Amount', or something else entirely on a
different statement layout). This module normalizes that into a stable
{date, description, amount} schema so downstream agents always get the
same shape, regardless of the source document's actual header text. An
earlier version of this file promised that normalization in its
docstring without actually implementing it, which surfaced as raw
Docling column names leaking into the categorized CSV output.
"""
import re
from pathlib import Path

from deterministic_pipeline.parser import extract_transactions, parse_statement

_AMOUNT_PATTERN = re.compile(r"-?\$[\d,]+\.\d{2}")


def _normalize_transaction(row: dict) -> dict:
    """Map an arbitrary Docling-column-named row to {date, description, amount}."""
    date_candidates, amount_val, desc_val = [], "", ""

    for col, val in row.items():
        col_lower = str(col).lower()
        val_str = str(val).strip() if val is not None else ""
        if not val_str:
            continue
        if "date" in col_lower:
            date_candidates.append(val_str)
        elif "amount" in col_lower:
            amount_val = val_str
        elif "description" in col_lower:
            desc_val = val_str

    # Prefer a labeled amount column; fall back to any cell matching a
    # dollar pattern if the column wasn't named "amount" for some reason.
    if not amount_val:
        for val in row.values():
            val_str = str(val).strip() if val is not None else ""
            if _AMOUNT_PATTERN.match(val_str):
                amount_val = val_str
                break

    # Prefer a labeled description column; fall back to whatever's left
    # over once date-like and amount-like columns are excluded.
    if not desc_val:
        leftover = [
            str(val).strip()
            for col, val in row.items()
            if "date" not in str(col).lower()
            and "amount" not in str(col).lower()
            and str(val).strip()
        ]
        desc_val = leftover[0] if leftover else ""

    return {
        "date": date_candidates[0] if date_candidates else "",
        "description": desc_val,
        "amount": amount_val,
    }


def parse_bank_statement(pdf_path: str) -> dict:
    """Parse a bank statement PDF into transactions using Docling.

    Args:
        pdf_path: Path to the bank statement PDF on disk.

    Returns:
        A dict with "transactions" (list of {date, description, amount},
        a stable schema regardless of the source document's own column
        headers) and "warning" (non-empty string if the extracted row
        count didn't match the independent date-marker count from the
        source text, empty string otherwise).
    """
    result = parse_statement(Path(pdf_path))
    transactions_df = extract_transactions(result.tables)
    raw_transactions = transactions_df.to_dict(orient="records")
    transactions = [_normalize_transaction(row) for row in raw_transactions]

    warning = ""
    if len(transactions) != result.expected_transaction_count:
        warning = (
            f"Extracted {len(transactions)} transaction(s), but the source "
            f"text contains {result.expected_transaction_count} date "
            "marker(s). Some rows may have been dropped or merged during "
            "table detection."
        )

    return {"transactions": transactions, "warning": warning}
