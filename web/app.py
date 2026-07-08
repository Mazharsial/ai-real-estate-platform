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

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
