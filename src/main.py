"""
Main FastAPI Application Entry Point for Returns Manager.
Includes health check, tenant API routers, CORS, and static demo UI serving.
"""
from __future__ import annotations

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from src.config import get_settings
from src.database.connection import init_db
from src.ingestion.router import router as returns_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
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


# Resolve UI index.html path reliably in local and serverless environments
BASE_DIR = Path(__file__).resolve().parent.parent
UI_INDEX_PATH = BASE_DIR / "ui" / "public" / "index.html"


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def serve_ui():
    if UI_INDEX_PATH.exists():
        with open(UI_INDEX_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="""
        <html>
            <body style="font-family:sans-serif; padding:2rem; text-align:center;">
                <h2>Cube 04 — Returns Manager API Active</h2>
                <p>Visit <a href="/docs">/docs</a> for interactive OpenAPI Swagger documentation.</p>
            </body>
        </html>
        """
    )
