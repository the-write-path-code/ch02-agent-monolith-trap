import sys
from pathlib import Path

from parser import parse_statement


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run main.py <path_to_bank_statement.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    df = parse_statement(pdf_path)

    print(f"\nExtracted {len(df)} transaction rows from {pdf_path.name}\n")
    print(df.to_string(index=False))

    out_path = pdf_path.with_suffix(".csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
