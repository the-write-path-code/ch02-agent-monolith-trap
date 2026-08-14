import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter
from pypdf import PdfReader

AMOUNT_PATTERN = re.compile(r"-?\$[\d,]+\.\d{2}")
DATE_LINE_PATTERN = re.compile(r"^\d{2}/\d{2}$")
DATE_CELL_PATTERN = re.compile(r"^\d{2}/\d{2}(?:\s+\d{2}/\d{2})?$")


@dataclass
class ParseResult:
    tables: list
    expected_transaction_count: int


def _dedupe_columns(columns) -> list:
    seen = {}
    deduped = []
    for col in columns:
        col = str(col).strip() or "unnamed"
        if col in seen:
            seen[col] += 1
            deduped.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            deduped.append(col)
    return deduped


def _best_matching_column(df: pd.DataFrame, pattern: re.Pattern, min_rate: float = 0.3):
    """Find the column whose values best match a given pattern."""
    best_col, best_rate = None, 0.0
    for col in df.columns:
        values = df[col].astype(str).str.strip()
        non_empty = values[values != ""]
        if non_empty.empty:
            continue
        rate = non_empty.str.match(pattern).mean()
        if rate > best_rate:
            best_col, best_rate = col, rate
    return best_col if best_rate >= min_rate else None


def _drop_header_and_section_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows that look like an actual transaction: a date-shaped
    cell in one column and a dollar-shaped cell in another.

    Multi-line table headers (a "Sale" / "Date" label split across two
    physical rows), section labels ("Standard Purchases", cardholder
    names), and summary rows ("TOTAL FEES FOR THIS PERIOD ... $0.00",
    an APR disclosure row) can all carry a dollar-shaped value in the
    amount column, so filtering on the amount alone isn't enough. Adding
    the date-column check screens those out too, since none of them
    start with an MM/DD date the way a real transaction row does.
    """
    amount_col = _best_matching_column(df, AMOUNT_PATTERN)
    date_col = _best_matching_column(df, DATE_CELL_PATTERN)

    if amount_col is None:
        return df

    amount_mask = df[amount_col].astype(str).str.strip().str.match(AMOUNT_PATTERN)

    if date_col is not None:
        date_mask = df[date_col].astype(str).str.strip().str.match(DATE_CELL_PATTERN)
        mask = amount_mask & date_mask
    else:
        mask = amount_mask

    return df[mask].reset_index(drop=True)


def _count_likely_transaction_lines(pdf_path: Path) -> int:
    """Independent sanity check: count date markers in the raw PDF text.

    This reads the PDF's text layer directly with pypdf, bypassing
    Docling's table-structure model entirely. Statements typically print
    a bare "MM/DD" line immediately before each transaction's
    description, sometimes twice in a row for a sale date and a post
    date. Consecutive duplicate date lines are collapsed into one count
    so a single transaction with two dates isn't counted twice. This is
    a heuristic tied to this statement's layout, not a general-purpose
    transaction counter, but a mismatch against the extracted row count
    is a strong signal that the table model dropped or merged rows.
    """
    reader = PdfReader(str(pdf_path))
    count = 0
    prev_line = None
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if DATE_LINE_PATTERN.match(line):
                if line != prev_line:
                    count += 1
                prev_line = line
            else:
                prev_line = None
    return count


def parse_statement(pdf_path: Path) -> ParseResult:
    """Parse a bank statement PDF and return every table Docling detects,
    plus an independent estimate of how many transaction rows to expect.
    """
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    tables = []
    for table in doc.tables:
        df = table.export_to_dataframe(doc=doc)
        if df.empty:
            continue
        df.columns = _dedupe_columns(df.columns)
        df = df.reset_index(drop=True)
        tables.append(df)

    if not tables:
        raise ValueError(f"No tables detected in {pdf_path.name}")

    expected = _count_likely_transaction_lines(pdf_path)
    return ParseResult(tables=tables, expected_transaction_count=expected)


def largest_table(tables: list) -> pd.DataFrame:
    """Heuristic: the transaction ledger is usually the table with the most rows."""
    return max(tables, key=len)


def extract_transactions(tables: list) -> pd.DataFrame:
    """Pick the likely ledger table and strip it down to real transaction rows."""
    ledger = largest_table(tables)
    return _drop_header_and_section_rows(ledger)
