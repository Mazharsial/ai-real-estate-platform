"""AI Investment Advisor (Module 8) with deterministic fallbacks."""
from __future__ import annotations

import json

from app.services.analysis import score_reasons
from app.services.ai.provider import generate_text


def _money(n) -> str:
    return "$" + f"{round(float(n or 0)):,}"


def investment_advice(p: dict, fin: dict) -> dict:
    """Return structured advice: summary, pros, cons, risks, recommendation, suggested_offer."""
    suggested_offer = round(float(p.get("price", 0)) * 0.96)  # opening negotiation anchor

    fallback = {
        "summary": (
            f"{p.get('address')} is priced at {_money(p.get('price'))} "
            f"({_money(p.get('price_per_sqft'))}/sqft vs neighborhood {_money(p.get('neighborhood_avg_ppsf'))}). "
            f"Investment score {p.get('investment_score')}/100 with an estimated "
            f"{fin.get('cash_on_cash')}% cash-on-cash return and {fin.get('cap_rate')}% cap rate."
        ),
        "pros": score_reasons(p),
        "cons": _cons(p, fin),
        "risks": _risks(p, fin),
        "recommendation": _recommendation(p, fin),
        "suggested_offer": suggested_offer,
        "source": "rules",
    }

    prompt = (
        "You are a real-estate investment advisor. Given the property and financials, return ONLY compact JSON "
        'with keys: summary (string), pros (array of short strings), cons (array), risks (array), '
        'recommendation (one of "Strong Buy","Buy","Hold","Pass" with a one-line reason), '
        "suggested_offer (integer USD). Be specific and realistic.\n\n"
        f"PROPERTY: {json.dumps({k: p.get(k) for k in ['address','city','zip','price','price_per_sqft','neighborhood_avg_ppsf','undervalued_pct','beds','baths','sqft','year_built','days_on_market','school_rating','crime_score','appreciation_trend','investment_score']})}\n"
        f"FINANCIALS: {json.dumps({k: fin.get(k) for k in ['monthly_cash_flow','annual_cash_flow','cap_rate','cash_on_cash','gross_yield','net_yield','noi','break_even_occupancy','mortgage_monthly']})}\n"
        "JSON:"
    )
    text = generate_text(prompt, temperature=0.4, max_tokens=600)
    if text:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end + 1])
                data.setdefault("suggested_offer", suggested_offer)
                data["source"] = "ai"
                return data
            except Exception:  # noqa: BLE001
                pass
    return fallback


def _cons(p: dict, fin: dict) -> list[str]:
    c = []
    if fin.get("monthly_cash_flow", 0) < 0:
        c.append(f"Negative monthly cash flow ({_money(fin['monthly_cash_flow'])})")
    if (p.get("undervalued_pct") or 0) < 0:
        c.append("Priced above the neighborhood average")
    if (p.get("days_on_market") or 0) > 45:
        c.append("On the market a long time")
    if (p.get("crime_score") or 10) < 6:
        c.append("Below-average safety score")
    if (p.get("hoa") or 0) > 300:
        c.append("High HOA fees reduce cash flow")
    return c or ["No major red flags identified"]


def _risks(p: dict, fin: dict) -> list[str]:
    r = ["Estimates rely on market data and assumptions; verify locally."]
    if (fin.get("break_even_occupancy") or 0) > 90:
        r.append("High break-even occupancy — little margin for vacancy")
    if (p.get("appreciation_trend") or 0) < 3:
        r.append("Modest historical appreciation")
    return r


def _recommendation(p: dict, fin: dict) -> str:
    score = p.get("investment_score", 0)
    coc = fin.get("cash_on_cash", 0)
    if score >= 70 and coc >= 6:
        return "Strong Buy — strong score with healthy cash-on-cash return."
    if score >= 60:
        return "Buy — solid fundamentals at a fair entry price."
    if score >= 50:
        return "Hold — acceptable but negotiate on price."
    return "Pass — weak return profile at the current price."
