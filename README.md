# 🏢 AI Real Estate Platform

Enterprise **AI Real Estate Deal Analyzer, Property Finder & Investment Advisor** — a
production-structured platform built in **Python** with **FastAPI** (backend) and
**Flask + Jinja2 + Bootstrap 5** (frontend), **PostgreSQL**, and a **configurable AI provider**
(Gemini / Ollama / OpenRouter / OpenAI). Uses only free/open resources.

> **Status: Session 9 — all 15 modules + admin/export/CI + AI Chatbot, NL search, nearby maps, password reset, email alerts & CSRF/upload hardening (complete & tested, 55 passing tests).**
> This is being built module-by-module. See the [roadmap](#-module-roadmap) for what's done and next.

---

## ✅ What works today (Session 1)

- **Auth (Module 1)** — register / login / JWT / roles (admin, investor, agent, guest), password hashing,
  **password reset** (email a time-limited, single-use reset link; token bound to the current password hash).
- **Property discovery (Module 2)** — search by city, budget, beds, type; pagination.
- **Data ingestion (Module 3, adapter)** — RentCast free tier with automatic demo-data fallback (swap-in point).
- **Analyzer + Financial engine (Modules 5 & 6)** — price/sqft, undervalued %, investment score (0–100),
  rental yield, mortgage, NOI, **cap rate, cash-on-cash, gross/net yield, closing costs, break-even, cash flow**,
  3-year appreciation forecast.
- **AI Investment Advisor (Module 8)** — summary, pros, cons, risks, recommendation, suggested offer
  (configurable AI provider, with a deterministic rules fallback).
- **AI Chatbot + Natural-Language Search** — ask in plain English ("3-bedroom houses under $150k with high
  rental yield", "which city has the highest rental yield?"). A deterministic NL parser turns the question
  into structured filters, retrieves the matching properties, and the AI answers grounded on that real data
  (works fully offline via rules fallback). Endpoints: `POST /api/assistant/search`, `POST /api/assistant/chat`;
  UI at `/assistant`.
- **Favorites & saved searches (Module 11)** — save/list/remove; **email alerts** — the daily scan emails
  each user whose alert-enabled saved search matches new deals (free via Gmail SMTP; skipped cleanly when
  SMTP isn't set).
- **REST API + Swagger** — interactive docs at `/docs`, ReDoc at `/redoc`, OpenAPI JSON at `/openapi.json`.
- **Flask UI** — dashboard (search, stat tiles, ranked deal cards, Leaflet/OSM map),
  property detail (financial table, AI advice, Chart.js score breakdown, map), login/register.
- **Nearby search (Module 4)** — each property detail page maps nearby schools, hospitals, restaurants,
  groceries, banks, parks, gyms & transit with straight-line distances, via **OpenStreetMap Overpass** (free,
  no key; multi-mirror fallback, graceful when offline). Endpoint: `GET /api/properties/{id}/nearby`.
- **Security** — CSRF protection on all Flask forms (session token, constant-time compare); secure CSV
  upload (extension + content-type + 5 MB size cap).
- **Tests** — 55 passing unit + integration tests (pytest).
- **Docker Compose**, **Alembic** scaffold, **seed script**.

---

## 🧰 Tech stack

| Layer | Tech |
|---|---|
| Backend API | Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PyJWT · Passlib |
| Frontend | Flask · Jinja2 · Bootstrap 5 · Leaflet/OpenStreetMap · Chart.js |
| Database | PostgreSQL (SQLite supported for quick dev/tests) |
| Migrations | Alembic |
| AI | Configurable: Gemini · Ollama · OpenRouter · OpenAI-compatible |
| Data | RentCast free tier + built-in demo dataset |
| Infra | Docker · Docker Compose · Gunicorn · Uvicorn |

---

## 🚀 Quickstart

### Option A — Docker (recommended)
```bash
cp .env.example .env          # then set GEMINI_API_KEY etc.
docker compose up --build
# API   -> http://localhost:8000/docs
# Web   -> http://localhost:5001
```

### Option B — Local (Python 3.11+)
```bash
python -m venv .venv && . .venv/Scripts/activate   # (Linux/mac: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL (Postgres) + GEMINI_API_KEY

# terminal 1 — API
uvicorn app.main:app --reload --port 8000

# terminal 2 — Flask UI
python -m flask --app web/app.py run --port 5001

# optional — seed an admin user + demo data
python scripts/seed.py        # admin@platform.com / admin12345
```

> No API keys? It still runs: the built-in **demo dataset** powers everything, and the AI advisor
> falls back to a deterministic rules engine when no AI key is set.

---

## 🔌 Configuration (`.env`)

Key settings (see `.env.example` for all):

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres DSN (or `sqlite:///./dev.db`) |
| `SECRET_KEY` | JWT signing secret |
| `AI_PROVIDER` | `gemini` \| `ollama` \| `openrouter` \| `openai` |
| `GEMINI_API_KEY` | free key from aistudio.google.com |
| `RENTCAST_API_KEY` | optional free listings API (blank ⇒ demo data) |
| `API_BASE_URL` | Flask → FastAPI URL |

---

## 🧪 Tests
```bash
pytest -q          # 15 tests: analysis math, auth flow, property API, favorites
```
Tests use an isolated SQLite DB and disable external AI for determinism.

---

## 🗄️ Database migrations (Alembic)
```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```
(For local dev the app auto-creates tables on startup; production should use migrations.)

---

## 📚 Key API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account → JWT |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/properties/search` | Search + analyze + rank |
| GET | `/api/properties` | List ranked (pagination) |
| GET | `/api/properties/{id}` | Property detail |
| POST | `/api/properties/{id}/analyze` | Full financial analysis |
| GET | `/api/properties/{id}/advice` | AI investment advice |
| POST | `/api/assistant/search` | Natural-language search → filtered, ranked properties |
| POST | `/api/assistant/chat` | Ask the AI chatbot → grounded answer + relevant listings |
| GET | `/api/properties/{id}/nearby` | Nearby amenities (schools/hospitals/transit/…) via OpenStreetMap |
| GET/POST/DELETE | `/api/favorites` | Manage favorites (auth) |
| GET | `/health` | Service + AI/data status |

Full interactive reference: **`/docs`**.

---

## 🗂️ Project structure

```
app/                     # FastAPI backend
  core/                  # config, database, security
  models/                # SQLAlchemy models (User, Property, Favorite, SavedSearch, AuditLog, ...)
  schemas/               # Pydantic request/response models
  services/              # business logic
    analysis.py          # analyzer + financial engine (Modules 5 & 6)
    property_service.py   # fetch → analyze → persist → query (repository)
    data_sources/        # rentcast adapter + demo dataset (Module 3 swap point)
    ai/                  # configurable provider + investment advisor (Module 8)
  api/                   # routers + auth dependencies
  main.py                # app factory
web/                     # Flask + Jinja2 + Bootstrap frontend
  app.py, templates/, static/
alembic/                 # migrations
scripts/seed.py          # admin + demo data
tests/                   # pytest suite
Dockerfile.api · Dockerfile.web · docker-compose.yml
```

---

## 🧭 Module roadmap

| Module | Status |
|---|---|
| 1. User Management (auth, roles, JWT) | ✅ done |
| 2. Property Discovery (search) | ✅ done |
| 3. Data ingestion (adapter + demo) | ✅ adapter (scrapers/open-data next) |
| 5. Property Analyzer | ✅ done |
| 6. Financial Calculator | ✅ done |
| 8. AI Investment Advisor | ✅ done |
| AI Chatbot + Natural-Language / semantic search | ✅ done |
| 11. Saved searches / favorites + email alerts | ✅ done |
| Password reset (email link) | ✅ done |
| 4. Maps (dashboard + detail + nearby amenities) | ✅ done |
| 7. Market Analysis | ✅ done |
| 9. Deal Finder (categories) | ✅ done |
| 10. Property Comparison | ✅ done |
| 12. PDF Investment Reports | ✅ done |
| 13. Analytics Dashboard | ✅ done |
| 14. Portfolio Manager | ✅ done |
| Admin panel (users, roles, stats) | ✅ done |
| CSV / Excel / JSON export | ✅ done |
| 15. Automation (n8n daily scan + alerts) | ✅ done |
| Security: rate limiting, headers, audit log, CSRF, secure uploads | ✅ done |
| CI/CD (GitHub Actions) · CSV import | ✅ done |

---

## 🔒 Security notes
- Passwords hashed with `pbkdf2_sha256`; JWT bearer auth; role-based guards.
- **Rate limiting** (per-IP sliding window) + **security headers** middleware.
- **Audit logging** of auth events; admin-only endpoints for user management.
- Secrets via environment only (`.env` gitignored). Pydantic validation on all inputs.
- SQLAlchemy ORM (parameterized) prevents SQL injection; Jinja2 autoescaping mitigates XSS.
- **CSRF protection** on every Flask form (per-session token, constant-time compare via `hmac`).
- **Secure uploads** — CSV import validates extension + content-type and caps size at 5 MB.

## ⚠️ Disclaimer
Estimates and AI output are for research/education only — **not financial advice**. Respect all
data-provider terms of service; the ingestion layer is designed to swap providers cleanly.
