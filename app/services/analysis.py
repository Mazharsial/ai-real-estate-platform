"""Property analysis + financial engine (Modules 5 & 6).

Pure, deterministic functions operating on plain dicts so they are trivially
unit-testable and independent of the ORM / web layers.
"""
from __future__ import annotations

from typing import Any, Iterable


# ------------------------------------------------------------------ helpers
def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def rnd(n: float, d: int = 0) -> float:
    return round(float(n), d)


def price_per_sqft(price: float, sqft: float) -> float:
    if not price or not sqft:
        return 0.0
    return rnd(price / sqft, 2)


# ------------------------------------------------------------------ market
def neighborhood_averages(items: list[dict]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for p in items:
        ppsf = price_per_sqft(p.get("price"), p.get("sqft"))
        if not ppsf:
            continue
        key = p.get("zip") or p.get("city") or "all"
        buckets.setdefault(key, []).append(ppsf)
    return {k: rnd(sum(v) / len(v), 2) for k, v in buckets.items()}


def undervalued_pct(ppsf: float, benchmark: float) -> float:
    if not ppsf or not benchmark:
        return 0.0
    return rnd((benchmark - ppsf) / benchmark * 100, 1)


# ------------------------------------------------------------------ rental
def heuristic_monthly_rent(price: float) -> float:
    return rnd(price * 0.007, 0) if price else 0.0


def rental_yield(annual_rent: float, price: float) -> float:
    if not annual_rent or not price:
        return 0.0
    return rnd(annual_rent / price * 100, 2)


# ------------------------------------------------------------------ mortgage
def monthly_mortgage(price: float, down_pct: float, annual_rate_pct: float, years: int) -> float:
    principal = price * (1 - down_pct / 100)
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return rnd(principal / n, 0) if n else 0.0
    m = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return rnd(m, 0)


# ------------------------------------------------------------------ appreciation
def predict_value(price_history: list[dict] | None, current_price: float, years: int = 3) -> dict:
    cagr = 0.045
    if price_history and len(price_history) >= 2:
        first, last = price_history[0], price_history[-1]
        span = (last["year"] - first["year"]) or 1
        if first["value"] > 0:
            cagr = (last["value"] / first["value"]) ** (1 / span) - 1
    cagr = clamp(cagr, -0.05, 0.15)
    predicted = current_price * (1 + cagr) ** years
    return {"predicted": rnd(predicted, 0), "cagr": rnd(cagr * 100, 1)}


# ------------------------------------------------------------------ score
def investment_score(p: dict) -> dict:
    """0-100 weighted score per the platform spec."""
    price_below = clamp((p.get("undervalued_pct") or 0) / 30, 0, 1)
    yield_n = clamp((p.get("rental_yield") or 0) / 10, 0, 1)
    school_n = clamp((p.get("school_rating") or 0) / 10, 0, 1)
    crime_n = clamp((p.get("crime_score") or 0) / 10, 0, 1)
    appr_n = clamp((p.get("appreciation_trend") or 0) / 8, 0, 1)
    dom_n = clamp(1 - (p.get("days_on_market") or 0) / 60, 0, 1)

    score = 100 * (
        0.30 * price_below
        + 0.20 * yield_n
        + 0.15 * school_n
        + 0.15 * crime_n
        + 0.10 * appr_n
        + 0.10 * dom_n
    )
    return {
        "score": round(clamp(score, 0, 100)),
        "breakdown": {
            "price_below_market": round(price_below * 100),
            "rental_yield": round(yield_n * 100),
            "school": round(school_n * 100),
            "safety": round(crime_n * 100),
            "appreciation": round(appr_n * 100),
            "days_on_market": round(dom_n * 100),
        },
    }


def score_reasons(p: dict) -> list[str]:
    r: list[str] = []
    if (p.get("undervalued_pct") or 0) >= 8:
        r.append(f"{p['undervalued_pct']}% below neighborhood average")
    if (p.get("rental_yield") or 0) >= 6:
        r.append(f"Strong {p['rental_yield']}% rental yield")
    if (p.get("school_rating") or 0) >= 8:
        r.append("Excellent schools")
    if (p.get("crime_score") or 0) >= 8:
        r.append("Low-crime area")
    if (p.get("appreciation_trend") or 0) >= 5:
        r.append("High appreciation history")
    if (p.get("days_on_market") or 0) <= 14:
        r.append("Fresh listing")
    return r or ["Priced near market value"]


# ------------------------------------------------------------------ full financial model (Module 6)
DEFAULT_ASSUMPTIONS = {
    "down_pct": 20.0,
    "interest_pct": 6.5,
    "loan_years": 30,
    "vacancy_pct": 5.0,
    "management_pct": 8.0,
    "maintenance_pct": 5.0,
    "insurance_annual": 1400.0,
    "closing_pct": 3.0,
}


def full_financials(p: dict, assumptions: dict[str, Any] | None = None) -> dict:
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    price = float(p.get("price") or 0)
    monthly_rent = float(p.get("rent_estimate") or heuristic_monthly_rent(price))
    gross_annual_rent = monthly_rent * 12

    vacancy = gross_annual_rent * a["vacancy_pct"] / 100
    management = gross_annual_rent * a["management_pct"] / 100
    maintenance = gross_annual_rent * a["maintenance_pct"] / 100
    taxes = float(p.get("taxes") or price * 0.02)
    insurance = a["insurance_annual"]
    hoa_annual = float(p.get("hoa") or 0) * 12

    operating_expenses = vacancy + management + maintenance + taxes + insurance + hoa_annual
    noi = gross_annual_rent - operating_expenses  # excludes mortgage

    mortgage_monthly = monthly_mortgage(price, a["down_pct"], a["interest_pct"], int(a["loan_years"]))
    annual_debt_service = mortgage_monthly * 12

    annual_cash_flow = noi - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12

    down_payment = price * a["down_pct"] / 100
    closing_costs = price * a["closing_pct"] / 100
    cash_invested = down_payment + closing_costs

    cap_rate = (noi / price * 100) if price else 0
    cash_on_cash = (annual_cash_flow / cash_invested * 100) if cash_invested else 0
    gross_yield = (gross_annual_rent / price * 100) if price else 0
    net_yield = (noi / price * 100) if price else 0

    # break-even occupancy: what fraction of rent covers expenses + debt
    total_annual_costs = operating_expenses + annual_debt_service
    break_even_occupancy = (total_annual_costs / gross_annual_rent * 100) if gross_annual_rent else 0

    return {
        "assumptions": a,
        "monthly_rent": rnd(monthly_rent, 0),
        "gross_annual_rent": rnd(gross_annual_rent, 0),
        "operating_expenses": rnd(operating_expenses, 0),
        "noi": rnd(noi, 0),
        "mortgage_monthly": rnd(mortgage_monthly, 0),
        "annual_debt_service": rnd(annual_debt_service, 0),
        "monthly_cash_flow": rnd(monthly_cash_flow, 0),
        "annual_cash_flow": rnd(annual_cash_flow, 0),
        "down_payment": rnd(down_payment, 0),
        "closing_costs": rnd(closing_costs, 0),
        "cash_invested": rnd(cash_invested, 0),
        "cap_rate": rnd(cap_rate, 2),
        "cash_on_cash": rnd(cash_on_cash, 2),
        "gross_yield": rnd(gross_yield, 2),
        "net_yield": rnd(net_yield, 2),
        "break_even_occupancy": rnd(break_even_occupancy, 1),
    }


# ------------------------------------------------------------------ pipeline
def analyze_properties(raw: Iterable[dict]) -> list[dict]:
    """Enrich a batch of raw property dicts with analytics (blended benchmark)."""
    items = [dict(p) for p in raw]
    for p in items:
        p["price_per_sqft"] = price_per_sqft(p.get("price"), p.get("sqft"))

    avg_by_zip = neighborhood_averages(items)
    counts: dict[str, int] = {}
    for p in items:
        key = p.get("zip") or p.get("city") or "all"
        counts[key] = counts.get(key, 0) + 1
    all_ppsf = [p["price_per_sqft"] for p in items if p["price_per_sqft"]]
    city_avg = rnd(sum(all_ppsf) / len(all_ppsf), 2) if all_ppsf else 0

    out: list[dict] = []
    for p in items:
        key = p.get("zip") or p.get("city") or "all"
        benchmark = avg_by_zip[key] if counts.get(key, 0) >= 3 else city_avg
        p["neighborhood_avg_ppsf"] = benchmark
        p["undervalued_pct"] = undervalued_pct(p["price_per_sqft"], benchmark)

        monthly_rent = p.get("rent_estimate") or heuristic_monthly_rent(p.get("price"))
        p["rent_estimate"] = monthly_rent
        p["rental_yield"] = rental_yield(monthly_rent * 12, p.get("price"))

        p["investment_score"] = investment_score(p)["score"]
        p["predicted_value_3yr"] = predict_value(p.get("price_history"), p.get("price"))["predicted"]
        out.append(p)
    return out
