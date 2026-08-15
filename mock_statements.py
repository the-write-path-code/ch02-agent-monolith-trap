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

OUT_DIR = Path(__file__).parent / "mock_data"

# The same 10 transactions are held constant across every complexity
# level. Only the page layout changes between levels, never the
# underlying data, so any accuracy dropoff can be attributed to layout
# complexity rather than to a harder or longer transaction list.
TRANSACTIONS = [
    {"date": "07/03", "description": "Payroll Deposit - Acme Corp", "amount": 2450.00},
    {"date": "07/05", "description": "SQ *THE COPPER Q CAFE", "amount": -8.75},
    {"date": "07/06", "description": "Rent Payment - Bayview Apts", "amount": -1450.00},
    {"date": "07/08", "description": "AMAZON.COM*A1B2C3D4", "amount": -64.32},
    {"date": "07/10", "description": "Uber Trip Help.uber.com", "amount": -14.20},
    {"date": "07/12", "description": "Whole Foods Market #103", "amount": -92.14},
    {"date": "07/15", "description": "Interest Payment", "amount": 1.42},
    {"date": "07/18", "description": "Netflix.com", "amount": -15.49},
    {"date": "07/20", "description": "Con Edison Utility Bill", "amount": -118.60},
    {"date": "07/25", "description": "Transfer to Savings", "amount": -500.00},
]


def _amount_str(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ])


def build_level_1() -> Path:
    """Clean: one table, one header row, nothing else on the page."""
    out_path = OUT_DIR / "level_1_clean.pdf"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter)
    styles = getSampleStyleSheet()

    rows = [["Date", "Description", "Amount"]]
    rows += [[t["date"], t["description"], _amount_str(t["amount"])] for t in TRANSACTIONS]

    table = Table(rows, colWidths=[70, 280, 80])
    table.setStyle(_table_style())
    table.setStyle(TableStyle([("ALIGN", (2, 0), (2, -1), "RIGHT")]))

    doc.build([
        Paragraph("First Trust Bank - July Statement", styles["Title"]),
        Spacer(1, 12),
        table,
    ])
    return out_path


def build_level_2() -> Path:
    """Sectioned: account summary block plus section labels between groups of rows."""
    out_path = OUT_DIR / "level_2_sectioned.pdf"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("First Trust Bank - July Statement", styles["Title"]),
        Paragraph("ACCOUNT SUMMARY", styles["Heading2"]),
        Paragraph("Previous balance $0.00 | Payments -$500.00 | Purchases +$1,763.50", styles["Normal"]),
        Spacer(1, 12),
    ]

    rows = [["Date", "Description", "Amount"]]
    rows.append(["Deposits", "Deposits", ""])
    rows.append([TRANSACTIONS[0]["date"], TRANSACTIONS[0]["description"], _amount_str(TRANSACTIONS[0]["amount"])])
    rows.append([TRANSACTIONS[6]["date"], TRANSACTIONS[6]["description"], _amount_str(TRANSACTIONS[6]["amount"])])
    rows.append(["Standard Purchases", "Standard Purchases", ""])
    for t in TRANSACTIONS[1:6] + TRANSACTIONS[7:]:
        rows.append([t["date"], t["description"], _amount_str(t["amount"])])

    table = Table(rows, colWidths=[70, 280, 80])
    table.setStyle(_table_style())
    table.setStyle(TableStyle([("ALIGN", (2, 0), (2, -1), "RIGHT")]))
    elements.append(table)
    doc.build(elements)
    return out_path


def build_level_3() -> Path:
    """Dual dates plus a two-line column header, like a real card statement."""
    out_path = OUT_DIR / "level_3_dual_dates.pdf"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter)
    styles = getSampleStyleSheet()

    rows = [["Sale\nDate", "Post\nDate", "Description", "Amount"]]
    for i, t in enumerate(TRANSACTIONS):
        post_date = t["date"] if i % 3 == 0 else ""
        rows.append([t["date"], post_date, t["description"], _amount_str(t["amount"])])

    table = Table(rows, colWidths=[55, 55, 260, 70])
    table.setStyle(_table_style())
    table.setStyle(TableStyle([("ALIGN", (3, 0), (3, -1), "RIGHT")]))

    doc.build([
        Paragraph("First Trust Bank - July Statement", styles["Title"]),
        Spacer(1, 12),
        table,
    ])
    return out_path


def build_level_4() -> Path:
    """Dense: cardholder summary, a sectioned/dual-date ledger, and a trailing fees/interest block."""
    out_path = OUT_DIR / "level_4_dense.pdf"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("First Trust Bank - July Statement", styles["Title"]),
        Paragraph("CARDHOLDER SUMMARY", styles["Heading2"]),
        Paragraph("J. RIVERA New Charges Card ending in 4821 $1,263.50", styles["Normal"]),
        Paragraph("ACCOUNT SUMMARY", styles["Heading2"]),
        Spacer(1, 12),
    ]

    rows = [["Sale\nDate", "Post\nDate", "Description", "Amount"]]
    rows.append(["Deposits and Credits", "Deposits and Credits", "Deposits and Credits", ""])
    rows.append([TRANSACTIONS[0]["date"], "", TRANSACTIONS[0]["description"], _amount_str(TRANSACTIONS[0]["amount"])])
    rows.append([TRANSACTIONS[6]["date"], "", TRANSACTIONS[6]["description"], _amount_str(TRANSACTIONS[6]["amount"])])
    rows.append(["J. RIVERA", "J. RIVERA", "", ""])
    rows.append(["Standard Purchases", "Standard Purchases", "", ""])
    remaining = TRANSACTIONS[1:6] + TRANSACTIONS[7:]
    for i, t in enumerate(remaining):
        post_date = t["date"] if i % 3 == 0 else ""
        rows.append([t["date"], post_date, t["description"], _amount_str(t["amount"])])

    table = Table(rows, colWidths=[55, 55, 260, 70])
    table.setStyle(_table_style())
    table.setStyle(TableStyle([("ALIGN", (3, 0), (3, -1), "RIGHT")]))
    elements.append(table)

    elements.append(Spacer(1, 16))
    elements.append(Paragraph("Fees Charged", styles["Heading3"]))
    elements.append(Paragraph("TOTAL FEES FOR THIS PERIOD $0.00", styles["Normal"]))
    elements.append(Paragraph("Interest Charged", styles["Heading3"]))
    elements.append(Paragraph("TOTAL INTEREST FOR THIS PERIOD $0.00", styles["Normal"]))
    elements.append(Paragraph("Interest charge calculation", styles["Heading3"]))
    elements.append(Paragraph("Standard Purch 24.99% (V) $0.00 (D) $0.00", styles["Normal"]))

    doc.build(elements)
    return out_path


LEVELS = {
    1: ("Clean", build_level_1),
    2: ("Sectioned", build_level_2),
    3: ("Dual dates + split header", build_level_3),
    4: ("Dense / multi-section", build_level_4),
}


def build_all() -> dict:
    """Generate every complexity level's PDF and return {level: path}."""
    return {level: builder() for level, (_, builder) in LEVELS.items()}
