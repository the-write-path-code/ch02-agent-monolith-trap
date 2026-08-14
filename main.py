import sys
from pathlib import Path

from parser import largest_table, parse_statement


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run main.py <path_to_bank_statement.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    tables = parse_statement(pdf_path)

    print(f"\nDocling found {len(tables)} table(s) in {pdf_path.name}:\n")
    for i, df in enumerate(tables):
        print(f"--- Table {i} ({len(df)} rows x {len(df.columns)} cols) ---")
        print(f"Columns: {list(df.columns)}")
        print(df.head(3).to_string(index=False))
        print()

    best = largest_table(tables)
    print(f"Likely transaction table: the one with {len(best)} rows.\n")
    print(best.to_string(index=False))

    out_path = pdf_path.with_suffix(".csv")
    best.to_csv(out_path, index=False)
    print(f"\nSaved likely transaction table to {out_path}")


if __name__ == "__main__":
    main()
