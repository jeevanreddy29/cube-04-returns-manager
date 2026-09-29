"""
Vercel Serverless Function entry point.
Exposes the FastAPI application to Vercel's Python runtime.
Ensures SQLite DB tables and directories exist in /tmp on invocation.
"""
import sys
import os

# Ensure project root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set VERCEL environment flag
os.environ["VERCEL"] = "1"

# Prepare /tmp storage directory
os.makedirs("/tmp/storage/images", exist_ok=True)

from src.database.connection import init_db
from src.main import app

# Initialize DB on cold start
try:
    init_db()
except Exception as e:
    print(f"Database initialization note: {e}")
