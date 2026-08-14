from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


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


def parse_statement(pdf_path: Path) -> list:
    """Parse a bank statement PDF and return every table Docling detects.

    Bank statements often contain more than one table per document, e.g.
    an account summary box plus the transaction ledger, and the ledger
    itself may split across pages. We don't assume which table is the
    one we want; we hand back all of them so the caller can inspect or
    pick the right one.
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

    return tables


def largest_table(tables: list) -> pd.DataFrame:
    """Heuristic: the transaction ledger is usually the table with the most rows."""
    return max(tables, key=len)
