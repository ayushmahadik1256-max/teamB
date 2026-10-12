from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.routes import router
from datetime import datetime, timezone
import uuid

app = FastAPI(
    title="Smart File Backup System - Team A Engine",
    description="Backup Job Scheduler & Concurrency Locks (OS Engine)",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS Middleware with exposed headers for browser frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-API-Version", "Idempotency-Key"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    details = [{"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"], "code": err["type"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "INVALID_ARGUMENT", "message": "Request payload validation failed", "details": details},
            "meta": {"correlation_id": corr_id, "api_version": "v1", "timestamp": datetime.now(timezone.utc).isoformat()}
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    return JSONResponse(
        status_code=500,
        content={
            "error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc), "details": []},
            "meta": {"correlation_id": corr_id, "api_version": "v1", "timestamp": datetime.now(timezone.utc).isoformat()}
        }
    )

app.include_router(router)