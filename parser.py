from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def parse_statement(pdf_path: Path) -> pd.DataFrame:
    """Parse a bank statement PDF into a single DataFrame of transactions.

    Docling extracts every table it finds on the page. Bank statements
    typically hold one transaction table (sometimes split across pages),
    so we concatenate every table found and normalize column names before
    returning.
    """
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    tables = []
    for table in doc.tables:
        df = table.export_to_dataframe()
        if not df.empty:
            tables.append(df)

    if not tables:
        raise ValueError(f"No tables detected in {pdf_path.name}")

    combined = pd.concat(tables, ignore_index=True)
    combined.columns = [str(c).strip() for c in combined.columns]
    return combined
