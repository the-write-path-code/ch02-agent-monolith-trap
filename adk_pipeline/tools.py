"""ADK tool wrapper around the existing Docling parser.

This is the deterministic boundary from section 2.3: parsing is a plain
Python function, never a model call, so it can't hallucinate a
transaction. It's called directly in pipeline.py, not wrapped in an
agent, deliberately, see pipeline.py's docstring for why.
"""
from pathlib import Path

from parser import extract_transactions, parse_statement


def parse_bank_statement(pdf_path: str) -> dict:
    """Parse a bank statement PDF into transactions using Docling.

    Args:
        pdf_path: Path to the bank statement PDF on disk.

    Returns:
        A dict with "transactions" (list of {date, description, amount})
        and "warning" (non-empty string if the extracted row count
        didn't match the independent date-marker count from the source
        text, empty string otherwise).
    """
    result = parse_statement(Path(pdf_path))
    transactions_df = extract_transactions(result.tables)
    transactions = transactions_df.to_dict(orient="records")

    warning = ""
    if len(transactions) != result.expected_transaction_count:
        warning = (
            f"Extracted {len(transactions)} transaction(s), but the source "
            f"text contains {result.expected_transaction_count} date "
            "marker(s). Some rows may have been dropped or merged during "
            "table detection."
        )

    return {"transactions": transactions, "warning": warning}
