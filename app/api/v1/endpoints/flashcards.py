"""Flashcard endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.flashcard import FlashcardRead, FlashcardReviewInput, FlashcardReviewResponse
from app.services.flashcard_service import FlashcardService

router = APIRouter()


@router.get(
    "/flashcards",
    response_model=list[FlashcardRead],
    responses={500: {"model": ErrorResponse}},
    summary="List flashcards",
)
async def list_flashcards(
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_id: Annotated[uuid.UUID | None, Query(description="Workspace ID")] = None,
    document_id: Annotated[uuid.UUID | None, Query(description="Filter by document ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[FlashcardRead]:
    """List flashcards for the authenticated user, optionally filtered by workspace and/or document.
    
    If only document_id is provided, workspace_id will be inferred from the document.
    At least one of workspace_id or document_id must be provided.
    """
    try:
        from sqlalchemy import select
        from app.models.flashcard import Flashcard
        from app.models.document import Document
        
        # If only document_id is provided, fetch the document to get workspace_id
        # Also verify user has access to the document/workspace
        resolved_workspace_id = workspace_id
        if not resolved_workspace_id and document_id:
            doc_stmt = select(Document).where(Document.id == document_id)
            doc_result = await db.execute(doc_stmt)
            document = doc_result.scalar_one_or_none()
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
            resolved_workspace_id = document.workspace_id
            
            # Verify user has access to this document's workspace
            # Check if user owns the document
            if document.user_id == current_user.id:
                pass  # User owns document, has access
            else:
                # Check if user owns the workspace
                from app.models.workspace import Workspace
                workspace_stmt = select(Workspace).where(Workspace.id == resolved_workspace_id)
                workspace_result = await db.execute(workspace_stmt)
                workspace = workspace_result.scalar_one_or_none()
                if workspace and workspace.owner_id == current_user.id:
                    pass  # User owns workspace, has access
                else:
                    # Check if user is a workspace member
                    from app.models.workspace_membership import WorkspaceMembership
                    membership_stmt = select(WorkspaceMembership).where(
                        (WorkspaceMembership.workspace_id == resolved_workspace_id) &
                        (WorkspaceMembership.user_id == current_user.id)
                    )
                    membership_result = await db.execute(membership_stmt)
                    if not membership_result.scalar_one_or_none():
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="You don't have permission to access flashcards for this document"
                        )
        elif not resolved_workspace_id:
            raise HTTPException(
                status_code=400,
                detail="Either workspace_id or document_id must be provided"
            )
        else:
            # workspace_id provided - verify user has access to the workspace
            from app.models.workspace import Workspace
            workspace_stmt = select(Workspace).where(Workspace.id == resolved_workspace_id)
            workspace_result = await db.execute(workspace_stmt)
            workspace = workspace_result.scalar_one_or_none()
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {resolved_workspace_id} not found")
            
            # Check if user owns the workspace
            if workspace.owner_id != current_user.id:
                # Check if user is a workspace member
                from app.models.workspace_membership import WorkspaceMembership
                membership_stmt = select(WorkspaceMembership).where(
                    (WorkspaceMembership.workspace_id == resolved_workspace_id) &
                    (WorkspaceMembership.user_id == current_user.id)
                )
                membership_result = await db.execute(membership_stmt)
                if not membership_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to access flashcards in this workspace"
                    )
        
        # Only show flashcards for the authenticated user
        stmt = select(Flashcard).where(
            Flashcard.workspace_id == resolved_workspace_id,
            Flashcard.user_id == current_user.id
        )
        if document_id:
            stmt = stmt.where(Flashcard.document_id == document_id)
        stmt = stmt.limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        flashcards = list(result.scalars().all())
        return [FlashcardRead.model_validate(f) for f in flashcards]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing flashcards: {str(e)}")


@router.get(
    "/flashcards/{flashcard_id}",
    response_model=FlashcardRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get a flashcard",
)
async def get_flashcard(
    flashcard_id: Annotated[uuid.UUID, Path(description="Flashcard ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlashcardRead:
    """Get a flashcard by ID. Only accessible by the flashcard owner."""
    try:
        from sqlalchemy import select
        from app.models.flashcard import Flashcard
        
        stmt = select(Flashcard).where(Flashcard.id == flashcard_id)
        result = await db.execute(stmt)
        flashcard = result.scalar_one_or_none()
        if not flashcard:
            raise HTTPException(status_code=404, detail=f"Flashcard {flashcard_id} not found")
        
        # Authorization check: ensure user owns the flashcard
        if flashcard.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this flashcard"
            )
        
        return FlashcardRead.model_validate(flashcard)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting flashcard: {str(e)}")


@router.get(
    "/flashcards/due",
    response_model=list[FlashcardRead],
    responses={500: {"model": ErrorResponse}},
    summary="Get due flashcards",
)
async def get_due_flashcards(
    workspace_id: Annotated[uuid.UUID, Query(description="Workspace ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 20,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[FlashcardRead]:
    """Get flashcards due for review for the authenticated user."""
    try:
        service = FlashcardService(db)
        flashcards = await service.get_due_flashcards(
            user_id=current_user.id,
            workspace_id=workspace_id,
            limit=limit,
        )
        return [FlashcardRead.model_validate(f) for f in flashcards]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting due flashcards: {str(e)}")


class FlashcardReviewRequest(BaseModel):
    """Request body for reviewing a flashcard."""
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    grade: int = Field(ge=0, le=4, description="Grade: 0=Again, 1=Hard, 2=Good, 3=Easy, 4=Perfect")
    response_time_ms: int | None = Field(default=None, ge=0, description="Response time in milliseconds")


@router.post(
    "/flashcards/{flashcard_id}/review",
    response_model=FlashcardReviewResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Review a flashcard",
    description="Record a flashcard review and update SRS state. By default, prevents reviewing cards that are not due yet or within cooldown period. Use force=true to bypass these checks.",
)
async def review_flashcard(
    flashcard_id: Annotated[uuid.UUID, Path(description="Flashcard ID")],
    request: FlashcardReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: Annotated[bool, Query(description="Bypass due check and cooldown")] = False,
) -> FlashcardReviewResponse:
    """Record a flashcard review and update SRS state. Only accessible by the flashcard owner."""
    try:
        # Verify user owns the flashcard
        from sqlalchemy import select
        from app.models.flashcard import Flashcard
        
        stmt = select(Flashcard).where(Flashcard.id == flashcard_id)
        result = await db.execute(stmt)
        flashcard = result.scalar_one_or_none()
        if not flashcard:
            raise HTTPException(status_code=404, detail=f"Flashcard {flashcard_id} not found")
        
        if flashcard.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to review this flashcard"
            )
        
        service = FlashcardService(db)
        review, srs_state = await service.record_review(
            flashcard_id=flashcard_id,
            user_id=current_user.id,
            grade=request.grade,
            response_time_ms=request.response_time_ms,
            force=force,
        )
        
        # Use due_at from SRS state (already calculated correctly)
        next_due_at = srs_state.due_at if srs_state else None
        
        return FlashcardReviewResponse(
            review_id=review.id,
            flashcard_id=flashcard_id,
            next_review_due=next_due_at,
            interval_days=srs_state.interval_days if srs_state else None,
            ease_factor=srs_state.ease_factor if srs_state else None,
            reviewed_at=review.reviewed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording review: {str(e)}")

