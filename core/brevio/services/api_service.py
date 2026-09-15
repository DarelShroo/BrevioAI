import asyncio
import logging
from typing import Any, Callable, Coroutine, List, Optional, Tuple

from openai import AsyncOpenAI

from core.brevio_api.models.errors.provider_errors import ProviderError
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import get_model_capabilities

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
        credential_resolver=None,
    ):
        self.clients: dict[str, AsyncOpenAI] = {}
        self._client_versions: dict[str, tuple[str, str]] = {}
        self.credential_resolver = credential_resolver
        self.client_lock = client_lock
        self.task_done_calls = task_done_calls
        self.tasks_put = tasks_put
        self.running_tasks: List[asyncio.Task] = running_tasks
        self.queue_lock = queue_lock
        self.task_queue: asyncio.Queue[
            Tuple[Callable[..., Coroutine[Any, Any, Any]], List[Any]]
        ] = task_queue
        self.running = running
        # Last resolved provider quota identity (never contains API keys)
        self.last_provider: Optional[str] = None
        self.last_quota_scope_id: Optional[str] = None
        self.last_model: Optional[str] = None

    async def _initialize_client(
        self, model: ModelType, user_id: Optional[str] = None
    ) -> AsyncOpenAI:
        provider = get_model_capabilities(model).provider.lower()
        async with self.client_lock:
            if not self.credential_resolver:
                logger.error("Credential resolver is missing in ApiService")
                raise ValueError("Credential resolver is not configured")

            if not user_id:
                raise ValueError(
                    f"user_id is required to resolve credentials for {model.value}"
                )

            # Use CredentialResolver
            try:
                cred = await self.credential_resolver.resolve(user_id, provider)
            except ProviderError as e:
                # If a credential was revoked or deleted, it fails here. Clear any existing cache to prevent leaks.
                cache_key = f"usr:{user_id}:{provider}"
                if cache_key in self.clients:
                    old_client = self.clients.pop(cache_key)
                    self._client_versions.pop(cache_key, None)
                    try:
                        await old_client.close()
                        logger.info(
                            f"Invalidated and closed cached client for cache_key {cache_key} due to resolution error"
                        )
                    except Exception as ex:
                        logger.warning(f"Error closing invalidated client: {ex}")
                raise e

            if cred.is_platform:
                # Assuming v1 for now, or extending it globally later if dynamic rotation inside memory is needed
                cache_key = f"plt:{provider}:v1:{cred.base_url}"
            else:
                cache_key = f"usr:{user_id}:{provider}"

            cred_version = (cred.credential_id, str(cred.updated_at.timestamp()))

            # Check for credential rotation via explicit metadata
            if cache_key in self.clients:
                if self._client_versions.get(cache_key) != cred_version:
                    logger.info(
                        f"Credential rotated for cache_key {cache_key}, closing old client"
                    )
                    old_client = self.clients.pop(cache_key)
                    try:
                        await old_client.close()
                    except Exception as e:
                        logger.warning(f"Error closing old client during rotation: {e}")

            if cache_key not in self.clients:
                # Sole app RetryCoordinator owns retries — disable SDK retries.
                client = AsyncOpenAI(
                    api_key=cred.api_key,
                    base_url=cred.base_url,
                    max_retries=0,
                )
                self.clients[cache_key] = client
                self._client_versions[cache_key] = cred_version
                logger.info(f"Initialized new client for cache_key {cache_key}")

            self.last_provider = provider
            self.last_quota_scope_id = cred.quota_scope_id
            self.last_model = model.value

            return self.clients[cache_key]

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
                for cache_key, client in self.clients.items():
                    try:
                        await client.close()
                        logger.info(f"Closed client for cache_key {cache_key}")
                    except Exception as e:
                        logger.error(
                            f"Error closing client for cache_key {cache_key}: {str(e)}",
                            exc_info=True,
                        )
                self.clients.clear()
                self._client_versions.clear()

            logger.info(
                f"Total tasks put: {self.tasks_put}, total task_done calls: {self.task_done_calls}"
            )

    async def get_clients(self) -> dict[str, AsyncOpenAI]:
        return self.clients

    async def check_api_connectivity(
        self, model: ModelType, user_id: Optional[str] = None
    ) -> bool:
        """Validate credentials and client construction. Does not consume a completion.

        The first MAP/REDUCE request is the live connectivity check.
        """
        logger.debug(f"Checking API client initialization for model {model.value}")
        try:
            await self._initialize_client(model, user_id)
            logger.info(
                f"API client initialized for {model.value} (no completion probe)"
            )
            return True
        except Exception as e:
            logger.error(f"API connectivity check failed for {model.value}: {str(e)}")
            return False
