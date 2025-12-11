import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TokenManager:
    def __init__(self) -> None:
        self.tokens_per_minute = int(os.getenv("MAX_TOKEN_PER_MINUTE", 200000))
        self.token_bucket = self.tokens_per_minute
        self.last_token_reset = time.time()
        self.max_wait = int(os.getenv("MAX_TOKEN_WAIT", 300))  # 5 minutes

    async def _update_token_bucket(self) -> None:
        current_time = time.time()
        elapsed_minutes = (current_time - self.last_token_reset) / 60
        if elapsed_minutes >= 1:
            self.token_bucket = min(
                self.tokens_per_minute,
                self.token_bucket + int(self.tokens_per_minute * elapsed_minutes),
            )
            self.last_token_reset = current_time
            logger.info(f"Token bucket updated: tokens_available={self.token_bucket}")

    async def check_token_limit(self, tokens_needed: int) -> bool:
        await self._update_token_bucket()
        safety_margin = self.tokens_per_minute * 0.1
        if self.token_bucket >= (tokens_needed + safety_margin):
            logger.debug(
                f"Token check passed: needed={tokens_needed}, available={self.token_bucket}"
            )
            return True

        waited = 0
        while waited <= self.max_wait:
            logger.warning(
                f"Token limit reached: needed={tokens_needed}, available={self.token_bucket}, waiting 5 seconds (waited {waited}s)"
            )
            await asyncio.sleep(5)
            await self._update_token_bucket()
            if self.token_bucket >= (tokens_needed + safety_margin):
                logger.debug(
                    f"Token check passed after waiting: needed={tokens_needed}, available={self.token_bucket}"
                )
                return True
            waited += 5

        logger.error(f"Waited too long ({waited}s) for tokens, aborting")
        raise TimeoutError(
            f"Could not acquire {tokens_needed} tokens after {self.max_wait}s"
        )

    def consume_tokens(self, tokens: int) -> None:
        self.token_bucket -= tokens
