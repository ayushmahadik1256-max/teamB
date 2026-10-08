from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

T = TypeVar("T")

class MetaEnvelope(BaseModel):
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_version: str = "v1"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SuccessResponse(BaseModel, Generic[T]):
    data: T
    meta: MetaEnvelope = Field(default_factory=MetaEnvelope)

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorBody(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    error: ErrorBody
    meta: MetaEnvelope = Field(default_factory=MetaEnvelope)
