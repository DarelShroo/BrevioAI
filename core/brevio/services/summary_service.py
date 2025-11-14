import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine, List, Optional, Tuple

import aiofiles
import httpx
import markdown
from bs4 import BeautifulSoup, Tag
from docx import Document
from dotenv import load_dotenv
from googletrans import Translator
from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.brevio.constants.summary_messages import SummaryMessages
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.role import RoleType
from core.brevio.enums.style import StyleType
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.shared.enums.model import ModelType
from core.shared.enums.type_call import TypeCall
from core.shared.models.brevio.history_token_call import HistoryTokenCall
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.models.user.data_result import DataResult
from core.shared.utils.json_data_utils import save_log_to_json
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
        self.tokens_per_minute = int(os.getenv("MAX_TOKEN_PER_MINUTE", 200000))
        self.temperature = float(os.getenv("TEMPERATURE", 0.2))
        self.max_concurrent_chunks = 8
        self.max_concurrent_files = 1000
        self.max_concurrent_requests = 100000
        self.token_bucket = self.tokens_per_minute

        self.last_token_reset = time.time()
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
        self.MIN_TOKENS_FOR_POSTPROCESS = 2000
        logger.debug(
            f"Initialized with max_tokens={self.max_tokens}, "
            f"max_tokens_per_chunk={self.max_tokens_per_chunk}, "
            f"tokens_per_minute={self.tokens_per_minute}, "
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
            # Primero, detener el procesador
            self.running = False
            # Cancelar todas las tareas pendientes
            if self.running_tasks:
                for task in self.running_tasks:
                    if not task.done():
                        task.cancel()
                        logger.debug(
                            f"Cancelled task: {task.get_name() if hasattr(task, 'get_name') else 'unnamed'}"
                        )
                # Esperar a que se cancelen
                if self.running_tasks:
                    await asyncio.gather(*self.running_tasks, return_exceptions=True)
                    logger.debug("All running tasks cancelled or completed.")
            # Luego, shutdown del API service
            await self.api_service.shutdown()
            logger.debug("SummaryService shutdown completed")

    async def chunk_text(
        self, text: str, chunk_size: int, overlap: float, model: ModelType
    ) -> List[str]:
        logger.debug(
            f"Chunking text of length {len(text)} with chunk_size={chunk_size}, overlap={overlap}"
        )
        encoder = get_encoder(model)
        tokens = encoder.encode(text)
        input_tokens = len(tokens)
        logger.debug(f"Encoded text to {input_tokens} tokens")

        chunks = []
        chunk_token_counts = []

        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            chunk_token_count = len(encoder.encode(chunk_text))
            chunk_token_counts.append(chunk_token_count)
            logger.debug(
                f"Created chunk {len(chunks)-1}: {chunk_token_count} tokens, preview={chunk_text[:50]}..."
            )

            overlap_tokens = int(chunk_size * overlap)
            start = end - overlap_tokens if end - overlap_tokens > start else end

        logger.info(
            f"Text split into {len(chunks)} chunks, "
            f"total_input_tokens={input_tokens}, "
            f"chunk_size={chunk_size}, overlap={overlap}, "
            f"chunk_token_counts={chunk_token_counts}"
        )
        return chunks

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

    async def _check_token_limit(self, tokens_needed: int) -> bool:
        await self._update_token_bucket()
        safety_margin = self.tokens_per_minute * 0.1
        if self.token_bucket >= (tokens_needed + safety_margin):
            logger.debug(
                f"Token check passed: needed={tokens_needed}, available={self.token_bucket}"
            )
            return True
        waited = 0
        max_wait = int(os.getenv("MAX_TOKEN_WAIT", 300))  # 5 minutos
        while waited <= max_wait:
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
            f"Could not acquire {tokens_needed} tokens after {max_wait}s"
        )

    @retry(
        wait=wait_exponential(multiplier=2, min=1, max=30),
        stop=stop_after_attempt(8),
        retry=retry_if_exception_type(
            (
                RateLimitError,
                APIConnectionError,
                AuthenticationError,
                asyncio.TimeoutError,
                httpx.HTTPError,
            )
        ),
    )
    async def generate_summary_chunk(
        self,
        index: int,
        chunk: str,
        prompt: str,
        accumulated_summary: str,
        model: ModelType,
        language: LanguageType,
        retries: int = 0,
    ) -> Tuple[int, Optional[str], int]:
        MAX_RETRIES_PER_CHUNK = 10

        if retries > MAX_RETRIES_PER_CHUNK:
            logger.error(
                f"Chunk {index} alcanzó máximo de retries ({MAX_RETRIES_PER_CHUNK}), descartado"
            )
            return index, None, 0

        logger.info(
            f"Processing chunk {index} (retry={retries}) for model {model.value}"
        )

        try:
            encoder = get_encoder(model)
            chunk_tokens = len(encoder.encode(chunk))
            summary_tokens = encoder.encode(accumulated_summary)
            truncated_tokens = (
                summary_tokens[-self.context_token_limit :]
                if len(summary_tokens) > self.context_token_limit
                else summary_tokens
            )

            previous_context = encoder.decode(truncated_tokens)

            previous_context_prompt = ""
            if len(previous_context) > 0:
                previous_context_prompt = (
                    await self.advanced_prompt_generator.get_summary_chunk_prompt(
                        previous_context, language
                    )
                )

            full_prompt = prompt + "\n" + previous_context_prompt

            messages: List[ChatCompletionMessageParam] = [
                {"role": RoleType.SYSTEM.value, "content": full_prompt},
                {"role": RoleType.USER.value, "content": chunk},
            ]

            if not self.client:
                raise ValueError("Client not initialized")

            try:
                response: ChatCompletion = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model.value,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    ),
                    timeout=300,
                )
                system_tokens = len(encoder.encode(full_prompt))
                user_tokens = len(encoder.encode(chunk))
                output_tokens = (
                    response.usage.completion_tokens
                    if response.usage is not None
                    else 0
                )
                self.history_token_model.history_tokens_per_call.append(
                    HistoryTokenCall(
                        type_call=TypeCall.SUMMARY,
                        system_prompt_tokens=system_tokens,
                        user_prompt_tokens=user_tokens,
                        response_tokens=output_tokens,
                    )
                )
                self.history_token_model.total_tokens_summary_input += (
                    system_tokens + user_tokens
                )
                self.history_token_model.total_tokens_summary_output += output_tokens
            except asyncio.TimeoutError:
                logger.warning(f"Timeout processing chunk {index}, requeueing...")
                await self._requeue_chunk(
                    index,
                    chunk,
                    prompt,
                    accumulated_summary,
                    model,
                    language,
                    retries + 1,
                )
                return index, None, 0
            except (BadRequestError, AuthenticationError) as e:
                logger.error(f"Chunk {index} error irreparable: {e}")
                return index, None, 0

            if not hasattr(response, "choices") or not response.choices:
                logger.error(f"Invalid API response for chunk {index}")
                return index, None, 0

            content = response.choices[0].message.content
            if not content or not content.strip():
                logger.warning(f"Chunk {index} has no content in response")
                return index, None, 0

            content += "\n\n" + "\u200b"

            summary = content.strip()
            word_count = len(summary.split())
            if word_count < 10:
                logger.warning(f"Chunk {index} summary too short: {word_count} words")
                return index, None, 0

            output_tokens = len(encoder.encode(summary))
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.token_bucket -= tokens_used

            logger.info(
                f"Chunk {index} processed: output_tokens={output_tokens}, "
                f"total_tokens_used={tokens_used}, tokens_remaining={self.token_bucket}"
            )

            return index, summary, tokens_used

        except (
            RateLimitError,
            APIConnectionError,
            AuthenticationError,
            httpx.HTTPError,
        ) as e:
            logger.warning(f"Retryable error on chunk {index}: {e}, requeueing...")
            await self._requeue_chunk(
                index, chunk, prompt, accumulated_summary, model, language, retries + 1
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error on chunk {index}: {e}", exc_info=True)
            return index, None, 0

    async def _requeue_chunk(
        self,
        index: int,
        chunk: str,
        prompt: str,
        accumulated_summary: str,
        model: ModelType,
        language: LanguageType,
        retries: int = 0,
    ) -> None:
        async with self.queue_lock:
            await self.task_queue.put(
                (
                    self.generate_summary_chunk,
                    [
                        index,
                        chunk,
                        prompt,
                        accumulated_summary,
                        model,
                        language,
                        retries,
                    ],
                )
            )
            self.tasks_put += 1
            logger.debug(f"Chunk {index} requeued, total tasks put: {self.tasks_put}")

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

                while not await self._check_token_limit(total_tokens_needed):
                    logger.warning(
                        f"Token limit reached for group: needed={total_tokens_needed}, "
                        f"available={self.token_bucket}. Waiting 5 seconds"
                    )
                    try:
                        await asyncio.sleep(5)
                    except asyncio.CancelledError:
                        logger.info("Cancelled while waiting for tokens")
                        raise

                tasks = [
                    asyncio.create_task(
                        self.generate_summary_chunk(
                            index, chunk, prompt, accumulated_summary, model, language
                        )
                    )
                    for index, chunk in zip(group_indices, group_chunks)
                ]
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
                            logger.debug(
                                f"Chunk {index} added to summary: "
                                f"summary_length={len(accumulated_summary)}, "
                                f"summary_tokens={len(encoder.encode(accumulated_summary))}"
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
                    result = await self.generate_summary_chunk(
                        index, chunk, prompt, accumulated_summary, model, language
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
                        logger.debug(
                            f"Retry succeeded for chunk {index}: "
                            f"summary_length={len(accumulated_summary)}, "
                            f"summary_tokens={len(encoder.encode(accumulated_summary))}"
                        )
                    else:
                        logger.error(
                            f"Retry failed for chunk {index}, omitting from summary"
                        )

            full_summary = "\n".join(
                summary for summary in chunk_summaries if summary is not None
            ).strip()
            logger.info(
                f"Full summary generated: length={len(full_summary)}, preview={full_summary[:50]}..."
            )
            return full_summary, total_tokens_used

        except asyncio.CancelledError:
            logger.info("Processing cancelled, returning partial summary")
            partial_summary = "\n".join(
                summary for summary in chunk_summaries if summary is not None
            ).strip()
            logger.debug(
                f"Partial summary on cancellation: length={len(partial_summary)}"
            )
            return partial_summary, total_tokens_used

    async def _process_queue(self) -> None:
        logger.info("Starting queue processor")
        idle_time = 0
        max_idle_time = int(os.getenv("MAX_IDLE_TIME", 60))  # 60 segundos por defecto
        while self.running:
            try:
                if self.task_queue.empty():
                    await asyncio.sleep(1)
                    idle_time += 1
                    logger.debug(
                        f"Queue empty, idle_time={idle_time}s, running_tasks={len(self.running_tasks)}"
                    )
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
                logger.debug(f"Retrieved task from queue: {func.__name__}")
                try:
                    task = asyncio.create_task(func(*args))
                    self.running_tasks.append(task)
                    await task
                    logger.debug(f"Completed task: {func.__name__}")
                except asyncio.CancelledError:
                    logger.info(f"Task cancelled: {func.__name__}")
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
                        logger.debug(
                            f"Called task_done() for task: {func.__name__}, total calls: {self.task_done_calls}"
                        )
            except asyncio.CancelledError:
                logger.warning(
                    f"Queue processor cancelled (running={self.running}, "
                    f"queue_size={self.task_queue.qsize()}, running_tasks={len(self.running_tasks)})"
                )
                if not self.running:
                    logger.info("Queue processor stopped gracefully")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in queue processor: {str(e)}", exc_info=True
                )

    @retry(
        wait=wait_exponential(multiplier=2, min=1, max=30),
        stop=stop_after_attempt(8),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, AuthenticationError)
        ),
    )
    async def postprocess_summary(
        self,
        clean_summary: str,
        clean_summary_tokens: int,
        model: ModelType,
        language: LanguageType,
    ) -> str:
        encoder = get_encoder(model)

        logger.info(f"Postprocessing summary: input_tokens={clean_summary_tokens}")

        if not clean_summary.strip():
            logger.error("Input summary is empty, skipping postprocessing")
            return clean_summary

        try:
            tokens_needed = clean_summary_tokens + 500
            logger.debug(f"Postprocessing tokens needed: {tokens_needed}")

            postprocess_prompt = (
                await self.advanced_prompt_generator.get_postprocess_prompt(language)
            )
            logger.debug(f"Postprocess prompt: {postprocess_prompt[:100]}...")
            client = await self.api_service._initialize_client(model)

            if tokens_needed <= self.max_tokens:
                if not await self._check_token_limit(tokens_needed):
                    logger.warning(
                        f"Token limit reached for postprocessing: needed={tokens_needed}, "
                        f"available={self.token_bucket}"
                    )
                    if self.running:
                        async with self.queue_lock:
                            await self.task_queue.put(
                                (
                                    self.postprocess_summary,
                                    [clean_summary, model, language],
                                )
                            )
                            self.tasks_put += 1
                            logger.debug(
                                f"Queued postprocess_summary task, total tasks put: {self.tasks_put}"
                            )
                    else:
                        logger.warning(
                            "Service is shutting down, not queuing postprocess task"
                        )
                    return clean_summary

                try:
                    response: ChatCompletion = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model.value,
                            messages=[
                                {"role": "system", "content": postprocess_prompt},
                                {"role": "user", "content": f"\n\n{clean_summary}"},
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=300,
                    )
                    system_tokens = len(encoder.encode(postprocess_prompt))
                    user_tokens = len(encoder.encode(f"\n\n{clean_summary}"))
                    output_tokens = (
                        response.usage.completion_tokens
                        if response.usage is not None
                        else 0
                    )

                    self.history_token_model.history_tokens_per_call.append(
                        HistoryTokenCall(
                            type_call=TypeCall.POSTPROCESSING,
                            system_prompt_tokens=system_tokens,
                            user_prompt_tokens=user_tokens,
                            response_tokens=output_tokens,
                        )
                    )
                    self.history_token_model.total_tokens_postprocess_input += (
                        system_tokens + user_tokens
                    )
                    self.history_token_model.total_tokens_postprocess_output += (
                        output_tokens
                    )
                    logger.debug(f"Postprocess API response: {response}")
                except asyncio.TimeoutError:
                    logger.error(
                        "Timeout in postprocess_summary: API call exceeded 90 seconds"
                    )
                    return clean_summary
                except BadRequestError as e:
                    logger.error(
                        f"Bad request error in postprocessing: {str(e)}", exc_info=True
                    )
                    return clean_summary
                except AuthenticationError as e:
                    logger.error(
                        f"Authentication error in postprocessing: {str(e)}",
                        exc_info=True,
                    )
                    return clean_summary

                content = response.choices[0].message.content
                if content is None or not content.strip():
                    logger.error("Postprocess response content is None or empty")
                    return clean_summary
                content += "\n\n" + "\u200b"
                word_count = len(content.split())
                if word_count < clean_summary_tokens // 4:
                    logger.warning(
                        f"Postprocessed summary is too short: {word_count} words, "
                        f"expected at least {clean_summary_tokens // 4}, "
                        f"content={content[:50]}..."
                    )
                    return clean_summary

                output_tokens = len(encoder.encode(content))
                total_tokens_used = response.usage.total_tokens if response.usage else 0
                self.token_bucket -= total_tokens_used
                reduction_factor = (
                    output_tokens / clean_summary_tokens
                    if clean_summary_tokens > 0
                    else 0
                )

                logger.info(
                    f"Postprocessing completed: output_tokens={output_tokens}, "
                    f"total_tokens_used={total_tokens_used}, "
                    f"reduction_factor={reduction_factor:.4f}, "
                    f"summary_preview={content[:50]}..."
                )
                return content.strip()

            overlap = self.max_tokens_per_chunk * self._percent_chunk_overlap
            chunks = await self.chunk_text(
                clean_summary, self.max_tokens_per_chunk, overlap, model
            )
            logger.debug(f"Summary split into {len(chunks)} chunks for postprocessing")

            chunk_results: List[Optional[str]] = [None] * len(chunks)
            total_tokens_used = 0

            for i, chunk in enumerate(chunks):
                chunk_tokens = len(encoder.encode(chunk))
                tokens_needed = chunk_tokens + 500
                if not await self._check_token_limit(tokens_needed):
                    logger.warning(
                        f"Token limit reached for postprocess chunk {i}: needed={tokens_needed}, "
                        f"available={self.token_bucket}"
                    )
                    return clean_summary

                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model.value,
                            messages=[
                                {"role": "system", "content": postprocess_prompt},
                                {"role": "user", "content": f"\n\n{chunk}"},
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=300,
                    )

                    system_tokens = len(encoder.encode(postprocess_prompt))
                    user_tokens = len(encoder.encode(f"\n\n{clean_summary}"))
                    output_tokens = (
                        response.usage.completion_tokens
                        if response.usage is not None
                        else 0
                    )

                    self.history_token_model.history_tokens_per_call.append(
                        HistoryTokenCall(
                            type_call=TypeCall.POSTPROCESSING,
                            system_prompt_tokens=system_tokens,
                            user_prompt_tokens=user_tokens,
                            response_tokens=output_tokens,
                        )
                    )
                    self.history_token_model.total_tokens_postprocess_input += (
                        system_tokens + user_tokens
                    )
                    self.history_token_model.total_tokens_postprocess_output += (
                        output_tokens
                    )
                    content = response.choices[0].message.content

                    if content is None or not content.strip():
                        logger.error(f"Postprocess chunk {i} response is empty")
                        return clean_summary

                    content += "\n\n" + "\u200b"

                    word_count = len(content.split())
                    if word_count < chunk_tokens // 4:
                        logger.warning(
                            f"Postprocessed chunk {i} is too short: {word_count} words, "
                            f"expected at least {chunk_tokens // 4}, "
                            f"content={content[:50]}..."
                        )
                        return clean_summary

                    chunk_results[i] = content.strip()
                    total_tokens_used += (
                        response.usage.total_tokens if response.usage else 0
                    )
                    logger.debug(
                        f"Postprocessed chunk {i}: output_tokens={len(encoder.encode(content))}, "
                        f"preview={content[:50]}..."
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Timeout in postprocess chunk {i}: API call exceeded 90 seconds"
                    )
                    return clean_summary
                except Exception as e:
                    logger.error(
                        f"Failed to postprocess chunk {i}: {str(e)}", exc_info=True
                    )
                    return clean_summary

            final_summary = "\n".join(
                result for result in chunk_results if result is not None
            ).strip()
            final_word_count = len(final_summary.split())
            if final_word_count < clean_summary_tokens // 4:
                logger.warning(
                    f"Postprocessed chunked summary is too short: {final_word_count} words, "
                    f"expected at least {clean_summary_tokens // 4}, "
                    f"content={final_summary[:50]}..."
                )
                return clean_summary

            final_summary_tokens = len(encoder.encode(final_summary))
            reduction_factor = (
                final_summary_tokens / clean_summary_tokens
                if clean_summary_tokens > 0
                else 0
            )
            logger.info(
                f"Postprocessing of chunks completed: "
                f"total_tokens_used={total_tokens_used}, "
                f"final_summary_tokens={final_summary_tokens}, "
                f"reduction_factor={reduction_factor:.4f}, "
                f"final_summary_preview={final_summary[:50]}..."
            )
            return final_summary

        except (RateLimitError, APIConnectionError, AuthenticationError) as e:
            logger.error(f"Retryable error in postprocessing: {str(e)}", exc_info=True)
            raise
        except asyncio.CancelledError:
            logger.info("Postprocessing cancelled")
            raise
        except Exception as e:
            logger.error(f"Postprocessing failed: {str(e)}", exc_info=True)
            return clean_summary

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
            self.history_token_model.summary_level = prompt_config.summary_level.value
            self.history_token_model.category = CategoryType(
                prompt_config.category
            ).value
            self.history_token_model.style = StyleType(prompt_config.style).value
            self.history_token_model.output_format = prompt_config.format.value

            prompt = await self.advanced_prompt_generator.generate_prompt(
                category=CategoryType(prompt_config.category),
                style=StyleType(prompt_config.style),
                output_format=prompt_config.format,
                lang=prompt_config.language,
                summary_level=prompt_config.summary_level,
            )

            model = prompt_config.model

            results = []
            for file_config in file_configs:
                logger.debug(
                    f"Processing document sequentially: {file_config.document_path}"
                )
                try:
                    result = await self._process_single_document(
                        prompt, file_config, model, prompt_config.language
                    )
                    results.append(result)
                    logger.info(
                        f"Completed processing for {file_config.document_path}: success={result.success}, message={result.message}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing document {file_config.document_path}: {str(e)}",
                        exc_info=True,
                    )
                    results.append(
                        SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Error processing document: {str(e)}",
                        )
                    )

            logger.info(f"All document summaries completed, results: {len(results)}")

            return results
        except asyncio.CancelledError:
            logger.info("Summary generation cancelled")
            raise
        except Exception as e:
            logger.error(
                f"Error in multiple document summary generation: {str(e)}",
                exc_info=True,
            )
            raise

    async def detect_language_with_retry_safe(self, text: str) -> str:
        fallback_lang = "en"

        @retry(
            wait=wait_exponential(multiplier=5, min=10, max=60),
            stop=stop_after_attempt(10),
            retry=retry_if_exception_type(
                (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPError, Exception)
            ),
            reraise=True,
        )
        async def _detect(text: str) -> str:
            try:
                result = await asyncio.to_thread(self.translator.detect, text)
                return getattr(result, "lang", fallback_lang)
            except Exception as e:
                logger.error(f"Error detectando idioma: {e}", exc_info=True)
                raise

        try:
            if not text.strip():
                logger.warning(
                    "No text available for language detection, using fallback English"
                )
                return fallback_lang
            detected_lang = await _detect(text[:2000])
            logger.info(f"Detected language: {detected_lang}")
            return detected_lang
        except Exception as e:
            logger.warning(
                f"Language detection ultimately failed, falling back to English: {e}"
            )
            return fallback_lang

    async def _process_single_document(
        self,
        prompt: str,
        file_config: FileConfig,
        model: ModelType,
        language: LanguageType,
    ) -> SummaryResponse:
        from core.brevio_api.services.billing.billing_estimator_service import (
            BillingEstimatorService,
        )

        billing_estimator = BillingEstimatorService()
        encoder = get_encoder(model)
        logger.info(f"Processing document: {file_config.document_path}")
        try:
            try:
                assert (
                    file_config.document_path is not None
                ), "document_path must be provided"
                assert (
                    file_config.summary_path is not None
                ), "summary_path must be provided"

                logger.debug(f"Validating paths for {file_config.document_path}")
                try:
                    await self.directory_manager.validate_paths(
                        file_config.document_path
                    )
                except Exception as e:
                    logger.error(
                        f"Path validation failed for {file_config.document_path}: {str(e)}"
                    )
                    return SummaryResponse(
                        success=False,
                        summary="",
                        message=f"Path validation failed: {str(e)}",
                    )

                file_extension = (
                    file_config.document_path.split(".")[-1].lower()
                    if file_config.document_path
                    else ""
                )
                logger.debug(f"Detected file extension: {file_extension}")

                full_text = ""
                if file_extension == "pdf":
                    logger.debug(f"Reading PDF: {file_config.document_path}")
                    try:
                        pdf = await self.directory_manager.read_pdf(
                            file_config.document_path, self.history_token_model
                        )
                        fragments = list(pdf)
                        full_text = "\n".join(fragments)
                    except Exception as e:
                        logger.error(
                            f"Failed to read PDF {file_config.document_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to read PDF: {str(e)}",
                        )
                elif file_extension == "docx":
                    logger.debug(f"Reading DOCX: {file_config.document_path}")
                    try:
                        full_text = await self.directory_manager.read_docx(
                            file_config.document_path
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to read DOCX {file_config.document_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to read DOCX: {str(e)}",
                        )
                else:
                    logger.error(f"Unsupported file type: {file_extension}")
                    return SummaryResponse(
                        success=False,
                        summary="",
                        message=f"Unsupported file type: {file_extension}",
                    )

                logger.debug(f"Text extracted, length: {len(full_text)} characters")

                try:
                    logger.debug("Detecting language")
                    text_sample = full_text[:2000] if full_text else ""
                    if not text_sample:
                        logger.warning(
                            f"No text available for language detection in {file_config.document_path}"
                        )
                        self.history_token_model.language_input = (
                            LanguageType.ENGLISH.name.lower()
                        )

                    else:
                        detected_language = await self.detect_language_with_retry_safe(
                            text_sample
                        )
                        try:
                            if detected_language in LanguageType._value2member_map_:
                                self.history_token_model.language_input = LanguageType(
                                    detected_language
                                ).name.lower()

                            else:
                                raise ValueError(
                                    f"Unsupported language: {detected_language}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to set language input: {str(e)}",
                                exc_info=True,
                            )
                            self.history_token_model.language_input = LanguageType(
                                "en"
                            ).name.lower()

                        logger.info(f"Detected language: {detected_language}")
                except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                    logger.warning(
                        f"Language detection failed after retries: {str(e)}. Falling back to English"
                    )
                    self.history_token_model.language_input = LanguageType(
                        "en"
                    ).name.lower()
                except Exception as e:
                    logger.error(
                        f"Unexpected error in language detection: {str(e)}",
                        exc_info=True,
                    )
                    self.history_token_model.language_input = LanguageType(
                        "en"
                    ).name.lower()

                file_tokens = len(encoder.encode(full_text))
                self.history_token_model.num_tokens_file = file_tokens
                logger.debug(f"Set num_tokens_file: {file_tokens}")

                overlap = self.max_tokens_per_chunk * self._percent_chunk_overlap
                chunks = await self.chunk_text(
                    full_text, self.max_tokens_per_chunk, overlap, model
                )
                logger.info(
                    f"Document split into {len(chunks)} chunks: "
                    f"chunk_size={self.max_tokens_per_chunk}, "
                    f"overlap={overlap}"
                )

                partial_summary_file = file_config.summary_path + ".partial"
                partial_backup_file = file_config.summary_path + ".partial.bak"

                async def save_partial_summary(summary: str) -> None:
                    try:
                        # Guardar archivo principal
                        async with aiofiles.open(
                            partial_summary_file, "w", encoding="utf-8"
                        ) as f:
                            await f.write(summary)
                        # Guardar archivo de respaldo
                        async with aiofiles.open(
                            partial_backup_file, "w", encoding="utf-8"
                        ) as f:
                            await f.write(summary)

                        logger.debug(
                            f"Partial summary saved successfully to {partial_summary_file} and {partial_backup_file}, length={len(summary)}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to save partial summary to {partial_summary_file}: {str(e)}",
                            exc_info=True,
                        )

                full_summary: str = ""
                final_summary: str = ""
                try:
                    logger.debug("Generating summary for chunks")
                    (
                        full_summary,
                        total_tokens_used,
                    ) = await self.process_chunks_in_groups(
                        chunks,
                        prompt,
                        model,
                        language,
                        callback=save_partial_summary,
                    )
                    logger.debug(
                        f"Full summary before postprocessing: length={len(full_summary)}, preview={full_summary[:50]}..."
                    )
                    logger.debug("Postprocessing summary")

                    clean_summary = "\n".join(
                        line
                        for line in full_summary.split("\n")
                        if not line.startswith("Error procesando chunk")
                    ).strip()
                    clean_summary_tokens = len(encoder.encode(clean_summary))

                    if clean_summary_tokens < self.MIN_TOKENS_FOR_POSTPROCESS:
                        logger.warning(
                            f"Clean summary too short for postprocessing: tokens={clean_summary_tokens}, "
                            f"minimum required={self.MIN_TOKENS_FOR_POSTPROCESS}"
                        )
                    else:
                        logger.debug(
                            f"Proceeding with postprocessing: tokens={clean_summary_tokens}"
                        )
                        final_summary += await self.postprocess_summary(
                            clean_summary,
                            clean_summary_tokens,
                            model,
                            language,
                        )

                    final_word_count = len(final_summary.split())
                    if final_word_count < len(full_summary.split()) // 4:
                        logger.warning(
                            f"Postprocessed summary is too short: {final_word_count} words, "
                            f"expected at least {len(full_summary.split()) // 4}, "
                            f"content={final_summary[:50]}..."
                        )
                        file_exists = await asyncio.to_thread(
                            os.path.exists, partial_summary_file
                        )
                        if file_exists:
                            try:
                                async with aiofiles.open(
                                    partial_summary_file, "r", encoding="utf-8"
                                ) as f:
                                    partial_summary = await f.read()
                                if partial_summary.strip():
                                    logger.info(
                                        f"Using partial summary as fallback: length={len(partial_summary)}"
                                    )
                                    final_summary = partial_summary
                                else:
                                    logger.warning(
                                        f"Partial summary file {partial_summary_file} is empty"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Failed to read partial summary file {partial_summary_file}: {str(e)}",
                                    exc_info=True,
                                )
                except asyncio.CancelledError:
                    logger.info(
                        f"Document processing cancelled: {file_config.document_path}"
                    )
                    if full_summary is not None:
                        try:
                            clean_summary = "\n".join(
                                line
                                for line in full_summary.split("\n")
                                if not line.startswith("Error procesando chunk")
                            ).strip()
                            clean_summary_tokens = len(encoder.encode(clean_summary))
                            if clean_summary_tokens < self.MIN_TOKENS_FOR_POSTPROCESS:
                                logger.warning(
                                    f"Clean summary too short for postprocessing: tokens={clean_summary_tokens}, "
                                    f"minimum required={self.MIN_TOKENS_FOR_POSTPROCESS}"
                                )
                            else:
                                logger.debug(
                                    f"Proceeding with postprocessing: tokens={clean_summary_tokens}"
                                )
                                final_summary = await self.postprocess_summary(
                                    clean_summary,
                                    clean_summary_tokens,
                                    model,
                                    language,
                                )

                            message = "Processing cancelled during postprocessing, full summary available"
                        except Exception as e:
                            final_summary = full_summary
                            message = f"Processing cancelled, full summary available but postprocessing failed: {str(e)}"
                    elif file_exists:
                        try:
                            async with aiofiles.open(
                                partial_summary_file, "r", encoding="utf-8"
                            ) as f:
                                partial_summary = await f.read()
                            if not partial_summary.strip():
                                logger.warning(
                                    f"Partial summary file {partial_summary_file} is empty"
                                )
                                final_summary = "Procesamiento cancelado, no se pudo generar un resumen parcial."
                                message = "Processing cancelled, partial summary file is empty"
                            else:
                                final_summary = (
                                    "Resumen parcial debido a cancelación:\n"
                                    + partial_summary
                                )
                                message = "Processing cancelled, partial summary saved"
                                logger.debug(
                                    f"Read partial summary from {partial_summary_file}, length={len(partial_summary)}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to read partial summary file {partial_summary_file}: {str(e)}",
                                exc_info=True,
                            )
                            final_summary = "Procesamiento cancelado, no se pudo leer el resumen parcial."
                            message = f"Processing cancelled, failed to read partial summary: {str(e)}"
                    else:
                        final_summary = (
                            "Procesamiento cancelado antes de generar un resumen."
                        )
                        message = "Processing cancelled, no summary generated"
                        logger.debug(
                            f"No partial summary file found at {partial_summary_file}"
                        )
                    try:
                        await self.directory_manager.write_summary(
                            final_summary, file_config.summary_path
                        )
                        logger.info(
                            f"Summary written to {file_config.summary_path}, length={len(final_summary)}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to write summary to {file_config.summary_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary=final_summary,
                            message=f"Failed to write summary: {str(e)}",
                        )
                    if file_exists:
                        try:
                            await asyncio.to_thread(os.remove, partial_summary_file)
                            logger.debug(
                                f"Removed partial summary file {partial_summary_file}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to remove partial summary file {partial_summary_file}: {str(e)}"
                            )
                    return SummaryResponse(
                        success=False, summary=final_summary, message=message
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to generate summary for {file_config.document_path}: {str(e)}",
                        exc_info=True,
                    )
                    if file_exists:
                        try:
                            async with aiofiles.open(
                                partial_summary_file, "r", encoding="utf-8"
                            ) as f:
                                partial_summary = await f.read()
                            if partial_summary.strip():
                                final_summary = (
                                    "Resumen parcial debido a error:\n"
                                    + partial_summary
                                )
                                message = f"Processing failed, partial summary saved: {str(e)}"
                                logger.info(
                                    f"Using partial summary as fallback: length={len(partial_summary)}"
                                )
                            else:
                                logger.warning(
                                    f"Partial summary file {partial_summary_file} is empty"
                                )
                                final_summary = ""
                                message = f"Processing failed, partial summary empty: {str(e)}"
                            await self.directory_manager.write_summary(
                                final_summary, file_config.summary_path
                            )
                            logger.info(
                                f"Summary written to {file_config.summary_path}, length={len(final_summary)}"
                            )
                        except Exception as write_e:
                            logger.error(
                                f"Failed to write partial summary to {file_config.summary_path}: {str(write_e)}"
                            )
                            return SummaryResponse(
                                success=False,
                                summary="",
                                message=f"Failed to write partial summary: {str(write_e)}",
                            )
                    else:
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to generate summary: {str(e)}",
                        )
                    if file_exists:
                        try:
                            await asyncio.to_thread(os.remove, partial_summary_file)
                            logger.debug(
                                f"Removed partial summary file {partial_summary_file}"
                            )
                        except Exception as remove_e:
                            logger.error(
                                f"Failed to remove partial summary file {partial_summary_file}: {str(remove_e)}"
                            )
                    return SummaryResponse(
                        success=False, summary=final_summary, message=message
                    )

                logger.debug(f"Writing summary to {file_config.summary_path}")
                try:
                    await self.directory_manager.write_summary(
                        final_summary, file_config.summary_path
                    )
                    logger.info(
                        f"Summary written to {file_config.summary_path}, length={len(final_summary)}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to write summary to {file_config.summary_path}: {str(e)}",
                        exc_info=True,
                    )
                    return SummaryResponse(
                        success=False,
                        summary=final_summary,
                        message=f"Failed to write summary: {str(e)}",
                    )

                logger.debug(f"Creating DOCX version for {file_config.summary_path}")
                try:
                    await self.directory_manager.create_docx_version(
                        file_config.summary_path
                    )

                    logger.info(f"DOCX version created for {file_config.summary_path}")
                except Exception as e:
                    logger.error(
                        f"Failed to create DOCX version for {file_config.summary_path}: {str(e)}",
                        exc_info=True,
                    )
                    return SummaryResponse(
                        success=False,
                        summary=final_summary,
                        message=f"Failed to create DOCX version: {str(e)}",
                    )

                logger.debug("Saving token log")
                try:
                    logger.info(self.history_token_model.model_dump_json(indent=2))
                    await save_log_to_json(
                        self.history_token_model.model_dump_json(indent=2)
                    )
                except Exception as e:
                    logger.error(f"Failed to save token log: {str(e)}", exc_info=True)

                if file_exists:
                    try:
                        await asyncio.to_thread(os.remove, partial_summary_file)
                        logger.debug(
                            f"Removed partial summary file {partial_summary_file}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to remove partial summary file {partial_summary_file}: {str(e)}"
                        )

                return SummaryResponse(
                    success=True,
                    summary=final_summary,
                    message=SummaryMessages.WRITE_SUMMARY.format(
                        file_config.summary_path
                    ),
                )
            finally:
                logger.debug(f"Released file_semaphore for {file_config.document_path}")
        except asyncio.CancelledError:
            logger.info(f"Document processing cancelled: {file_config.document_path}")
            raise
        except ValueError as e:
            logger.error(
                f"Validation error for {file_config.document_path}: {str(e)}",
                exc_info=True,
            )
            return SummaryResponse(
                success=False, summary="", message=f"Validation error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Error processing document {file_config.document_path}: {str(e)}",
                exc_info=True,
            )
            return SummaryResponse(
                success=False,
                summary="",
                message=f"Error processing document: {str(e)}",
            )

    async def _process_single_transcription(
        self,
        prompt_config: PromptConfig,
        file_config: FileConfig,
        data_result: DataResult,
    ) -> SummaryResponse:
        encoder = get_encoder(prompt_config.model)
        logger.info(
            f"Starting transcription processing: {file_config.transcription_path}"
        )

        try:
            self.client = await self.api_service._initialize_client(prompt_config.model)
            logger.debug("Generating prompt...")

            try:
                prompt = await self.advanced_prompt_generator.generate_prompt(
                    category=CategoryType(prompt_config.category),
                    style=StyleType(prompt_config.style),
                    output_format=prompt_config.format,
                    lang=prompt_config.language,
                    summary_level=prompt_config.summary_level,
                )
                logger.debug(f"Prompt generated successfully, length: {len(prompt)}")
            except Exception as e:
                logger.error(f"Failed to generate prompt: {str(e)}", exc_info=True)
                return SummaryResponse(
                    success=False,
                    summary="",
                    message=f"Failed to generate prompt: {str(e)}",
                )

            logger.debug(
                f"Acquired file_semaphore for {file_config.transcription_path}"
            )

            try:
                if not file_config.transcription_path or not file_config.summary_path:
                    raise ValueError(
                        "Both transcription_path and summary_path must be provided"
                    )
                file_exists = await asyncio.to_thread(
                    os.path.exists, file_config.transcription_path
                )
                if not file_exists:
                    raise FileNotFoundError(
                        f"Transcription file not found: {file_config.transcription_path}"
                    )

                try:
                    await self.directory_manager.validate_paths(
                        file_config.transcription_path
                    )
                except Exception as e:
                    logger.error(f"Path validation failed: {str(e)}")
                    return SummaryResponse(
                        success=False,
                        summary="",
                        message=f"Path validation failed: {str(e)}",
                    )

                transcription = await self.directory_manager.read_transcription(
                    file_config.transcription_path
                )
                if not transcription or transcription.strip() == "":
                    raise ValueError(
                        "Transcription is empty or contains only whitespace"
                    )

                input_tokens = len(encoder.encode(transcription))
                logger.debug(f"Transcription read successfully: {input_tokens} tokens")

                try:
                    text_sample = transcription[:2000]
                    if text_sample.strip():
                        detected = await self.detect_language_with_retry_safe(
                            text_sample
                        )
                        detected_language = (
                            detected
                            if detected in LanguageType._value2member_map_
                            else "en"
                        )
                    else:
                        detected_language = "en"

                    self.history_token_model.language_input = LanguageType(
                        detected_language
                    ).name.lower()
                    logger.info(f"Detected language: {detected_language}")
                except Exception as e:
                    logger.error(
                        f"Language detection failed: {str(e)}, defaulting to English",
                        exc_info=True,
                    )
                    detected_language = "en"
                    self.history_token_model.language_input = LanguageType(
                        "en"
                    ).name.lower()

                self.history_token_model.language_output = (
                    prompt_config.language.name.lower()
                )
                self.history_token_model.num_tokens_file = input_tokens
                self.history_token_model.num_chars_file = len(transcription)
                self.history_token_model.total_time = data_result.duration

                total_input_tokens = len(encoder.encode(transcription))

                logger.debug(
                    f"Input statistics: total_tokens={total_input_tokens}, "
                    f"prompt_tokens={len(encoder.encode(prompt))}, transcription_tokens={input_tokens}"
                )

                if total_input_tokens <= self.max_tokens_per_chunk:
                    logger.debug("No chunking needed, processing as single chunk")
                    chunks = [transcription]
                else:
                    overlap = int(
                        self.max_tokens_per_chunk * self._percent_chunk_overlap
                    )
                    logger.debug(
                        f"Creating chunks: size={self.max_tokens_per_chunk}, overlap={overlap}"
                    )
                    chunks = await self.chunk_text(
                        transcription,
                        self.max_tokens_per_chunk,
                        overlap,
                        prompt_config.model,
                    )

                logger.info(f"Processing {len(chunks)} chunks for transcription")

                try:
                    (
                        full_summary,
                        total_tokens_used,
                    ) = await self.process_chunks_in_groups(
                        chunks, prompt, prompt_config.model, prompt_config.language
                    )

                    if not full_summary or full_summary.strip() == "":
                        raise ValueError("Generated summary is empty")

                    logger.debug(
                        f"Summary generated successfully: {len(full_summary)} characters"
                    )
                except Exception as e:
                    logger.error(f"Failed to generate summary: {str(e)}", exc_info=True)
                    return SummaryResponse(
                        success=False,
                        summary="",
                        message=f"Failed to generate summary: {str(e)}",
                    )

                # ✅ Postprocesamiento
                logger.debug("Postprocessing summary...")
                try:
                    clean_summary = "\n".join(
                        line
                        for line in full_summary.split("\n")
                        if not line.startswith("Error procesando chunk")
                    ).strip()
                    clean_summary_tokens = len(encoder.encode(clean_summary))

                    if clean_summary_tokens >= self.MIN_TOKENS_FOR_POSTPROCESS:
                        final_summary = await self.postprocess_summary(
                            clean_summary,
                            clean_summary_tokens,
                            prompt_config.model,
                            prompt_config.language,
                        )
                        logger.debug(
                            f"Summary postprocessed successfully: {len(final_summary)} characters"
                        )
                    else:
                        logger.warning("Clean summary too short for postprocessing")
                        final_summary = clean_summary
                except Exception as e:
                    logger.error(
                        f"Failed to postprocess summary: {str(e)}", exc_info=True
                    )
                    final_summary = full_summary

                try:
                    await asyncio.to_thread(
                        os.makedirs,
                        os.path.dirname(file_config.summary_path),
                        exist_ok=True,
                    )
                    await self.directory_manager.write_summary(
                        final_summary, file_config.summary_path
                    )
                    logger.info(
                        f"Summary written successfully to {file_config.summary_path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to write summary: {str(e)}", exc_info=True)
                    return SummaryResponse(
                        success=False,
                        summary=final_summary,
                        message=f"Summary generated but failed to write: {str(e)}",
                    )

                try:
                    await self.directory_manager.create_docx_version(
                        file_config.summary_path
                    )

                    logger.info("DOCX version created successfully")
                except Exception as e:
                    logger.error(
                        f"Failed to create DOCX version: {str(e)}", exc_info=True
                    )

                summary_tokens = len(encoder.encode(final_summary))
                logger.info(
                    f"Summary completed successfully: "
                    f"input_tokens={total_input_tokens}, summary_tokens={summary_tokens}, "
                    f"total_used_tokens={total_tokens_used}, compression_ratio={summary_tokens/input_tokens:.2f}"
                )

                await save_log_to_json(
                    self.history_token_model.model_dump_json(indent=2)
                )

                return SummaryResponse(
                    success=True,
                    summary=final_summary,
                    message=SummaryMessages.WRITE_SUMMARY.format(
                        file_config.summary_path
                    ),
                )

            except asyncio.CancelledError:
                logger.warning(
                    f"Processing cancelled: {file_config.transcription_path}"
                )
                raise
            except Exception as e:
                logger.error(f"Error in processing block: {str(e)}", exc_info=True)
                return SummaryResponse(
                    success=False, summary="", message=f"Processing error: {str(e)}"
                )
            finally:
                logger.debug(
                    f"Released file_semaphore for {file_config.transcription_path}"
                )

        except asyncio.CancelledError:
            logger.warning(
                f"Transcription processing cancelled: {file_config.transcription_path}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error processing transcription: {str(e)}", exc_info=True
            )
            return SummaryResponse(
                success=False, summary="", message=f"Unexpected error: {str(e)}"
            )

    async def generate_summary_document(
        self,
        prompt_config: PromptConfig,
        file_config: FileConfig,
    ) -> SummaryResponse:
        logger.info(
            f"Starting summary generation for document: {file_config.document_path}"
        )
        self.client = await self.api_service._initialize_client(prompt_config.model)
        try:
            async with self.lifespan():
                results = await self.generate_summary_documents(
                    prompt_config, [file_config]
                )
                if not results:
                    logger.error("No results returned from summary generation")
                    raise ValueError("No results returned from summary generation")
                logger.info(
                    f"Summary generation completed for {file_config.document_path}"
                )
                await self.api_service.shutdown()
                return results[0]
        except asyncio.CancelledError:
            logger.info("Summary generation cancelled")
            raise
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, initiating graceful shutdown")
            await self.api_service.shutdown()
            raise
        except Exception as e:
            logger.error(
                f"Error generating summary for document: {str(e)}", exc_info=True
            )
            return SummaryResponse(
                success=False, summary="", message=f"Error generating summary: {str(e)}"
            )

    async def process_user_summaries(
        self, user_id: int, prompt_config: PromptConfig, file_configs: List[FileConfig]
    ) -> None:
        async with self.lifespan():
            logger.info(
                f"User {user_id} starting summary generation for {len(file_configs)} documents"
            )
            try:
                results = await self.generate_summary_documents(
                    prompt_config, file_configs
                )
                for file_config, result in zip(file_configs, results):
                    encoder = get_encoder(prompt_config.model)
                    tokens = encoder.encode(result.summary)
                    summary_tokens = len(tokens)
                    logger.info(
                        f"User {user_id} summary completed for {file_config.document_path}: "
                        f"success={result.success}, "
                        f"summary_tokens={summary_tokens}, "
                        f"message={result.message}, "
                        f"preview={result.summary[:50]}..."
                    )
            except asyncio.CancelledError:
                logger.info(f"Summary processing cancelled for user {user_id}")
                raise
            except KeyboardInterrupt:
                logger.info(
                    f"Received KeyboardInterrupt for user {user_id}, initiating graceful shutdown"
                )
                await self.api_service.shutdown()
                raise
            except Exception as e:
                logger.error(
                    f"Error processing summaries for user {user_id}: {str(e)}",
                    exc_info=True,
                )
                raise
