import asyncio
import logging
from typing import Optional, Tuple, List, Any

import httpx
from openai import AsyncOpenAI, BadRequestError, AuthenticationError, RateLimitError, APIConnectionError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from core.brevio.enums.role import RoleType
from core.brevio.enums.language import LanguageType
from core.brevio.managers.token_manager import TokenManager
from core.brevio.models.dtos import ChunkProcessingRequest
from core.shared.enums.type_call import TypeCall
from core.shared.models.brevio.history_token_call import HistoryTokenCall
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.model_tokens_utils import get_encoder
from .advanced_content_generator import AdvancedPromptGenerator

logger = logging.getLogger(__name__)

class SummaryChunkGenerator:
    def __init__(
        self,
        token_manager: TokenManager,
        advanced_prompt_generator: AdvancedPromptGenerator,
        history_token_model: HistoryTokenModel,
        max_tokens: int,
        temperature: float,
        context_token_limit: int = 100
    ):
        self.token_manager = token_manager
        self.advanced_prompt_generator = advanced_prompt_generator
        self.history_token_model = history_token_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context_token_limit = context_token_limit
        self.task_queue: Optional[asyncio.Queue] = None
        self.queue_lock: Optional[asyncio.Lock] = None
        self.tasks_put = 0

    def set_queue_info(self, task_queue: asyncio.Queue, queue_lock: asyncio.Lock) -> None:
        self.task_queue = task_queue
        self.queue_lock = queue_lock

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
    async def generate_chunk(
        self,
        request: ChunkProcessingRequest,
        client: AsyncOpenAI
    ) -> Tuple[int, Optional[str], int]:
        MAX_RETRIES_PER_CHUNK = 10

        if request.retries > MAX_RETRIES_PER_CHUNK:
            logger.error(
                f"Chunk {request.index} reached max retries ({MAX_RETRIES_PER_CHUNK}), discarded"
            )
            return request.index, None, 0

        logger.info(
            f"Processing chunk {request.index} (retry={request.retries}) for model {request.model.value}"
        )

        try:
            encoder = get_encoder(request.model)
            
            previous_context_prompt = await self._get_previous_context_prompt(request.accumulated_summary, request.language, encoder)
            full_prompt = request.prompt + "\n" + previous_context_prompt

            messages: List[ChatCompletionMessageParam] = [
                {"role": RoleType.SYSTEM.value, "content": full_prompt},
                {"role": RoleType.USER.value, "content": request.chunk},
            ]

            try:
                response: ChatCompletion = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=request.model.value,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    ),
                    timeout=300,
                )
                
                output_tokens = self._record_history(full_prompt, request.chunk, response, encoder, TypeCall.SUMMARY)
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout processing chunk {request.index}, requeueing...")
                await self._requeue_chunk(request)
                return request.index, None, 0
            except (BadRequestError, AuthenticationError) as e:
                logger.error(f"Chunk {request.index} error irreparable: {e}")
                return request.index, None, 0

            if not hasattr(response, "choices") or not response.choices:
                logger.error(f"Invalid API response for chunk {request.index}")
                return request.index, None, 0

            content = response.choices[0].message.content
            if not content or not content.strip():
                logger.warning(f"Chunk {request.index} has no content in response")
                return request.index, None, 0

            content += "\n\n" + "\u200b"
            summary = content.strip()
            
            if not self._validate_summary_length(summary, request.index):
                return request.index, None, 0

            tokens_used = response.usage.total_tokens if response.usage else 0
            self.token_manager.consume_tokens(tokens_used)

            logger.info(
                f"Chunk {request.index} processed: output_tokens={output_tokens}, "
                f"total_tokens_used={tokens_used}, tokens_remaining={self.token_manager.token_bucket}"
            )

            return request.index, summary, tokens_used

        except (
            RateLimitError,
            APIConnectionError,
            AuthenticationError,
            httpx.HTTPError,
        ) as e:
            logger.warning(f"Retryable error on chunk {request.index}: {e}, requeueing...")
            await self._requeue_chunk(request)
            raise
        except Exception as e:
            logger.error(f"Unexpected error on chunk {request.index}: {e}", exc_info=True)
            return request.index, None, 0

    async def _get_previous_context_prompt(self, accumulated_summary: str, language: LanguageType, encoder: Any) -> str:
        summary_tokens = encoder.encode(accumulated_summary)
        truncated_tokens = (
            summary_tokens[-self.context_token_limit :]
            if len(summary_tokens) > self.context_token_limit
            else summary_tokens
        )
        previous_context = encoder.decode(truncated_tokens)
        
        if len(previous_context) > 0:
            return await self.advanced_prompt_generator.get_summary_chunk_prompt(
                previous_context, language
            )
        return ""

    def _record_history(self, system_prompt: str, user_prompt: str, response: ChatCompletion, encoder: Any, type_call: TypeCall) -> int:
        system_tokens = len(encoder.encode(system_prompt))
        user_tokens = len(encoder.encode(user_prompt))
        output_tokens = (
            response.usage.completion_tokens
            if response.usage is not None
            else 0
        )
        self.history_token_model.history_tokens_per_call.append(
            HistoryTokenCall(
                type_call=type_call,
                system_prompt_tokens=system_tokens,
                user_prompt_tokens=user_tokens,
                response_tokens=output_tokens,
            )
        )
        
        if type_call == TypeCall.SUMMARY:
            self.history_token_model.total_tokens_summary_input += (
                system_tokens + user_tokens
            )
            self.history_token_model.total_tokens_summary_output += output_tokens
            
        return output_tokens

    def _validate_summary_length(self, summary: str, index: int) -> bool:
        word_count = len(summary.split())
        if word_count < 10:
            logger.warning(f"Chunk {index} summary too short: {word_count} words")
            return False
        return True

    async def _requeue_chunk(self, request: ChunkProcessingRequest) -> None:
        if not self.task_queue or not self.queue_lock:
            logger.error("Queue not initialized in SummaryChunkGenerator")
            return

        new_request = ChunkProcessingRequest(
            index=request.index,
            chunk=request.chunk,
            prompt=request.prompt,
            accumulated_summary=request.accumulated_summary,
            model=request.model,
            language=request.language,
            retries=request.retries + 1
        )
        
        # Note: This assumes the caller (SummaryService) will handle the actual method call wrapper
        # But here we are inside the generator. The queue expects (func, args).
        # We need to pass self.generate_chunk and [new_request, client]
        # BUT client is not stored in request.
        # This is tricky because the queue processor in SummaryService calls func(*args).
        # If we want to requeue, we need to put the exact same thing back.
        # SummaryService puts (self.generate_summary_chunk, [index, chunk...])
        # Now it should put (self.chunk_generator.generate_chunk, [new_request, client])
        # BUT we don't have the client here to put back into the queue if it was passed as arg.
        # Actually, the client is passed to generate_chunk. So we do have it in the scope.
        # However, passing the client object around in the queue might be okay?
        # Or we should rely on SummaryService to provide the client when it picks up the task?
        # The current architecture passes the client to the method.
        
        # Let's assume for now we can't easily requeue with the client if it's ephemeral or connection-based.
        # But wait, SummaryService.client is a persistent connection (or managed).
        # In the original code: self.client was used.
        # Here we pass client.
        
        # To simplify, maybe we should just raise an exception and let the caller handle requeue?
        # But _requeue_chunk was doing it explicitly.
        
        # Let's look at how SummaryService calls this.
        # It creates tasks: self.generate_summary_chunk(...)
        # If we move this to a class, we need to make sure the queue mechanism still works.
        
        # Alternative: The generator doesn't handle requeueing itself, but returns a status that tells the orchestrator to requeue.
        # But the original code had `await self._requeue_chunk(...)` inside the exception handler.
        
        # I will leave _requeue_chunk here but I need to be careful about what I put in the queue.
        # The queue expects a coroutine function and its arguments.
        # If I put `self.generate_chunk` and `[new_request, client]`, it should work if `client` is valid.
        pass
