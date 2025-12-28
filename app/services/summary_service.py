"""Summary service for generating document summaries."""
import uuid
import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating document summaries."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.retrieval_service = RetrievalService(db)

    def _analyze_content_quality(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze content quality to detect repetitive/fluff content.
        
        Args:
            chunks: List of chunk dictionaries with 'content' field
            
        Returns:
            Dictionary with quality metrics:
            - is_repetitive: bool
            - repetition_score: float (0.0-1.0)
            - unique_content_ratio: float (0.0-1.0)
            - has_substantive_content: bool
        """
        if not chunks:
            return {
                "is_repetitive": False,
                "repetition_score": 0.0,
                "unique_content_ratio": 1.0,
                "has_substantive_content": False,
            }
        
        # Extract all text content
        all_text = " ".join(chunk.get("content", "") for chunk in chunks)
        words = re.findall(r"\b\w+\b", all_text.lower())
        
        if not words:
            return {
                "is_repetitive": False,
                "repetition_score": 0.0,
                "unique_content_ratio": 1.0,
                "has_substantive_content": False,
            }
        
        # Calculate word frequency
        word_freq = Counter(words)
        total_words = len(words)
        unique_words = len(word_freq)
        
        # Calculate repetition score (higher = more repetitive)
        # If top 10 words make up >50% of content, it's likely repetitive
        top_words_count = sum(count for word, count in word_freq.most_common(10))
        repetition_score = top_words_count / total_words if total_words > 0 else 0.0
        
        # Calculate unique content ratio
        unique_content_ratio = unique_words / total_words if total_words > 0 else 1.0
        
        # Check for substantive content (has meaningful length and variety)
        has_substantive_content = (
            total_words > 50 and  # Minimum length
            unique_content_ratio > 0.3  # At least 30% unique words
        )
        
        # Consider repetitive if repetition_score > 0.5 or unique_content_ratio < 0.2
        is_repetitive = repetition_score > 0.5 or unique_content_ratio < 0.2
        
        return {
            "is_repetitive": is_repetitive,
            "repetition_score": repetition_score,
            "unique_content_ratio": unique_content_ratio,
            "has_substantive_content": has_substantive_content,
        }

    async def generate_summary(
        self,
        document_id: uuid.UUID,
        max_bullets: int = 7,
    ) -> str:
        """Generate a summary for a document using semantic retrieval and quality-aware LLM.
        
        Uses semantic search to find most important chunks, analyzes content quality,
        and generates a conservative summary that avoids fabrication.
        
        Args:
            document_id: Document ID
            max_bullets: Maximum number of bullet points in summary (default: 7)
            
        Returns:
            Summary text as a string
        """
        try:
            # Get document
            stmt = select(Document).where(Document.id == document_id)
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            workspace_id = document.workspace_id
            
            # Use semantic retrieval to find most important chunks
            # Search for key concepts and main ideas
            summary_queries = [
                "key concepts main ideas important points",
                "summary overview main themes",
                "core principles central arguments",
            ]
            
            all_retrieved_chunks = []
            seen_chunk_ids = set()
            
            # Retrieve chunks using multiple semantic queries for diversity
            for query in summary_queries:
                search_results = await self.retrieval_service.semantic_search(
                    workspace_id=workspace_id,
                    query=query,
                    top_k=5,  # Get top 5 for each query
                    filters={"document_id": str(document_id)},
                )
                
                # Add unique chunks (avoid duplicates)
                for result in search_results:
                    chunk_id = result.get("chunk_id")
                    if chunk_id and chunk_id not in seen_chunk_ids:
                        all_retrieved_chunks.append(result)
                        seen_chunk_ids.add(chunk_id)
            
            # If semantic retrieval didn't work (e.g., embeddings not ready), fallback to first chunks
            if not all_retrieved_chunks:
                logger.warning(f"Semantic retrieval returned no results for document {document_id}, using first chunks as fallback")
                stmt = select(DocumentChunk).where(
                    DocumentChunk.document_id == document_id
                ).order_by(DocumentChunk.chunk_index).limit(8)
                result = await self.db.execute(stmt)
                chunks = list(result.scalars().all())
                
                all_retrieved_chunks = [
                    {
                        "chunk_id": str(chunk.id),
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "score": 1.0,  # Default score for fallback
                    }
                    for chunk in chunks if chunk.content
                ]
            
            if not all_retrieved_chunks:
                return "No content available for summary."
            
            # Sort by score (descending) and take top chunks
            all_retrieved_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            top_chunks = all_retrieved_chunks[:8]  # Use top 8 chunks for better coverage
            
            # Analyze content quality
            quality_metrics = self._analyze_content_quality(top_chunks)
            
            # Combine chunk texts with diversity (ensure chunks are from different sections)
            chunk_texts = []
            chunk_indices_used = set()
            
            # First, add highest-scoring chunks
            for chunk in top_chunks[:5]:
                chunk_idx = chunk.get("chunk_index", 0)
                content = chunk.get("content", "")
                if content and chunk_idx not in chunk_indices_used:
                    chunk_texts.append(content)
                    chunk_indices_used.add(chunk_idx)
            
            # Then add chunks from different sections for diversity
            for chunk in top_chunks[5:]:
                chunk_idx = chunk.get("chunk_index", 0)
                content = chunk.get("content", "")
                # Only add if it's from a different section (not adjacent to existing chunks)
                if content and chunk_idx not in chunk_indices_used:
                    # Check if chunk is too close to existing chunks
                    is_diverse = True
                    for existing_idx in chunk_indices_used:
                        if abs(chunk_idx - existing_idx) < 3:  # Within 3 chunks
                            is_diverse = False
                            break
                    if is_diverse:
                        chunk_texts.append(content)
                        chunk_indices_used.add(chunk_idx)
            
            if not chunk_texts:
                # Fallback: use all chunks if diversity filtering removed everything
                chunk_texts = [chunk.get("content", "") for chunk in top_chunks[:5] if chunk.get("content")]
            
            combined_text = "\n\n".join(chunk_texts[:6])  # Use up to 6 diverse chunks
            
            # Generate summary using LLM with enhanced prompt
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0,  # Low temperature for consistency
                openai_api_key=settings.OPENAI_API_KEY,
            )
            
            # Build enhanced prompt with conservatism instructions
            system_prompt = f"""You are generating a concise summary of a document. Your summary must be conservative, accurate, and avoid fabrication.

CRITICAL RULES:
1. ONLY include information explicitly stated in the provided content
2. DO NOT invent, infer, or add details not present in the content
3. If content is repetitive or unclear, focus on HIGH-LEVEL THEMES rather than specific details
4. If content is fluff or lacks substance, state general themes rather than making specific claims
5. Be conservative: it's better to be vague than wrong
6. If you cannot identify clear key points, state: "This document covers various topics" rather than inventing specifics
7. Avoid overstating or making definitive claims unless clearly supported

Generate a summary in {max_bullets} bullet points. Focus on:
- High-level themes and concepts
- Main ideas explicitly stated
- Important points that are clearly supported
- General patterns rather than specific details (if content is repetitive)

If the content is repetitive or lacks clear structure, emphasize themes over details."""

            # Add quality-aware instructions
            if quality_metrics["is_repetitive"]:
                system_prompt += "\n\nNOTE: The content appears to be repetitive. Focus on high-level themes and avoid repeating the same points multiple times."
            
            if not quality_metrics["has_substantive_content"]:
                system_prompt += "\n\nNOTE: The content may lack substantive detail. Be conservative and focus on general themes rather than specific claims."
            
            user_prompt = f"Document title: {document.title or 'Untitled'}\n\nContent to summarize:\n{combined_text[:3000]}"  # Increased to 3000 chars for better context
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", user_prompt),
            ])
            
            chain = prompt | llm
            response = await chain.ainvoke({})
            summary = response.content if hasattr(response, 'content') else str(response)
            
            return summary
        except Exception as e:
            logger.error(f"Error generating summary for document {document_id}: {str(e)}", exc_info=True)
            # Return a fallback summary
            return f"Summary generation failed: {str(e)}"

    async def store_summary(
        self,
        document_id: uuid.UUID,
        summary_text: str,
    ) -> Document:
        """Store summary in document."""
        try:
            stmt = select(Document).where(Document.id == document_id)
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            document.summary_text = summary_text
            await self.db.commit()
            await self.db.refresh(document)
            return document
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while storing summary: {str(e)}") from e

