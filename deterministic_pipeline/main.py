import sys
from pathlib import Path

from parser import extract_transactions, parse_statement


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run main.py <path_to_bank_statement.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    result = parse_statement(pdf_path)

    print(f"\nDocling found {len(result.tables)} table(s) in {pdf_path.name}:\n")
    for i, df in enumerate(result.tables):
        print(f"--- Table {i} ({len(df)} rows x {len(df.columns)} cols) ---")
        print(f"Columns: {list(df.columns)}")
        print(df.head(3).to_string(index=False))
        print()

    transactions = extract_transactions(result.tables)
    print(f"Likely transaction rows (amount-bearing only): {len(transactions)}\n")
    print(transactions.to_string(index=False))

    print(
        f"\nRaw text contains {result.expected_transaction_count} date marker(s). "
        f"Extracted {len(transactions)} transaction row(s)."
    )
    if len(transactions) != result.expected_transaction_count:
        print(
            "WARNING: these counts don't match. Some transactions may have "
            "been dropped or merged during table detection. Check the source "
            "PDF against this output before trusting it."
        )

    out_path = pdf_path.with_suffix(".csv")
    transactions.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
