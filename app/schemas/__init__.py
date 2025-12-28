"""Pydantic schemas module."""
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
)
from app.schemas.common import (
    AsyncTaskResponse,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentStatusUpdate,
)
from app.schemas.flashcard import (
    FlashcardRead,
    FlashcardReviewInput,
    FlashcardReviewResponse,
)
from app.schemas.note import NoteCreate, NoteRead
from app.schemas.user import UserCreate, UserRead
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "ErrorResponse",
    "MessageResponse",
    "AsyncTaskResponse",
    # User
    "UserCreate",
    "UserRead",
    # Workspace
    "WorkspaceCreate",
    "WorkspaceRead",
    # Document
    "DocumentCreate",
    "DocumentRead",
    "DocumentStatusUpdate",
    # Note
    "NoteCreate",
    "NoteRead",
    # Flashcard
    "FlashcardRead",
    "FlashcardReviewInput",
    "FlashcardReviewResponse",
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatStreamChunk",
]
