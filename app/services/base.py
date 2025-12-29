"""Base service class with common patterns."""
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Base service class with common database operations and error handling."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.
        
        Args:
            db: Database session
        """
        self.db = db

    @asynccontextmanager
    async def _transaction(self) -> AsyncGenerator[None, None]:
        """Context manager for database transactions with automatic rollback on error.
        
        Usage:
            async with self._transaction():
                # Database operations here
                await self.db.commit()
        """
        try:
            yield
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def _commit_and_refresh(self, *objects: Any) -> None:
        """Commit transaction and refresh objects with error handling.
        
        Args:
            *objects: Objects to refresh after commit
            
        Raises:
            ValueError: If SQLAlchemyError occurs, with standardized message
        """
        try:
            await self.db.commit()
            for obj in objects:
                await self.db.refresh(obj)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise self._handle_db_error("committing transaction", e) from e

    def _handle_db_error(self, operation: str, error: Exception) -> ValueError:
        """Create a standardized ValueError for database errors.
        
        Args:
            operation: Description of the operation that failed
            error: The original exception
            
        Returns:
            ValueError with standardized error message
        """
        return ValueError(f"Database error while {operation}: {str(error)}")

    async def _execute_with_error_handling(
        self, operation: str, func: callable, *args, **kwargs
    ) -> Any:
        """Execute a function with standardized error handling.
        
        Args:
            operation: Description of the operation (for error messages)
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            ValueError: If SQLAlchemyError occurs, with standardized message
        """
        try:
            return await func(*args, **kwargs)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise self._handle_db_error(operation, e) from e

