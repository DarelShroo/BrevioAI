import asyncio
import logging
from typing import Optional, List, Any

import httpx
from openai import AsyncOpenAI, BadRequestError, AuthenticationError, RateLimitError, APIConnectionError
from openai.types.chat import ChatCompletion
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from core.brevio.managers.token_manager import TokenManager
from core.brevio.models.dtos import PostProcessRequest
from core.brevio.utils.text_chunker import TextChunker
from core.shared.enums.type_call import TypeCall
from core.shared.models.brevio.history_token_call import HistoryTokenCall
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.model_tokens_utils import get_encoder
from .advanced_content_generator import AdvancedPromptGenerator
from .api_service import ApiService

logger = logging.getLogger(__name__)

class SummaryPostProcessor:
    def __init__(
        self,
        token_manager: TokenManager,
        advanced_prompt_generator: AdvancedPromptGenerator,
        history_token_model: HistoryTokenModel,
        api_service: ApiService,
        max_tokens: int,
        temperature: float,
        max_tokens_per_chunk: int,
        percent_chunk_overlap: float = 0.2
    ):
        self.token_manager = token_manager
        self.advanced_prompt_generator = advanced_prompt_generator
        self.history_token_model = history_token_model
        self.api_service = api_service
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.percent_chunk_overlap = percent_chunk_overlap
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
            (RateLimitError, APIConnectionError, AuthenticationError)
        ),
    )
    async def postprocess_summary(
        self,
        request: PostProcessRequest
    ) -> str:
        encoder = get_encoder(request.model)

        logger.info(f"Postprocessing summary: input_tokens={request.clean_summary_tokens}")

        if not request.clean_summary.strip():
            logger.error("Input summary is empty, skipping postprocessing")
            return request.clean_summary

        try:
            tokens_needed = request.clean_summary_tokens + 500
            logger.debug(f"Postprocessing tokens needed: {tokens_needed}")

            postprocess_prompt = (
                await self.advanced_prompt_generator.get_postprocess_prompt(request.language)
            )
            logger.debug(f"Postprocess prompt: {postprocess_prompt[:100]}...")
            client = await self.api_service._initialize_client(request.model)

            if tokens_needed <= self.max_tokens:
                if not await self.token_manager.check_token_limit(tokens_needed):
                    logger.warning(
                        f"Token limit reached for postprocessing: needed={tokens_needed}, "
                        f"available={self.token_manager.token_bucket}"
                    )
                    # Requeue logic if needed, similar to original
                    # For now, just returning original summary if we can't process
                    # Or we should implement the requeue logic here if we have access to the queue
                    if self.task_queue and self.queue_lock:
                         async with self.queue_lock:
                            await self.task_queue.put(
                                (
                                    self.postprocess_summary,
                                    [request],
                                )
                            )
                            self.tasks_put += 1
                            logger.debug(
                                f"Queued postprocess_summary task, total tasks put: {self.tasks_put}"
                            )
                            return request.clean_summary # Return original while task is queued
                    
                    return request.clean_summary

                try:
                    response: ChatCompletion = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=request.model.value,
                            messages=[
                                {"role": "system", "content": postprocess_prompt},
                                {"role": "user", "content": f"\n\n{request.clean_summary}"},
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=300,
                    )

                    self._record_history(
                        postprocess_prompt,
                        f"\n\n{request.clean_summary}",
                        response,
                        encoder,
                        TypeCall.POSTPROCESSING,
                    )
                    logger.debug(f"Postprocess API response: {response}")
                except asyncio.TimeoutError:
                    logger.error(
                        "Timeout in postprocess_summary: API call exceeded 90 seconds"
                    )
                    return request.clean_summary
                except BadRequestError as e:
                    logger.error(
                        f"Bad request error in postprocessing: {str(e)}", exc_info=True
                    )
                    return request.clean_summary
                except AuthenticationError as e:
                    logger.error(
                        f"Authentication error in postprocessing: {str(e)}",
                        exc_info=True,
                    )
                    return request.clean_summary

                content = response.choices[0].message.content
                if content is None or not content.strip():
                    logger.error("Postprocess response content is None or empty")
                    return request.clean_summary
                content += "\n\n" + "\u200b"
                word_count = len(content.split())
                if word_count < request.clean_summary_tokens // 4:
                    logger.warning(
                        f"Postprocessed summary is too short: {word_count} words, "
                        f"expected at least {request.clean_summary_tokens // 4}, "
                        f"content={content[:50]}..."
                    )
                    return request.clean_summary

                output_tokens = len(encoder.encode(content))
                total_tokens_used = response.usage.total_tokens if response.usage else 0
                self.token_manager.consume_tokens(total_tokens_used)
                reduction_factor = (
                    output_tokens / request.clean_summary_tokens
                    if request.clean_summary_tokens > 0
                    else 0
                )

                logger.info(
                    f"Postprocessing completed: output_tokens={output_tokens}, "
                    f"total_tokens_used={total_tokens_used}, "
                    f"reduction_factor={reduction_factor:.4f}, "
                    f"summary_preview={content[:50]}..."
                )
                return content.strip()

            # Chunking logic for large summaries
            overlap = self.max_tokens_per_chunk * self.percent_chunk_overlap
            chunks = TextChunker.chunk_text(
                request.clean_summary, self.max_tokens_per_chunk, overlap, request.model
            )
            logger.debug(f"Summary split into {len(chunks)} chunks for postprocessing")

            chunk_results: List[Optional[str]] = [None] * len(chunks)
            total_tokens_used = 0

            for i, chunk in enumerate(chunks):
                chunk_tokens = len(encoder.encode(chunk))
                tokens_needed = chunk_tokens + 500
                if not await self.token_manager.check_token_limit(tokens_needed):
                    logger.warning(
                        f"Token limit reached for postprocess chunk {i}: needed={tokens_needed}, "
                        f"available={self.token_manager.token_bucket}"
                    )
                    return request.clean_summary

                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=request.model.value,
                            messages=[
                                {"role": "system", "content": postprocess_prompt},
                                {"role": "user", "content": f"\n\n{chunk}"},
                            ],
                            max_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                        timeout=300,
                    )

                    self._record_history(
                        postprocess_prompt,
                        f"\n\n{chunk}",
                        response,
                        encoder,
                        TypeCall.POSTPROCESSING,
                    )

                    content = response.choices[0].message.content

                    if content is None or not content.strip():
                        logger.error(f"Postprocess chunk {i} response is empty")
                        return request.clean_summary

                    content += "\n\n" + "\u200b"

                    word_count = len(content.split())
                    if word_count < chunk_tokens // 4:
                        logger.warning(
                            f"Postprocessed chunk {i} is too short: {word_count} words, "
                            f"expected at least {chunk_tokens // 4}, "
                            f"content={content[:50]}..."
                        )
                        return request.clean_summary

                    output_tokens = len(encoder.encode(content))
                    tokens_used = response.usage.total_tokens if response.usage else 0
                    self.token_manager.consume_tokens(tokens_used)
                    total_tokens_used += tokens_used

                    logger.info(
                        f"Postprocess chunk {i} completed: output_tokens={output_tokens}, "
                        f"tokens_used={tokens_used}, preview={content[:50]}..."
                    )
                    chunk_results[i] = content.strip()

                except asyncio.TimeoutError:
                    logger.error(
                        f"Timeout in postprocess chunk {i}: API call exceeded 90 seconds"
                    )
                    return request.clean_summary
                except Exception as e:
                    logger.error(
                        f"Failed to postprocess chunk {i}: {str(e)}", exc_info=True
                    )
                    return request.clean_summary

            final_summary = "\n".join(
                result for result in chunk_results if result is not None
            ).strip()
            final_word_count = len(final_summary.split())
            if final_word_count < request.clean_summary_tokens // 4:
                logger.warning(
                    f"Postprocessed chunked summary is too short: {final_word_count} words, "
                    f"expected at least {request.clean_summary_tokens // 4}, "
                    f"content={final_summary[:50]}..."
                )
                return request.clean_summary

            final_summary_tokens = len(encoder.encode(final_summary))
            reduction_factor = (
                final_summary_tokens / request.clean_summary_tokens
                if request.clean_summary_tokens > 0
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
            return request.clean_summary

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
        
        if type_call == TypeCall.POSTPROCESSING:
            self.history_token_model.total_tokens_postprocess_input += (
                system_tokens + user_tokens
            )
            self.history_token_model.total_tokens_postprocess_output += output_tokens
            
        return output_tokens
