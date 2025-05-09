import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine, List, Optional, Tuple

import httpx
import markdown
from bs4 import BeautifulSoup, Tag
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from dotenv import load_dotenv
from googletrans import Translator
from openai import APIConnectionError, AsyncOpenAI, RateLimitError
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.brevio.constants.summary_messages import SummaryMessages
from core.brevio.enums.language import LanguageType
from core.brevio.enums.role import RoleType
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.json_data_utils import save_log_to_json
from core.shared.utils.model_tokens_utils import get_encoder, is_deepseek

from .advanced_content_generator import AdvancedPromptGenerator

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
        self.max_concurrent_files = 4
        self.max_concurrent_requests = 20
        self.token_bucket = self.tokens_per_minute
        self.last_token_reset = time.time()
        self.task_queue: asyncio.Queue[
            Tuple[Callable[..., Coroutine[Any, Any, Any]], List[Any]]
        ] = asyncio.Queue()
        self.running = False
        self._percent_chunk_overlap = 0.2
        self.context_token_limit = 100
        self.api_semaphore = asyncio.Semaphore(4)
        self.file_semaphore = asyncio.Semaphore(self.max_concurrent_files)
        self.running_tasks: List[asyncio.Task] = []
        self.client_lock = asyncio.Lock()
        self.queue_lock = asyncio.Lock()
        self.tasks_put = 0
        self.task_done_calls = 0
        self.clients: dict[str, AsyncOpenAI] = {}
        self.advanced_prompt_generator = AdvancedPromptGenerator()
        self.history_token_model = HistoryTokenModel()
        self.translator = Translator()

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

    async def start(self) -> None:
        if not self.running:
            self.running = True
            task = asyncio.create_task(self._process_queue())
            self.running_tasks.append(task)
            logger.info("Started queue processor")

    async def shutdown(self) -> None:
        if self.running:
            self.running = False
            logger.info("Shutting down SummaryService")
            for task in self.running_tasks:
                task.cancel()
            if self.running_tasks:
                try:
                    await asyncio.gather(*self.running_tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    logger.debug("Tasks cancelled during shutdown")
            self.running_tasks.clear()
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
            async with self.client_lock:
                for model_key, client in self.clients.items():
                    try:
                        if isinstance(client, httpx.AsyncClient):
                            await client.aclose()
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

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        await self.start()
        try:
            yield
        finally:
            await self.shutdown()

    async def set_client(self, model: ModelType) -> None:
        logger.warning(
            "set_client is deprecated; client is now managed via _initialize_client"
        )
        await self._initialize_client(model)

    async def check_api_connectivity(self, model: ModelType) -> bool:
        logger.debug(f"Checking API connectivity for model {model.value}")
        try:
            client = await self._initialize_client(model)
            async with self.api_semaphore:
                await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model.value,
                        messages=[{"role": "user", "content": "Test"}],
                        max_tokens=10,
                    ),
                    timeout=None,
                )
            logger.info(f"API connectivity check passed for {model.value}")
            return True
        except Exception as e:
            logger.error(f"API connectivity check failed for {model.value}: {str(e)}")
            return False

    def chunk_text(
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
        logger.warning(
            f"Token limit reached: needed={tokens_needed}, available={self.token_bucket}"
        )
        return False

    @retry(
        wait=wait_exponential(multiplier=2, min=1, max=30),
        stop=stop_after_attempt(8),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def generate_summary_chunk(
        self,
        index: int,
        chunk: str,
        prompt: str,
        accumulated_summary: str,
        model: ModelType,
    ) -> Tuple[int, str, int]:
        logger.info(f"Processing chunk {index} for model {model.value}")
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
            context_tokens = len(truncated_tokens)

            logger.debug(
                f"Chunk {index} setup: "
                f"context_tokens={context_tokens}, "
                f"previous_context_preview={previous_context[:50]}..."
            )

            full_prompt = self.advanced_prompt_generator.get_summary_chunk_prompt(
                prompt, previous_context
            )

            messages: List[ChatCompletionMessageParam] = [
                {"role": RoleType.SYSTEM.value, "content": full_prompt},
                {"role": RoleType.USER.value, "content": chunk},
            ]

            client = await self._initialize_client(model)

            async with self.api_semaphore:
                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model.value,
                            messages=messages,
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=None,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Timeout processing chunk {index}: API call exceeded 60 seconds"
                    )
                    return index, f"Error procesando chunk {index}: Timeout", 0

                if not hasattr(response, "choices") or not response.choices:
                    logger.error(f"Invalid API response for chunk {index}: {response}")
                    return (
                        index,
                        f"Error procesando chunk {index}: Respuesta inválida de la API",
                        0,
                    )

                content = response.choices[0].message.content
                if content is None:
                    logger.error(f"Chunk {index} has no content in response")
                    return index, "Error: No content in response", 0

                if response.usage:
                    usage: CompletionUsage = response.usage
                    self.history_token_model.num_tokens_summary_input += (
                        usage.prompt_tokens
                    )
                    self.history_token_model.num_tokens_summary_output += (
                        usage.completion_tokens
                    )
                    self.history_token_model.num_total_tokens += usage.total_tokens
                    logger.info(
                        f"Token stats for chunk {index} - input: {self.history_token_model.num_tokens_summary_input}, "
                        f"output: {self.history_token_model.num_tokens_summary_output}, "
                        f"total: {self.history_token_model.num_total_tokens}"
                    )

                summary = content.strip()
                output_tokens = len(encoder.encode(summary))
                tokens_used = (
                    response.usage.total_tokens if response.usage is not None else 0
                )
                self.token_bucket -= tokens_used
                output_factor = output_tokens / chunk_tokens if chunk_tokens > 0 else 0
                logger.info(
                    f"Chunk {index} processed: "
                    f"output_tokens={output_tokens}, "
                    f"total_tokens_used={tokens_used}, "
                    f"tokens_remaining={self.token_bucket}, "
                    f"output_factor={output_factor:.4f}, "
                    f"summary_preview={summary[:50]}..."
                )
                return index, summary, tokens_used

        except (RateLimitError, APIConnectionError) as e:
            logger.error(
                f"Retryable error processing chunk {index}: {str(e)}", exc_info=True
            )
            raise
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error processing chunk {index}: {str(e)}", exc_info=True
            )
            return index, f"Error procesando chunk {index}: {str(e)}", 0
        except Exception as e:
            logger.error(
                f"Unexpected error processing chunk {index}: {str(e)}", exc_info=True
            )
            return index, f"Error procesando chunk {index}: {str(e)}", 0

    async def process_chunks_in_groups(
        self,
        chunks: List[str],
        prompt: str,
        model: ModelType,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, int]:
        logger.info(f"Processing {len(chunks)} chunks in groups")
        accumulated_summary = ""
        total_tokens_used = 0
        chunk_summaries: List[Optional[str]] = [None] * len(chunks)
        try:
            for group_start in range(0, len(chunks), self.max_concurrent_chunks):
                group_end = min(group_start + self.max_concurrent_chunks, len(chunks))
                group_chunks = chunks[group_start:group_end]
                group_indices = list(range(group_start, group_end))
                logger.info(f"Processing chunk group {group_start} to {group_end - 1}")

                total_tokens_needed = sum(
                    len(chunk) // 4 + 500 for chunk in group_chunks
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
                            index, chunk, prompt, accumulated_summary, model
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
                self.running_tasks = [t for t in self.running_tasks if not t.done()]

                for result in results:
                    if isinstance(result, tuple):
                        index, chunk_summary, tokens_used = result
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
                            f"summary_tokens={len(get_encoder(model).encode(accumulated_summary))}"
                        )
                # Guardar el resumen parcial después de cada grupo
                if callback:
                    callback(accumulated_summary)

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
        while self.running:
            try:
                if self.task_queue.empty():
                    await asyncio.sleep(1)
                    continue
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
                    break
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
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Unexpected error in queue processor: {str(e)}", exc_info=True
                )

    async def generate_summary_documents(
        self, prompt_config: PromptConfig, file_configs: List[FileConfig]
    ) -> List[SummaryResponse]:
        logger.info(f"Starting summary generation for {len(file_configs)} documents")
        try:
            if not await self.check_api_connectivity(prompt_config.model):
                logger.error("Cannot proceed: API connectivity check failed")
                return [
                    SummaryResponse(
                        success=False,
                        summary="",
                        message="API connectivity check failed",
                    )
                    for _ in file_configs
                ]

            self.history_token_model.language_output = prompt_config.language
            self.history_token_model.summary_level = prompt_config.summary_level
            self.history_token_model.source_type = prompt_config.source_types
            self.history_token_model.category = prompt_config.category
            self.history_token_model.style = prompt_config.style
            self.history_token_model.output_format = prompt_config.format

            prompt = await self.advanced_prompt_generator.generate_prompt(
                category=prompt_config.category,
                style=prompt_config.style,
                output_format=prompt_config.format,
                lang=prompt_config.language,
                source_type=prompt_config.source_types,
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
                        prompt, file_config, model
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

    async def _process_single_document(
        self, prompt: str, file_config: FileConfig, model: ModelType
    ) -> SummaryResponse:
        from core.brevio_api.services.billing.billing_estimator_service import (
            BillingEstimatorService,
        )

        from ..managers.directory_manager import DirectoryManager

        directory_manager = DirectoryManager()
        billing_estimator = BillingEstimatorService()

        logger.info(f"Processing document: {file_config.document_path}")
        try:
            async with self.file_semaphore:
                logger.debug(f"Acquired file_semaphore for {file_config.document_path}")
                try:
                    # Validación de rutas
                    assert (
                        file_config.document_path is not None
                    ), "document_path must be provided"
                    assert (
                        file_config.summary_path is not None
                    ), "summary_path must be provided"

                    logger.debug(f"Validating paths for {file_config.document_path}")
                    try:
                        await directory_manager.validate_paths(
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
                            fragments = list(
                                directory_manager.read_pdf(
                                    file_config.document_path, self.history_token_model
                                )
                            )
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
                            doc = Document(file_config.document_path)
                            full_text = "\n".join(
                                [
                                    para.text
                                    for para in doc.paragraphs
                                    if para.text.strip()
                                ]
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

                    @retry(
                        wait=wait_exponential(multiplier=2, min=5, max=30),
                        stop=stop_after_attempt(3),
                        retry=retry_if_exception_type(
                            (httpx.ConnectTimeout, httpx.ReadTimeout)
                        ),
                    )
                    async def detect_language_with_retry(text: str) -> Any:
                        async with httpx.AsyncClient(
                            timeout=httpx.Timeout(60.0)
                        ) as client:
                            detected = await asyncio.to_thread(
                                self.translator.detect, text
                            )
                            return await detected

                    try:
                        logger.debug("Detecting language")
                        async with self.api_semaphore:
                            text_sample = full_text[:2000] if full_text else ""
                            if not text_sample:
                                logger.warning(
                                    f"No text available for language detection in {file_config.document_path}"
                                )
                                self.history_token_model.language_input = LanguageType(
                                    "en"
                                )
                            else:
                                detected = await detect_language_with_retry(text_sample)
                                detected_language = detected.lang
                                try:
                                    if (
                                        detected_language
                                        in LanguageType._value2member_map_
                                    ):
                                        self.history_token_model.language_input = (
                                            LanguageType(detected_language)
                                        )
                                    else:
                                        raise ValueError(
                                            f"Unsupported language: {detected_language}"
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Failed to set language input: {str(e)}",
                                        exc_info=True,
                                    )
                                    self.history_token_model.language_input = (
                                        LanguageType("en")
                                    )

                                logger.info(f"Detected language: {detected_language}")
                    except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                        logger.warning(
                            f"Language detection failed after retries: {str(e)}. Falling back to English"
                        )
                        self.history_token_model.language_input = LanguageType("en")
                    except Exception as e:
                        logger.error(
                            f"Unexpected error in language detection: {str(e)}",
                            exc_info=True,
                        )
                        self.history_token_model.language_input = LanguageType("en")

                    full_input_text = prompt + "\n" + full_text
                    total_input_tokens = len(get_encoder(model).encode(full_input_text))

                    file_tokens = len(get_encoder(model).encode(full_text))
                    self.history_token_model.num_tokens_file = file_tokens
                    logger.debug(f"Set num_tokens_file: {file_tokens}")

                    overlap = self.max_tokens_per_chunk * self._percent_chunk_overlap
                    chunks = self.chunk_text(
                        full_input_text, self.max_tokens_per_chunk, overlap, model
                    )
                    logger.info(
                        f"Document split into {len(chunks)} chunks: "
                        f"total_input_tokens={total_input_tokens}, "
                        f"chunk_size={self.max_tokens_per_chunk}, "
                        f"overlap={overlap}"
                    )

                    partial_summary_file = file_config.summary_path + ".partial"

                    def save_partial_summary(summary: str) -> None:
                        try:
                            with open(partial_summary_file, "w", encoding="utf-8") as f:
                                f.write(summary)
                            logger.debug(
                                f"Partial summary saved to {partial_summary_file}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to save partial summary to {partial_summary_file}: {str(e)}"
                            )

                    full_summary = None
                    try:
                        logger.debug("Generating summary for chunks")
                        (
                            full_summary,
                            total_tokens_used,
                        ) = await self.process_chunks_in_groups(
                            chunks, prompt, model, callback=save_partial_summary
                        )
                        logger.debug("Postprocessing summary")
                        final_summary = await self.postprocess_summary(
                            full_summary, model
                        )
                    except asyncio.CancelledError:
                        logger.info(
                            f"Document processing cancelled: {file_config.document_path}"
                        )
                        if full_summary is not None:
                            try:
                                final_summary = await self.postprocess_summary(
                                    full_summary, model
                                )
                                message = "Processing cancelled during postprocessing, full summary available"
                            except Exception as e:
                                final_summary = full_summary
                                message = f"Processing cancelled, full summary available but postprocessing failed: {str(e)}"
                        elif os.path.exists(partial_summary_file):
                            try:
                                with open(
                                    partial_summary_file, "r", encoding="utf-8"
                                ) as f:
                                    partial_summary = f.read()
                                final_summary = (
                                    "Resumen parcial debido a cancelación:\n"
                                    + partial_summary
                                )
                                message = "Processing cancelled, partial summary saved"
                            except Exception as e:
                                final_summary = "Procesamiento cancelado, no se pudo leer el resumen parcial."
                                message = f"Processing cancelled, failed to read partial summary: {str(e)}"
                        else:
                            final_summary = (
                                "Procesamiento cancelado antes de generar un resumen."
                            )
                            message = "Processing cancelled, no summary generated"
                        try:
                            directory_manager.write_summary(
                                final_summary, file_config.summary_path
                            )
                            logger.info(
                                f"Summary written to {file_config.summary_path}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to write summary to {file_config.summary_path}: {str(e)}"
                            )
                            return SummaryResponse(
                                success=False,
                                summary=final_summary,
                                message=f"Failed to write summary: {str(e)}",
                            )
                        if os.path.exists(partial_summary_file):
                            try:
                                os.remove(partial_summary_file)
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
                        if os.path.exists(partial_summary_file):
                            try:
                                with open(
                                    partial_summary_file, "r", encoding="utf-8"
                                ) as f:
                                    partial_summary = f.read()
                                final_summary = (
                                    "Resumen parcial debido a error:\n"
                                    + partial_summary
                                )
                                message = f"Processing failed, partial summary saved: {str(e)}"
                                directory_manager.write_summary(
                                    final_summary, file_config.summary_path
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
                        if os.path.exists(partial_summary_file):
                            try:
                                os.remove(partial_summary_file)
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
                        directory_manager.write_summary(
                            final_summary, file_config.summary_path
                        )
                        logger.info(f"Summary written to {file_config.summary_path}")
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

                    logger.debug(
                        f"Creating DOCX version for {file_config.summary_path}"
                    )
                    try:
                        self._create_docx_version(file_config.summary_path)
                        logger.info(
                            f"DOCX version created for {file_config.summary_path}"
                        )
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

                    try:
                        file_tokens = self.history_token_model.num_tokens_file
                        language_input = self.history_token_model.language_input
                        language_output = (
                            self.history_token_model.language_output
                            if self.history_token_model.language_output
                            else language_input
                        )
                        summary_level = self.history_token_model.summary_level

                        (
                            summary_input_tokens,
                            summary_output_tokens,
                            postprocess_input_tokens,
                            postprocess_output_tokens,
                        ) = billing_estimator.summary_tokens_predict(
                            file_tokens,
                            language_input,
                            language_output,
                            summary_level,
                            self.history_token_model,
                        )

                        self.history_token_model.num_tokens_summary_predict_input = (
                            summary_input_tokens
                        )
                        self.history_token_model.num_tokens_summary_predict_output = (
                            summary_output_tokens
                        )
                        self.history_token_model.num_tokens_postprocess_predict_input = (
                            postprocess_input_tokens
                        )
                        self.history_token_model.num_tokens_postprocess_predict_output = (
                            postprocess_output_tokens
                        )
                        self.history_token_model.num_total_tokens_predict = (
                            summary_input_tokens
                            + summary_output_tokens
                            + postprocess_input_tokens
                            + postprocess_output_tokens
                        )

                        logger.info(
                            f"Token prediction for billing: "
                            f"summary_input_tokens={summary_input_tokens}, "
                            f"summary_output_tokens={summary_output_tokens}, "
                            f"postprocess_output_tokens={postprocess_output_tokens}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to predict tokens for billing: {str(e)}",
                            exc_info=True,
                        )

                    logger.debug("Saving token log")
                    try:
                        logger.info(self.history_token_model.model_dump_json(indent=2))
                        save_log_to_json(
                            self.history_token_model.model_dump_json(indent=2)
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to save token log: {str(e)}", exc_info=True
                        )

                    if os.path.exists(partial_summary_file):
                        try:
                            os.remove(partial_summary_file)
                            logger.debug(
                                f"Removed partial summary file {partial_summary_file}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to remove partial summary file {partial_summary_file}: {str(e)}"
                            )

                    logger.info(
                        {
                            "total_input_tokens": self.history_token_model.num_tokens_summary_input,
                            "total_output_tokens": self.history_token_model.num_tokens_summary_output,
                            "total_tokens": self.history_token_model.num_total_tokens,
                        }
                    )

                    return SummaryResponse(
                        success=True,
                        summary=final_summary,
                        message=SummaryMessages.WRITE_SUMMARY.format(
                            file_config.summary_path
                        ),
                    )
                finally:
                    logger.debug(
                        f"Released file_semaphore for {file_config.document_path}"
                    )
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
        self, prompt: str, file_config: FileConfig, model: ModelType
    ) -> SummaryResponse:
        from ..managers.directory_manager import DirectoryManager

        directory_manager = DirectoryManager()
        logger.info(f"Processing transcription: {file_config.transcription_path}")
        try:
            async with self.file_semaphore:
                logger.debug(
                    f"Acquired file_semaphore for {file_config.transcription_path}"
                )
                try:
                    assert (
                        file_config.transcription_path is not None
                    ), "transcription_path must be provided"
                    assert (
                        file_config.summary_path is not None
                    ), "summary_path must be provided"

                    logger.debug(
                        f"Validating paths for {file_config.transcription_path}"
                    )
                    try:
                        await directory_manager.validate_paths(
                            file_config.transcription_path
                        )
                    except Exception as e:
                        logger.error(
                            f"Path validation failed for {file_config.transcription_path}: {str(e)}"
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Path validation failed: {str(e)}",
                        )

                    logger.debug(
                        f"Reading transcription: {file_config.transcription_path}"
                    )
                    try:
                        transcription = directory_manager.read_transcription(
                            file_config.transcription_path
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to read transcription {file_config.transcription_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to read transcription: {str(e)}",
                        )

                    input_tokens = len(get_encoder(model).encode(transcription))
                    logger.debug(
                        f"Read transcription: "
                        f"input_tokens={input_tokens}, "
                        f"transcription_preview={transcription[:50]}..."
                    )

                    full_input_text = prompt + "\n" + transcription
                    total_input_tokens = len(get_encoder(model).encode(full_input_text))
                    logger.debug(
                        f"Adjusted input with system prompt: "
                        f"total_input_tokens={total_input_tokens}, "
                        f"prompt_tokens={len(get_encoder(model).encode(prompt))}, "
                        f"input_tokens={input_tokens}"
                    )

                    overlap = self.max_tokens_per_chunk * self._percent_chunk_overlap
                    chunks = self.chunk_text(
                        full_input_text, self.max_tokens_per_chunk, overlap, model
                    )
                    logger.info(
                        f"Transcription split into {len(chunks)} chunks: "
                        f"total_input_tokens={total_input_tokens}, "
                        f"chunk_size={self.max_tokens_per_chunk}, "
                        f"overlap={overlap}"
                    )

                    logger.debug("Generating summary for chunks")
                    try:
                        (
                            full_summary,
                            total_tokens_used,
                        ) = await self.process_chunks_in_groups(chunks, prompt, model)
                    except Exception as e:
                        logger.error(
                            f"Failed to generate summary for {file_config.transcription_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to generate summary: {str(e)}",
                        )

                    logger.debug("Postprocessing summary")
                    try:
                        final_summary = await self.postprocess_summary(
                            full_summary, model
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to postprocess summary for {file_config.transcription_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to postprocess summary: {str(e)}",
                        )

                    logger.debug(f"Writing summary to {file_config.summary_path}")
                    try:
                        directory_manager.write_summary(
                            final_summary, file_config.summary_path
                        )
                        logger.info(
                            f"Summary written for transcription: {file_config.transcription_path}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to write summary to {file_config.summary_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to write summary: {str(e)}",
                        )

                    logger.debug(
                        f"Creating DOCX version for {file_config.summary_path}"
                    )
                    try:
                        self._create_docx_version(file_config.summary_path)
                        logger.info(
                            f"DOCX version created for {file_config.summary_path}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to create DOCX version for {file_config.summary_path}: {str(e)}",
                            exc_info=True,
                        )
                        return SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Failed to create DOCX version: {str(e)}",
                        )

                    logger.info(
                        f"Summary completed for {file_config.transcription_path}: "
                        f"summary_tokens={len(get_encoder(model).encode(final_summary))}, "
                        f"total_tokens_used={total_tokens_used}, "
                        f"saved_to={file_config.summary_path}"
                    )
                    return SummaryResponse(
                        success=True,
                        summary=final_summary,
                        message=SummaryMessages.WRITE_SUMMARY.format(
                            file_config.summary_path
                        ),
                    )
                finally:
                    logger.debug(
                        f"Released file_semaphore for {file_config.transcription_path}"
                    )
        except asyncio.CancelledError:
            logger.info(
                f"Transcription processing cancelled: {file_config.transcription_path}"
            )
            raise
        except ValueError as e:
            logger.error(
                f"Validation error for {file_config.transcription_path}: {str(e)}",
                exc_info=True,
            )
            return SummaryResponse(
                success=False, summary="", message=f"Validation error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Error processing transcription {file_config.transcription_path}: {str(e)}",
                exc_info=True,
            )
            return SummaryResponse(
                success=False,
                summary="",
                message=f"Error processing transcription: {str(e)}",
            )

    @retry(
        wait=wait_exponential(multiplier=2, min=1, max=30),
        stop=stop_after_attempt(8),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def postprocess_summary(self, summary: str, model: ModelType) -> str:
        summary_tokens = len(get_encoder(model).encode(summary))
        logger.info(f"Postprocessing summary: {summary_tokens} tokens")
        try:
            tokens_needed = summary_tokens // 4 + 500
            logger.debug(f"Postprocessing estimated tokens needed: {tokens_needed}")
            if tokens_needed <= self.max_tokens:
                if not await self._check_token_limit(tokens_needed):
                    logger.warning(
                        f"Token limit reached for postprocessing: needed={tokens_needed}, "
                        f"available={self.token_bucket}"
                    )
                    if self.running:
                        async with self.queue_lock:
                            await self.task_queue.put(
                                (self.postprocess_summary, [summary, model])
                            )
                            self.tasks_put += 1
                            logger.debug(
                                f"Queued postprocess_summary task, total tasks put: {self.tasks_put}"
                            )
                    else:
                        logger.warning(
                            "Service is shutting down, not queuing postprocess task"
                        )
                    return summary

                postprocess_prompt = (
                    self.advanced_prompt_generator.get_postprocess_prompt()
                )
                client = await self._initialize_client(model)
                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model.value,
                            messages=[
                                {"role": "system", "content": postprocess_prompt},
                                {"role": "user", "content": f"\n\n{summary}"},
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=None,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "Timeout in postprocess_summary: API call exceeded 60 seconds"
                    )
                    return summary

                content = response.choices[0].message.content
                if content is None:
                    logger.error("Response content is None")
                    return summary
                output_tokens = len(get_encoder(model).encode(content))
                total_tokens_used = response.usage.total_tokens if response.usage else 0
                self.token_bucket -= total_tokens_used
                reduction_factor = (
                    output_tokens / summary_tokens if summary_tokens > 0 else 0
                )

                if response.usage:
                    usage: CompletionUsage = response.usage
                    self.history_token_model.num_tokens_postprocess_input += (
                        usage.prompt_tokens
                    )
                    self.history_token_model.num_tokens_postprocess_output += (
                        usage.completion_tokens
                    )
                    self.history_token_model.num_total_tokens += usage.total_tokens
                    logger.info(
                        f"Token stats postprocessing - input: {self.history_token_model.num_tokens_postprocess_input}, "
                        f"output: {self.history_token_model.num_tokens_postprocess_output}, "
                        f"total: {self.history_token_model.num_total_tokens}"
                    )

                return content.strip() if content is not None else summary

            overlap = self.max_tokens_per_chunk * self._percent_chunk_overlap
            chunks = self.chunk_text(summary, self.max_tokens_per_chunk, overlap, model)
            logger.debug(f"Summary split into {len(chunks)} chunks for postprocessing")

            postprocess_prompt = self.advanced_prompt_generator.get_postprocess_prompt()

            try:
                final_summary, total_tokens_used = await self.process_chunks_in_groups(
                    chunks, postprocess_prompt, model
                )
            except Exception as e:
                logger.error(
                    f"Failed to process chunks in postprocessing: {str(e)}",
                    exc_info=True,
                )
                return summary

            final_summary_tokens = len(get_encoder(model).encode(final_summary))
            reduction_factor = (
                final_summary_tokens / summary_tokens if summary_tokens > 0 else 0
            )
            logger.info(
                f"Postprocessing of chunks completed: "
                f"total_tokens_used={total_tokens_used}, "
                f"final_summary_tokens={final_summary_tokens}, "
                f"reduction_factor={reduction_factor:.4f}, "
                f"final_summary_preview={final_summary[:50]}..."
            )
            logger.info(
                {
                    "num_tokens_postprocess_input": self.history_token_model.num_tokens_postprocess_input,
                    "num_tokens_postprocess_output": self.history_token_model.num_tokens_postprocess_output,
                }
            )
            return final_summary
        except (RateLimitError, APIConnectionError) as e:
            logger.error(f"Retryable error in postprocessing: {str(e)}", exc_info=True)
            raise
        except asyncio.CancelledError:
            logger.info("Postprocessing cancelled")
            raise
        except Exception as e:
            logger.error(f"Postprocessing failed: {str(e)}", exc_info=True)
            return summary

    def _add_toc(self, doc: DocumentType) -> None:
        logger.debug("Adding table of contents to DOCX")
        doc.add_heading("Índice", level=1)
        paragraph = doc.add_paragraph()
        run = paragraph.add_run()
        fld_char = OxmlElement("w:fldChar")
        fld_char.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_char)
        instr_text = OxmlElement("w:instrText")
        instr_text.text = 'TOC \\o "1-3" \\h \\z \\u'
        run._r.append(instr_text)
        fld_char = OxmlElement("w:fldChar")
        fld_char.set(qn("w:fldCharType"), "end")
        run._r.append(fld_char)
        doc.add_paragraph(
            "Nota: Haga clic derecho en el índice y seleccione 'Actualizar campo' al abrir en Word."
        )

    def _create_docx_version(self, md_path: Optional[str]) -> None:
        if md_path is None:
            logger.error("No path provided for DOCX conversion")
            return

        docx_path = md_path.replace(".md", ".docx")
        logger.debug(f"Creating DOCX version: {docx_path}")
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            doc = Document()
            self._add_toc(doc)
            doc.add_page_break()

            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, "html.parser")

            for element in soup:
                if isinstance(element, Tag):
                    if element.name in ["h1", "h2", "h3"]:
                        level = int(element.name[1])
                        heading = doc.add_heading(
                            element.get_text().strip(), level=level
                        )
                        heading.style = f"Heading {level}"
                    elif element.name == "p":
                        doc.add_paragraph(element.get_text().strip())
                    elif element.name == "ul":
                        for item in element.find_all("li", recursive=False):
                            doc.add_paragraph(
                                item.get_text().strip(), style="List Bullet"
                            )
                    elif element.name == "ol":
                        counter = 1
                        for item in element.find_all("li", recursive=False):
                            text = item.get_text().strip()
                            doc.add_paragraph(f"{counter}. {text}", style="List Number")
                            counter += 1

            doc.save(docx_path)
            logger.info(f"DOCX version created: {docx_path}")
        except Exception as e:
            logger.error(f"DOCX conversion failed: {str(e)}", exc_info=True)
            raise

    async def generate_summary_document(
        self, prompt_config: PromptConfig, file_config: FileConfig
    ) -> SummaryResponse:
        logger.info(
            f"Starting summary generation for document: {file_config.document_path}"
        )
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
                return results[0]
        except asyncio.CancelledError:
            logger.info("Summary generation cancelled")
            raise
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, initiating graceful shutdown")
            await self.shutdown()
            raise
        except Exception as e:
            logger.error(
                f"Error generating summary for document: {str(e)}", exc_info=True
            )
            return SummaryResponse(
                success=False, summary="", message=f"Error generating summary: {str(e)}"
            )


async def process_user_summaries(
    user_id: int, prompt_config: PromptConfig, file_configs: List[FileConfig]
) -> None:
    service = SummaryService()
    async with service.lifespan():
        logger.info(
            f"User {user_id} starting summary generation for {len(file_configs)} documents"
        )
        try:
            results = await service.generate_summary_documents(
                prompt_config, file_configs
            )
            for file_config, result in zip(file_configs, results):
                summary_tokens = len(
                    get_encoder(prompt_config.model).encode(result.summary)
                )
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
            await service.shutdown()
            raise
        except Exception as e:
            logger.error(
                f"Error processing summaries for user {user_id}: {str(e)}",
                exc_info=True,
            )
            raise
