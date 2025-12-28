"""Background task runner with exception logging."""
import asyncio
import logging
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_background_task(
    coro: Awaitable[Any],
    db: AsyncSession,
    context: dict[str, Any] | None = None,
) -> Any:
    """Run a coroutine in the background with exception logging.
    
    Args:
        coro: Coroutine to execute
        db: Database session for the task
        context: Optional context dictionary for logging
        
    Returns:
        Result of the coroutine execution
    """
    context = context or {}
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())

    try:
        logger.info(f"Starting background task [{context_str}]")
        result = await coro
        logger.info(f"Background task completed successfully [{context_str}]")
        return result
    except Exception as e:
        logger.error(
            f"Background task failed [{context_str}]: {str(e)}",
            exc_info=True,
            extra=context,
        )
        raise
    finally:
        # Note: Don't close the session here as it's managed by FastAPI dependency
        pass


def create_background_task(
    coro_fn: Callable[..., Awaitable[Any]],
    *args: Any,
    db: AsyncSession,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Awaitable[Any]:
    """Create a background task from a coroutine function.
    
    Args:
        coro_fn: Coroutine function to execute
        *args: Positional arguments for the coroutine function
        db: Database session for the task
        context: Optional context dictionary for logging
        **kwargs: Keyword arguments for the coroutine function
        
    Returns:
        Coroutine that can be added to FastAPI BackgroundTasks
    """
    coro = coro_fn(*args, **kwargs)
    return run_background_task(coro, db, context)

