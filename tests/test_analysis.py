"""Unit tests for the analysis & financial engine (no DB, no network)."""
from app.services import analysis as A


def test_price_per_sqft():
    assert A.price_per_sqft(450000, 2000) == 225.0
    assert A.price_per_sqft(0, 2000) == 0.0


def test_undervalued_pct():
    assert A.undervalued_pct(180, 225) == 20.0
    assert A.undervalued_pct(225, 225) == 0.0


def test_monthly_mortgage_known_value():
    # $300k loan (after 20% down on $375k), 6% / 30y ≈ $1,798
    m = A.monthly_mortgage(375000, 20, 6, 30)
    assert 1780 <= m <= 1815


def test_investment_score_bounds_and_weighting():
    great = {"undervalued_pct": 30, "rental_yield": 10, "school_rating": 10,
             "crime_score": 10, "appreciation_trend": 8, "days_on_market": 0}
    poor = {"undervalued_pct": -20, "rental_yield": 1, "school_rating": 2,
            "crime_score": 3, "appreciation_trend": 1, "days_on_market": 90}
    assert A.investment_score(great)["score"] == 100
    assert A.investment_score(poor)["score"] < 40


def test_full_financials_shape_and_signs():
    p = {"price": 350000, "rent_estimate": 2500, "taxes": 7000, "hoa": 0}
    fin = A.full_financials(p)
    for k in ["noi", "cap_rate", "cash_on_cash", "gross_yield", "monthly_cash_flow", "closing_costs"]:
        assert k in fin
    assert fin["gross_annual_rent"] == 30000
    assert fin["cap_rate"] > 0


def test_analyze_properties_blended_benchmark():
    raw = [
        {"external_id": "a", "zip": "1", "city": "X", "price": 200000, "sqft": 2000},
        {"external_id": "b", "zip": "2", "city": "X", "price": 400000, "sqft": 2000},
        {"external_id": "c", "zip": "3", "city": "X", "price": 300000, "sqft": 2000},
    ]
    out = A.analyze_properties(raw)
    # cheapest per-sqft should be flagged most undervalued and score highest
    out_sorted = sorted(out, key=lambda x: x["investment_score"], reverse=True)
    assert out_sorted[0]["price"] == 200000
    assert out_sorted[0]["undervalued_pct"] > 0
