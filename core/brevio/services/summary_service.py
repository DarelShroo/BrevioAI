import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine, List, Optional, Tuple

from dotenv import load_dotenv
from googletrans import Translator
from openai import AsyncOpenAI

from core.brevio.enums.language import LanguageType
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.managers.token_manager import TokenManager
from core.brevio.models.dtos import ChunkProcessingRequest, DocumentProcessingRequest
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.document_processor import DocumentProcessor
from core.brevio.services.pdf_service import PdfService
from core.brevio.services.summary_chunk_generator import SummaryChunkGenerator
from core.brevio.services.summary_post_processor import SummaryPostProcessor
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.yt_service import YTService
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.model_tokens_utils import get_encoder

from .advanced_content_generator import AdvancedPromptGenerator
from .api_service import ApiService

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SummaryService:
    def __init__(self) -> None:
        logger.info("Initializing SummaryService")
        self.max_tokens = int(os.getenv("MAX_TOKENS", 4096))
        self.max_tokens_per_chunk = int(os.getenv("MAX_TOKENS_PER_CHUNK", 2000))
        self.temperature = float(os.getenv("TEMPERATURE", 0.2))
        self.max_concurrent_chunks = 8
        self.max_concurrent_files = 1000
        self.max_concurrent_requests = 100000

        self.token_manager = TokenManager()

        self.task_queue: asyncio.Queue[
            Tuple[Callable[..., Coroutine[Any, Any, Any]], List[Any]]
        ] = asyncio.Queue()
        self.running = False
        self._percent_chunk_overlap = 0.2
        self.context_token_limit = 100
        self.running_tasks: List[asyncio.Task] = []
        self.client_lock = asyncio.Lock()
        self.queue_lock = asyncio.Lock()
        self.tasks_put = 0
        self.task_done_calls = 0
        self.clients: dict[str, AsyncOpenAI] = {}
        self.advanced_prompt_generator = AdvancedPromptGenerator()
        self.history_token_model = HistoryTokenModel()
        self.translator = Translator()
        self.api_service = ApiService(
            self.running,
            self.task_queue,
            self.queue_lock,
            self.client_lock,
            self.tasks_put,
            self.task_done_calls,
            self.running_tasks,
        )
        self.client: Optional[AsyncOpenAI] = None
        self.directory_manager = DirectoryManager()

        # Initialize sub-services
        self.chunk_generator = SummaryChunkGenerator(
            self.token_manager,
            self.advanced_prompt_generator,
            self.history_token_model,
            self.max_tokens,
            self.temperature,
            self.context_token_limit,
        )
        self.chunk_generator.set_queue_info(self.task_queue, self.queue_lock)

        self.post_processor = SummaryPostProcessor(
            self.token_manager,
            self.advanced_prompt_generator,
            self.history_token_model,
            self.api_service,
            self.max_tokens,
            self.temperature,
            self.max_tokens_per_chunk,
            self._percent_chunk_overlap,
        )
        self.post_processor.set_queue_info(self.task_queue, self.queue_lock)

        self.transcription_service = TranscriptionService()
        self.yt_service = YTService()
        self.pdf_service = PdfService()

        self.document_processor = DocumentProcessor(
            self.token_manager,
            self.chunk_generator,
            self.post_processor,
            self.transcription_service,
            self.yt_service,
            self.directory_manager,
            self.pdf_service,
            self.max_tokens_per_chunk,
        )

        logger.debug(
            f"Initialized with max_tokens={self.max_tokens}, "
            f"max_tokens_per_chunk={self.max_tokens_per_chunk}, "
            f"temperature={self.temperature}, "
            f"max_concurrent_files={self.max_concurrent_files}, "
            f"max_concurrent_requests={self.max_concurrent_requests}, "
            f"overlap={self._percent_chunk_overlap}, "
            f"context_limit={self.context_token_limit}"
        )

    async def start(self) -> None:
        if not self.running:
            self.running = True
            task = asyncio.create_task(self._process_queue(), name="queue_processor")
            self.running_tasks.append(task)
            logger.info("Started queue processor")

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        await self.start()
        try:
            yield
        finally:
            logger.debug("Initiating SummaryService shutdown")
            self.running = False
            if self.running_tasks:
                for task in self.running_tasks:
                    if not task.done():
                        task.cancel()
                        logger.debug(
                            f"Cancelled task: {task.get_name() if hasattr(task, 'get_name') else 'unnamed'}"
                        )
                if self.running_tasks:
                    await asyncio.gather(*self.running_tasks, return_exceptions=True)
                    logger.debug("All running tasks cancelled or completed.")
            await self.api_service.shutdown()
            logger.debug("SummaryService shutdown completed")

    async def process_chunks_in_groups(
        self,
        chunks: List[str],
        prompt: str,
        model: ModelType,
        language: LanguageType,
        callback: Optional[Any] = None,
    ) -> Tuple[str, int]:
        logger.info(f"Processing {len(chunks)} chunks in groups")
        accumulated_summary = ""
        total_tokens_used = 0
        chunk_summaries: List[Optional[str]] = [None] * len(chunks)
        failed_chunks: List[Tuple[int, str]] = []

        try:
            for group_start in range(0, len(chunks), self.max_concurrent_chunks):
                group_end = min(group_start + self.max_concurrent_chunks, len(chunks))
                group_chunks = chunks[group_start:group_end]
                group_indices = list(range(group_start, group_end))
                logger.info(f"Processing chunk group {group_start} to {group_end - 1}")
                encoder = get_encoder(model)
                total_tokens_needed = sum(
                    len(encoder.encode(chunk)) + 500 for chunk in group_chunks
                )
                logger.debug(f"Group estimated tokens needed: {total_tokens_needed}")

                while not await self.token_manager.check_token_limit(
                    total_tokens_needed
                ):
                    logger.warning(
                        f"Token limit reached for group: needed={total_tokens_needed}, "
                        f"available={self.token_manager.token_bucket}. Waiting 5 seconds"
                    )
                    try:
                        await asyncio.sleep(5)
                    except asyncio.CancelledError:
                        logger.info("Cancelled while waiting for tokens")
                        raise

                tasks = []
                for index, chunk in zip(group_indices, group_chunks):
                    request = ChunkProcessingRequest(
                        index=index,
                        chunk=chunk,
                        prompt=prompt,
                        accumulated_summary=accumulated_summary,
                        model=model,
                        language=language,
                    )
                    if not self.client:
                        raise ValueError("Client not initialized")
                    tasks.append(
                        asyncio.create_task(
                            self.chunk_generator.generate_chunk(request, self.client)
                        )
                    )

                self.running_tasks.extend(tasks)

                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    logger.info(
                        f"Chunk group {group_start} to {group_end - 1} cancelled"
                    )
                    raise
                finally:
                    self.running_tasks = [t for t in self.running_tasks if not t.done()]

                for index, chunk, result in zip(group_indices, group_chunks, results):
                    if isinstance(result, Exception):
                        logger.error(f"Chunk {index} failed with exception: {result}")
                        failed_chunks.append((index, chunk))
                    elif isinstance(result, tuple):
                        idx, chunk_summary, tokens_used = result
                        if chunk_summary is None:
                            logger.warning(
                                f"Chunk {index} failed, added to failed_chunks for retry"
                            )
                            failed_chunks.append((index, chunk))
                        else:
                            chunk_summaries[index] = chunk_summary
                            total_tokens_used += tokens_used
                            accumulated_summary += (
                                "\n" + chunk_summary
                                if accumulated_summary
                                else chunk_summary
                            )
                    else:
                        logger.error(
                            f"Unexpected result type for chunk {index}: {type(result)}"
                        )
                        failed_chunks.append((index, chunk))

                if callback:
                    await callback(accumulated_summary)

            if failed_chunks:
                logger.info(f"Retrying {len(failed_chunks)} failed chunks")
                for index, chunk in failed_chunks:
                    logger.info(f"Retrying failed chunk {index}")
                    request = ChunkProcessingRequest(
                        index=index,
                        chunk=chunk,
                        prompt=prompt,
                        accumulated_summary=accumulated_summary,
                        model=model,
                        language=language,
                    )
                    if not self.client:
                        raise ValueError("Client not initialized")
                    result = await self.chunk_generator.generate_chunk(
                        request, self.client
                    )
                    idx, chunk_summary, tokens_used = result
                    if chunk_summary is not None:
                        chunk_summaries[index] = chunk_summary
                        total_tokens_used += tokens_used
                        accumulated_summary += (
                            "\n" + chunk_summary
                            if accumulated_summary
                            else chunk_summary
                        )
                    else:
                        logger.error(
                            f"Retry failed for chunk {index}, omitting from summary"
                        )

            full_summary = "\n".join(
                summary for summary in chunk_summaries if summary is not None
            ).strip()
            return full_summary, total_tokens_used

        except asyncio.CancelledError:
            logger.info("Processing cancelled, returning partial summary")
            partial_summary = "\n".join(
                summary for summary in chunk_summaries if summary is not None
            ).strip()
            return partial_summary, total_tokens_used

    async def _process_queue(self) -> None:
        logger.info("Starting queue processor")
        idle_time = 0
        max_idle_time = int(os.getenv("MAX_IDLE_TIME", 60))
        while self.running:
            try:
                if self.task_queue.empty():
                    await asyncio.sleep(1)
                    idle_time += 1
                    if idle_time >= max_idle_time and len(self.running_tasks) <= 1:
                        logger.warning(
                            f"Queue idle too long ({idle_time}s) with minimal tasks, forcing shutdown"
                        )
                        await self.api_service.shutdown()
                        break
                    continue
                idle_time = 0
                async with self.queue_lock:
                    func, args = await self.task_queue.get()
                try:
                    task = asyncio.create_task(func(*args))
                    self.running_tasks.append(task)
                    await task
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(
                        f"Error processing queued task {func.__name__}: {str(e)}",
                        exc_info=True,
                    )
                finally:
                    async with self.queue_lock:
                        self.task_queue.task_done()
                        self.task_done_calls += 1
            except asyncio.CancelledError:
                if not self.running:
                    logger.info("Queue processor stopped gracefully")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in queue processor: {str(e)}", exc_info=True
                )

    async def generate_summary_documents(
        self, prompt_config: PromptConfig, file_configs: List[FileConfig]
    ) -> List[SummaryResponse]:
        logger.info(f"Starting summary generation for {len(file_configs)} documents")
        try:
            if not await self.api_service.check_api_connectivity(prompt_config.model):
                logger.error("Cannot proceed: API connectivity check failed")
                return [
                    SummaryResponse(
                        success=False,
                        summary="",
                        message="API connectivity check failed",
                    )
                    for _ in file_configs
                ]
            self.history_token_model.model = prompt_config.model
            self.history_token_model.language_output = (
                prompt_config.language.name.lower()
            )

            prompt = await self.advanced_prompt_generator.generate_prompt(
                prompt_config.category,
                prompt_config.style,
                prompt_config.format,
                prompt_config.language,
                prompt_config.summary_level,
            )

            tasks = [
                self._process_single_document(
                    prompt,
                    file_config,
                    prompt_config.model,
                    prompt_config.language,
                    prompt_config,
                )
                for file_config in file_configs
            ]
            return await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(
                f"Error in generate_summary_documents: {str(e)}", exc_info=True
            )
            return [
                SummaryResponse(
                    success=False,
                    summary="",
                    message=f"Error generating summaries: {str(e)}",
                )
                for _ in file_configs
            ]

    async def _process_single_document(
        self,
        prompt: str,
        file_config: FileConfig,
        model: ModelType,
        language: LanguageType,
        prompt_config: PromptConfig,
    ) -> SummaryResponse:
        self.client = await self.api_service._initialize_client(model)
        request = DocumentProcessingRequest(
            prompt_config=prompt_config, file_config=file_config
        )
        return await self.document_processor.process_single_document(
            request, prompt, self.process_chunks_in_groups
        )
