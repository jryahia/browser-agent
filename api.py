#!/usr/bin/env python3
"""BrowserBot API Server — FastAPI entry point."""

import argparse
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.server.api import router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BrowserBot API",
    description="Autonomous browser agent — submit tasks and get results",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "BrowserBot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "POST /api/v1/tasks": "Submit a new task",
            "GET /api/v1/tasks": "List all tasks",
            "GET /api/v1/tasks/{id}": "Get task status",
            "GET /api/v1/tasks/{id}/result": "Get task result",
            "GET /api/v1/health": "Health check",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Start BrowserBot API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    logger.info("BrowserBot API Server running on http://%s:%s", args.host, args.port)
    logger.info("API docs at http://%s:%s/docs", args.host, args.port)

    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
