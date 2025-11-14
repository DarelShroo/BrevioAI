import asyncio
import logging
import os
from typing import Any, Callable, Coroutine, List, Tuple

import httpx
from openai import AsyncOpenAI

from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder, is_deepseek

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ApiService:
    def __init__(
        self,
        running: bool,
        task_queue: asyncio.Queue[
            Tuple[Callable[..., Coroutine[Any, Any, Any]], List[Any]]
        ],
        queue_lock: asyncio.Lock,
        client_lock: asyncio.Lock,
        tasks_put: int,
        task_done_calls: int,
        running_tasks: List[asyncio.Task],
    ):
        self.clients: dict[str, AsyncOpenAI] = {}
        self.client_lock = client_lock
        self.task_done_calls = task_done_calls
        self.tasks_put = tasks_put
        self.running_tasks: List[asyncio.Task] = running_tasks
        self.queue_lock = queue_lock
        self.task_queue: asyncio.Queue[
            Tuple[Callable[..., Coroutine[Any, Any, Any]], List[Any]]
        ] = task_queue
        self.running = running

    async def _initialize_client(self, model: ModelType) -> AsyncOpenAI:
        model_key = model.value
        async with self.client_lock:
            if model_key not in self.clients:
                api_key = (
                    os.getenv("DEEPSEEK_API_KEY", "")
                    if is_deepseek(model)
                    else os.getenv("OPENAI_API_KEY", "")
                )
                base_url = (
                    os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
                    if is_deepseek(model)
                    else os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")
                )
                if not api_key:
                    logger.error(f"API key not set for model {model.value}")
                    raise ValueError(f"API key not configured for {model.value}")
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                self.clients[model_key] = client
                logger.info(
                    f"Initialized new client for model {model.value} with base_url={base_url}"
                )
            return self.clients[model_key]

    async def shutdown(self) -> None:
        if self.running:
            self.running = False
            logger.info("Shutting down ApiService")

            # Cancel running tasks
            for task in self.running_tasks:
                task.cancel()
            if self.running_tasks:
                try:
                    await asyncio.gather(*self.running_tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    logger.debug("Tasks cancelled during shutdown")
            self.running_tasks.clear()

            # Clear task queue
            async with self.queue_lock:
                logger.debug(f"Clearing queue, current size: {self.task_queue.qsize()}")
                while not self.task_queue.empty():
                    func, args = await self.task_queue.get()
                    logger.debug(f"Cleared task from queue: {func.__name__}")
                    self.task_queue.task_done()
                    self.task_done_calls += 1
                    logger.debug(
                        f"Called task_done() during shutdown, total calls: {self.task_done_calls}"
                    )

            # Close clients
            async with self.client_lock:
                for model_key, client in self.clients.items():
                    try:
                        if hasattr(client, "aclose"):
                            await client.close()
                        else:
                            logger.warning(
                                f"Client {model_key} does not support aclose()"
                            )
                        logger.info(f"Closed client for model {model_key}")
                    except Exception as e:
                        logger.error(
                            f"Error closing client for model {model_key}: {str(e)}",
                            exc_info=True,
                        )
                self.clients.clear()

            logger.info(
                f"Total tasks put: {self.tasks_put}, total task_done calls: {self.task_done_calls}"
            )

    async def get_clients(self) -> dict[str, AsyncOpenAI]:
        return self.clients

    async def set_client(self, model: ModelType) -> None:
        logger.warning(
            "set_client is deprecated; client is now managed via _initialize_client"
        )
        await self._initialize_client(model)

    async def check_api_connectivity(self, model: ModelType) -> bool:
        logger.debug(f"Checking API connectivity for model {model.value}")
        try:
            client = await self._initialize_client(model)
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=model.value,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=10,
                ),
                timeout=10,
            )
            logger.info(f"API connectivity check passed for {model.value}")
            return True
        except Exception as e:
            logger.error(f"API connectivity check failed for {model.value}: {str(e)}")
            return False
