import uuid
from datetime import datetime, timezone
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..models.contracts import MetaEnvelope

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a valid X-Correlation-ID header,
    propagating it through request processing and outgoing response.
    """
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = str(uuid.uuid4())
        request.state.correlation_id = corr_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-API-Version"] = "v1"
        return response

def build_meta(request: Request) -> MetaEnvelope:
    corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return MetaEnvelope(
        correlation_id=corr_id,
        api_version="v1",
        timestamp=datetime.now(timezone.utc).isoformat()
    )

def error_response(code: str, message: str, details=None, status_code: int = 400, correlation_id: str = ""):
    meta = {
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "api_version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or []
            },
            "meta": meta
        }
    )
