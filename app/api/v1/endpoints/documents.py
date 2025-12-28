"""Document processing endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.router import AgentRouter
from app.agents.types import (
    FlashcardAgentInput,
    FlashcardAgentOutput,
    IngestionAgentInput,
    IngestionAgentOutput,
    KGExtractionAgentInput,
    KGExtractionAgentOutput,
    SummaryAgentInput,
    SummaryAgentOutput,
)
from app.api.dependencies import get_agent_router
from app.infrastructure.database import get_db
from app.schemas.common import AsyncTaskResponse, ErrorResponse
from app.schemas.document import DocumentCreate, DocumentRead
from app.services.agent_run_service import AgentRunService
from app.services.document_service import DocumentService
from app.tasks.agent_tasks import add_agent_task

router = APIRouter()


def get_request_id(x_request_id: Annotated[str | None, Header()] = None) -> str:
    """Extract or generate request ID."""
    import uuid as uuid_lib
    return x_request_id or str(uuid_lib.uuid4())


class CreateDocumentRequest(DocumentCreate):
    """Request body for creating a document (extends DocumentCreate with user_id)."""
    
    user_id: uuid.UUID = Field(description="User ID creating the document")


@router.post(
    "/documents",
    response_model=DocumentRead,
    responses={
        201: {"model": DocumentRead},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Create a new document",
    description="Create a new document in a workspace. Returns the created document with its ID.",
    status_code=201,
)
async def create_document(
    request: CreateDocumentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> DocumentRead:
    """Create a new document."""
    try:
        document_service = DocumentService(db)
        document = await document_service.create_document(
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            title=request.title,
            source_type=request.doc_type,
            source_uri=request.source_url,
            metadata=request.metadata,
        )
        
        # Store raw text if provided
        if request.content:
            document = await document_service.store_raw_text(document.id, request.content)
        
        return DocumentRead.model_validate(document)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating document [request_id={request_id}]: {str(e)}",
        )


class IngestDocumentRequest(BaseModel):
    """Request body for document ingestion."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    raw_text: str | None = Field(default=None, description="Optional raw text to store")


class GenerateFlashcardsRequest(BaseModel):
    """Request body for flashcard generation."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    mode: str = Field(default="key_terms", description="Generation mode: key_terms, qa, or cloze")


class ExtractKGRequest(BaseModel):
    """Request body for KG extraction."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")


# Rate limit placeholder
async def check_rate_limit(
    workspace_id: uuid.UUID, user_id: uuid.UUID, request_id: str
) -> None:
    """Placeholder for rate limiting logic.
    
    TODO: Implement actual rate limiting (e.g., using slowapi or redis)
    """
    # Placeholder: no-op for now
    pass


