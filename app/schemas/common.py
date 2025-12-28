"""Common schemas for pagination and error responses."""
import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T] = Field(description="List of items in current page")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(description="Error message")
    detail: str | None = Field(default=None, description="Detailed error information")
    code: str | None = Field(default=None, description="Error code")

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str = Field(description="Response message")

    model_config = ConfigDict(from_attributes=True)


class AsyncTaskResponse(BaseModel):
    """Response for async task submission."""

    run_id: uuid.UUID = Field(description="Agent run ID")
    status: str = Field(description="Initial status (queued)")
    message: str = Field(description="Status message")

    model_config = ConfigDict(from_attributes=True)

