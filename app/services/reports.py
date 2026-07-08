"""Investment Report generator (Module 12) — professional PDF via ReportLab."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#0d9488")
INK = colors.HexColor("#0f1b2d")
MUTED = colors.HexColor("#64748b")


def _money(n) -> str:
    return "$" + f"{round(float(n or 0)):,}"


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1", parent=ss["Title"], textColor=INK, fontSize=20, spaceAfter=2))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], textColor=MUTED, fontSize=10, spaceAfter=10))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], textColor=BRAND, fontSize=12, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.5, leading=13))
    return ss


def _kv_table(rows: list[tuple[str, str]], col2_align="RIGHT") -> Table:
    t = Table([[k, v] for k, v in rows], colWidths=[70 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("ALIGN", (1, 0), (1, -1), col2_align),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#e6ecf5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _bullets(items: list[str], ss) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(str(x), ss["Body"]), leftIndent=10) for x in (items or ["—"])],
        bulletType="bullet", start="•", leftIndent=12,
    )


def build_property_report(bundle: dict, advice: dict) -> bytes:
    p = bundle["property"]
    fin = bundle["financials"]
    sc = bundle["score"]
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm, title=f"Investment Report — {p.get('address')}")
    story = []

    story.append(Paragraph("Investment Report", ss["H1"]))
    story.append(Paragraph(f"{p.get('address')} · {p.get('city')}, {p.get('state')} {p.get('zip')} — "
                           f"generated {datetime.now():%d %b %Y}", ss["Sub"]))

    # Executive summary
    story.append(Paragraph("Executive Summary", ss["H2"]))
    story.append(Paragraph(advice.get("summary", ""), ss["Body"]))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("List price", _money(p.get("price"))),
        ("Investment score", f"{p.get('investment_score')} / 100"),
        ("Recommendation", str(advice.get("recommendation", ""))),
        ("Suggested opening offer", _money(advice.get("suggested_offer"))),
    ]))

    # Property overview
    story.append(Paragraph("Property Overview", ss["H2"]))
    story.append(_kv_table([
        ("Type / Year built", f"{p.get('property_type')} · {p.get('year_built')}"),
        ("Beds / Baths", f"{p.get('beds')} / {p.get('baths')}"),
        ("Area", f"{p.get('sqft')} sqft"),
        ("Days on market", str(p.get("days_on_market"))),
        ("Price / sqft", _money(p.get("price_per_sqft"))),
        ("Neighborhood avg / sqft", _money(p.get("neighborhood_avg_ppsf"))),
        ("Undervalued", f"{p.get('undervalued_pct')}%"),
        ("3-year estimated value", _money(p.get("predicted_value_3yr"))),
    ]))

    # Financials
    story.append(Paragraph("Financial Analysis", ss["H2"]))
    story.append(_kv_table([
        ("Estimated rent / month", _money(fin.get("monthly_rent"))),
        ("Net operating income (NOI)", _money(fin.get("noi"))),
        ("Mortgage / month", _money(fin.get("mortgage_monthly"))),
        ("Monthly cash flow", _money(fin.get("monthly_cash_flow"))),
        ("Cap rate", f"{fin.get('cap_rate')}%"),
        ("Cash-on-cash return", f"{fin.get('cash_on_cash')}%"),
        ("Gross / net yield", f"{fin.get('gross_yield')}% / {fin.get('net_yield')}%"),
        ("Cash needed (down + closing)", _money(fin.get("cash_invested"))),
        ("Break-even occupancy", f"{fin.get('break_even_occupancy')}%"),
    ]))

    # AI advisor
    story.append(Paragraph("AI Investment Advisor", ss["H2"]))
    story.append(Paragraph("<b>Pros</b>", ss["Body"]))
    story.append(_bullets(advice.get("pros"), ss))
    story.append(Paragraph("<b>Cons</b>", ss["Body"]))
    story.append(_bullets(advice.get("cons"), ss))
    story.append(Paragraph("<b>Risks</b>", ss["Body"]))
    story.append(_bullets(advice.get("risks"), ss))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Disclaimer: estimates and AI output are for research and education only and are not financial "
        "advice. Verify all figures independently before making an investment decision.",
        ParagraphStyle("disc", parent=ss["Body"], textColor=MUTED, fontSize=7.5)))

    doc.build(story)
    return buf.getvalue()
