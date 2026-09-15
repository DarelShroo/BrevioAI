import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class BrevioRateLimiter:
    """
    Handles API rate limits (Requests Per Minute, Tokens Per Minute)
    and controls concurrency for the BrevioAI pipeline.
    """

    def __init__(
        self,
        requests_per_minute: int = 14,
        tokens_per_minute: int = 200000,
        max_concurrency: int = 3,
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.max_concurrency = max_concurrency

        self.token_bucket = tokens_per_minute
        self.request_bucket = requests_per_minute

        self.last_reset = time.time()
        self.concurrency_semaphore = asyncio.Semaphore(max_concurrency)
        self.lock = asyncio.Lock()

    async def _update_buckets(self):
        now = time.time()
        elapsed = now - self.last_reset
        if elapsed >= 60.0:
            self.token_bucket = self.tokens_per_minute
            self.request_bucket = self.requests_per_minute
            self.last_reset = now
            logger.debug(
                f"Buckets reset: tokens={self.token_bucket}, requests={self.request_bucket}"
            )

    async def acquire(self, tokens_needed: int) -> None:
        """
        Blocks until the requested tokens and a request slot are available.
        """
        while True:
            async with self.lock:
                await self._update_buckets()

                # Cap tokens_needed to max bucket size to prevent infinite deadlock
                actual_needed = min(tokens_needed, self.tokens_per_minute)

                # Check if we have both a request slot and enough tokens
                if self.request_bucket >= 1 and self.token_bucket >= actual_needed:
                    self.request_bucket -= 1
                    self.token_bucket -= actual_needed
                    return

                now = time.time()
                time_until_reset = 60.0 - (now - self.last_reset)
                wait_time = min(max(time_until_reset, 0.1), 5.0)

            logger.warning(
                f"Rate limit reached. Needed: {tokens_needed} tokens, 1 request. "
                f"Available: {self.token_bucket} tokens, {self.request_bucket} requests. "
                f"Waiting {wait_time:.2f}s."
            )
            await asyncio.sleep(wait_time)

    async def refund_tokens(self, tokens: int):
        """
        Refunds tokens if the actual usage was less than estimated.
        """
        async with self.lock:
            self.token_bucket = min(self.tokens_per_minute, self.token_bucket + tokens)
