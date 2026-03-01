"""Flashcard service with SRS (Spaced Repetition System)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.flashcard_review import FlashcardReview
from app.models.flashcard_srs_state import FlashcardSRSState
from app.schemas.insights import WorkspaceInsightsResponse
from app.services.base import BaseService

# Mastery formula: ease_factor 2.5 = 100%; same as frontend min(100, (ease_factor/2.5)*100)
EASE_FULL_MASTERY = 2.5


class FlashcardService(BaseService):
    """Service for flashcard operations with SRS."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_flashcards_from_text(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        source_document_id: uuid.UUID | None,
        cards: list[dict[str, Any]],
        batch_id: uuid.UUID | None = None,
    ) -> list[Flashcard]:
        """Create flashcards from card data.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            source_document_id: Source document ID
            cards: List of card dictionaries
            batch_id: Optional batch/generation ID to group cards from same run
        """
        flashcards = []
        for card_data in cards:
            flashcard = Flashcard(
                workspace_id=workspace_id,
                user_id=user_id,
                document_id=source_document_id,
                card_type=card_data.get("card_type", "basic"),
                front=card_data.get("front"),
                back=card_data.get("back"),
                source_chunk_ids=card_data.get("source_chunk_ids"),
                batch_id=batch_id,
                tags=card_data.get("tags"),
                meta_data=card_data.get("metadata"),
            )
            self.db.add(flashcard)
            flashcards.append(flashcard)

        await self._commit_and_refresh(*flashcards)
        return flashcards

    async def find_existing_flashcards(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        card_type: str,
        limit: int = 10,
    ) -> list[Flashcard]:
        """Find existing flashcards for a document + mode (card_type).
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            document_id: Document ID
            card_type: Card type (mode) - "qa" or "mcq"
            limit: Maximum number of results to return
            
        Returns:
            List of existing flashcards
        """
        stmt = (
            select(Flashcard)
            .where(
                Flashcard.workspace_id == workspace_id,
                Flashcard.user_id == user_id,
                Flashcard.document_id == document_id,
                Flashcard.card_type == card_type,
            )
            .order_by(Flashcard.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_due_flashcards(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID, limit: int = 20
    ) -> list[Flashcard]:
        """Get flashcards due for review."""
        now = datetime.now(timezone.utc)

        # Get flashcards with SRS state where due_at is in the past or null
        stmt = (
            select(Flashcard)
            .join(
                FlashcardSRSState,
                (Flashcard.id == FlashcardSRSState.flashcard_id)
                & (FlashcardSRSState.user_id == user_id),
                isouter=True,
            )
            .where(
                (Flashcard.workspace_id == workspace_id)
                & (Flashcard.user_id == user_id)
                & (
                    (FlashcardSRSState.due_at.is_(None))
                    | (FlashcardSRSState.due_at <= now)
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _calculate_srs_update(
        self, rating: int, current_state: FlashcardSRSState | None
    ) -> dict[str, Any]:
        """Calculate new SRS state based on rating (SM-2 algorithm variant)."""
        # SM-2 algorithm parameters
        INITIAL_EASE = 2.5
        MIN_EASE = 1.3
        EASE_CHANGE = 0.1

        if current_state is None:
            # New card
            if rating >= 3:  # Good or easy
                return {
                    "interval_days": 1,
                    "ease_factor": INITIAL_EASE,
                    "repetitions": 1,
                    "lapses": 0,
                }
            else:  # Hard or again
                return {
                    "interval_days": 0,
                    "ease_factor": INITIAL_EASE,
                    "repetitions": 0,
                    "lapses": 1,
                }

        # Existing card
        ease = current_state.ease_factor or INITIAL_EASE
        interval = current_state.interval_days or 0
        repetitions = current_state.repetitions or 0
        lapses = current_state.lapses or 0

        if rating >= 3:  # Good or easy
            # Successful recall
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                new_interval = int(interval * ease)

            # Enhanced handling for grade 4 (Perfect) - larger interval boost
            if rating == 4:  # Perfect
                # Boost interval by 20% for perfect reviews
                new_interval = int(new_interval * 1.2)
                # Also boost ease factor more for perfect reviews
                new_ease = min(ease + (EASE_CHANGE * 1.5), 2.5)
            else:  # Good (rating == 3)
                new_ease = min(ease + EASE_CHANGE, 2.5)
            
            new_repetitions = repetitions + 1
            new_lapses = lapses
        else:  # Hard or again
            # Failed recall
            new_interval = 0
            new_ease = max(ease - EASE_CHANGE, MIN_EASE)
            new_repetitions = 0
            new_lapses = lapses + 1

        return {
            "interval_days": new_interval,
            "ease_factor": new_ease,
            "repetitions": new_repetitions,
            "lapses": new_lapses,
        }

    async def record_review(
        self,
        flashcard_id: uuid.UUID,
        user_id: uuid.UUID,
        grade: int,
        response_time_ms: int | None = None,
        force: bool = False,
        cooldown_seconds: int = 30,
    ) -> tuple[FlashcardReview, FlashcardSRSState]:
        """Record a flashcard review and update SRS state.
        
        Args:
            flashcard_id: ID of the flashcard
            user_id: ID of the user reviewing
            grade: Rating (0-4): 0=Again, 1=Hard, 2=Good, 3=Easy, 4=Perfect
            response_time_ms: Optional response time in milliseconds
            force: If True, bypass due check and cooldown (default: False)
            cooldown_seconds: Minimum seconds between reviews (default: 30)
            
        Raises:
            ValueError: If flashcard not found, grade invalid, card not due, or database error
        """
        # Validate grade
        if not isinstance(grade, int) or grade < 0 or grade > 4:
            raise ValueError(f"Grade must be an integer between 0 and 4, got: {grade}")

        # Get flashcard
        stmt = select(Flashcard).where(Flashcard.id == flashcard_id)
        result = await self.db.execute(stmt)
        flashcard = result.scalar_one_or_none()
        if not flashcard:
            raise ValueError(f"Flashcard {flashcard_id} not found")

        # Get or create SRS state
        stmt = select(FlashcardSRSState).where(
            (FlashcardSRSState.flashcard_id == flashcard_id)
            & (FlashcardSRSState.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        srs_state = result.scalar_one_or_none()
        
        # Get current time (used for checks and updates)
        now = datetime.now(timezone.utc)
        
        # Check if card is due (unless forced)
        if not force and srs_state:
            # Check due date
            if srs_state.due_at and srs_state.due_at > now:
                raise ValueError(
                    f"Card not due yet. Next review: {srs_state.due_at.isoformat()}. "
                    f"Use force=true to review anyway."
                )
            
            # Check cooldown (prevent rapid re-reviews)
            if srs_state.last_reviewed_at:
                time_since_review = (now - srs_state.last_reviewed_at).total_seconds()
                if time_since_review < cooldown_seconds:
                    raise ValueError(
                        f"Please wait {cooldown_seconds - int(time_since_review)} more seconds before reviewing again. "
                        f"Use force=true to bypass cooldown."
                    )

        # Calculate new SRS values
        srs_update = self._calculate_srs_update(grade, srs_state)

        if srs_state:
            # Update existing state
            srs_state.interval_days = srs_update["interval_days"]
            srs_state.ease_factor = srs_update["ease_factor"]
            srs_state.repetitions = srs_update["repetitions"]
            srs_state.lapses = srs_update["lapses"]
            srs_state.last_reviewed_at = now
            if srs_update["interval_days"] > 0:
                srs_state.due_at = now + timedelta(days=srs_update["interval_days"])
            else:
                srs_state.due_at = now  # Review again today
        else:
            # Create new state
            srs_state = FlashcardSRSState(
                flashcard_id=flashcard_id,
                user_id=user_id,
                interval_days=srs_update["interval_days"],
                ease_factor=srs_update["ease_factor"],
                repetitions=srs_update["repetitions"],
                lapses=srs_update["lapses"],
                last_reviewed_at=now,
                due_at=now + timedelta(days=srs_update["interval_days"])
                if srs_update["interval_days"] > 0
                else now,
            )
            self.db.add(srs_state)

        # Create review record
        review = FlashcardReview(
            flashcard_id=flashcard_id,
            user_id=user_id,
            rating=grade,
            response_time_ms=response_time_ms,
        )
        self.db.add(review)

        await self._commit_and_refresh(review, srs_state)
        return review, srs_state

    async def get_workspace_insights(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceInsightsResponse:
        """Compute workspace-level insights for dashboard (average mastery, cards due, etc.)."""
        now = datetime.now(timezone.utc)

        # Total flashcards in workspace for this user
        total_stmt = (
            select(func.count(Flashcard.id))
            .where(
                Flashcard.workspace_id == workspace_id,
                Flashcard.user_id == user_id,
            )
        )
        total_result = await self.db.execute(total_stmt)
        total_flashcards = total_result.scalar() or 0

        # SRS state rows for user's cards in this workspace
        srs_stmt = (
            select(FlashcardSRSState.ease_factor, FlashcardSRSState.due_at)
            .join(Flashcard, Flashcard.id == FlashcardSRSState.flashcard_id)
            .where(
                Flashcard.workspace_id == workspace_id,
                Flashcard.user_id == user_id,
                FlashcardSRSState.user_id == user_id,
            )
        )
        srs_result = await self.db.execute(srs_stmt)
        srs_rows = list(srs_result.all())

        total_cards_with_srs = len(srs_rows)

        # Average mastery: mean of min(100, (ease_factor/2.5)*100) for cards with ease_factor
        mastery_values = []
        due_count = 0
        for ease_factor, due_at in srs_rows:
            if ease_factor is not None:
                mastery = min(100.0, (float(ease_factor) / EASE_FULL_MASTERY) * 100.0)
                mastery_values.append(mastery)
            if due_at is None or due_at <= now:
                due_count += 1

        average_mastery = (
            round(sum(mastery_values) / len(mastery_values), 1) if mastery_values else None
        )

        # Cards due = never reviewed (no SRS) + SRS rows that are due
        cards_due = (total_flashcards - total_cards_with_srs) + due_count

        # Knowledge graph concepts count in workspace
        kg_count_stmt = (
            select(func.count(Concept.id)).where(Concept.workspace_id == workspace_id)
        )
        kg_count_result = await self.db.execute(kg_count_stmt)
        kg_concepts_count = kg_count_result.scalar() or 0

        # Documents count in workspace
        doc_count_stmt = (
            select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
        )
        doc_count_result = await self.db.execute(doc_count_stmt)
        documents_count = doc_count_result.scalar() or 0

        # Recent activity: documents uploaded in the current week (ISO week, Monday–Sunday)
        start_of_week = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        recent_stmt = (
            select(func.count(Document.id))
            .where(Document.workspace_id == workspace_id)
            .where(Document.created_at >= start_of_week)
        )
        recent_result = await self.db.execute(recent_stmt)
        recent_activity = recent_result.scalar() or 0

        return WorkspaceInsightsResponse(
            average_mastery=average_mastery,
            cards_due=cards_due,
            total_cards_with_srs=total_cards_with_srs,
            total_flashcards=total_flashcards,
            kg_concepts_count=kg_concepts_count,
            documents_count=documents_count,
            recent_activity=recent_activity,
        )

