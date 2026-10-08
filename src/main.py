from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .api.middleware import CorrelationIdMiddleware, error_response
from .config import SERVICE_NAME, API_VERSION

app = FastAPI(
    title="Smart File Backup System - Team B Engine",
    description="Deduplication & Integrity Engine (Chunking, Hash Indexing, Deduplication, Merkle Trees, Telemetry)",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID Middleware
app.add_middleware(CorrelationIdMiddleware)

# Exception handlers for standard error envelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    corr_id = getattr(request.state, "correlation_id", "")
    details = [{"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"], "code": err["type"]} for err in exc.errors()]
    return error_response(
        code="INVALID_ARGUMENT",
        message="Request payload validation failed",
        details=details,
        status_code=422,
        correlation_id=corr_id
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    corr_id = getattr(request.state, "correlation_id", "")
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message=str(exc),
        status_code=500,
        correlation_id=corr_id
    )

# Include routes
app.include_router(router)
