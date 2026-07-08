"""Property Comparison (Module 10) — side-by-side + AI recommendation."""
from __future__ import annotations

import json

from app.services.analysis import full_financials
from app.services.ai.provider import generate_text


def _money(n) -> str:
    return "$" + f"{round(float(n or 0)):,}"


def compare_properties(properties: list[dict]) -> dict:
    rows = []
    for p in properties:
        fin = full_financials(p)
        rows.append({**p, "financials": fin})

    winner = max(rows, key=lambda r: (r.get("investment_score") or 0, r["financials"]["monthly_cash_flow"]))
    recommendation = _ai_recommendation(rows, winner) or _fallback(rows, winner)

    return {"count": len(rows), "properties": rows, "winner_id": winner.get("id"),
            "recommendation": recommendation}


def _fallback(rows: list[dict], winner: dict) -> str:
    others = [r for r in rows if r is not winner]
    reason = []
    if winner.get("undervalued_pct", 0) == max(r.get("undervalued_pct", 0) for r in rows):
        reason.append("most undervalued")
    if winner["financials"]["cash_on_cash"] == max(r["financials"]["cash_on_cash"] for r in rows):
        reason.append("best cash-on-cash return")
    if winner.get("investment_score", 0) == max(r.get("investment_score", 0) for r in rows):
        reason.append("highest investment score")
    why = ", ".join(reason) or "the best overall blend of value and returns"
    return f"Recommendation: buy {winner.get('address')} — it offers {why}."


def _ai_recommendation(rows: list[dict], winner: dict) -> str | None:
    def fmt(r):
        f = r["financials"]
        return (f"{r.get('address')}: {_money(r.get('price'))}, {r.get('sqft')}sqft, {r.get('beds')}bd, "
                f"score {r.get('investment_score')}, {r.get('undervalued_pct')}% below market, "
                f"{r.get('rental_yield')}% yield, cap {f['cap_rate']}%, "
                f"cash-on-cash {f['cash_on_cash']}%, monthly cash flow {_money(f['monthly_cash_flow'])}")

    prompt = (
        "Compare these investment properties and recommend ONE to buy. "
        "Give the pick on the first line, then 3 short bullet reasons.\n"
        + "\n".join(f"{i + 1}) {fmt(r)}" for i, r in enumerate(rows))
    )
    return generate_text(prompt, temperature=0.4, max_tokens=280)
