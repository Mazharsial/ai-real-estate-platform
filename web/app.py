"""Flask + Jinja2 frontend. Consumes the FastAPI backend over HTTP."""
from __future__ import annotations

import os

import httpx
from flask import Flask, flash, redirect, render_template, request, session, url_for

API = os.environ.get("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 45


def _api(method: str, path: str, *, json=None, auth=False):
    headers = {}
    if auth and session.get("token"):
        headers["Authorization"] = f"Bearer {session['token']}"
    url = f"{API}{path}"
    r = httpx.request(method, url, json=json, headers=headers, timeout=TIMEOUT)
    return r


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    @app.context_processor
    def inject_globals():
        return {"current_user": session.get("user"), "api_base": API}

    @app.template_filter("money")
    def money(v):
        try:
            return "${:,.0f}".format(float(v or 0))
        except (TypeError, ValueError):
            return "$0"

    @app.route("/")
    def index():
        criteria = {}
        if request.args.get("city"):
            criteria["city"] = request.args["city"]
        if request.args.get("max_price"):
            criteria["max_price"] = float(request.args["max_price"])
        if request.args.get("min_beds"):
            criteria["min_beds"] = int(request.args["min_beds"])
        if request.args.get("property_type") and request.args["property_type"] != "Any":
            criteria["property_type"] = request.args["property_type"]

        props, source, note = [], None, None
        try:
            data = _api("POST", "/api/properties/search", json=criteria or {}).json()
            props = data.get("properties", [])
            source = data.get("source")
            note = data.get("note")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not reach the API: {exc}", "danger")

        stats = None
        if props:
            stats = {
                "count": len(props),
                "avg_score": round(sum(p["investment_score"] for p in props) / len(props)),
                "deals": sum(1 for p in props if (p.get("undervalued_pct") or 0) >= 8),
                "avg_ppsf": round(sum(p["price_per_sqft"] for p in props) / len(props)),
            }
        return render_template("index.html", props=props, source=source, note=note,
                               criteria=request.args, stats=stats)

    @app.route("/property/<int:pid>")
    def detail(pid: int):
        try:
            p = _api("GET", f"/api/properties/{pid}").json()
            analysis = _api("POST", f"/api/properties/{pid}/analyze", json={}).json()
            advice = _api("GET", f"/api/properties/{pid}/advice").json().get("advice")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load property: {exc}", "danger")
            return redirect(url_for("index"))
        return render_template("property_detail.html", p=p, analysis=analysis, advice=advice)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                r = _api("POST", "/api/auth/login",
                         json={"email": request.form["email"], "password": request.form["password"]})
                if r.status_code == 200:
                    body = r.json()
                    session["token"] = body["access_token"]
                    session["user"] = body["user"]
                    flash("Welcome back!", "success")
                    return redirect(url_for("index"))
                flash(r.json().get("detail", "Login failed"), "danger")
            except Exception as exc:  # noqa: BLE001
                flash(f"API error: {exc}", "danger")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            try:
                r = _api("POST", "/api/auth/register", json={
                    "email": request.form["email"],
                    "password": request.form["password"],
                    "full_name": request.form.get("full_name", ""),
                })
                if r.status_code == 201:
                    body = r.json()
                    session["token"] = body["access_token"]
                    session["user"] = body["user"]
                    flash("Account created!", "success")
                    return redirect(url_for("index"))
                flash(r.json().get("detail", "Registration failed"), "danger")
            except Exception as exc:  # noqa: BLE001
                flash(f"API error: {exc}", "danger")
        return render_template("register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Signed out.", "info")
        return redirect(url_for("index"))

    @app.route("/favorites", methods=["POST"])
    def toggle_favorite():
        pid = request.form.get("pid")
        if not session.get("token"):
            flash("Please sign in to save favorites.", "warning")
            return redirect(url_for("login"))
        try:
            _api("POST", f"/api/favorites/{pid}", auth=True)
            flash("Saved to favorites.", "success")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not save: {exc}", "danger")
        return redirect(request.referrer or url_for("index"))

    @app.route("/deals")
    def deals():
        city = request.args.get("city", "Dallas")
        data = {"categories": []}
        try:
            data = _api("GET", f"/api/deals?city={city}").json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load deals: {exc}", "danger")
        return render_template("deals.html", data=data, city=city)

    @app.route("/market")
    def market():
        city = request.args.get("city", "Dallas")
        m = None
        try:
            m = _api("GET", f"/api/market/overview?city={city}").json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load market data: {exc}", "danger")
        return render_template("market.html", m=m, city=city)

    @app.route("/compare")
    def compare():
        ids = [int(i) for i in request.args.getlist("ids") if str(i).isdigit()]
        all_props, result = [], None
        try:
            all_props = _api("GET", "/api/properties?limit=100").json()
            if len(ids) >= 2:
                result = _api("POST", "/api/comparison", json={"ids": ids}).json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Comparison error: {exc}", "danger")
        return render_template("compare.html", all_props=all_props, result=result, selected=ids)

    @app.route("/analytics")
    def analytics():
        city = request.args.get("city", "Dallas")
        a = None
        try:
            a = _api("GET", f"/api/analytics/summary?city={city}").json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load analytics: {exc}", "danger")
        return render_template("analytics.html", a=a, city=city)

    @app.route("/save-search", methods=["POST"])
    def save_search():
        if not session.get("token"):
            flash("Please sign in to save searches.", "warning")
            return redirect(url_for("login"))
        filters = {}
        for k in ("city", "max_price", "min_beds", "property_type"):
            v = request.form.get(k)
            if v and v != "Any":
                filters[k] = float(v) if k == "max_price" else int(v) if k == "min_beds" else v
        name = request.form.get("name") or f"{filters.get('city', 'All')} search"
        try:
            _api("POST", "/api/saved-searches",
                 json={"name": name, "filters": filters, "alert_enabled": False}, auth=True)
            flash("Search saved.", "success")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not save: {exc}", "danger")
        return redirect(request.referrer or url_for("index"))

    @app.route("/saved")
    def saved():
        if not session.get("token"):
            flash("Please sign in to view saved searches.", "warning")
            return redirect(url_for("login"))
        rows = []
        try:
            rows = _api("GET", "/api/saved-searches", auth=True).json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load saved searches: {exc}", "danger")
        return render_template("saved.html", rows=rows)

    @app.route("/saved/<int:sid>/delete", methods=["POST"])
    def delete_saved(sid: int):
        try:
            _api("DELETE", f"/api/saved-searches/{sid}", auth=True)
            flash("Saved search removed.", "info")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not delete: {exc}", "danger")
        return redirect(url_for("saved"))

    @app.route("/portfolio")
    def portfolio():
        if not session.get("token"):
            flash("Please sign in to view your portfolio.", "warning")
            return redirect(url_for("login"))
        data = None
        try:
            data = _api("GET", "/api/portfolio", auth=True).json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load portfolio: {exc}", "danger")
        return render_template("portfolio.html", data=data)

    @app.route("/portfolio/add", methods=["POST"])
    def portfolio_add():
        if not session.get("token"):
            return redirect(url_for("login"))

        def num(k):
            v = request.form.get(k)
            return float(v) if v else 0

        payload = {
            "address": request.form.get("address", ""), "city": request.form.get("city", ""),
            "property_type": request.form.get("property_type", "House"),
            "purchase_price": num("purchase_price"), "current_value": num("current_value"),
            "monthly_rent": num("monthly_rent"), "monthly_expenses": num("monthly_expenses"),
            "mortgage_balance": num("mortgage_balance"),
            "purchase_date": request.form.get("purchase_date") or None,
        }
        try:
            _api("POST", "/api/portfolio", json=payload, auth=True)
            flash("Property added to your portfolio.", "success")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not add: {exc}", "danger")
        return redirect(url_for("portfolio"))

    @app.route("/portfolio/<int:hid>/delete", methods=["POST"])
    def portfolio_delete(hid: int):
        try:
            _api("DELETE", f"/api/portfolio/{hid}", auth=True)
            flash("Removed from portfolio.", "info")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not remove: {exc}", "danger")
        return redirect(url_for("portfolio"))

    @app.route("/admin")
    def admin():
        if (session.get("user") or {}).get("role") != "admin":
            flash("Admin access only.", "warning")
            return redirect(url_for("index"))
        stats = users = None
        try:
            stats = _api("GET", "/api/admin/stats", auth=True).json()
            users = _api("GET", "/api/admin/users", auth=True).json()
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load admin data: {exc}", "danger")
        return render_template("admin.html", stats=stats, users=users)

    @app.route("/admin/users/<int:uid>", methods=["POST"])
    def admin_user(uid: int):
        if (session.get("user") or {}).get("role") != "admin":
            return redirect(url_for("index"))
        body = {"role": request.form.get("role"), "is_active": bool(request.form.get("is_active"))}
        try:
            _api("PATCH", f"/api/admin/users/{uid}", json=body, auth=True)
            flash("User updated.", "success")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not update user: {exc}", "danger")
        return redirect(url_for("admin"))

    @app.route("/alerts")
    def alerts():
        city = request.args.get("city", "Dallas")
        scan, alist = None, []
        try:
            if request.args.get("scan"):
                scan = _api("GET", f"/api/monitor/scan?city={city}").json()
            alist = _api("GET", "/api/monitor/alerts").json().get("alerts", [])
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not load alerts: {exc}", "danger")
        return render_template("alerts.html", alerts=alist, scan=scan, city=city)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
