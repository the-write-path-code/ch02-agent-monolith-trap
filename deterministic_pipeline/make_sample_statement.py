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
OUT_PATH = OUT_DIR / "sample_statement.pdf"

TRANSACTIONS = [
    ["Date", "Description", "Amount", "Balance"],
    ["01/03/2026", "Payroll Deposit - Acme Corp", "2,450.00", "5,120.44"],
    ["01/05/2026", "SQ *THE COPPER Q CAFE", "-8.75", "5,111.69"],
    ["01/06/2026", "Rent Payment - Bayview Apts", "-1,450.00", "3,661.69"],
    ["01/08/2026", "AMAZON.COM*A1B2C3D4", "-64.32", "3,597.37"],
    ["01/10/2026", "Uber Trip Help.uber.com", "-14.20", "3,583.17"],
    ["01/12/2026", "Whole Foods Market #103", "-92.14", "3,491.03"],
    ["01/15/2026", "Interest Payment", "1.42", "3,492.45"],
    ["01/18/2026", "Netflix.com", "-15.49", "3,476.96"],
    ["01/20/2026", "Con Edison Utility Bill", "-118.60", "3,358.36"],
    ["01/25/2026", "Transfer to Savings", "-500.00", "2,858.36"],
]


def build_pdf():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUT_PATH), pagesize=letter)

    elements = [
        Paragraph("First Trust Bank", styles["Title"]),
        Paragraph("Monthly Statement \u2014 January 2026", styles["Heading2"]),
        Paragraph(
            "Account holder: Jordan Rivera &nbsp;&nbsp;|&nbsp;&nbsp; Account: ****4821",
            styles["Normal"],
        ),
        Spacer(1, 16),
    ]

    table = Table(TRANSACTIONS, colWidths=[80, 250, 80, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f2f2f2")],
                ),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    print(f"Sample statement written to {OUT_PATH}")


if __name__ == "__main__":
    build_pdf()
