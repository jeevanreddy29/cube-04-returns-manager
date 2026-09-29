"""
Main FastAPI Application Entry Point for Returns Manager.
Includes health check, tenant API routers, CORS, and static demo UI serving.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


# Static UI mount for lightweight standalone operation
ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui", "public")
if os.path.exists(ui_dir):
    app.mount("/static", StaticFiles(directory=ui_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_ui():
        index_file = os.path.join(ui_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Returns Manager API Active. Visit /docs for Swagger."}
