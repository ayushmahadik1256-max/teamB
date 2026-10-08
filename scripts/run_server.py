#!/usr/bin/env python3
"""
Server runner for Team B FastAPI Application.
"""
import sys
import os
import uvicorn

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Team B Deduplication & Integrity Engine on http://{host}:{port}")
    uvicorn.run("src.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
