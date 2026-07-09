"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routers import (
    admin,
    analytics,
    assistant,
    auth,
    comparison,
    deals,
    export,
    favorites,
    health,
    import_data,
    market,
    monitor,
    portfolio,
    properties,
    saved_searches,
)
from app.core.config import settings
from app.core.database import init_db
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Production uses Alembic migrations.
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Enterprise AI Real Estate Deal Analyzer, Property Finder & Investment Advisor.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(properties.router)
    app.include_router(favorites.router)
    app.include_router(deals.router)
    app.include_router(comparison.router)
    app.include_router(market.router)
    app.include_router(analytics.router)
    app.include_router(saved_searches.router)
    app.include_router(portfolio.router)
    app.include_router(export.router)
    app.include_router(admin.router)
    app.include_router(monitor.router)
    app.include_router(import_data.router)
    app.include_router(assistant.router)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {"app": settings.APP_NAME, "version": __version__, "docs": "/docs"}

    return app


app = create_app()
