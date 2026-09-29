"""
Vercel Serverless Function entry point.
Exposes the FastAPI application to Vercel's Python runtime.
"""
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
