"""
Network retry utilities for handling Telegram API connection issues.
Implements exponential backoff for transient network errors.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Any

from telegram.error import NetworkError, TimedOut, RetryAfter

logger = logging.getLogger(__name__)


def retry_on_network_error(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except RetryAfter as e:
                    # Telegram rate limit - wait as instructed
                    wait_time = e.retry_after + 1
                    logger.warning(
                        f"Rate limited by Telegram. "
                        f"Waiting {wait_time}s before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    last_exception = e

                except (NetworkError, TimedOut, OSError) as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s...
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Network error on attempt {attempt + 1}/{max_retries}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Network error after {max_retries} attempts: {e}",
                            exc_info=True
                        )

                except Exception as e:
                    # Non-network error - don't retry
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            raise last_exception

        return wrapper

    return decorator


async def safe_send_message(
        message_obj,
        text: str,
        max_retries: int = 3,
        **kwargs
) -> Any:

    @retry_on_network_error(max_retries=max_retries)
    async def _send():
        return await message_obj.reply_text(text, **kwargs)

    try:
        return await _send()
    except Exception as e:
        logger.error(f"Failed to send message after retries: {e}")
        return None


async def safe_send_photo(
        message_obj,
        photo,
        max_retries: int = 3,
        **kwargs
) -> Any:


    @retry_on_network_error(max_retries=max_retries)
    async def _send():
        return await message_obj.reply_photo(photo, **kwargs)

    try:
        return await _send()
    except Exception as e:
        logger.error(f"Failed to send photo after retries: {e}")
        return None


async def safe_delete_message(message_obj, max_retries: int = 2) -> bool:
    @retry_on_network_error(max_retries=max_retries)
    async def _delete():
        return await message_obj.delete()

    try:
        await _delete()
        return True
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")
        return False