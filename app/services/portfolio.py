"""Portfolio metrics (Module 14)."""
from __future__ import annotations

from collections import Counter

from app.services.analysis import rnd


def holding_metrics(h: dict) -> dict:
    purchase = float(h.get("purchase_price") or 0)
    value = float(h.get("current_value") or 0)
    mortgage = float(h.get("mortgage_balance") or 0)
    rent = float(h.get("monthly_rent") or 0)
    expenses = float(h.get("monthly_expenses") or 0)

    equity = value - mortgage
    monthly_cash_flow = rent - expenses
    annual_cash_flow = monthly_cash_flow * 12
    roi = (annual_cash_flow / purchase * 100) if purchase else 0
    appreciation = value - purchase
    appreciation_pct = (appreciation / purchase * 100) if purchase else 0

    return {
        **h,
        "equity": rnd(equity, 0),
        "monthly_cash_flow": rnd(monthly_cash_flow, 0),
        "annual_cash_flow": rnd(annual_cash_flow, 0),
        "roi": rnd(roi, 2),
        "appreciation": rnd(appreciation, 0),
        "appreciation_pct": rnd(appreciation_pct, 1),
    }


def portfolio_summary(holdings: list[dict]) -> dict:
    m = [holding_metrics(h) for h in holdings]
    total_value = sum(h.get("current_value") or 0 for h in m)
    total_purchase = sum(h.get("purchase_price") or 0 for h in m)
    total_mortgage = sum(h.get("mortgage_balance") or 0 for h in m)
    total_equity = sum(h["equity"] for h in m)
    total_monthly_cf = sum(h["monthly_cash_flow"] for h in m)
    total_annual_cf = sum(h["annual_cash_flow"] for h in m)
    overall_roi = (total_annual_cf / total_purchase * 100) if total_purchase else 0
    total_appreciation = total_value - total_purchase

    by_type = Counter((h.get("property_type") or "?") for h in m)
    by_city = Counter((h.get("city") or "?") for h in m)

    return {
        "holdings": m,
        "count": len(m),
        "total_value": rnd(total_value, 0),
        "total_purchase": rnd(total_purchase, 0),
        "total_equity": rnd(total_equity, 0),
        "total_mortgage": rnd(total_mortgage, 0),
        "total_monthly_cash_flow": rnd(total_monthly_cf, 0),
        "total_annual_cash_flow": rnd(total_annual_cf, 0),
        "overall_roi": rnd(overall_roi, 2),
        "total_appreciation": rnd(total_appreciation, 0),
        "diversification_type": [{"label": k, "count": v} for k, v in by_type.items()],
        "diversification_city": [{"label": k, "count": v} for k, v in by_city.items()],
    }
