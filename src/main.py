"""
Main FastAPI Application Entry Point for Returns Manager.
Includes health check, tenant API routers, CORS, and full demo UI dashboard.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.config import get_settings
from src.database.connection import init_db
from src.ingestion.router import router as returns_router
from src.ui_template import DASHBOARD_HTML


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    try:
        init_db()
    except Exception as e:
        print(f"Lifespan DB initialization notice: {e}")
    yield


settings = get_settings()

app = FastAPI(
    title="Cube Buildathon 04 — Returns Manager",
    description="Production-style Returns Manager Agent for Amazon FBA & merchant returns inspection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(returns_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "cube-04-returns-manager",
        "gemini_model": settings.gemini_model,
        "environment": settings.app_env,
    }


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def serve_ui():
    """Serves the complete interactive Returns Manager Operator Dashboard directly."""
    return HTMLResponse(content=DASHBOARD_HTML)
