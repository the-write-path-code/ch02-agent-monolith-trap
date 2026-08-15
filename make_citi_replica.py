"""Generate a sanitized replica of the dense real-world statement layout
that originally exposed Docling's table-structure bug (see
docs/pipeline.md). All personal information, name, address, and account
numbers, has been replaced with fictional placeholders, and the bank
branding is fictional too. The transaction merchants, dates, and amounts
are preserved as-is: they're generic business trade names, not personal
data, and keeping them intact means this replica reproduces the same
known failure (a dropped row and a corrupted description) that the real
statement triggered, safely and shareably.

Run: uv run python make_citi_replica.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = Path(__file__).parent / "sample_data"
OUT_PATH = OUT_DIR / "citi_replica_statement.pdf"

CARDHOLDER_NAME = "JORDAN RIVERA"
CARDHOLDER_ADDRESS = "100 MAIN ST, ANYTOWN CA 90001-0000"
CARD_LAST_4 = "0000"
SECOND_CARDHOLDER = "SAM TAYLOR"
SECOND_CARD_LAST_4 = "1111"

# Same merchants, dates, and amounts as the real statement that exposed
# the bug. These are generic business trade names, not personal data.
LEDGER_ROWS = [
    ("07/27", "", "ONLINE PAYMENT, THANK YOU", "-$139.73"),
    ("07/10", "", "TACO BELL 029551 CHESTER VA", "$11.33"),
    ("07/10", "", "SHELL OIL 575410295QPS WILLIAMSBURG VA", "$47.45"),
    ("07/12", "", "CVS/PHARMACY #01549 MIDLOTHIAN VA", "$3.25"),
    ("07/14", "", "PUBLIX #1694 MIDLOTHIAN VA", "$29.49"),
    ("07/15", "07/15", "DOMINOS 4256 MIDLOTHIAN VA", "$11.64"),
    ("07/31", "", "CVS/PHARMACY #01549 MIDLOTHIAN VA", "$7.45"),
    ("08/03", "", "QLT*Habitat ReStore Williamsburg VA", "$6.96"),
    ("08/03", "08/03", "PIZZA HUT 042350 MIDLOTHIAN VA", "$13.78"),
    ("08/05", "", "ROYAL BAZAAR FARMERS M HENRICO VA", "$66.29"),
    ("08/06", "08/06", "PARK'N GO RIC AIRPORT 8049057700 VA", "$52.00"),
    ("08/10", "", "TRADER JOE S #011 BREA CA", "$82.51"),
    ("08/10", "", "PROV ST JUDE PARKING FULLERTON CA", "$5.00"),
    ("08/10", "", "TOUS LES JOURS BREA BREA CA", "$34.00"),
]


def build_replica() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUT_PATH), pagesize=letter)

    elements = [
        Paragraph("First Trust Bank / Rewards Card", styles["Title"]),
        Paragraph(f"Member: {CARDHOLDER_NAME}, account ending in {CARD_LAST_4}", styles["Normal"]),
        Paragraph(CARDHOLDER_ADDRESS, styles["Normal"]),
        Paragraph("AUGUST STATEMENT   Billing Period: 07/10-08/11", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("CARDHOLDER SUMMARY", styles["Heading2"]),
        Paragraph(f"{CARDHOLDER_NAME} New Charges, Card ending in {CARD_LAST_4}, $371.15", styles["Normal"]),
        Paragraph(f"{SECOND_CARDHOLDER} New Charges, Card ending in {SECOND_CARD_LAST_4}, $0.00", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("ACCOUNT SUMMARY", styles["Heading2"]),
    ]

    # Two-line header, this specific structure is what originally
    # confused Docling's table-structure model.
    rows = [["Sale\nDate", "Post\nDate", "Description", "Amount"]]
    rows.append(["Payments, Credits and Adjustments"] * 3 + [""])
    rows.append(list(LEDGER_ROWS[0]))
    rows.append([CARDHOLDER_NAME, CARDHOLDER_NAME, "", ""])
    rows.append(["Standard Purchases", "Standard Purchases", "", ""])
    for r in LEDGER_ROWS[1:]:
        rows.append(list(r))
    rows.append([SECOND_CARDHOLDER, SECOND_CARDHOLDER, "", ""])
    rows.append(["No Activity", "No Activity", "", ""])

    table = Table(rows, colWidths=[55, 55, 260, 70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 16))
    elements.append(Paragraph("Fees Charged", styles["Heading3"]))
    elements.append(Paragraph("TOTAL FEES FOR THIS PERIOD $0.00", styles["Normal"]))
    elements.append(Paragraph("Interest Charged", styles["Heading3"]))
    elements.append(Paragraph("TOTAL INTEREST FOR THIS PERIOD $0.00", styles["Normal"]))
    elements.append(Paragraph("2026 totals year-to-date", styles["Heading3"]))
    elements.append(Paragraph("Total fees charged $0.00   Total interest charged $0.00", styles["Normal"]))
    elements.append(Paragraph("Interest charge calculation", styles["Heading3"]))
    elements.append(Paragraph("Days in billing cycle: 33", styles["Normal"]))

    calc_rows = [
        ["Balance type", "Annual percentage rate (APR)", "Balance subject to interest rate", "Interest charge"],
        ["PURCHASES", "", "", ""],
        ["Standard Purch", "27.49% (V)", "$0.00 (D)", "$0.00"],
        ["ADVANCES", "", "", ""],
        ["Standard Adv", "29.74% (V)", "$0.00 (D)", "$0.00"],
    ]
    calc_table = Table(calc_rows, colWidths=[110, 130, 130, 80])
    calc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(Spacer(1, 8))
    elements.append(calc_table)

    doc.build(elements)
    print(f"Sanitized replica written to {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    build_replica()