@router.post(
    "/documents/{document_id}/ingest",
    responses={
        200: {"model": IngestionAgentOutput},
        202: {"model": AsyncTaskResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},  # Conflict - ingestion already in progress
        500: {"model": ErrorResponse},
    },
    summary="Ingest and process a document",
    description="Process a document: chunk it and generate embeddings. Use async=true to run in background.",
)
async def ingest_document(
    document_id: Annotated[uuid.UUID, Path(description="Document ID to process")],
    request_body: IngestDocumentRequest,
    background_tasks: BackgroundTasks,
    async_mode: Annotated[bool, Query(description="Run in background")] = False,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    request_id: Annotated[str, Depends(get_request_id)] = None,
) -> IngestionAgentOutput | AsyncTaskResponse:
    """Ingest a document using IngestionAgent."""
    # Rate limit check (placeholder)
    await check_rate_limit(request_body.workspace_id, request_body.user_id, request_id)

    # Idempotency check: prevent duplicate ingestion runs
    document_service = DocumentService(db)
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check if ingestion is already in progress
    if document.status in ("storing", "chunking", "embedding"):
        raise HTTPException(
            status_code=409,
            detail=f"Ingestion already in progress for document {document_id}. Current status: {document.status}",
        )
    
    # Check for active agent runs for this document
    agent_run_service = AgentRunService(db)
    active_runs = await agent_run_service.get_active_runs(
        workspace_id=request_body.workspace_id,
        agent_name="ingestion",
        document_id=document_id,
    )
    if active_runs:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestion already queued/running for document {document_id}. Run ID: {active_runs[0].id}",
        )

    # Create input
    input_data = IngestionAgentInput(
        document_id=document_id,
        workspace_id=request_body.workspace_id,
        user_id=request_body.user_id,
        raw_text=request_body.raw_text,
    )

    # If async mode, create run and return immediately
    if async_mode:
        try:
            agent_run_service = AgentRunService(db)
            input_json = input_data.model_dump()
            agent_run = await agent_run_service.create_run(
                workspace_id=request_body.workspace_id,
                user_id=request_body.user_id,
                agent_name="ingestion",
                input_json=input_json,
                status="queued",
            )

            # Add to background tasks
            agent_router = AgentRouter(db)
            add_agent_task(
                background_tasks,
                "ingestion",
                agent_router.run_ingestion,
                input_data,
                agent_run.id,
                db,
            )

            return AsyncTaskResponse(
                run_id=agent_run.id,
                status="queued",
                message="Document ingestion queued. Check agent_runs table for status.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error queuing document ingestion [request_id={request_id}]: {str(e)}",
            )

    # Synchronous execution
    try:
        # Agent router provided via dependency (uses shared GraphRegistry)
        result = await agent_router.run_ingestion(input_data)

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log error with request ID
        import logging
        logger = logging.getLogger(__name__)
        error_str = str(e).lower()
        logger.error(f"Document ingestion failed [request_id={request_id}]: {str(e)}", exc_info=True)
        
        # Provide user-friendly error messages with "try again" guidance
        if "timeout" in error_str or "timed out" in error_str:
            error_msg = (
                f"Request timed out. Please try again or contact support if the problem persists. "
                f"[request_id={request_id}]"
            )
        elif "connection" in error_str or "unreachable" in error_str or "qdrant" in error_str:
            error_msg = (
                f"Vector database temporarily unavailable. Please try again in a moment. "
                f"The document status has been set to 'failed' - you can retry ingestion when the service is available. "
                f"[request_id={request_id}]"
            )
        elif "rate limit" in error_str or "quota" in error_str:
            error_msg = (
                f"Rate limit exceeded. Please wait a moment before trying again. "
                f"[request_id={request_id}]"
            )
        else:
            error_msg = (
                f"An error occurred processing the document. The document status has been set to 'failed' - "
                f"you can retry ingestion. If the problem persists, contact support. [request_id={request_id}]"
            )
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.post(
    "/documents/{document_id}/flashcards",
    responses={
        200: {"model": FlashcardAgentOutput},
        202: {"model": AsyncTaskResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate flashcards from a document",
    description="Generate flashcards from a document using FlashcardAgent. Use async=true to run in background.",
)
async def generate_flashcards(
    document_id: Annotated[uuid.UUID, Path(description="Source document ID")],
    request_body: GenerateFlashcardsRequest,
    background_tasks: BackgroundTasks,
    async_mode: Annotated[bool, Query(description="Run in background")] = False,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    request_id: Annotated[str, Depends(get_request_id)] = None,
) -> FlashcardAgentOutput | AsyncTaskResponse:
    """Generate flashcards from a document using FlashcardAgent."""
    # Rate limit check (placeholder)
    await check_rate_limit(request_body.workspace_id, request_body.user_id, request_id)

    # Validate mode
    valid_modes = {"key_terms", "qa", "cloze"}
    if request_body.mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}",
        )

    # Map mode to card_type for duplicate check
    mode_to_card_type = {
        "key_terms": "basic",
        "qa": "qa",
        "cloze": "cloze",
    }
    card_type = mode_to_card_type[request_body.mode]

    # Check for existing flashcards (duplicate prevention)
    from app.services.flashcard_service import FlashcardService
    flashcard_service = FlashcardService(db)
    existing_flashcards = await flashcard_service.find_existing_flashcards(
        workspace_id=request_body.workspace_id,
        user_id=request_body.user_id,
        document_id=document_id,
        card_type=card_type,
        limit=10,
    )
    
    # Note: We always create a new batch (cards tagged with batch_id)
    # This allows multiple generations while tracking which batch created which cards
    # Future: Add `idempotent=true` query param to return existing cards instead

    # Create input
    input_data = FlashcardAgentInput(
        workspace_id=request_body.workspace_id,
        user_id=request_body.user_id,
        source_document_id=document_id,
        mode=request_body.mode,
    )

    # If async mode, create run and return immediately
    if async_mode:
        try:
            agent_run_service = AgentRunService(db)
            input_json = input_data.model_dump()
            agent_run = await agent_run_service.create_run(
                workspace_id=request_body.workspace_id,
                user_id=request_body.user_id,
                agent_name="flashcard",
                input_json=input_json,
                status="queued",
            )

            # Add to background tasks
            agent_router = AgentRouter(db)
            add_agent_task(
                background_tasks,
                "flashcard",
                agent_router.run_flashcard,
                input_data,
                agent_run.id,
                db,
            )

            return AsyncTaskResponse(
                run_id=agent_run.id,
                status="queued",
                message="Flashcard generation queued. Check agent_runs table for status.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error queuing flashcard generation [request_id={request_id}]: {str(e)}",
            )

    # Synchronous execution
    try:
        # Agent router provided via dependency (uses shared GraphRegistry)
        result = await agent_router.run_flashcard(input_data)

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log error with request ID
        import logging
        logger = logging.getLogger(__name__)
        error_str = str(e).lower()
        logger.error(f"Flashcard generation failed [request_id={request_id}]: {str(e)}", exc_info=True)
        
        # Provide user-friendly error messages with "try again" guidance
        if "timeout" in error_str or "timed out" in error_str:
            error_msg = (
                f"Request timed out. Please try again with a shorter document or wait a moment. "
                f"[request_id={request_id}]"
            )
        elif "connection" in error_str or "unreachable" in error_str:
            error_msg = (
                f"Service temporarily unavailable. Please try again in a moment. "
                f"[request_id={request_id}]"
            )
        elif "rate limit" in error_str or "quota" in error_str:
            error_msg = (
                f"Rate limit exceeded. Please wait a moment before trying again. "
                f"[request_id={request_id}]"
            )
        else:
            error_msg = (
                f"An error occurred generating flashcards. Please try again in a moment. "
                f"If the problem persists, contact support. [request_id={request_id}]"
            )
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.post(
    "/documents/{document_id}/kg",
    responses={
        200: {"model": KGExtractionAgentOutput},
        202: {"model": AsyncTaskResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Extract knowledge graph from a document",
    description="Extract concepts and relationships from a document using KGExtractionAgent. Use async=true to run in background.",
)
async def extract_kg(
    document_id: Annotated[uuid.UUID, Path(description="Source document ID")],
    request_body: ExtractKGRequest,
    background_tasks: BackgroundTasks,
    async_mode: Annotated[bool, Query(description="Run in background")] = False,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    request_id: Annotated[str, Depends(get_request_id)] = None,
) -> KGExtractionAgentOutput | AsyncTaskResponse:
    """Extract knowledge graph from a document using KGExtractionAgent."""
    # Rate limit check (placeholder)
    await check_rate_limit(request_body.workspace_id, request_body.user_id, request_id)

    # Create input
    input_data = KGExtractionAgentInput(
        workspace_id=request_body.workspace_id,
        user_id=request_body.user_id,
        source_document_id=document_id,
    )

    # If async mode, create run and return immediately
    if async_mode:
        try:
            agent_run_service = AgentRunService(db)
            input_json = input_data.model_dump()
            agent_run = await agent_run_service.create_run(
                workspace_id=request_body.workspace_id,
                user_id=request_body.user_id,
                agent_name="kg_extraction",
                input_json=input_json,
                status="queued",
            )

            # Add to background tasks
            agent_router = AgentRouter(db)
            add_agent_task(
                background_tasks,
                "kg_extraction",
                agent_router.run_kg_extraction,
                input_data,
                agent_run.id,
                db,
            )

            return AsyncTaskResponse(
                run_id=agent_run.id,
                status="queued",
                message="KG extraction queued. Check agent_runs table for status.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error queuing KG extraction [request_id={request_id}]: {str(e)}",
            )

    # Synchronous execution
    try:
        # Agent router provided via dependency (uses shared GraphRegistry)
        result = await agent_router.run_kg_extraction(input_data)

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log error with request ID
        # TODO: Add proper logging with request_id context
        # import logging
        # logger.error(f"KG extraction failed [request_id={request_id}]: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting knowledge graph [request_id={request_id}]: {str(e)}",
        )


# Workspace-scoped document routes (contract requirement)
@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentRead,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create a document in a workspace",
    description="Create a document in a workspace. If preferences.auto_ingest_on_upload=true, ingestion will be triggered automatically.",
)
async def create_workspace_document(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    request: CreateDocumentRequest,
    background_tasks: BackgroundTasks,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    request_id: Annotated[str, Depends(get_request_id)] = None,
) -> DocumentRead:
    """Create a document in a workspace, optionally auto-ingesting."""
    try:
        # Verify workspace_id matches
        if request.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail="Workspace ID mismatch")
        
        document_service = DocumentService(db)
        document = await document_service.create_document(
            workspace_id=workspace_id,
            user_id=request.user_id,
            title=request.title,
            source_type=request.doc_type,
            source_uri=request.source_url,
            metadata=request.metadata,
        )
        
        # Store raw text if provided
        if request.content:
            document = await document_service.store_raw_text(document.id, request.content)
        
        # Check preferences for auto-ingest
        from app.services.user_preference_service import UserPreferenceService
        pref_service = UserPreferenceService(db)
        preferences = await pref_service.get_preferences(user_id=request.user_id)
        
        run_id = None
        if preferences.auto_ingest_on_upload and request.content:
            # Trigger auto-ingest in background
            input_data = IngestionAgentInput(
                document_id=document.id,
                workspace_id=workspace_id,
                user_id=request.user_id,
                raw_text=None,  # Already stored
            )
            agent_run_service = AgentRunService(db)
            input_json = input_data.model_dump()
            agent_run = await agent_run_service.create_run(
                workspace_id=workspace_id,
                user_id=request.user_id,
                agent_name="ingestion",
                input_json=input_json,
                status="queued",
            )
            run_id = agent_run.id
            document.last_run_id = run_id
            await db.commit()
            
            add_agent_task(
                background_tasks,
                "ingestion",
                agent_router.run_ingestion,
                input_data,
                agent_run.id,
                db,
            )
        
        return DocumentRead.model_validate(document)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating document [request_id={request_id}]: {str(e)}",
        )


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=list[DocumentRead],
    responses={500: {"model": ErrorResponse}},
    summary="List documents in a workspace",
)
async def list_workspace_documents(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[DocumentRead]:
    """List all documents in a workspace."""
    try:
        document_service = DocumentService(db)
        documents = await document_service.list_documents(workspace_id=workspace_id)
        return [DocumentRead.model_validate(d) for d in documents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@router.get(
    "/documents/{document_id}",
    response_model=DocumentRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get a document",
)
async def get_document(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentRead:
    """Get a document by ID (includes status, summary_text, last_run_id)."""
    try:
        document_service = DocumentService(db)
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return DocumentRead.model_validate(document)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update a document",
)
async def update_document(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    request: DocumentCreate,  # Reuse for partial update
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentRead:
    """Update a document."""
    try:
        document_service = DocumentService(db)
        document = await document_service.update_document(
            document_id=document_id,
            title=request.title,
            doc_type=request.doc_type,
            source_url=request.source_url,
            language=request.language,
            metadata=request.metadata,
        )
        return DocumentRead.model_validate(document)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")


@router.delete(
    "/documents/{document_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete a document",
)
async def delete_document(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> None:
    """Delete a document (cascade deletes chunks, embeddings, etc.)."""
    try:
        document_service = DocumentService(db)
        await document_service.delete_document(document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


@router.get(
    "/documents/{document_id}/status",
    response_model=DocumentRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get document status",
)
async def get_document_status(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentRead:
    """Get document status (alias to document GET)."""
    return await get_document(document_id, db)


@router.get(
    "/documents/{document_id}/summary",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get document summary",
)
async def get_document_summary(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    """Get document summary."""
    try:
        document_service = DocumentService(db)
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return {"summary": document.summary_text, "document_id": str(document_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")


@router.post(
    "/documents/{document_id}/summary",
    responses={
        200: {"model": SummaryAgentOutput},
        202: {"model": AsyncTaskResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Regenerate document summary",
    description="Generate or regenerate document summary using SummaryAgent. Use async=true to run in background.",
)
async def regenerate_document_summary(
    document_id: Annotated[uuid.UUID, Path(description="Document ID")],
    background_tasks: BackgroundTasks,
    async_mode: Annotated[bool, Query(description="Run in background")] = False,
    max_bullets: Annotated[int, Query(description="Maximum number of bullet points", ge=1, le=20)] = 7,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    request_id: Annotated[str, Depends(get_request_id)] = None,
) -> SummaryAgentOutput | AsyncTaskResponse:
    """Regenerate document summary using SummaryAgent."""
    try:
        # Get document to extract workspace_id and user_id
        document_service = DocumentService(db)
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        # Create input
        input_data = SummaryAgentInput(
            document_id=document_id,
            workspace_id=document.workspace_id,
            user_id=document.created_by,  # Use document creator as user_id
            max_bullets=max_bullets,
        )

        # If async mode, create run and return immediately
        if async_mode:
            try:
                agent_run_service = AgentRunService(db)
                input_json = input_data.model_dump()
                agent_run = await agent_run_service.create_run(
                    workspace_id=document.workspace_id,
                    user_id=document.created_by,
                    agent_name="summary",
                    input_json=input_json,
                    status="queued",
                )

                # Add to background tasks
                agent_router = AgentRouter(db)
                add_agent_task(
                    background_tasks,
                    "summary",
                    agent_router.run_summary,
                    input_data,
                    agent_run.id,
                    db,
                )

                return AsyncTaskResponse(
                    run_id=agent_run.id,
                    status="queued",
                    message="Summary generation queued. Check agent_runs table for status.",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error queuing summary generation [request_id={request_id}]: {str(e)}",
                )

        # Synchronous execution
        try:
            # Agent router provided via dependency (uses shared GraphRegistry)
            result = await agent_router.run_summary(input_data)

            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating summary [request_id={request_id}]: {str(e)}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating summary: {str(e)}")


@router.post(
    "/documents/{document_id}/reindex",
    responses={
        200: {"description": "Reindex successful"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Reindex document embeddings",
    description="Delete old embeddings and regenerate with current embedding model. Useful after changing embedding model configuration.",
)
async def reindex_document(
    document_id: Annotated[uuid.UUID, Path(description="Document ID to reindex")],
    embedding_model: Annotated[str, Query(description="Embedding model to use")] = "default",
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    """Reindex document embeddings.
    
    This endpoint:
    - Deletes old embeddings from Qdrant (by document_id filter)
    - Deletes old Embedding records from DB
    - Regenerates embeddings with the specified model
    - Upserts new vectors to Qdrant
    
    Chunk IDs remain stable, ensuring chat and other features continue to work.
    """
    try:
        from app.services.embedding_service import EmbeddingService
        from app.infrastructure.qdrant import QdrantClientWrapper
        
        document_service = DocumentService(db)
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        # Reindex embeddings
        qdrant_client = QdrantClientWrapper()
        embedding_service = EmbeddingService(db, qdrant_client=qdrant_client)
        new_embeddings = await embedding_service.reindex_document(
            document_id=document_id,
            embedding_model=embedding_model,
        )
        
        return {
            "document_id": str(document_id),
            "embeddings_created": len(new_embeddings),
            "embedding_model": embedding_model,
            "message": "Document reindexed successfully. Old vectors replaced with new ones.",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reindexing document: {str(e)}"
        )

