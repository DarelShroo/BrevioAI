import asyncio
import hashlib
import logging
import math
import os
import re
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    List,
    Optional,
    Tuple,
    Union,
)

import aiofiles
import httpx
import markdown
from bs4 import BeautifulSoup, Tag
from docx import Document
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from core.brevio.constants.summary_messages import SummaryMessages
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.role import RoleType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.provider_quota.errors import (
    JobRequestBudgetExceededError,
    ProviderQuotaUnavailableError,
    QuotaAcquireTimeoutError,
    QuotaPolicyMissingError,
)
from core.brevio.services.provider_quota.executor import ProviderCallExecutor
from core.shared.enums.model import ModelType
from core.shared.enums.type_call import TypeCall
from core.shared.models.brevio.history_token_call import HistoryTokenCall
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.models.user.data_result import DataResult
from core.shared.utils.adaptive_salience_policy import (
    FINAL_REDUCE_PACK_CAP,
    INTERMEDIATE_COMPRESSION_RATIO,
    MAP_COMPLETION_HEADROOM,
    MIN_USABLE_MAP_WORDS,
    REDUCE_COMPLETION_HEADROOM,
    SECTION_KEEP_RATIO,
    AdaptiveSaliencePolicy,
)
from core.shared.utils.chunking_utils import (
    extract_document_outline,
    extract_toc_entry_labels,
    is_table_of_contents_chunk,
    is_toc_map_stub,
    last_toc_strip_stats,
    outline_for_chunk,
    strip_document_front_matter_toc,
    strip_leading_toc,
)
from core.shared.utils.environment import (
    format_phase_enabled,
    keep_partials_enabled,
    max_token_wait_seconds,
    min_tokens_for_postprocess_override,
    tokens_per_minute,
)
from core.shared.utils.json_data_utils import save_log_to_json
from core.shared.utils.model_capabilities import (
    generation_temperature,
    get_model_capabilities,
    packing_token_multiplier,
    summary_max_output_tokens,
)
from core.shared.utils.model_tokens_utils import completion_extra_kwargs, get_encoder
from core.shared.utils.pricing_registry import (
    calculate_provider_cost,
    get_pricing_snapshot,
)
from core.shared.utils.summary_quality import (
    QualitySignals,
    _safe_int,
    choose_deliverable_text,
    count_words,
)
from core.shared.utils.summary_quality import (
    looks_like_assistant_chat as quality_looks_like_assistant_chat,
)

from .advanced_content_generator import (
    AdvancedPromptGenerator,
    resolve_language_prompts,
)
from .api_service import ApiService
from .summary_pipeline import (
    ArtifactQualityError,
    ContextOverflowError,
    DocumentPipelineState,
    ImpossibleRequestError,
    InvariantViolationError,
    MapPhaseFailedError,
    PipelineDocumentError,
    PipelineOutcome,
    PipelinePhase,
    ReduceConvergenceError,
    SummaryArtifactManager,
    cancel_pending_tasks,
    gather_or_cancel,
    job_phase_for,
    job_status_for,
)
from .summary_providers.provider import CompletionRequest
from .summary_providers.registry import SummaryProviderRegistry

load_dotenv()

AUDIT_DIR = "data/audit"
_audit_run_id: ContextVar[str] = ContextVar("audit_run_id", default="unknown")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def set_audit_run_id(run_id: Optional[str]) -> None:
    raw = (run_id or "unknown").strip() or "unknown"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw)[:64]
    _audit_run_id.set(safe)


def dump_audit(phase: str, stage: str, content: str, identifier: str = ""):
    """Best-effort debug dump. Must never raise (audit dir may be unwritable)."""
    run_id = _audit_run_id.get()

    def _safe_part(value: object) -> str:
        return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(value))[
            :80
        ]

    filename = f"{_safe_part(run_id)}_{_safe_part(phase)}_{_safe_part(stage)}_{_safe_part(identifier)}.txt"
    path = os.path.join(AUDIT_DIR, filename)
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.debug("Audit dump failed: %s", e)


@dataclass
class ReduceChunk:
    text: str
    source_chunk_indices: List[int]
    tokens: int = 0
    synthesized: bool = False


class ReduceResult:
    def __init__(
        self,
        text: str,
        tokens: int,
        source_chunk_indices: List[int],
        finish_reason: str = "stop",
    ):
        self.text = text
        self.tokens = tokens
        self.source_chunk_indices = sorted(list(set(source_chunk_indices)))
        self.finish_reason = finish_reason

    def __iter__(self):
        return iter((self.text, self.tokens))

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int):
        return (self.text, self.tokens)[index]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return other[0] == self.text and other[1] == self.tokens
        if isinstance(other, str):
            return self.text == other
        return super().__eq__(other)

    def __repr__(self) -> str:
        return (
            f"ReduceResult(tokens={self.tokens}, "
            f"covered_chunks={len(self.source_chunk_indices)}, "
            f"text_len={len(self.text)})"
        )


# REDUCE_SPLIT_SAFETY_CAP is a circuit breaker against infinite recursion.
# The primary stop condition is indivisibility / non-progress, not this number.
REDUCE_SPLIT_SAFETY_CAP = 16
MAX_INTERMEDIATE_REDUCE_ROUNDS = 2
MAX_FINAL_REDUCE_ROUNDS = 4
# Leftover MAP extracts below this size are passed through. A 153-token
# leftover previously received ~500 padding + 1.35 headroom, filled the
# output cap (finish_reason=length), and failed closed because it could
# not be split.
MIN_SINGLE_INTERMEDIATE_REDUCE_TOKENS = 750


@dataclass
class MapChunkResult:
    chunk_id: int
    original_text: str
    status: str  # "SUCCESS" or "FAILED"
    summary_text: Optional[str]
    error_message: Optional[str] = None

    def validate_contract(self) -> None:
        if self.status == "SUCCESS":
            if not self.summary_text or not self.summary_text.strip():
                raise InvariantViolationError(
                    f"MAP SUCCESS chunk {self.chunk_id} has empty summary_text",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                    chunk_id=self.chunk_id,
                )
        elif self.status == "FAILED":
            if not self.original_text or not self.original_text.strip():
                raise InvariantViolationError(
                    f"MAP FAILED chunk {self.chunk_id} has empty original_text",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                    chunk_id=self.chunk_id,
                )
        else:
            raise InvariantViolationError(
                f"MAP chunk {self.chunk_id} has unknown status={self.status!r}",
                phase=PipelinePhase.INVARIANT_FAILED.value,
                chunk_id=self.chunk_id,
                status=self.status,
            )

    def text_for_reduce(self, *, allow_original_fallback: bool = False) -> str:
        self.validate_contract()
        if self.status == "SUCCESS":
            return self.summary_text or ""
        if allow_original_fallback:
            return self.original_text
        raise MapPhaseFailedError(
            f"MAP chunk {self.chunk_id} failed and original_text fallback into REDUCE is disabled: "
            f"{self.error_message or 'unknown error'}",
            phase=PipelinePhase.MAP_FAILED.value,
            chunk_id=self.chunk_id,
            error_message=self.error_message,
        )


class SummaryService:
    def __init__(self) -> None:
        logger.info("Initializing SummaryService")
        # Removed global limits, now using ModelCapabilities dynamically
        self.tokens_per_minute = tokens_per_minute()
        self.temperature = 0.0
        self.max_concurrent_chunks = 8
        self.max_concurrent_files = 1000
        self.max_concurrent_requests = 100000
        self.token_bucket = self.tokens_per_minute

        self.last_token_reset = time.time()
        self._pipeline_t0: Optional[float] = None
        self.running = False
        self._percent_chunk_overlap = 0.2
        self.context_token_limit = 100
        self.running_tasks: List[asyncio.Task] = []
        self.client_lock = asyncio.Lock()
        self.clients: dict[str, AsyncOpenAI] = {}
        self.advanced_prompt_generator = AdvancedPromptGenerator()
        self.history_token_model = HistoryTokenModel()

        from core.brevio.services.credential_resolver import CredentialResolver
        from core.brevio.services.platform_access_policy import PlatformAccessPolicy
        from core.brevio.services.provider_registry import ProviderRegistry
        from core.brevio_api.core.database import AsyncDB
        from core.brevio_api.repositories.user_credential_repository import (
            UserCredentialRepository,
        )
        from core.brevio_api.services.encryption_service import EncryptionService

        db = AsyncDB().database()
        encryption_service = EncryptionService()
        user_credential_repository = UserCredentialRepository(db, encryption_service)
        platform_policy = PlatformAccessPolicy()
        provider_registry = ProviderRegistry()

        self.credential_resolver = CredentialResolver(
            repository=user_credential_repository,
            platform_policy=platform_policy,
            provider_registry=provider_registry,
        )

        self.api_service = ApiService(
            self.running,
            None,
            None,
            self.client_lock,
            0,
            0,
            self.running_tasks,
            self.credential_resolver,
        )
        self.client: Optional[AsyncOpenAI] = None
        self.summary_providers = SummaryProviderRegistry()
        self.directory_manager = DirectoryManager()
        self.MIN_TOKENS_FOR_POSTPROCESS = 2000
        self.provider_executor = ProviderCallExecutor()
        self._provider_metrics = self.provider_executor.metrics
        self._job_budget = None
        # LOCAL backpressure only (per SummaryService instance). NOT Google TPM.
        # Distributed provider limits live in ProviderQuotaManager (Redis).
        logger.debug(
            f"Initialized SummaryService, "
            f"tokens_per_minute={self.tokens_per_minute} (LOCAL backpressure only; not Google TPM), "
            f"temperature={self.temperature}, "
            f"max_concurrent_files={self.max_concurrent_files}, "
            f"max_concurrent_requests={self.max_concurrent_requests}, "
            f"overlap={self._percent_chunk_overlap}, "
            f"context_limit={self.context_token_limit}"
        )

    def _safe_completion_token_limit(
        self,
        model: ModelType,
        system_tokens: int,
        user_tokens: int,
        requested_output_tokens: int,
        reserved_tokens: int = 512,
    ) -> int:
        capabilities = get_model_capabilities(model)
        counted_system = int(
            math.ceil(system_tokens * packing_token_multiplier(capabilities))
        )
        counted_user = int(
            math.ceil(user_tokens * packing_token_multiplier(capabilities))
        )
        reserved = max(
            reserved_tokens,
            1024 if capabilities.provider == "ollama" else reserved_tokens,
        )
        context_available = (
            capabilities.context_window - counted_system - counted_user - reserved
        )
        if context_available <= 0:
            raise ContextOverflowError(
                f"Context overflow: available={context_available} (window={capabilities.context_window}, system={system_tokens}, user={user_tokens}, reserved={reserved})"
            )
        return min(
            requested_output_tokens,
            summary_max_output_tokens(capabilities),
            context_available,
            *(
                [self._generation_max_output_tokens]
                if getattr(self, "_generation_max_output_tokens", None)
                else []
            ),
        )

    def _map_completion_token_limit(
        self,
        model: ModelType,
        summary_level: SummaryLevel,
        system_tokens: int,
        chunk_tokens: int,
        total_document_tokens: int,
    ) -> int:
        capabilities = get_model_capabilities(model)
        native_max = summary_max_output_tokens(capabilities)
        safety_ceiling = AdaptiveSaliencePolicy.calculate_map_safety_ceiling(
            chunk_input_tokens=(system_tokens + chunk_tokens),
            summary_level=summary_level,
            capabilities=capabilities,
        )
        requested = self._map_api_max_tokens(safety_ceiling, native_max)
        return self._safe_completion_token_limit(
            model,
            system_tokens,
            chunk_tokens,
            requested,
        )

    def _reduce_batch_token_limit(
        self,
        model: ModelType,
        summary_level: SummaryLevel,
        reduce_prompt_tokens: int,
        is_intermediate: bool = False,
    ) -> int:
        capabilities = get_model_capabilities(model)
        safety_margin = capabilities.reduce_safety_margin
        native_max_output = summary_max_output_tokens(capabilities)
        context_window = capabilities.context_window
        reduce_prompt_tokens = int(
            math.ceil(reduce_prompt_tokens * packing_token_multiplier(capabilities))
        )

        if is_intermediate:
            # Policy 1: Dynamic L_batch for intermediate REDUCE
            # Maximize physical capacity to allow grouping chunks, but cap it at the model's configured reduce_batch_tokens
            # to ensure proper hierarchical reduction and prevent "Lost in the Middle" information loss.
            # batch_input_tokens + prompt_overhead + max_output_tokens <= context_window
            limit_by_context = (
                context_window
                - reduce_prompt_tokens
                - native_max_output
                - safety_margin
            )
            return max(
                capabilities.reduce_min_batch_tokens,
                min(capabilities.reduce_batch_tokens, limit_by_context),
            )

        # For Final REDUCE: apply multiplier to the basic budget
        level_multiplier = {
            SummaryLevel.VERY_DETAILED: 0.85,
            SummaryLevel.DETAILED: 0.95,
            SummaryLevel.MODERATE: 1.0,
            SummaryLevel.CONCISE: 1.05,
            SummaryLevel.VERY_CONCISE: 1.1,
        }.get(summary_level, 1.0)

        base_budget = getattr(capabilities, "reduce_input_token_budget", None)
        if base_budget is None:
            base_budget = min(capabilities.reduce_batch_tokens, native_max_output)

        context_limited_input = (
            context_window - reduce_prompt_tokens - native_max_output - safety_margin
        )

        output_limited_input = int(base_budget * level_multiplier)
        return max(
            capabilities.reduce_min_batch_tokens,
            min(
                capabilities.reduce_batch_tokens,
                context_limited_input,
                output_limited_input,
            ),
        )

    def _final_reduce_pack_limit(
        self,
        model: ModelType,
        summary_level: SummaryLevel,
        reduce_prompt_tokens: int,
        output_target_tokens: int,
    ) -> int:
        """Pack limit for a true final synthesis call.

        Intermediate packing stays on reduce_batch_tokens. Final synthesis may
        pack more so multiple surviving blocks become one document instead of
        being concatenated.
        """
        capabilities = get_model_capabilities(model)
        output_reserve = min(
            summary_max_output_tokens(capabilities),
            max(
                int(output_target_tokens) + capabilities.output_padding_tokens,
                capabilities.output_padding_tokens,
            ),
        )
        reduce_prompt_tokens = int(
            math.ceil(reduce_prompt_tokens * packing_token_multiplier(capabilities))
        )
        context_limited = (
            capabilities.context_window
            - reduce_prompt_tokens
            - output_reserve
            - capabilities.reduce_safety_margin
        )
        synthesis_cap = max(
            capabilities.reduce_batch_tokens,
            min(
                FINAL_REDUCE_PACK_CAP,
                capabilities.reduce_batch_tokens * 4,
                max(1, capabilities.context_window // 4),
            ),
        )
        return max(
            capabilities.reduce_min_batch_tokens,
            min(synthesis_cap, context_limited),
        )

    def _chunk_overlap_ratio(self, model: ModelType) -> float:
        capabilities = get_model_capabilities(model)
        if capabilities.max_tokens_per_chunk <= 0:
            return self._percent_chunk_overlap
        derived = capabilities.chunk_overlap / float(capabilities.max_tokens_per_chunk)
        return min(self._percent_chunk_overlap, max(0.0, derived))

    @staticmethod
    def _reduce_chunks_without_toc_stubs(
        chunks: List["ReduceChunk"],
    ) -> List["ReduceChunk"]:
        """Keep developed MAP text; drop index stubs so REDUCE cannot mention them."""
        body = [chunk for chunk in chunks if not is_toc_map_stub(chunk.text)]
        return body if body else chunks

    def _pack_reduce_chunks(
        self,
        chunks: List["ReduceChunk"],
        batch_limit: int,
        encoder,
        token_multiplier: float = 1.0,
    ) -> List[List["ReduceChunk"]]:
        batches: List[List[ReduceChunk]] = []
        current_batch: List[ReduceChunk] = []
        current_batch_tokens = 0
        for chunk in chunks:
            raw = chunk.tokens or len(encoder.encode(chunk.text))
            chunk_tokens = int(math.ceil(raw * token_multiplier))
            needed = chunk_tokens + (10 if current_batch else 0)
            if current_batch and (current_batch_tokens + needed > batch_limit):
                batches.append(current_batch)
                current_batch = [chunk]
                current_batch_tokens = chunk_tokens
            else:
                current_batch.append(chunk)
                current_batch_tokens += needed
        if current_batch:
            batches.append(current_batch)
        return batches

    def _map_api_max_tokens(self, policy_ceiling: int, native_max: int) -> int:
        padded = int(policy_ceiling * MAP_COMPLETION_HEADROOM)
        return min(native_max, max(policy_ceiling, padded, 1))

    def _reduce_api_max_tokens(self, instruction_target: int, native_max: int) -> int:
        padded = int(instruction_target * REDUCE_COMPLETION_HEADROOM)
        return min(native_max, max(instruction_target, padded))

    def _completion_timeout_s(self, model: ModelType, phase: str) -> float:
        """Local dense models exceed the old 60–120s wait_for caps."""
        provider = get_model_capabilities(model).provider.lower()
        if provider == "ollama":
            if model in {
                ModelType.GEMMA4_31B_IQ3,
                ModelType.QWEN3_32B,
                ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS,
            }:
                return 600.0
            return 300.0
        if phase == "DIRECT":
            return 180.0
        if phase == "REDUCE":
            return 180.0
        if phase == "FORMAT":
            return 90.0
        return 120.0

    def _reduce_output_budget_for_batch(
        self,
        instruction_target: int,
        batch_input_tokens: int,
        native_max: int,
        output_padding_tokens: int,
        is_final: bool,
    ) -> int:
        """Cap REDUCE max_tokens so leftovers cannot pad-fill a document-sized budget."""
        instruction_target = max(1, int(instruction_target))
        leftover_span = MIN_SINGLE_INTERMEDIATE_REDUCE_TOKENS * 4
        if batch_input_tokens < MIN_SINGLE_INTERMEDIATE_REDUCE_TOKENS:
            # 1.5x of a tiny leftover without REDUCE_COMPLETION_HEADROOM made
            # max_tokens == generated tokens (asyncio L3 leftovers req=128, finish=length).
            capped_instruction = max(128, int(max(1, batch_input_tokens) * 1.5))
            return self._reduce_api_max_tokens(capped_instruction, native_max)
        if is_final:
            capped_instruction = min(
                instruction_target,
                max(batch_input_tokens, int(batch_input_tokens * 1.15)),
            )
            if batch_input_tokens <= leftover_span:
                capped_instruction = max(capped_instruction, batch_input_tokens)
        else:
            compressed = int(batch_input_tokens * INTERMEDIATE_COMPRESSION_RATIO)
            capped_instruction = min(
                instruction_target,
                compressed + min(128, output_padding_tokens),
            )
            # Leftovers just above the passthrough floor must still be able to
            # emit the whole extract with finish_reason=stop. Capping at 0.55x
            # plus 128 made max_tokens ~= output, so every leftover hit length
            # and split until empty (asyncio 166p REDUCE batch 3).
            if batch_input_tokens <= leftover_span:
                capped_instruction = max(capped_instruction, batch_input_tokens)
        return self._reduce_api_max_tokens(capped_instruction, native_max)

    def _salvage_unsplittable_reduce(
        self, reduced: str, reduce_status: str
    ) -> Optional[str]:
        """Keep a complete leftover when finish_reason=length cannot be split.

        Short garbage such as ``cut`` is not salvageable. A finished paragraph
        from a tiny leftover is: failing the job discards valid coverage.
        """
        if reduce_status in {"EMPTY", "API_ERROR"}:
            return None
        text = (reduced or "").strip()
        if not text:
            return None
        if self._looks_incomplete_tail(text):
            trimmed = self._trim_to_last_complete_unit(text)
            if not trimmed:
                return None
            text = trimmed.strip()
            if self._looks_incomplete_tail(text):
                return None
        if len(text.split()) < 20:
            return None
        if self._looks_like_assistant_chat(text):
            return None
        return text

    def _leftover_blocks_are_deliverable(self, chunks: List["ReduceChunk"]) -> bool:
        """True when remaining REDUCE blocks can be concatenated instead of failing.

        Incomplete tails are allowed: leftover originals kept after finish_reason=length
        often lack sentence punctuation. A pile of tiny REDUCE stubs is not a summary;
        reconstructed source fragments that join into substantial text are salvageable.
        """
        if not chunks:
            return False
        if any(self._looks_like_assistant_chat(chunk.text) for chunk in chunks):
            return False
        joined = "\n\n".join(
            (chunk.text or "").strip() for chunk in chunks if (chunk.text or "").strip()
        )
        if not joined or self._looks_like_assistant_chat(joined):
            return False
        if any(getattr(chunk, "synthesized", False) for chunk in chunks):
            return True
        joined_words = len(joined.split())
        if joined_words >= 180 or len(joined) >= 2000:
            return True
        return False

    async def start(self) -> None:
        if not self.running:
            self.running = True

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
            if end == len(tokens):
                break
            start = end - overlap_tokens if end - overlap_tokens > start else end

        for i, c in enumerate(chunks):
            dump_audit("01_CHUNKING", "chunk", c, str(i))

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

    async def _check_token_limit(
        self,
        tokens_needed: int,
        request_type: str = "UNKNOWN",
        model_name: str = "UNKNOWN",
        input_tokens: int = 0,
        requested_output_tokens: int = 0,
    ) -> bool:
        """
        LOCAL per-process backpressure using MAX_TOKEN_PER_MINUTE.

        This is NOT Google TPM and NOT a distributed provider limit.
        Global Gemini/OpenAI pressure is governed by ProviderQuotaManager (Redis).
        """
        await self._update_token_bucket()

        logger.info(
            f"TokenLimiter: model={model_name} phase={request_type} input={input_tokens} "
            f"requested_output={requested_output_tokens} needed={tokens_needed} "
            f"available={self.token_bucket} TPM={self.tokens_per_minute}"
        )

        # 1. Circuit Breaker for Impossible Requests (Avoid Infinite Loop)
        if tokens_needed > self.tokens_per_minute:
            logger.warning(
                f"TokenBudgetWarning: Needed tokens ({tokens_needed}) exceeds maximum "
                f"bucket capacity ({self.tokens_per_minute}). Borrowing from future capacity."
            )
            # Wait until the bucket is FULL before allowing the massive request
            waited = 0
            max_wait = max_token_wait_seconds()
            while waited <= max_wait:
                if self.token_bucket >= self.tokens_per_minute:
                    self.token_bucket -= tokens_needed
                    return True
                await asyncio.sleep(5)
                await self._update_token_bucket()
                waited += 5

            raise TimeoutError(
                f"Could not refill bucket to max capacity after {max_wait}s for a massive request."
            )

        safety_margin = self.tokens_per_minute * 0.1
        if self.token_bucket >= (tokens_needed + safety_margin):
            logger.debug(
                f"Token check passed: needed={tokens_needed}, available={self.token_bucket}"
            )
            # Acotamos los tokens del bucket aquí
            self.token_bucket -= tokens_needed
            return True

        waited = 0
        max_wait = max_token_wait_seconds()
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
                self.token_bucket -= tokens_needed
                return True
            waited += 5

        logger.error(f"Waited too long ({waited}s) for tokens, aborting")
        raise TimeoutError(
            f"Could not acquire {tokens_needed} tokens after {max_wait}s"
        )

    def refund_tokens(self, unused_tokens: int) -> None:
        if unused_tokens > 0:
            self.token_bucket = min(
                self.tokens_per_minute, self.token_bucket + unused_tokens
            )
            logger.debug(
                f"Refunded {unused_tokens} tokens. Current bucket: {self.token_bucket}"
            )

    def _elapsed_s(self) -> float:
        if not self._pipeline_t0:
            return 0.0
        return time.time() - self._pipeline_t0

    def _record_api_request(self, phase: str) -> int:
        self.history_token_model.api_request_count = (
            int(self.history_token_model.api_request_count or 0) + 1
        )
        elapsed = self._elapsed_s()
        self.history_token_model.total_time = round(elapsed, 3)
        count = self.history_token_model.api_request_count
        logger.info(
            "METRIC: api_requests=%s phase=%s elapsed_s=%.2f",
            count,
            phase,
            elapsed,
        )
        return count

    def _record_prompt_hash(self, phase: str, prompt: str) -> None:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        key = phase.upper()
        hashes = self.history_token_model.phase_prompt_hashes.setdefault(key, [])
        if digest not in hashes:
            hashes.append(digest)

    def _finalize_timing(self) -> None:
        # total_time = wall-clock duration in seconds; completed_at = finish datetime.
        self._sync_provider_metrics()
        elapsed = round(self._elapsed_s(), 3)
        self.history_token_model.total_time = elapsed
        self.history_token_model.completed_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        logger.info(
            "METRIC: pipeline_complete elapsed_s=%.2f completed_at=%s api_requests=%s "
            "physical=%s success=%s failed=%s retries=%s 429s=%s cooldown=%s "
            "budget_consumed=%s budget_remaining=%s",
            elapsed,
            self.history_token_model.completed_at,
            self.history_token_model.api_request_count or 0,
            self.history_token_model.physical_http_requests,
            self.history_token_model.successful_requests,
            self.history_token_model.failed_requests,
            self.history_token_model.retry_requests,
            self.history_token_model.provider_429_count,
            self.history_token_model.global_cooldown_count,
            self.history_token_model.job_request_budget_consumed,
            self.history_token_model.job_request_budget_remaining,
        )

    def _sync_provider_metrics(self) -> None:
        metrics = self.provider_executor.metrics
        budget = self._job_budget
        if budget is not None:
            metrics.apply_budget(
                budget.physical, budget.remaining(), budget.expected_requests
            )
        hist = self.history_token_model
        hist.physical_http_requests = metrics.physical_http_requests
        hist.successful_requests = metrics.successful_requests
        hist.failed_requests = metrics.failed_requests
        hist.retry_requests = metrics.retry_requests
        hist.rate_limit_waits = metrics.rate_limit_waits
        hist.rate_limit_wait_seconds = round(metrics.rate_limit_wait_seconds, 3)
        hist.provider_429_count = metrics.provider_429_count
        hist.global_cooldown_count = metrics.global_cooldown_count
        hist.job_request_budget_consumed = metrics.job_request_budget_consumed
        hist.job_request_budget_remaining = metrics.job_request_budget_remaining
        hist.job_expected_requests = metrics.job_expected_requests
        hist.connectivity_probes = metrics.connectivity_probes
        hist.provider_requests_by_phase = {
            phase: phase_metrics.as_dict()
            for phase, phase_metrics in sorted(metrics.by_phase.items())
        }
        hist.map_requests = (
            metrics.by_phase["MAP"].physical_http_requests
            if "MAP" in metrics.by_phase
            else 0
        )
        hist.reduce_requests = (
            metrics.by_phase["REDUCE"].physical_http_requests
            if "REDUCE" in metrics.by_phase
            else 0
        )
        hist.format_requests = (
            metrics.by_phase["FORMAT"].physical_http_requests
            if "FORMAT" in metrics.by_phase
            else 0
        )
        hist.direct_requests = (
            metrics.by_phase["DIRECT"].physical_http_requests
            if "DIRECT" in metrics.by_phase
            else 0
        )
        # api_request_count stays the physical MAP/REDUCE/FORMAT HTTP counter.
        if metrics.physical_http_requests:
            hist.api_request_count = metrics.physical_http_requests

    def _reset_provider_job_controls(self, model: ModelType, n_chunks: int) -> None:
        from core.brevio.services.provider_quota.job_budget import (
            JobRequestBudget,
            derive_job_max_provider_requests,
        )
        from core.brevio.services.provider_quota.metrics import ProviderCallMetrics

        metrics = ProviderCallMetrics()
        provider, scope = self._quota_scope_and_provider(model)
        policy = self.provider_executor.quota_manager.resolve_policy(
            provider, model.value, scope
        )
        max_req = derive_job_max_provider_requests(n_chunks=n_chunks, policy=policy)
        expected = n_chunks + 1
        budget = JobRequestBudget(max_physical=max_req, expected_requests=expected)
        metrics.apply_budget(0, budget.remaining(), expected)
        self.provider_executor.bind_job(budget, metrics)
        self._provider_metrics = metrics
        self._job_budget = budget
        logger.info(
            "METRIC: job_budget max=%s expected=%s n_chunks=%s max_attempts=%s",
            max_req,
            expected,
            n_chunks,
            policy.max_attempts,
        )

    def _min_tokens_for_postprocess(self, model: ModelType) -> int:
        env = min_tokens_for_postprocess_override()
        if env is not None:
            return env
        return get_model_capabilities(model).min_tokens_for_postprocess

    def _format_phase_enabled(self) -> bool:
        """FORMAT is opt-in. Final REDUCE / DIRECT already emit Markdown."""
        return format_phase_enabled()

    def _keep_partials(self) -> bool:
        return keep_partials_enabled()

    def _should_skip_formatting(self, text: str, model: ModelType) -> bool:
        """Skip FORMAT unless explicitly enabled and above the token threshold.

        Default: skip. FORMAT is a third LLM rewrite that often destroys coverage.
        Enable with BREVIO_ENABLE_FORMAT_PHASE=1 when a dedicated format pass is required.
        """
        if not self._format_phase_enabled():
            logger.info(
                "METRIC: format_skip_check reason=disabled_by_default skip=True"
            )
            return True
        encoder = get_encoder(model)
        tokens = len(encoder.encode(text or ""))
        min_tokens = self._min_tokens_for_postprocess(model)
        skip = tokens < min_tokens
        logger.info(
            "METRIC: format_skip_check tokens=%s min_tokens_for_postprocess=%s "
            "enabled=True skip=%s",
            tokens,
            min_tokens,
            skip,
        )
        return skip

    async def _persist_token_log(self) -> None:
        self._finalize_timing()
        try:
            snapshot = get_pricing_snapshot(self.history_token_model.model)
            actual_cost, _ = calculate_provider_cost(
                self.history_token_model.total_input_tokens,
                self.history_token_model.total_output_tokens,
                self.history_token_model.total_output_tokens,
                snapshot,
            )
            self.history_token_model.estimated_provider_cost = round(actual_cost, 8)
            self.history_token_model.cost_currency = snapshot.currency
            self.history_token_model.pricing_version = snapshot.pricing_version
            self.history_token_model.truncation_detected = any(
                call.finish_reason in {"length", "max_tokens"}
                for call in self.history_token_model.history_tokens_per_call
            )
            logger.info(self.history_token_model.model_dump_json(indent=2))
            await save_log_to_json(self.history_token_model.model_dump_json(indent=2))
        except Exception as log_error:
            logger.error(f"Failed to save token log: {str(log_error)}", exc_info=True)

    async def generate_summary_documents(
        self,
        prompt_config: PromptConfig,
        file_configs: List[FileConfig],
        folder_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[SummaryResponse]:
        self.history_token_model = HistoryTokenModel(
            folder_id=folder_id,
            user_id=user_id,
            started_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        logger.info(f"Starting summary generation for {len(file_configs)} documents")
        self._pipeline_t0 = time.time()
        caps = get_model_capabilities(prompt_config.model)
        self.temperature = generation_temperature(caps)
        self._generation_max_output_tokens = None
        self._generation_reasoning_effort = prompt_config.reasoning_effort
        from core.brevio.services.provider_quota.metrics import ProviderCallMetrics

        self.provider_executor.bind_job(None, ProviderCallMetrics())
        self._job_budget = None
        try:
            connected = await self.api_service.check_api_connectivity(
                prompt_config.model, user_id
            )
            self.provider_executor.metrics.record_probe()
            self.history_token_model.connectivity_probes = (
                int(self.history_token_model.connectivity_probes or 0) + 1
            )
            if not connected:
                logger.error("Cannot proceed: API client initialization failed")
                return [
                    SummaryResponse(
                        success=False,
                        summary="",
                        message="API connectivity check failed",
                        error_message="API connectivity check failed",
                        phase=PipelinePhase.INITIALIZING.value,
                        error_type="ConnectivityError",
                        status=job_status_for(success=False).value,
                        job_phase=job_phase_for(
                            PipelinePhase.INITIALIZING, success=False
                        ).value,
                    )
                    for _ in file_configs
                ]
            self.history_token_model.model = prompt_config.model
            target_language = self._resolve_target_language(prompt_config)
            self.history_token_model.language_output = target_language.name.lower()
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
                lang=target_language,
                summary_level=prompt_config.summary_level,
            )

            model = prompt_config.model
            self.client = await self.api_service._initialize_client(model, user_id)

            results = []
            for file_config in file_configs:
                logger.debug(
                    f"Processing document sequentially: {file_config.document_path}"
                )
                try:
                    result = await self._process_single_document(
                        prompt,
                        file_config,
                        model,
                        prompt_config,
                        folder_id=folder_id,
                        user_id=user_id,
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
                    fail_phase = getattr(
                        e, "phase", PipelinePhase.INVARIANT_FAILED.value
                    )
                    results.append(
                        SummaryResponse(
                            success=False,
                            summary="",
                            message=f"Error processing document: {str(e)}",
                            error_message=str(e),
                            phase=fail_phase,
                            error_type=type(e).__name__,
                            status=job_status_for(success=False).value,
                            job_phase=job_phase_for(fail_phase, success=False).value,
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

    def _resolve_target_language(self, prompt_config) -> LanguageType:
        """Return the user-configured output/instruction language.

        Never use detected document language (``language_input``) here.
        Accepts ``PromptConfig.target_language`` or the API field ``.language``.
        """
        tl = getattr(prompt_config, "target_language", None)
        if isinstance(tl, LanguageType):
            return tl
        lang = getattr(prompt_config, "language", None)
        if isinstance(lang, LanguageType):
            return lang
        raise TypeError(
            "prompt_config must provide target_language/language as LanguageType"
        )

    async def detect_language_with_retry_safe(self, text: str) -> str:
        try:
            import langdetect
            from langdetect import detect

            langdetect.DetectorFactory.seed = 0
            detected = detect(text)
            if detected:
                return detected
        except Exception as e:
            logger.warning(f"langdetect failed: {e}")
        return "en"

    def _quota_scope_and_provider(self, model: ModelType) -> Tuple[str, str]:
        provider = get_model_capabilities(model).provider.lower()
        scope = self.api_service.last_quota_scope_id or "unknown"
        try:
            policy = self.provider_executor.quota_manager.resolve_policy(
                provider, model.value, scope
            )
            if policy.quota_scope:
                scope = policy.quota_scope
        except Exception:
            pass
        return provider, scope

    async def _complete_chat(
        self,
        model: ModelType,
        messages: List[dict],
        *,
        max_tokens: int,
        temperature: float,
        extra: dict,
        timeout: float,
        client: Optional[AsyncOpenAI] = None,
    ) -> ChatCompletion:
        active = client or self.client
        if not active:
            raise ValueError("Client not initialized")
        provider_id = get_model_capabilities(model).provider.lower()
        provider = self.summary_providers.get(provider_id)
        extra_payload = dict(extra or {})
        effort = getattr(self, "_generation_reasoning_effort", None)
        caps = get_model_capabilities(model)
        if effort and caps.reasoning == "reasoning_effort":
            extra_payload["reasoning_effort"] = effort
        elif effort and caps.reasoning == "effort":
            extra_payload["effort"] = effort
        return await provider.complete(
            active,
            CompletionRequest(
                model=model.value,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                extra=extra_payload,
                timeout=timeout,
            ),
        )

    async def generate_summary_chunk(
        self,
        index: int,
        chunk: str,
        prompt: str,
        model: ModelType,
        target_language: LanguageType,
        total_document_tokens: int,
        total_chunks: int = 1,
        output_target_tokens: int = 0,
    ) -> Tuple[int, Optional[str], int]:
        import time

        start_time = time.time()
        logger.info(f"Processing chunk {index} for model {model.value}")

        try:
            encoder = get_encoder(model)
            if not self.client:
                raise ValueError("Client not initialized")

            summary_level = SummaryLevel(self.history_token_model.summary_level)
            map_chunk = chunk
            stripped = strip_leading_toc(chunk)
            if stripped and stripped != chunk.strip():
                map_chunk = stripped
                logger.info(
                    "MAP chunk %s: stripped leading TOC (%s → %s chars)",
                    index,
                    len(chunk),
                    len(map_chunk),
                )
            elif not stripped.strip() and chunk.strip():
                map_chunk = ""

            if (
                not map_chunk.strip()
                or is_table_of_contents_chunk(chunk)
                or is_table_of_contents_chunk(map_chunk)
            ):
                labels = extract_toc_entry_labels(chunk)
                stub = resolve_language_prompts(target_language).get_toc_map_stub(
                    labels
                )
                logger.info(
                    "MAP chunk %s treated as TOC stub (%s labels); skipping LLM",
                    index,
                    len(labels),
                )
                dump_audit("02_MAP", f"chunk_{index}_toc_stub", stub)
                return index, stub, 0

            # Do not prepend a document-level word quota. DeepSeek Flash with thinking
            # disabled treats "MUST be approximately N words" as a fill-the-budget
            # instruction, hits max_tokens, and MAP rejects the chunk (finish_reason=length).
            full_prompt = prompt
            user_tokens = len(encoder.encode(map_chunk))
            system_tokens = len(encoder.encode(full_prompt))
            chunk_max_tokens = self._map_completion_token_limit(
                model, summary_level, system_tokens, user_tokens, total_document_tokens
            )

            messages = [
                {"role": RoleType.SYSTEM.value, "content": full_prompt},
                {"role": RoleType.USER.value, "content": map_chunk},
            ]
            self._record_prompt_hash("MAP", full_prompt)

            # Reserve the MAP completion cap, not the document-level REDUCE target.
            tokens_needed = system_tokens + user_tokens + chunk_max_tokens
            await self._check_token_limit(
                tokens_needed=tokens_needed,
                request_type="MAP",
                model_name=model.value,
                input_tokens=system_tokens + user_tokens,
                requested_output_tokens=chunk_max_tokens,
            )

            provider, scope = self._quota_scope_and_provider(model)
            input_tokens = system_tokens + user_tokens

            async def _call():
                self._record_api_request("MAP")
                return await self._complete_chat(
                    model,
                    messages,
                    max_tokens=chunk_max_tokens,
                    temperature=self.temperature,
                    extra=completion_extra_kwargs(model, max_tokens=chunk_max_tokens),
                    timeout=self._completion_timeout_s(model, "MAP"),
                    client=self.client,
                )

            response = await self.provider_executor.execute(
                _call,
                provider=provider,
                model=model.value,
                quota_scope_id=scope,
                phase="MAP",
                estimated_input_tokens=input_tokens,
                chunk_id=str(index),
            )
            output_tokens = response.usage.completion_tokens if response.usage else 0

            if not hasattr(response, "choices") or not response.choices:
                logger.error(f"Invalid API response for chunk {index}")
                return index, None, 0

            finish_reason = (
                response.choices[0].finish_reason
                if response.choices[0].finish_reason
                else "unknown"
            )

            content = response.choices[0].message.content
            summary = (content or "").strip()

            if finish_reason in ["length", "max_tokens"]:
                usable = self._usable_map_extract(summary)
                if usable is None:
                    logger.warning(
                        f"Truncation detected via finish_reason: {finish_reason}"
                    )
                    raise ContextOverflowError(
                        f"MAP chunk {index} truncated (finish_reason={finish_reason})"
                    )
                if usable != summary:
                    logger.warning(
                        "MAP chunk %s hit finish_reason=%s; trimmed to last complete unit",
                        index,
                        finish_reason,
                    )
                else:
                    logger.info(
                        "MAP chunk %s filled completion budget with a complete extract "
                        "(finish_reason=%s)",
                        index,
                        finish_reason,
                    )
                summary = usable

            budget_utilization = (
                output_tokens / chunk_max_tokens if chunk_max_tokens > 0 else 0
            )
            execution_id = self.history_token_model.execution_id

            duration = time.time() - start_time
            logger.info(
                f"METRIC: phase=MAP execution_id={execution_id} summary_level={summary_level.name} model={model.value} "
                f"chunk_index={index} total_chunks={total_chunks} duration={duration:.2f}s "
                f"input_tokens={system_tokens+user_tokens} requested_max_tokens={chunk_max_tokens} "
                f"output_tokens={output_tokens} finish_reason={finish_reason} "
                f"budget_utilization={budget_utilization:.2f} output_target_tokens={output_target_tokens}"
            )

            self.history_token_model.history_tokens_per_call.append(
                HistoryTokenCall(
                    type_call=TypeCall.SUMMARY,
                    system_prompt_tokens=system_tokens,
                    user_prompt_tokens=user_tokens,
                    response_tokens=output_tokens,
                    request_index=len(self.history_token_model.history_tokens_per_call)
                    + 1,
                    duration_seconds=round(duration, 3),
                    finish_reason=finish_reason,
                    requested_output_tokens=chunk_max_tokens,
                    budget_utilization=round(budget_utilization, 4),
                    chunk_id=str(index),
                )
            )
            self.history_token_model.total_tokens_summary_input += (
                system_tokens + user_tokens
            )
            self.history_token_model.total_tokens_summary_output += output_tokens

            if not summary:
                logger.warning(f"Chunk {index} has no content in response")
                return index, None, 0
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Refund unused tokens from our original reservation
            unused = tokens_needed - tokens_used
            self.refund_tokens(unused)

            dump_audit("02_MAP_INPUT", "prompt", chunk, str(index))
            dump_audit("02_MAP_OUTPUT", "summary", summary, str(index))

            return index, summary, tokens_used

        except (
            RateLimitError,
            APIConnectionError,
            httpx.HTTPError,
            asyncio.TimeoutError,
        ) as e:
            # Refund everything if the call failed entirely
            if "tokens_needed" in locals():
                self.refund_tokens(tokens_needed)
            logger.warning(f"Retryable error on chunk {index}: {e}")
            raise
        except Exception as e:
            if "tokens_needed" in locals():
                self.refund_tokens(tokens_needed)
            logger.error(f"Unexpected error on chunk {index}: {e}", exc_info=True)
            raise

    async def run_direct_summary(
        self,
        full_text: str,
        prompt: str,
        model: ModelType,
        target_language: LanguageType,
        *,
        outline: Optional[List[str]] = None,
        output_target_tokens: int = 0,
    ) -> Tuple[str, int]:
        """Single-pass summary when the full document fits in context.

        One LLM call. No MAP, no REDUCE, no FORMAT.
        """
        import time

        start_time = time.time()
        encoder = get_encoder(model)
        model_cap = get_model_capabilities(model)
        if not self.client:
            self.client = await self.api_service._initialize_client(
                model, self.history_token_model.user_id
            )

        lang_prompts = resolve_language_prompts(target_language)
        checklist = lang_prompts.get_coverage_checklist(outline or [])
        system_prompt = prompt
        if checklist:
            system_prompt = f"{prompt}\n\n{checklist}"
        coverage = lang_prompts.get_coverage_guarantee()
        if coverage and coverage not in system_prompt:
            system_prompt = f"{system_prompt}\n\n{coverage}"

        system_tokens = len(encoder.encode(system_prompt))
        user_tokens = len(encoder.encode(full_text))
        try:
            summary_level = SummaryLevel(self.history_token_model.summary_level)
        except Exception:
            summary_level = SummaryLevel.MODERATE
        decision = AdaptiveSaliencePolicy().budget(
            model,
            summary_level,
            self.history_token_model.num_tokens_file or user_tokens,
            target_language,
        )
        target = output_target_tokens or decision.output_target_tokens
        requested = min(
            summary_max_output_tokens(model_cap),
            max(target + model_cap.output_padding_tokens, decision.output_min_tokens),
        )
        max_output_tokens = self._safe_completion_token_limit(
            model, system_tokens, user_tokens, requested
        )
        self._record_prompt_hash("DIRECT", system_prompt)

        await self._check_token_limit(
            tokens_needed=system_tokens + user_tokens + max_output_tokens,
            request_type="DIRECT",
            model_name=model.value,
            input_tokens=system_tokens + user_tokens,
            requested_output_tokens=max_output_tokens,
        )

        provider, scope = self._quota_scope_and_provider(model)

        async def _call():
            self._record_api_request("DIRECT")
            return await self._complete_chat(
                model,
                [
                    {"role": RoleType.SYSTEM.value, "content": system_prompt},
                    {"role": RoleType.USER.value, "content": full_text},
                ],
                max_tokens=max_output_tokens,
                temperature=self.temperature,
                extra=completion_extra_kwargs(model, max_tokens=max_output_tokens),
                timeout=self._completion_timeout_s(model, "DIRECT"),
                client=self.client,
            )

        response = await self.provider_executor.execute(
            _call,
            provider=provider,
            model=model.value,
            quota_scope_id=scope,
            phase="DIRECT",
            estimated_input_tokens=system_tokens + user_tokens,
            chunk_id="direct",
        )
        output_tokens = response.usage.completion_tokens if response.usage else 0
        finish_reason = (
            response.choices[0].finish_reason
            if response.choices and response.choices[0].finish_reason
            else "unknown"
        )
        content = (
            (response.choices[0].message.content or "").strip()
            if response.choices
            else ""
        )
        if not content:
            raise InvariantViolationError(
                "DIRECT summary returned empty content",
                phase=PipelinePhase.DIRECT_FAILED.value,
            )
        if finish_reason in ("length", "max_tokens"):
            usable = self._usable_map_extract(content)
            if usable is None:
                raise ContextOverflowError(
                    f"DIRECT summary truncated (finish_reason={finish_reason})"
                )
            content = usable

        duration = time.time() - start_time
        self.history_token_model.history_tokens_per_call.append(
            HistoryTokenCall(
                type_call=TypeCall.DIRECT,
                system_prompt_tokens=system_tokens,
                user_prompt_tokens=user_tokens,
                response_tokens=output_tokens,
                request_index=len(self.history_token_model.history_tokens_per_call) + 1,
                duration_seconds=round(duration, 3),
                finish_reason=finish_reason,
                requested_output_tokens=max_output_tokens,
                budget_utilization=round(
                    output_tokens / max_output_tokens if max_output_tokens > 0 else 0.0,
                    4,
                ),
                chunk_id="direct",
            )
        )
        self.history_token_model.total_tokens_summary_input += (
            system_tokens + user_tokens
        )
        self.history_token_model.total_tokens_summary_output += output_tokens

        logger.info(
            "METRIC: phase=DIRECT duration=%.2fs input_tokens=%s output_tokens=%s "
            "max_tokens=%s finish_reason=%s outline_entries=%s",
            duration,
            system_tokens + user_tokens,
            output_tokens,
            max_output_tokens,
            finish_reason,
            len(outline or []),
        )
        dump_audit("02_DIRECT", "OUT_summary", content)
        return content, (
            response.usage.total_tokens
            if response.usage
            else system_tokens + user_tokens + output_tokens
        )

    async def run_map_phase(
        self,
        chunks: List[str],
        map_prompt: str,
        model: ModelType,
        target_language: LanguageType,
        callback: Optional[Any] = None,
    ) -> Tuple[List[MapChunkResult], int]:
        import time

        start_time = time.time()
        logger.info(f"Starting Map phase for {len(chunks)} chunks")
        total_tokens_used = 0
        chunk_summaries: List[Optional[MapChunkResult]] = [None] * len(chunks)

        try:
            encoder = get_encoder(model)
            total_document_tokens = sum(len(encoder.encode(c)) for c in chunks)
            for group_start in range(0, len(chunks), self.max_concurrent_chunks):
                group_end = min(group_start + self.max_concurrent_chunks, len(chunks))
                group_chunks = chunks[group_start:group_end]
                group_indices = list(range(group_start, group_end))

                try:
                    summary_level = SummaryLevel(self.history_token_model.summary_level)
                except Exception:
                    summary_level = SummaryLevel.MODERATE

                from core.shared.utils.adaptive_salience_policy import (
                    AdaptiveSaliencePolicy,
                )

                policy = AdaptiveSaliencePolicy()
                decision = policy.budget(
                    model, summary_level, total_document_tokens, target_language
                )

                tasks = [
                    asyncio.create_task(
                        self.generate_summary_chunk(
                            index,
                            chunk,
                            map_prompt,
                            model,
                            target_language,
                            total_document_tokens,
                            total_chunks=len(chunks),
                            output_target_tokens=decision.output_target_tokens,
                        )
                    )
                    for index, chunk in zip(group_indices, group_chunks)
                ]

                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    await cancel_pending_tasks(tasks)
                    raise

                from httpx import RequestError
                from openai import OpenAIError

                EXPECTED_MAP_ERRORS = (
                    OpenAIError,
                    RequestError,
                    asyncio.TimeoutError,
                    ContextOverflowError,
                )

                fatal_error: Optional[BaseException] = None
                cancelled = False
                for result in results:
                    if isinstance(result, asyncio.CancelledError):
                        cancelled = True
                    elif isinstance(result, BaseException) and not isinstance(
                        result, EXPECTED_MAP_ERRORS
                    ):
                        fatal_error = result
                        break

                if cancelled or fatal_error is not None:
                    await cancel_pending_tasks(tasks)
                    if fatal_error is not None:
                        raise fatal_error
                    raise asyncio.CancelledError

                for index, chunk, result in zip(group_indices, group_chunks, results):
                    if isinstance(result, BaseException):
                        logger.error(f"Chunk {index} failed definitively: {result}")
                        chunk_summaries[index] = MapChunkResult(
                            chunk_id=index,
                            original_text=chunk,
                            status="FAILED",
                            summary_text=None,
                            error_message=str(result),
                        )
                    elif isinstance(result, tuple):
                        idx, chunk_summary, tokens_used = result
                        if idx != index:
                            raise InvariantViolationError(
                                f"Worker returned mismatched index: expected {index}, got {idx}",
                                phase=PipelinePhase.INVARIANT_FAILED.value,
                            )

                        if chunk_summary is not None and str(chunk_summary).strip():
                            chunk_summaries[index] = MapChunkResult(
                                chunk_id=index,
                                original_text=chunk,
                                status="SUCCESS",
                                summary_text=chunk_summary,
                            )
                        else:
                            chunk_summaries[index] = MapChunkResult(
                                chunk_id=index,
                                original_text=chunk,
                                status="FAILED",
                                summary_text=None,
                                error_message="Empty summary returned",
                            )
                        total_tokens_used += tokens_used

                if callback:
                    # Incremental progress: flush only newly completed SUCCESS texts
                    # for this group — do not rebuild/join the entire MAP output.
                    for index in group_indices:
                        item = chunk_summaries[index]
                        if (
                            item is not None
                            and item.status == "SUCCESS"
                            and item.summary_text
                            and item.summary_text.strip()
                            and not is_toc_map_stub(item.summary_text)
                        ):
                            await callback(item.summary_text)

            if any(s is None for s in chunk_summaries):
                raise InvariantViolationError(
                    f"MAP phase silently lost {chunk_summaries.count(None)} chunks (None values present).",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                )

            final_summaries = chunk_summaries

            duration = time.time() - start_time
            logger.info(
                f"METRIC: phase=GLOBAL_MAP map_calls={len(chunks)} duration={duration:.2f}s elapsed_s={self._elapsed_s():.2f} api_requests={self.history_token_model.api_request_count}"
            )

            return final_summaries, total_tokens_used

        except asyncio.CancelledError:
            logger.info("Processing cancelled")
            raise

    async def run_reduce_phase(
        self,
        mapped_summaries: List[Any],
        reduce_prompt: str,
        model: ModelType,
        target_language: LanguageType | None = None,
        force_reduce: bool = False,
        intermediate_reduce_prompt: str = None,
        language: LanguageType | None = None,
        assemble_sections: bool | None = None,
    ) -> Tuple[str, int]:
        """
        Reduce phase input contract:
        - Canonical: List[MapChunkResult] from run_map_phase
          SUCCESS → summary_text
          FAILED → original_text only if BREVIO_ALLOW_MAP_ORIGINAL_TEXT_FALLBACK
            (default false: fail the job instead of mixing original PDF into REDUCE)
        - Legacy (tests): List[str] or List[ReduceChunk] still accepted
        """
        import re

        encoder = get_encoder(model)
        model_cap = get_model_capabilities(model)
        logger.info(
            f"Starting hierarchical Reduce phase for {len(mapped_summaries)} summaries"
        )
        if target_language is None:
            target_language = language
        if target_language is None:
            raise TypeError("run_reduce_phase requires target_language")
        lang_prompts = resolve_language_prompts(target_language)

        # Convert input summaries into structured ReduceChunk objects
        current_chunks: List[ReduceChunk] = []
        for i, item in enumerate(mapped_summaries):
            if isinstance(item, ReduceChunk):
                current_chunks.append(item)
            elif isinstance(item, MapChunkResult):
                from core.brevio.services.provider_quota.policy import (
                    allow_map_original_text_fallback,
                )

                allow_fallback = allow_map_original_text_fallback()
                text_to_use = item.text_for_reduce(
                    allow_original_fallback=allow_fallback
                )
                current_chunks.append(
                    ReduceChunk(
                        text=text_to_use,
                        source_chunk_indices=[item.chunk_id],
                        tokens=len(encoder.encode(text_to_use)),
                    )
                )
            elif isinstance(item, str) and item.strip():
                current_chunks.append(
                    ReduceChunk(
                        text=item,
                        source_chunk_indices=[i],
                        tokens=len(encoder.encode(item)),
                    )
                )
            else:
                raise InvariantViolationError(
                    f"Unsupported REDUCE input[{i}] type={type(item).__name__}; "
                    "expected MapChunkResult (canonical), ReduceChunk, or non-empty str (legacy)",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                    input_index=i,
                    input_type=type(item).__name__,
                )

        dropped = len(current_chunks)
        current_chunks = self._reduce_chunks_without_toc_stubs(current_chunks)
        dropped -= len(current_chunks)
        if dropped:
            logger.info("REDUCE dropped %s TOC MAP stub(s) before synthesis", dropped)

        if not current_chunks:
            res = ReduceResult("", 0, [])
            self.last_reduce_result = res
            return res

        # All expected source chunk indices that entered REDUCE
        expected_chunk_indices = sorted(
            list(set.union(*(set(c.source_chunk_indices) for c in current_chunks)))
        )

        if len(current_chunks) <= 1 and not force_reduce:
            res = ReduceResult(
                current_chunks[0].text,
                0,
                current_chunks[0].source_chunk_indices,
            )
            self.last_reduce_result = res
            return res

        total_tokens_used = 0
        client = await self.api_service._initialize_client(
            model, self.history_token_model.user_id
        )
        try:
            summary_level = SummaryLevel(self.history_token_model.summary_level)
        except Exception:
            summary_level = SummaryLevel.MODERATE

        reduce_prompt_tokens = len(encoder.encode(reduce_prompt))
        final_batch_limit = self._reduce_batch_token_limit(
            model, summary_level, reduce_prompt_tokens, is_intermediate=False
        )
        intermediate_batch_limit = self._reduce_batch_token_limit(
            model, summary_level, reduce_prompt_tokens, is_intermediate=True
        )
        total_source_tokens = (
            self.history_token_model.num_tokens_file or model_cap.overhead
        )
        budget_decision = AdaptiveSaliencePolicy().budget(
            model, summary_level, total_source_tokens, target_language
        )
        if assemble_sections is None:
            assemble_sections = (
                getattr(budget_decision, "requires_section_assembly", False) is True
            )
        else:
            assemble_sections = assemble_sections is True
        final_target_max_tokens = budget_decision.output_target_tokens
        pack_multiplier = packing_token_multiplier(model_cap)
        section_keep = getattr(
            budget_decision, "section_keep_ratio", SECTION_KEEP_RATIO
        )
        if not isinstance(section_keep, (int, float)):
            section_keep = SECTION_KEEP_RATIO
        final_pack_limit = self._final_reduce_pack_limit(
            model, summary_level, reduce_prompt_tokens, final_target_max_tokens
        )

        logger.info(
            f"REDUCE configuration: model={model.value}, summary_level={summary_level.value}, "
            f"final_batch_limit={final_batch_limit}, final_pack_limit={final_pack_limit}, "
            f"intermediate_batch_limit={intermediate_batch_limit}, "
            f"native_max_output={summary_max_output_tokens(model_cap)}, "
            f"final_target_max_tokens={final_target_max_tokens}, "
            f"assemble_sections={assemble_sections}, total_input_chunks={len(current_chunks)}"
        )

        async def _reduce_batch(
            batch_items: List[ReduceChunk],
            level: int = 1,
            batch_idx: int = 1,
            total_batches: int = 1,
            is_final_round: bool = False,
            _depth: int = 0,
        ) -> Tuple[List[ReduceChunk], int, str]:
            """Reduce un batch estructurado; garantiza que no se pierde cobertura de chunks."""

            # Formar el texto del batch con delimitadores claros
            if len(batch_items) > 1:
                blocks = []
                for idx, item in enumerate(batch_items):
                    chunk_ids_str = ",".join(
                        str(cid) for cid in item.source_chunk_indices
                    )
                    blocks.append(
                        f"{lang_prompts.format_reduce_block_header(idx + 1, chunk_ids_str)}\n{item.text}"
                    )
                batch_text = "\n\n".join(blocks)
            else:
                batch_text = batch_items[0].text

            batch_chunk_ids = sorted(
                list(set.union(*(set(c.source_chunk_indices) for c in batch_items)))
            )
            batch_input_tokens = len(encoder.encode(batch_text))

            is_final = is_final_round

            if (
                not is_final
                and len(batch_items) == 1
                and batch_input_tokens < MIN_SINGLE_INTERMEDIATE_REDUCE_TOKENS
            ):
                logger.info(
                    "REDUCE passthrough tiny single item tokens=%s batch=%s depth=%s",
                    batch_input_tokens,
                    batch_idx,
                    _depth,
                )
                return batch_items, 0, "stop"

            if is_final:
                effective_final_target = final_target_max_tokens
                if batch_input_tokens < final_target_max_tokens:
                    effective_final_target = min(
                        final_target_max_tokens,
                        max(batch_input_tokens, int(batch_input_tokens * 1.1)),
                    )
                current_reduce_prompt = (
                    lang_prompts.get_final_reduce_instruction(effective_final_target)
                    + reduce_prompt
                )
                instruction_target = min(
                    summary_max_output_tokens(model_cap),
                    effective_final_target
                    + min(
                        model_cap.output_padding_tokens,
                        max(64, batch_input_tokens // 4),
                    ),
                )
                # 003 asyncio: 4 parallel finals requested ~7k and emitted ~5k each,
                # so L2 still had 4 blocks and join-cap concatenated ~50k chars
                # (fidelity 70→43). Cap each sibling so N outputs fit one pack.
                if total_batches > 1:
                    merge_cap = max(768, int(final_pack_limit / (total_batches + 1)))
                    instruction_target = min(instruction_target, merge_cap)
            else:
                r_comp = (
                    float(section_keep)
                    if assemble_sections
                    else INTERMEDIATE_COMPRESSION_RATIO
                )
                base_prompt_to_use = (
                    intermediate_reduce_prompt
                    if intermediate_reduce_prompt
                    else reduce_prompt
                )
                current_reduce_prompt = (
                    lang_prompts.get_intermediate_reduce_instruction(
                        batch_input_tokens, r_comp
                    )
                    + base_prompt_to_use
                )
                instruction_target = min(
                    summary_max_output_tokens(model_cap),
                    int(batch_input_tokens * r_comp) + model_cap.output_padding_tokens,
                )
            current_target_max_tokens = self._reduce_output_budget_for_batch(
                instruction_target,
                batch_input_tokens,
                summary_max_output_tokens(model_cap),
                model_cap.output_padding_tokens,
                is_final,
            )

            reduced, tokens, finish = await self._execute_reduce_call(
                batch_text,
                current_reduce_prompt,
                model,
                client,
                current_target_max_tokens,
                target_language,
                reduce_level=level,
                batch_index=batch_idx,
                split_depth=_depth,
                is_final_reduce=is_final,
            )
            if (
                reduced
                and reduced.strip()
                and (
                    (
                        is_final
                        and self._prose_language_mismatch(reduced, target_language)
                    )
                    or self._looks_like_assistant_chat(reduced)
                )
            ):
                logger.warning(
                    "REDUCE final output failed quality gate; retrying once target=%s chatbot=%s lang_mismatch=%s",
                    target_language,
                    self._looks_like_assistant_chat(reduced),
                    self._prose_language_mismatch(reduced, target_language),
                )
                retry_prompt = (
                    f"{self.advanced_prompt_generator.target_language_directive(lang_prompts)}\n\n"
                    f"{lang_prompts.get_reduce_quality_retry_instruction()}"
                    f"{current_reduce_prompt}"
                )
                retried, retry_tokens, retry_finish = await self._execute_reduce_call(
                    batch_text,
                    retry_prompt,
                    model,
                    client,
                    current_target_max_tokens,
                    target_language,
                    reduce_level=level,
                    batch_index=batch_idx,
                    split_depth=_depth,
                    is_final_reduce=is_final,
                )
                tokens += retry_tokens
                if retried and retried.strip():
                    reduced = retried
                    finish = retry_finish
                if self._looks_like_assistant_chat(reduced):
                    logger.error(
                        "REDUCE still assistant-chat after retry; "
                        "keeping batch source level=%s batch=%s depth=%s is_final=%s",
                        level,
                        batch_idx,
                        _depth,
                        is_final,
                    )
                    dump_audit(
                        f"03_REDUCE_L{level}",
                        f"IN_batch{batch_idx}_depth{_depth}",
                        batch_text,
                    )
                    dump_audit(
                        f"03_REDUCE_L{level}",
                        f"OUT_batch{batch_idx}_depth{_depth}_CHATBOT_REJECTED",
                        reduced,
                    )
                    kept_tokens = len(encoder.encode(batch_text))
                    return (
                        [
                            ReduceChunk(
                                text=batch_text,
                                source_chunk_indices=batch_chunk_ids,
                                tokens=kept_tokens,
                            )
                        ],
                        tokens,
                        "stop",
                    )

            dump_audit(
                f"03_REDUCE_L{level}", f"IN_batch{batch_idx}_depth{_depth}", batch_text
            )
            dump_audit(
                f"03_REDUCE_L{level}", f"OUT_batch{batch_idx}_depth{_depth}", reduced
            )

            actual_output_tokens = len(encoder.encode(reduced)) if reduced else 0
            logger.info(
                "METRIC: phase=REDUCE level=%s batch_index=%s depth=%s "
                "input_estimated_tokens=%s number_of_chunks=%s "
                "output_token_limit=%s actual_output_tokens=%s finish_reason=%s",
                level,
                batch_idx,
                _depth,
                batch_input_tokens,
                len(batch_items),
                current_target_max_tokens,
                actual_output_tokens,
                finish,
            )

            # finish_reason=length from the API is never SUCCESS.
            # Filling the instruction target with finish_reason=stop is SUCCESS:
            # max_tokens has headroom so a complete ~45% answer does not hit the cap.
            output_looks_cut = self._looks_incomplete_tail(reduced)
            hit_api_cap = (
                current_target_max_tokens > 0
                and actual_output_tokens >= current_target_max_tokens
            )
            if not reduced.strip():
                reduce_status = "EMPTY"
            elif finish == "error":
                reduce_status = "API_ERROR"
            elif finish == "length":
                reduce_status = "TRUNCATED"
            elif hit_api_cap and output_looks_cut:
                reduce_status = "TRUNCATED"
            else:
                reduce_status = "SUCCESS"

            batch_rejected = reduce_status != "SUCCESS"
            logger.info(
                "REDUCE level=%s batch=%s depth=%s finish_reason=%s status=%s "
                "input_tokens=%s output_tokens=%s is_final=%s",
                level,
                batch_idx,
                _depth,
                finish,
                reduce_status,
                batch_input_tokens,
                actual_output_tokens,
                is_final,
            )

            def _convergence_error(
                reason: str, extra_message: str
            ) -> ReduceConvergenceError:
                return ReduceConvergenceError(
                    extra_message,
                    phase=PipelinePhase.REDUCE_FAILED.value,
                    batch_index=batch_idx,
                    reduce_level=level,
                    split_depth=_depth,
                    max_split_depth=REDUCE_SPLIT_SAFETY_CAP,
                    finish_reason=finish,
                    input_estimated_tokens=batch_input_tokens,
                    number_of_chunks=len(batch_items),
                    output_token_limit=current_target_max_tokens,
                    actual_output_tokens=actual_output_tokens,
                    reason=reason,
                )

            if batch_rejected:
                can_split_items = len(batch_items) > 1
                sub_texts: List[str] = []
                if not can_split_items:
                    sub_limit = max(
                        model_cap.reduce_min_batch_tokens,
                        max(1, batch_input_tokens // 2),
                    )
                    try:
                        sub_texts = self._split_markdown_structurally(
                            batch_text, sub_limit, encoder
                        )
                    except ImpossibleRequestError as split_err:
                        salvaged = self._salvage_unsplittable_reduce(
                            reduced, reduce_status
                        )
                        if salvaged is not None:
                            reduced = salvaged
                            actual_output_tokens = len(encoder.encode(reduced))
                            finish = "stop"
                            sub_texts = []
                        elif (
                            batch_items
                            and reduce_status not in {"EMPTY", "API_ERROR"}
                            and (reduced or "").strip()
                        ):
                            logger.warning(
                                "REDUCE keeping original leftover after split error "
                                "finish=%s input_tokens=%s batch=%s depth=%s err=%s",
                                finish,
                                batch_input_tokens,
                                batch_idx,
                                _depth,
                                split_err,
                            )
                            return batch_items, tokens, "stop"
                        else:
                            raise _convergence_error(
                                "indivisible_input",
                                (
                                    f"REDUCE received an indivisible input that exceeds a single call. "
                                    f"batch={batch_idx} level={level} depth={_depth} "
                                    f"input_tokens={batch_input_tokens} finish_reason={finish}. {split_err}"
                                ),
                            ) from split_err
                can_split_structurally = len(sub_texts) > 1

                if not can_split_items and not can_split_structurally:
                    if finish != "stop":
                        salvaged = self._salvage_unsplittable_reduce(
                            reduced, reduce_status
                        )
                        if salvaged is not None:
                            logger.warning(
                                "REDUCE salvage unsplittable complete output status=%s finish=%s "
                                "input_tokens=%s output_tokens=%s batch=%s depth=%s is_final=%s",
                                reduce_status,
                                finish,
                                batch_input_tokens,
                                actual_output_tokens,
                                batch_idx,
                                _depth,
                                is_final,
                            )
                            reduced = salvaged
                            actual_output_tokens = len(encoder.encode(reduced))
                            finish = "stop"
                        elif (
                            batch_items
                            and reduce_status not in {"EMPTY", "API_ERROR"}
                            and (reduced or "").strip()
                        ):
                            logger.warning(
                                "REDUCE keeping original leftover after unsplittable %s "
                                "finish=%s input_tokens=%s batch=%s depth=%s is_final=%s",
                                reduce_status,
                                finish,
                                batch_input_tokens,
                                batch_idx,
                                _depth,
                                is_final,
                            )
                            return batch_items, tokens, "stop"
                        else:
                            raise _convergence_error(
                                "indivisible_input",
                                (
                                    f"REDUCE cannot split rejected batch {batch_idx} at level {level}. "
                                    f"Input is indivisible. depth={_depth} input_tokens={batch_input_tokens} "
                                    f"finish_reason={finish} status={reduce_status}."
                                ),
                            )
                elif can_split_items or can_split_structurally:
                    if _depth >= REDUCE_SPLIT_SAFETY_CAP:
                        raise _convergence_error(
                            "max_split_depth",
                            (
                                f"REDUCE split safety cap reached for batch {batch_idx} at level {level}. "
                                f"depth={_depth} max_split_depth={REDUCE_SPLIT_SAFETY_CAP} "
                                f"finish_reason={finish} status={reduce_status}."
                            ),
                        )

                    if can_split_items:
                        mid = max(1, len(batch_items) // 2)
                        left_items = batch_items[:mid]
                        right_items = batch_items[mid:]
                        recovery_parts = 2
                    else:
                        sub_chunks = [
                            ReduceChunk(
                                text=text,
                                source_chunk_indices=batch_chunk_ids,
                                tokens=len(encoder.encode(text)),
                            )
                            for text in sub_texts
                        ]
                        mid = max(1, len(sub_chunks) // 2)
                        left_items = sub_chunks[:mid]
                        right_items = sub_chunks[mid:]
                        recovery_parts = len(sub_chunks)

                    if not left_items or not right_items:
                        raise _convergence_error(
                            "non_progress_split",
                            (
                                f"REDUCE split produced an empty side for batch {batch_idx} at level {level}. "
                                f"left={len(left_items)} right={len(right_items)} finish_reason={finish}."
                            ),
                        )

                    left_tokens = sum(
                        item.tokens or len(encoder.encode(item.text))
                        for item in left_items
                    )
                    right_tokens = sum(
                        item.tokens or len(encoder.encode(item.text))
                        for item in right_items
                    )
                    logger.warning(
                        "REDUCE recovery strategy=split level=%s batch=%s depth=%s status=%s "
                        "parts=%s left_size=%s right_size=%s left_estimated_tokens=%s "
                        "right_estimated_tokens=%s parent_tokens=%s finish_reason=%s",
                        level,
                        batch_idx,
                        _depth,
                        reduce_status,
                        recovery_parts,
                        len(left_items),
                        len(right_items),
                        left_tokens,
                        right_tokens,
                        batch_input_tokens,
                        finish,
                    )
                    if max(left_tokens, right_tokens) >= batch_input_tokens and (
                        len(left_items) + len(right_items)
                    ) <= len(batch_items):
                        if not can_split_items:
                            raise _convergence_error(
                                "non_progress_split",
                                (
                                    f"REDUCE split did not reduce an indivisible-sized input. "
                                    f"batch={batch_idx} level={level} parent_tokens={batch_input_tokens} "
                                    f"left_tokens={left_tokens} right_tokens={right_tokens}."
                                ),
                            )

                    (res_1, tok_1, fin_1), (
                        res_2,
                        tok_2,
                        fin_2,
                    ) = await gather_or_cancel(
                        _reduce_batch(
                            left_items,
                            level,
                            batch_idx,
                            total_batches,
                            is_final,
                            _depth + 1,
                        ),
                        _reduce_batch(
                            right_items,
                            level,
                            batch_idx,
                            total_batches,
                            is_final,
                            _depth + 1,
                        ),
                    )
                    if fin_1 == "length" or fin_2 == "length":
                        raise _convergence_error(
                            "truncated_after_recovery",
                            (
                                f"REDUCE recovery still returned finish_reason=length "
                                f"batch={batch_idx} level={level} depth={_depth} "
                                f"fin_1={fin_1} fin_2={fin_2}."
                            ),
                        )
                    logger.info(
                        "REDUCE recovery status=SUCCESS level=%s batch=%s depth=%s "
                        "parts=%s fin_1=%s fin_2=%s",
                        level,
                        batch_idx,
                        _depth,
                        recovery_parts,
                        fin_1,
                        fin_2,
                    )
                    return res_1 + res_2, tokens + tok_1 + tok_2, fin_1

            return (
                [
                    ReduceChunk(
                        text=reduced,
                        source_chunk_indices=batch_chunk_ids,
                        tokens=actual_output_tokens,
                        synthesized=True,
                    )
                ],
                tokens,
                finish,
            )

        max_rounds = 10
        round_num = 0
        intermediate_rounds = 0
        final_rounds = 0
        semaphore = asyncio.Semaphore(self.max_concurrent_chunks)

        async def _process_batch_with_semaphore(
            batch: List[ReduceChunk],
            level: int,
            batch_idx: int,
            total_batches: int,
            is_final_round: bool,
        ) -> Tuple[List[ReduceChunk], int, str]:
            async with semaphore:
                return await _reduce_batch(
                    batch,
                    level=level,
                    batch_idx=batch_idx,
                    total_batches=total_batches,
                    is_final_round=is_final_round,
                )

        final_finish_reason = "stop"
        needs_final_pass = True

        # If there is exactly one summary but force_reduce is True, reduce it here.
        if len(current_chunks) == 1 and force_reduce:
            results, tokens, finish = await _reduce_batch(
                current_chunks,
                level=1,
                batch_idx=1,
                total_batches=1,
                is_final_round=True,
            )
            total_tokens_used += tokens
            current_chunks = results if results else current_chunks
            final_finish_reason = finish
            needs_final_pass = False

        if assemble_sections and len(current_chunks) > 1:
            logger.info(
                "REDUCE section-assembly: one intermediate pass then FINAL synthesis "
                "artifact_target=%s per_call_cap=%s chunks=%s",
                final_target_max_tokens,
                summary_max_output_tokens(model_cap),
                len(current_chunks),
            )
            batches = self._pack_reduce_chunks(
                current_chunks,
                intermediate_batch_limit,
                encoder,
                token_multiplier=pack_multiplier,
            )
            tasks = [
                asyncio.create_task(
                    _process_batch_with_semaphore(
                        batch, 1, idx + 1, len(batches), False
                    )
                )
                for idx, batch in enumerate(batches)
            ]
            batch_results = await gather_or_cancel(*tasks)
            next_chunks: List[ReduceChunk] = []
            for results, tokens, finish in batch_results:
                next_chunks.extend(results)
                total_tokens_used += tokens
                final_finish_reason = finish
            current_chunks = next_chunks if next_chunks else current_chunks
            # 002 concatenated these leftovers: asyncio fidelity 70→47.
            # Keep the section pass, then a real is_final REDUCE like 001.
            needs_final_pass = True
            logger.info(
                "REDUCE section-assembly entering final synthesis chunks=%s",
                len(current_chunks),
            )

        while (len(current_chunks) > 1 or needs_final_pass) and round_num < max_rounds:
            round_num += 1
            prev_count = len(current_chunks)
            total_current_tokens = sum(
                (c.tokens or len(encoder.encode(c.text))) for c in current_chunks
            ) + (len(current_chunks) * 10)

            fits_one_intermediate_batch = (
                total_current_tokens <= intermediate_batch_limit
            )
            if assemble_sections:
                is_final_round = True
            else:
                is_final_round = (
                    len(current_chunks) == 1
                    or fits_one_intermediate_batch
                    or intermediate_rounds >= MAX_INTERMEDIATE_REDUCE_ROUNDS
                    or (
                        intermediate_rounds >= 1
                        and total_current_tokens <= final_pack_limit
                    )
                )
            if is_final_round:
                if final_rounds >= MAX_FINAL_REDUCE_ROUNDS:
                    leftover_ok = self._leftover_blocks_are_deliverable(current_chunks)
                    remaining_tokens = total_current_tokens
                    compact_enough = remaining_tokens <= max(
                        final_pack_limit,
                        int(final_target_max_tokens * 1.25)
                        if final_target_max_tokens
                        else final_pack_limit,
                    )
                    if len(current_chunks) > 1 and not leftover_ok:
                        raise ReduceConvergenceError(
                            "REDUCE could not merge remaining blocks after the final join cap.",
                            phase=PipelinePhase.REDUCE_FAILED.value,
                            batch_index=1,
                            reduce_level=round_num,
                            split_depth=0,
                            number_of_chunks=len(current_chunks),
                            finish_reason="length",
                            reason="final_join_cap",
                        )
                    if compact_enough:
                        logger.warning(
                            "REDUCE final join cap reached with %s chunks; concatenating remaining blocks.",
                            len(current_chunks),
                        )
                        needs_final_pass = False
                        break
                    logger.warning(
                        "REDUCE final join cap with %s chunks tokens=%s still too large; compressing further",
                        len(current_chunks),
                        remaining_tokens,
                    )
                    current_batch_limit = final_pack_limit
                    is_final_round = True
                    needs_final_pass = False
                else:
                    final_rounds += 1
                    needs_final_pass = False
                    current_batch_limit = final_pack_limit
            else:
                intermediate_rounds += 1
                current_batch_limit = intermediate_batch_limit

            batches = self._pack_reduce_chunks(
                current_chunks,
                current_batch_limit,
                encoder,
                token_multiplier=pack_multiplier,
            )

            logger.info(
                f"Reduce round {round_num}: processing {len(batches)} batches concurrently. "
                f"Target limit: {current_batch_limit} is_final={is_final_round} "
                f"chunks={len(current_chunks)} tokens={total_current_tokens} "
                f"elapsed_s={self._elapsed_s():.2f} api_requests={self.history_token_model.api_request_count}"
            )
            tasks = [
                asyncio.create_task(
                    _process_batch_with_semaphore(
                        b, round_num, idx + 1, len(batches), is_final_round
                    )
                )
                for idx, b in enumerate(batches)
            ]
            batch_results = await gather_or_cancel(*tasks)

            next_chunks: List[ReduceChunk] = []
            for results, tokens, finish in batch_results:
                next_chunks.extend(results)
                total_tokens_used += tokens
                final_finish_reason = finish

            next_chunks_tokens_total = sum(
                (c.tokens or len(encoder.encode(c.text))) for c in next_chunks
            )
            input_chunk_tokens_total = sum(
                (c.tokens or len(encoder.encode(c.text))) for c in current_chunks
            )

            compression_ratio = next_chunks_tokens_total / max(1, total_current_tokens)
            target_ratio = (
                INTERMEDIATE_COMPRESSION_RATIO
                if not is_final_round
                else {
                    SummaryLevel.VERY_DETAILED: 0.90,
                    SummaryLevel.DETAILED: 0.85,
                    SummaryLevel.MODERATE: 0.70,
                    SummaryLevel.CONCISE: 0.55,
                    SummaryLevel.VERY_CONCISE: 0.45,
                }.get(summary_level, 0.70)
            )
            convergence_required = len(current_chunks) > 1
            convergence_achieved = (
                len(next_chunks) < len(current_chunks)
                or next_chunks_tokens_total < input_chunk_tokens_total
            )

            logger.info(
                f"METRIC: phase=REDUCE_CONVERGENCE level={round_num} "
                f"is_final={is_final_round} "
                f"input_chunks={prev_count} output_chunks={len(next_chunks)} "
                f"input_tokens_total={total_current_tokens} output_tokens_total={next_chunks_tokens_total} "
                f"compression_ratio={compression_ratio:.2f} target_ratio={target_ratio} "
                f"batch_limit={current_batch_limit} batch_count={len(batches)} "
                f"max_tokens={final_target_max_tokens if is_final_round else model_cap.native_max_output_tokens} finish_reason={final_finish_reason} "
                f"convergence_required={convergence_required} convergence_achieved={convergence_achieved}"
            )
            if not is_final_round and compression_ratio < (target_ratio * 0.5):
                logger.warning(
                    f"REDUCE intermediate over-compressed: compression_ratio={compression_ratio:.2f} "
                    f"target_ratio={target_ratio}. Downstream final REDUCE will have too little material."
                )

            current_chunks = next_chunks

            if is_final_round:
                if len(current_chunks) <= 1:
                    logger.info(
                        "REDUCE final round complete; assembling %s chunk(s) into the summary.",
                        len(current_chunks),
                    )
                    break
                next_total = sum(
                    (c.tokens or len(encoder.encode(c.text))) for c in current_chunks
                ) + (len(current_chunks) * 10)
                if next_total <= final_pack_limit or len(current_chunks) < prev_count:
                    logger.info(
                        "REDUCE final join continuing: chunks=%s tokens=%s pack_limit=%s",
                        len(current_chunks),
                        next_total,
                        final_pack_limit,
                    )
                    needs_final_pass = True
                    continue
                if not self._leftover_blocks_are_deliverable(current_chunks):
                    raise ReduceConvergenceError(
                        "REDUCE final synthesis could not merge remaining blocks into a valid summary.",
                        phase=PipelinePhase.REDUCE_FAILED.value,
                        batch_index=1,
                        reduce_level=round_num,
                        split_depth=0,
                        number_of_chunks=len(current_chunks),
                        finish_reason="length",
                        reason="final_join_unmergeable",
                    )
                logger.warning(
                    "REDUCE final synthesis could not merge %s blocks into one document; concatenating.",
                    len(current_chunks),
                )
                break

            if not is_final_round and not convergence_achieved and prev_count > 1:
                logger.warning(
                    "Reduce not converging yet (%s chunks -> %s chunks, "
                    "%s tokens -> %s tokens). Continuing toward a final synthesis pack.",
                    prev_count,
                    len(current_chunks),
                    input_chunk_tokens_total,
                    next_chunks_tokens_total,
                )

        if round_num >= max_rounds and len(current_chunks) > 1:
            logger.error(
                f"Reduce reached max rounds ({max_rounds}) but did not converge to 1 chunk. Aborting."
            )
            raise ReduceConvergenceError(
                f"HierarchicalReduce failed to converge after {max_rounds} rounds.",
                phase=PipelinePhase.REDUCE_FAILED.value,
                reduce_level=round_num,
                number_of_chunks=len(current_chunks),
                reason="max_rounds",
            )

        final_text = (
            "\n\n".join(c.text for c in current_chunks) if current_chunks else ""
        )
        final_source_chunks = (
            sorted(
                list(set.union(*(set(c.source_chunk_indices) for c in current_chunks)))
            )
            if current_chunks
            else []
        )

        # Coverage validation (FASE 6)
        covered_set = set(final_source_chunks)
        expected_set = set(expected_chunk_indices)
        missing = expected_set - covered_set
        unexpected = covered_set - expected_set

        if missing:
            logger.error(
                f"REDUCE COVERAGE ERROR: Expected {len(expected_set)} chunks, "
                f"covered {len(covered_set)}. Missing: {sorted(list(missing))}"
            )
            raise ReduceConvergenceError(
                f"REDUCE COVERAGE ERROR: Expected chunks missing from final output. "
                f"Missing {len(missing)} chunks.",
                phase=PipelinePhase.REDUCE_FAILED.value,
                reason="coverage",
                extra={"missing_chunk_ids": sorted(list(missing))},
            )
        else:
            logger.info(
                "REDUCE chunk-id representation: %s/%s source chunk IDs present in the tree "
                "(this is structural ID coverage, not content coverage).",
                len(covered_set),
                len(expected_set),
            )

        # Release per-chunk text refs now that final_text is assembled.
        for chunk in current_chunks:
            chunk.text = ""
        current_chunks.clear()

        result = ReduceResult(
            final_text, total_tokens_used, final_source_chunks, final_finish_reason
        )
        self.last_reduce_result = result
        return result

    async def _execute_reduce_call(
        self,
        batch_text: str,
        reduce_prompt: str,
        model: ModelType,
        client,
        target_max_tokens: int,
        target_language: LanguageType,
        *,
        reduce_level: int | None = None,
        batch_index: int | None = None,
        split_depth: int | None = None,
        is_final_reduce: bool | None = None,
    ) -> Tuple[str, int, str]:
        import time

        start_time = time.time()
        encoder = get_encoder(model)
        model_cap = get_model_capabilities(model)
        system_tokens = len(encoder.encode(reduce_prompt))
        user_content = resolve_language_prompts(
            target_language
        ).get_reduce_user_content(batch_text)
        user_tokens = len(encoder.encode(user_content))
        max_output_tokens = self._safe_completion_token_limit(
            model,
            system_tokens,
            user_tokens,
            target_max_tokens,
        )
        self._record_prompt_hash("REDUCE", reduce_prompt)

        tokens_needed = system_tokens + user_tokens + target_max_tokens
        await self._check_token_limit(
            tokens_needed=tokens_needed,
            request_type="REDUCE",
            model_name=model.value,
            input_tokens=system_tokens + user_tokens,
            requested_output_tokens=target_max_tokens,
        )

        try:
            provider, scope = self._quota_scope_and_provider(model)

            async def _call():
                self._record_api_request("REDUCE")
                return await self._complete_chat(
                    model,
                    [
                        {"role": "system", "content": reduce_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=max_output_tokens,
                    temperature=self.temperature,
                    extra=completion_extra_kwargs(model, max_tokens=max_output_tokens),
                    timeout=self._completion_timeout_s(model, "REDUCE"),
                    client=client,
                )

            response = await self.provider_executor.execute(
                _call,
                provider=provider,
                model=model.value,
                quota_scope_id=scope,
                phase="REDUCE",
                estimated_input_tokens=system_tokens + user_tokens,
            )
            content = response.choices[0].message.content or ""
            finish_reason = (
                response.choices[0].finish_reason
                if response.choices and response.choices[0].finish_reason
                else "unknown"
            )
            tokens_used = response.usage.total_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Only the provider finish_reason is a truncation signal here.
            # Hitting the requested completion budget with finish_reason=stop is a
            # complete answer (REDUCE sets max_tokens above the instruction target).
            if finish_reason in ["length", "max_tokens"]:
                logger.warning(
                    f"Truncation detected via finish_reason: {finish_reason}"
                )
                finish_reason = "length"

            duration = time.time() - start_time
            logger.info(
                f"METRIC: phase=REDUCE duration={duration:.2f}s "
                f"input_tokens={system_tokens+user_tokens} "
                f"output_tokens={output_tokens} finish_reason={finish_reason}"
            )

            self.history_token_model.history_tokens_per_call.append(
                HistoryTokenCall(
                    type_call=TypeCall.REDUCE,
                    system_prompt_tokens=system_tokens,
                    user_prompt_tokens=user_tokens,
                    response_tokens=output_tokens,
                    request_index=len(self.history_token_model.history_tokens_per_call)
                    + 1,
                    duration_seconds=round(duration, 3),
                    finish_reason=finish_reason,
                    requested_output_tokens=max_output_tokens,
                    budget_utilization=round(
                        output_tokens / max_output_tokens
                        if max_output_tokens > 0
                        else 0.0,
                        4,
                    ),
                    reduce_level=reduce_level,
                    batch_index=batch_index,
                    split_depth=split_depth,
                    is_final_reduce=is_final_reduce,
                )
            )
            self.history_token_model.total_tokens_postprocess_input += (
                system_tokens + user_tokens
            )
            self.history_token_model.total_tokens_postprocess_output += output_tokens

            # Refund unused tokens from original reservation
            unused = tokens_needed - tokens_used
            self.refund_tokens(unused)

            return content.strip(), tokens_used, finish_reason
        except (
            RateLimitError,
            APIConnectionError,
            httpx.HTTPError,
            asyncio.TimeoutError,
        ) as e:
            if "tokens_needed" in locals():
                self.refund_tokens(tokens_needed)
            logger.warning(f"Retryable error in Reduce call: {e}")
            raise
        except Exception as e:
            if "tokens_needed" in locals():
                self.refund_tokens(tokens_needed)
            logger.error(f"Error in Reduce call: {e}")
            raise

    def _paragraph_split(self, text: str) -> list[str]:
        """Divide por lineas en blanco SIN partir dentro de fences ```."""
        paragraphs: list[str] = []
        cur = ""
        in_fence = False
        for line in text.split("\n"):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
            if line.strip() == "" and not in_fence:
                if cur.strip():
                    paragraphs.append(cur.strip())
                    cur = ""
            else:
                cur += line + "\n"
        if cur.strip():
            paragraphs.append(cur.strip())
        return paragraphs

    def _pack_pieces(
        self,
        pieces: list[str],
        max_tokens: int,
        encoder,
        depth: int,
        sep: str,
    ) -> list[str]:
        """Empaqueta piezas en bloques <= max_tokens; recursa en piezas grandes."""
        blocks: list[str] = []
        cur = ""
        for p in pieces:
            if not p.strip():
                continue
            if len(encoder.encode(p)) > max_tokens:
                if cur:
                    blocks.append(cur.strip())
                    cur = ""
                blocks.extend(
                    self._split_markdown_structurally(p, max_tokens, encoder, depth + 1)
                )
                continue
            candidate = (cur + sep + p) if cur else p
            if len(encoder.encode(candidate)) > max_tokens and cur:
                blocks.append(cur.strip())
                cur = p
            else:
                cur = candidate
        if cur.strip():
            blocks.append(cur.strip())
        return blocks

    def _hard_split(self, text: str, max_tokens: int, encoder) -> list[str]:
        """Corte estricto por tokens mediante búsqueda binaria de offsets. Garantiza pérdida cero."""
        if not text:
            return []
        if len(encoder.encode(text)) <= max_tokens:
            return [text]

        pieces = []
        remaining = text
        while remaining:
            if len(encoder.encode(remaining)) <= max_tokens:
                pieces.append(remaining)
                break

            low = 1
            high = len(remaining) - 1
            best_cut = 0

            while low <= high:
                mid = (low + high) // 2
                if len(encoder.encode(remaining[:mid])) <= max_tokens:
                    best_cut = mid
                    low = mid + 1
                else:
                    high = mid - 1

            if best_cut == 0:
                raise ImpossibleRequestError(
                    f"A single character exceeds max_tokens={max_tokens}"
                )

            pieces.append(remaining[:best_cut])
            remaining = remaining[best_cut:]

        return pieces

    def _split_markdown_structurally(
        self, text: str, max_tokens: int, encoder, depth: int = 0
    ) -> list[str]:
        """Divide texto garantizando PÉRDIDA CERO (zero-loss split) respetando la jerarquía original."""
        import re

        if not text:
            return []
        if len(encoder.encode(text)) <= max_tokens:
            return [text]

        if depth >= 4:
            return self._hard_split(text, max_tokens, encoder)

        # Estrategia jerárquica con grupos de captura () para no perder los delimitadores
        if depth == 0:
            pieces = re.split(r"(\n{2,})", text)
        elif depth == 1:
            pieces = re.split(r"(?<=[.!?;:])(\s+)", text)
        elif depth == 2:
            pieces = re.split(r"(\n)", text)
        elif depth == 3:
            pieces = re.split(r"(\s+)", text)
        else:
            return self._hard_split(text, max_tokens, encoder)

        # Si la expresión regular no dividió nada (ej. no hay delimitador)
        if len(pieces) <= 1:
            return self._split_markdown_structurally(
                text, max_tokens, encoder, depth + 1
            )

        blocks = []
        current_block = ""

        for piece in pieces:
            if not piece:
                continue

            # Formamos el candidato uniendo el bloque actual y la nueva pieza
            candidate = current_block + piece

            # Si el candidato excede max_tokens
            if len(encoder.encode(candidate)) > max_tokens:
                # Si ya teníamos algo acumulado, lo guardamos y empezamos de nuevo con 'piece'
                if current_block:
                    if len(encoder.encode(current_block)) > max_tokens:
                        blocks.extend(
                            self._split_markdown_structurally(
                                current_block, max_tokens, encoder, depth + 1
                            )
                        )
                    else:
                        blocks.append(current_block)
                    current_block = piece
                else:
                    # Si no teníamos nada, significa que 'piece' por sí solo es > max_tokens
                    current_block = piece
            else:
                current_block = candidate

        if current_block:
            if len(encoder.encode(current_block)) > max_tokens:
                blocks.extend(
                    self._split_markdown_structurally(
                        current_block, max_tokens, encoder, depth + 1
                    )
                )
            else:
                blocks.append(current_block)

        return blocks

    async def _execute_formatting_call(
        self,
        text_block: str,
        formatting_prompt: str,
        model: ModelType,
        encoder,
        start_time: float,
        target_language: LanguageType,
        requested_output_tokens: Optional[int] = None,
    ) -> Tuple[str, int, str]:
        import time

        client = await self.api_service._initialize_client(
            model, self.history_token_model.user_id
        )
        user_content = resolve_language_prompts(
            target_language
        ).get_format_user_content(text_block)
        system_tokens = len(encoder.encode(formatting_prompt))
        user_tokens = len(encoder.encode(user_content))
        requested = (
            requested_output_tokens
            or get_model_capabilities(model).native_max_output_tokens
        )
        max_output_tokens = self._safe_completion_token_limit(
            model,
            system_tokens,
            user_tokens,
            requested,
        )
        self._record_prompt_hash("FORMAT", formatting_prompt)

        provider, scope = self._quota_scope_and_provider(model)

        async def _call():
            self._record_api_request("FORMAT")
            return await self._complete_chat(
                model,
                [
                    {"role": "system", "content": formatting_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_output_tokens,
                temperature=self.temperature,
                extra=completion_extra_kwargs(model, max_tokens=max_output_tokens),
                timeout=self._completion_timeout_s(model, "FORMAT"),
                client=client,
            )

        response = await self.provider_executor.execute(
            _call,
            provider=provider,
            model=model.value,
            quota_scope_id=scope,
            phase="FORMAT",
            estimated_input_tokens=system_tokens + user_tokens,
        )
        content = response.choices[0].message.content or text_block
        finish_reason = (
            response.choices[0].finish_reason
            if response.choices and response.choices[0].finish_reason
            else "unknown"
        )
        tokens_used = response.usage.total_tokens if response.usage else 0

        output_tokens = response.usage.completion_tokens if response.usage else 0

        duration = time.time() - start_time
        logger.info(
            f"METRIC: phase=FORMATTING duration={duration:.2f}s input_tokens={system_tokens+user_tokens} output_tokens={output_tokens} finish_reason={finish_reason}"
        )

        self.history_token_model.history_tokens_per_call.append(
            HistoryTokenCall(
                type_call=TypeCall.FORMAT,
                system_prompt_tokens=system_tokens,
                user_prompt_tokens=user_tokens,
                response_tokens=output_tokens,
                request_index=len(self.history_token_model.history_tokens_per_call) + 1,
                duration_seconds=round(duration, 3),
                finish_reason=finish_reason,
                requested_output_tokens=max_output_tokens,
                budget_utilization=round(
                    output_tokens / max_output_tokens if max_output_tokens > 0 else 0.0,
                    4,
                ),
            )
        )
        self.history_token_model.total_tokens_postprocess_input += (
            system_tokens + user_tokens
        )
        self.history_token_model.total_tokens_postprocess_output += output_tokens

        return content.strip(), tokens_used, finish_reason

    def _extract_anchors(self, text: str) -> set[str]:
        """Extrae anclas de contenido que DEBEN sobrevivir al formateo.

        Es agnostico al dominio: no conoce keywords ni secciones.
        Anclas:
          - URLs
          - Contenido entre backticks (identificadores, codigo inline)
          - Numeros con decimales o >=3 digitos
          - Identificadores punteados (document.write, javax.script)
          - Acronimos ALL-CAPS de >=3 letras
        """
        import re

        anchors: set[str] = set()

        for m in re.finditer(
            r"(?i)\b(?:los|las|the|estos|estas|these)\s+(\d{1,2})\s+([a-záéíóúñA-ZÁÉÍÓÚÑ]{4,})",
            text,
        ):
            number = m.group(1)
            concept = m.group(2).lower()
            if concept in [
                "significados",
                "categorías",
                "principios",
                "ideales",
                "tipos",
                "elementos",
                "conceptos",
                "pasos",
                "fases",
                "etapas",
                "meanings",
                "categories",
                "principles",
                "ideals",
                "types",
                "elements",
                "concepts",
                "steps",
                "phases",
                "stages",
            ]:
                anchors.add(f"{number} {concept}")

        anchors.update(re.findall(r"https?://[^\s)\]>\"']+", text))

        for m in re.findall(r"`([^`\n]{2,})`", text):
            anchors.add(m.strip())

        for m in re.findall(r"\b\d+(?:[.,]\d+)?\b", text):
            if "." in m or "," in m or len(m) >= 3:
                anchors.add(m)

        anchors.update(
            re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b", text)
        )

        anchors.update(re.findall(r"\b[A-Z]{3,}\b", text))

        return {a for a in anchors if len(a) >= 3}

    def _verify_block(
        self, source: str, output: str, encoder
    ) -> Tuple[bool, list[str]]:
        """Verificacion determinista, sin LLM, agnostica al contenido.

        Devuelve (ok, razones). Razones posibles:
          marker=..., truncated_tail, shrunk(x<y), over_expanded(x>y),
          missing_anchors(n/m: [...]), unbalanced_fence, empty
        """
        reasons: list[str] = []

        if not output.strip():
            return False, ["empty"]

        if self._looks_incomplete_tail(output):
            reasons.append("incomplete_tail")

        lower_out = output.lower()
        for marker in (
            "[texto truncado]",
            "[truncated]",
            "[...]",
            "texto truncado",
        ):
            if marker in lower_out:
                reasons.append(f"marker={marker!r}")

        src_clean = source.rstrip()
        src_ends_punct = bool(
            src_clean
            and (
                src_clean[-1] in ".!?:\"'`)]}>|*_”’"
                or src_clean.endswith("```")
                or src_clean.endswith("**")
                or src_clean.endswith("---")
            )
        )

        t = output.rstrip()
        if t and t[-1] not in ".!?:\"'`)]}>|*_”’":
            if not (t.endswith("```") or t.endswith("**") or t.endswith("---")):
                if src_ends_punct:
                    reasons.append("truncated_tail")

        src_t = len(encoder.encode(source))
        out_t = len(encoder.encode(output))
        if src_t >= 50:
            if out_t > src_t * 10:
                reasons.append(f"over_expanded({out_t}>{src_t * 10})")

        anchors = self._extract_anchors(source)
        if anchors:
            out_lower = output.lower()
            missing = [
                a for a in anchors if a not in output and a.lower() not in out_lower
            ]
            if missing:
                reasons.append(
                    f"missing_anchors({len(missing)}/{len(anchors)}: {missing[:2]})"
                )

        if source.count("```") % 2 == 0 and output.count("```") % 2 == 1:
            reasons.append("unbalanced_fence")

        return (not reasons, reasons)

    def _looks_incomplete_tail(self, output: str) -> bool:
        stripped = output.rstrip()
        if not stripped:
            return True

        last_line = next(
            (line.strip() for line in reversed(stripped.splitlines()) if line.strip()),
            "",
        )
        if not last_line:
            return True

        complete_endings = (
            ".",
            "!",
            "?",
            ":",
            '"',
            "'",
            "`",
            ")",
            "]",
            "}",
            ">",
            "|",
            "*",
            "”",
            "’",
        )
        if stripped.endswith(complete_endings) or stripped.endswith(
            ("```", "**", "---")
        ):
            return False

        if last_line.startswith(("#", "-", "*", ">")) or re.match(
            r"^(\d+[\.\)]\s|\*\*\d+\)|\*\*[A-Za-zÁÉÍÓÚÑáéíóúñ])", last_line
        ):
            return False

        if last_line.startswith("|") or re.match(r"^\|.*\|$", last_line):
            return False

        if len(stripped.split()) < 40:
            return False

        if stripped.endswith("-") or stripped.endswith(","):
            return True

        if len(last_line.split()) >= 12 and last_line[-1].isalnum():
            return True

        return False

    def _trim_to_last_complete_unit(self, text: str) -> Optional[str]:
        stripped = text.rstrip()
        if not stripped:
            return None
        terminators = ".!?"
        for i in range(len(stripped) - 1, -1, -1):
            if stripped[i] not in terminators:
                continue
            end = i + 1
            while end < len(stripped) and stripped[end] in "\"'”’)]]":
                end += 1
            candidate = stripped[:end].rstrip()
            if candidate:
                return candidate
        return None

    def _usable_map_extract(self, text: str) -> Optional[str]:
        """Keep a MAP extract that Flash filled to max_tokens if it is usable.

        finish_reason=length is not fatal when the model wrote a complete
        extract (or one that trims to a complete sentence). Empty / mid-cut
        leftovers with no salvageable sentence still fail closed.
        """
        stripped = (text or "").strip()
        if not stripped:
            return None
        cut_mid_token = stripped[-1].isalnum()
        if self._looks_incomplete_tail(stripped) or cut_mid_token:
            candidate = self._trim_to_last_complete_unit(stripped)
            if not candidate:
                return None
        else:
            candidate = stripped
        if len(candidate.split()) < MIN_USABLE_MAP_WORDS:
            return None
        return candidate

    async def run_formatting_phase(
        self,
        reduced_summary: str,
        formatting_prompt: str,
        model: ModelType,
        target_language: LanguageType,
    ) -> Tuple[str, int]:
        import time

        start_time = time.time()
        encoder = get_encoder(model)
        logger.info("Starting Formatting phase")
        lang_prompts = resolve_language_prompts(target_language)

        formatting_prompt = (
            formatting_prompt + "\n" + lang_prompts.get_format_strict_rules()
        )

        input_tokens = len(encoder.encode(reduced_summary))
        prompt_tokens = len(encoder.encode(formatting_prompt))
        model_cap = get_model_capabilities(model)
        max_output = model_cap.native_max_output_tokens

        # Lower expansion factor: formatting should not add much length.
        # We aggressively prefer a single-pass to avoid structural fragmentation.
        EXPANSION_FACTOR = 1.05
        estimated_output = (
            int(input_tokens * EXPANSION_FACTOR) + model_cap.output_padding_tokens
        )

        # Enforce context bounds on the formatting phase directly
        context_available = (
            model_cap.context_window
            - prompt_tokens
            - input_tokens
            - model_cap.format_safety_margin
        )
        if context_available <= 0:
            raise ContextOverflowError(
                f"Input exceeds useful context window before FORMATTING. available={context_available}"
            )

        safe_single_output = self._safe_completion_token_limit(
            model, prompt_tokens, input_tokens, estimated_output
        )

        tokens_needed = prompt_tokens + input_tokens + safe_single_output

        await self._check_token_limit(
            tokens_needed=tokens_needed,
            request_type="FORMAT_SINGLE",
            model_name=model.value,
            input_tokens=prompt_tokens + input_tokens,
            requested_output_tokens=estimated_output,
        )

        fits_single = (estimated_output <= safe_single_output) and (
            estimated_output <= context_available
        )
        logger.info(
            f"Formatting budget: input_tokens={input_tokens} "
            f"estimated_output={estimated_output} max_output={max_output} "
            f"safe_single_output={safe_single_output} context_available={context_available} "
            f"fits_single={fits_single}"
        )

        if fits_single:
            try:
                (
                    content,
                    tokens_used,
                    finish_reason,
                ) = await self._execute_formatting_call(
                    reduced_summary,
                    formatting_prompt,
                    model,
                    encoder,
                    start_time,
                    target_language,
                    requested_output_tokens=safe_single_output,
                )

                unused = tokens_needed - tokens_used
                self.refund_tokens(unused)

                dump_audit("04_FORMAT_SINGLE", "IN", reduced_summary)
                dump_audit("04_FORMAT_SINGLE", "OUT", content)

                ok, reasons = self._verify_block(reduced_summary, content, encoder)
                if ok and finish_reason != "length":
                    logger.info("Single-pass format succeeded and verified.")
                    return content, tokens_used
                logger.warning(
                    f"Single-pass format failed verification: {reasons}. Falling back to chunked formatting."
                )
            except Exception as e:
                self.refund_tokens(tokens_needed)
                logger.error(
                    f"Single formatting call failed: {e}. Falling back to chunking."
                )

        format_prompt_tokens = len(encoder.encode(formatting_prompt))
        context_limited_input = (
            model_cap.context_window
            - format_prompt_tokens
            - model_cap.native_max_output_tokens
            - model_cap.format_safety_margin
        )
        output_limited_input = int(
            (model_cap.native_max_output_tokens - model_cap.output_padding_tokens)
            / EXPANSION_FACTOR
        )
        chunk_limit = max(
            model_cap.reduce_min_batch_tokens,
            min(
                max_output,
                context_limited_input,
                output_limited_input,
            ),
        )
        blocks = self._split_markdown_structurally(
            reduced_summary, chunk_limit, encoder
        )

        if not blocks:
            logger.error("Splitter produced zero blocks; returning input as-is.")
            return reduced_summary, 0

        total_blocks = len(blocks)
        logger.info(
            f"Formatting split into {total_blocks} blocks (chunk_limit={chunk_limit}). "
            f"Block sizes (tokens): {[len(encoder.encode(b)) for b in blocks]}"
        )

        async def format_block(
            block: str, index: int, depth: int = 0, parent_prompt: str = None
        ) -> Tuple[int, str, int]:
            block_in_tokens = len(encoder.encode(block))

            if block_in_tokens <= 40:
                return index, block, 0

            need = block_in_tokens + model_cap.format_safety_margin
            await self._check_token_limit(
                tokens_needed=need,
                request_type="FORMAT_CHUNKED",
                model_name=model.value,
                input_tokens=block_in_tokens,
                requested_output_tokens=model_cap.format_safety_margin,
            )

            # Build a positional context hint to prevent structural duplication
            # when the document must be formatted in multiple chunks.
            # Only applied at depth=0 (top-level blocks). Sub-blocks inherit their parent's prompt.
            if parent_prompt is not None:
                block_prompt = parent_prompt
            elif total_blocks > 1:
                position_hint = lang_prompts.get_format_position_hint(
                    index, total_blocks
                )
                block_prompt = formatting_prompt + position_hint
            else:
                block_prompt = formatting_prompt

            while True:
                try:
                    b_content, b_tokens, b_finish = await self._execute_formatting_call(
                        block,
                        block_prompt,
                        model,
                        encoder,
                        time.time(),
                        target_language,
                        requested_output_tokens=int(block_in_tokens * EXPANSION_FACTOR)
                        + model_cap.output_padding_tokens,
                    )
                    ok, reasons = self._verify_block(block, b_content, encoder)
                    if ok and b_finish != "length":
                        self.refund_tokens(need - b_tokens)
                        return index, b_content, b_tokens

                    if b_finish == "length":
                        reasons.append("finish_reason=length")
                    logger.warning(
                        f"Block {index} (depth={depth}, in={block_in_tokens}t) "
                        f"rejected: {reasons}."
                    )
                except (
                    RateLimitError,
                    APIConnectionError,
                    httpx.HTTPError,
                    asyncio.TimeoutError,
                ) as e:
                    # RetryCoordinator in ProviderCallExecutor already retried.
                    logger.error(
                        f"Block {index} failed after executor retries: {e}. "
                        f"Using RAW block."
                    )
                    self.refund_tokens(need)
                    return index, block, 0
                except Exception as e:
                    logger.error(
                        f"Block {index} unexpected error: {e}. Using RAW block."
                    )
                    self.refund_tokens(need)
                    return index, block, 0

                if depth >= 6:
                    logger.error(
                        f"Block {index} reached max depth ({depth}). Using RAW block."
                    )
                    return index, block, 0

                sub_limit = max(model_cap.min_chunk_tokens, block_in_tokens // 2)
                sub_blocks = self._split_markdown_structurally(
                    block, sub_limit, encoder, depth + 1
                )
                if len(sub_blocks) <= 1:
                    logger.error(
                        f"Block {index} cannot be split further. Using RAW block."
                    )
                    return index, block, 0

                sub_results = await gather_or_cancel(
                    *[
                        format_block(sb, i, depth + 1, block_prompt)
                        for i, sb in enumerate(sub_blocks)
                    ]
                )
                sub_results.sort(key=lambda x: x[0])
                merged = "\n\n".join(r[1] for r in sub_results)
                merged_tokens = sum(r[2] for r in sub_results)
                return index, merged, merged_tokens

        tasks = [
            asyncio.create_task(format_block(b, i, 0)) for i, b in enumerate(blocks)
        ]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            await cancel_pending_tasks(tasks)
            raise

        formatted: list[str] = [""] * len(blocks)
        total_tokens = 0
        raw_fallbacks = 0
        for i, res in enumerate(results):
            if isinstance(res, asyncio.CancelledError):
                await cancel_pending_tasks(tasks)
                raise res
            if isinstance(res, BaseException):
                logger.error(f"Block {i} failed definitively: {res}. Using RAW block.")
                formatted[i] = blocks[i]
                raw_fallbacks += 1
                continue
            idx, content, toks = res
            formatted[idx] = content
            total_tokens += toks
            if content == blocks[idx]:
                raw_fallbacks += 1

        assembled = "\n\n".join(b for b in formatted if b)

        ok, reasons = self._verify_block(reduced_summary, assembled, encoder)
        if not ok:
            logger.warning(
                f"Assembled output failed global verification: {reasons}. "
                f"Returning reduced_summary (unformatted) as fallback to avoid content loss."
            )
            return reduced_summary, total_tokens

        logger.info(
            f"Formatting completed: blocks={len(blocks)} raw_fallbacks={raw_fallbacks} "
            f"input_tokens={input_tokens} "
            f"output_tokens={len(encoder.encode(assembled))} "
            f"total_used_tokens={total_tokens} "
            f"duration={time.time() - start_time:.2f}s"
        )
        return assembled, total_tokens

    def _validate_global_structure(self, text: str) -> Tuple[bool, list[str]]:
        import re

        errors = []

        intro_matches = len(
            re.findall(r"(?i)^#+\s*(?:1\.\s*)?introducci[oó]n", text, re.MULTILINE)
        )
        if intro_matches > 1:
            errors.append(f"Múltiples introducciones detectadas ({intro_matches})")

        conclusion_matches = len(
            re.findall(r"(?i)^#+\s*(?:\d+\.\s*)?conclusi[oó]n", text, re.MULTILINE)
        )
        if conclusion_matches > 1:
            errors.append(f"Múltiples conclusiones detectadas ({conclusion_matches})")

        number_ones = len(re.findall(r"^##\s*1\.\s", text, re.MULTILINE))
        if number_ones > 1:
            errors.append(
                f"Reinicio de numeración anómalo detectado (## 1. aparece {number_ones} veces)"
            )

        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        if len(paragraphs) > 5:
            duplicates = 0
            for i, p1 in enumerate(paragraphs):
                for p2 in paragraphs[i + 1 :]:
                    if p1 == p2 or (len(p1) > 100 and p1[:100] == p2[:100]):
                        duplicates += 1
            if duplicates > 2:
                errors.append("Duplicación significativa de párrafos detectada")

        return len(errors) == 0, errors

    @staticmethod
    def _prose_language_mismatch(
        text: str, target_language: LanguageType | str
    ) -> bool:
        """Cheap function-word check so REDUCE can retry once on a wrong-language draft."""
        if not text or not text.strip():
            return False
        key = (
            target_language.name
            if isinstance(target_language, LanguageType)
            else str(target_language).strip().upper()
        )
        sample = " " + re.sub(r"```[\s\S]*?```", " ", text).lower() + " "
        spanish_hits = sum(
            sample.count(marker)
            for marker in (
                " el ",
                " la ",
                " los ",
                " las ",
                " de ",
                " que ",
                " en ",
                " es ",
                " un ",
                " una ",
                " del ",
                " se ",
                " por ",
                " con ",
            )
        )
        english_hits = sum(
            sample.count(marker)
            for marker in (
                " the ",
                " and ",
                " of ",
                " to ",
                " in ",
                " is ",
                " for ",
                " that ",
                " with ",
                " this ",
                " from ",
                " are ",
            )
        )
        if key in {"SPANISH", "ES"}:
            return english_hits >= 8 and english_hits > spanish_hits * 1.5
        if key in {"ENGLISH", "EN"}:
            return spanish_hits >= 8 and spanish_hits > english_hits * 1.5
        return False

    async def _enforce_artifact_quality_gate(
        self,
        artifacts: SummaryArtifactManager,
        *,
        encoder,
        file_tokens: int,
        source_words: int,
        map_words: int,
        map_tokens: int,
        map_salvage_text: str,
        decision,
        summary_level: SummaryLevel,
    ) -> None:
        """Inspect the real .partial body before promoting it to summary.md."""
        disk_text = await artifacts.read_partial_text()
        encode = lambda text: len(encoder.encode(text or ""))
        toc_stats = last_toc_strip_stats()
        extraction = getattr(self.directory_manager, "last_extraction_report", None)
        signals = QualitySignals(
            source_tokens=_safe_int(file_tokens),
            source_words=_safe_int(source_words),
            map_tokens=_safe_int(map_tokens),
            map_words=_safe_int(map_words),
            final_tokens=encode(disk_text),
            final_words=count_words(disk_text),
            output_min_tokens=_safe_int(getattr(decision, "output_min_tokens", 0)),
            output_target_tokens=_safe_int(
                getattr(decision, "output_target_tokens", 0)
            ),
            output_hard_limit=_safe_int(getattr(decision, "output_hard_limit", 0)),
            summary_level=summary_level,
            route=decision.route
            if isinstance(getattr(decision, "route", None), str)
            else "",
            pages_dropped=_safe_int(getattr(extraction, "pages_dropped", 0)),
            pages_total=_safe_int(getattr(extraction, "pages_total", 0)),
            toc_drop_ratio=float(toc_stats.get("drop_ratio") or 0.0),
        )
        candidates: list[tuple[str, str]] = [("proposed", disk_text)]
        if (
            map_salvage_text.strip()
            and map_salvage_text.strip() != (disk_text or "").strip()
        ):
            candidates.append(("map_extracts", map_salvage_text))
        chosen, report = choose_deliverable_text(candidates, signals, encode=encode)
        self.history_token_model.quality_verdict = report.verdict.value
        self.history_token_model.salvage_source = report.salvage_source
        self.history_token_model.map_output_tokens = map_tokens
        self.history_token_model.map_output_words = map_words
        if not report.deliverable:
            logger.error(
                "Artifact quality gate rejected summary.md candidate verdict=%s "
                "reasons=%s chatbot_score=%.2f map_ratio=%.3f source_ratio=%.3f "
                "min_token_ratio=%.3f words=%s tokens=%s",
                report.verdict.value,
                report.reasons,
                report.chatbot_score,
                report.map_ratio,
                report.source_ratio,
                report.min_token_ratio,
                count_words(chosen),
                encode(chosen),
            )
            raise ArtifactQualityError(
                "Final artifact failed the summary quality contract: "
                + ", ".join(report.reasons or ["invalid"]),
                phase=PipelinePhase.QUALITY_FAILED.value,
                reasons=list(report.reasons),
                quality_verdict=report.verdict.value,
            )
        if chosen.strip() != (disk_text or "").strip():
            logger.warning(
                "Artifact quality gate salvaged from %s (proposed was not deliverable)",
                report.salvage_source or "map_extracts",
            )
            await artifacts.replace_partial(chosen)
        artifact_tokens = encode(chosen)
        artifact_words = count_words(chosen)
        self.history_token_model.final_artifact_tokens = artifact_tokens
        self.history_token_model.final_artifact_words = artifact_words
        self.history_token_model.reduce_output_tokens = (
            self.history_token_model.phase_token_totals.get("REDUCE", {}).get(
                "output_tokens", 0
            )
        )
        self.history_token_model.format_output_tokens = (
            self.history_token_model.phase_token_totals.get("FORMAT", {}).get(
                "output_tokens", 0
            )
        )
        compression_ratio = artifact_tokens / max(file_tokens, 1)
        logger.info(
            "[FINAL] artifact_tokens=%s artifact_words=%s source_tokens=%s "
            "source_words=%s map_tokens=%s map_words=%s map_ratio=%.3f "
            "source_ratio=%.3f verdict=%s salvage=%s compression_ratio=%.2f",
            artifact_tokens,
            artifact_words,
            file_tokens,
            source_words,
            map_tokens,
            map_words,
            report.map_ratio,
            report.source_ratio,
            report.verdict.value,
            report.salvage_source or "none",
            compression_ratio,
        )
        if report.warnings:
            logger.warning("Artifact quality warnings: %s", report.warnings)
        if not report.salvage_source:
            last = getattr(self, "last_reduce_result", None)
            final_finish = (
                getattr(last, "finish_reason", "stop") if last is not None else "stop"
            )
            if final_finish == "length":
                raise ReduceConvergenceError(
                    "Truncation marker detected in generated summary (finish_reason=length).",
                    phase=PipelinePhase.REDUCE_FAILED.value,
                    finish_reason="length",
                    reason="final_finish_length",
                )

    @staticmethod
    def _looks_like_assistant_chat(text: str) -> bool:
        """Catch chatbot menus that replace the summary after a context-shift."""
        return quality_looks_like_assistant_chat(text)

    def _sanitize_structure(self, text: str) -> str:
        import re

        lines = text.split("\n")
        sanitized_lines = []

        intro_seen = False
        conclusion_seen = False

        # To fix numbering like "## 1.", "## 1."
        # We will strip the numbers from level 2 headings if they are duplicated,
        # or we could just remove the numbering and let it be "## Introducción"
        # However, a simpler programmatic fix is to remove all repeated "## 1. " entirely
        # or renumber them sequentially.

        h2_counter = 1

        for line in lines:
            # Handle Intros
            if re.match(r"(?i)^#+\s*(?:1\.\s*)?introducci[oó]n", line):
                if intro_seen:
                    continue  # Skip duplicate intros
                intro_seen = True

            # Handle Conclusions
            if re.match(r"(?i)^#+\s*(?:\d+\.\s*)?conclusi[oó]n", line):
                # We can't easily drop all but the last conclusion in a single pass without knowing it's the last,
                # but if we see multiple conclusions, we can rename the earlier ones or skip them.
                # A safer approach for conclusions is to just keep the first one we see,
                # or rename subsequent ones to just "## Puntos Finales".
                if conclusion_seen:
                    line = line.replace("Conclusión", "Puntos Finales").replace(
                        "conclusión", "puntos finales"
                    )
                conclusion_seen = True

            # Handle Numbering Restarts (e.g., ## 1. appearing multiple times)
            match_num = re.match(r"^(##\s*)(\d+)(\.\s*)(.*)", line)
            if match_num:
                prefix = match_num.group(1)
                suffix = match_num.group(4)
                # Force sequential numbering for level 2 headings that are numbered
                line = f"{prefix}{h2_counter}. {suffix}"
                h2_counter += 1
            elif re.match(r"^##\s+.*", line):
                # Unnumbered h2, increment counter anyway to avoid collision if they mix numbered and unnumbered
                h2_counter += 1

            sanitized_lines.append(line)

        return self._drop_duplicate_heading_sections("\n".join(sanitized_lines))

    @staticmethod
    def _drop_duplicate_heading_sections(text: str) -> str:
        """Keep the first section for each heading; drop later clones of the same title."""
        import re

        lines = text.split("\n")
        heading = re.compile(r"^(#{1,6})\s+(.*)$")
        sections: list[list[str]] = [[]]
        for line in lines:
            if heading.match(line) and sections[-1]:
                sections.append([line])
            else:
                sections[-1].append(line)
        seen: set[str] = set()
        kept: list[str] = []
        for section in sections:
            first = next((item for item in section if item.strip()), "")
            match = heading.match(first)
            if match:
                key = re.sub(r"\s+", " ", match.group(2)).strip().lower()
                if key in seen:
                    continue
                seen.add(key)
            kept.extend(section)
        return "\n".join(kept)

    def _unexpected_failure_phase(self, current: PipelinePhase) -> PipelinePhase:
        if current in (PipelinePhase.QUEUED, PipelinePhase.INITIALIZING):
            return PipelinePhase.INITIALIZING
        if current == PipelinePhase.DIRECT_RUNNING:
            return PipelinePhase.DIRECT_FAILED
        if current == PipelinePhase.MAP_RUNNING:
            return PipelinePhase.MAP_FAILED
        if current in (PipelinePhase.REDUCE_RUNNING, PipelinePhase.MAP_COMPLETED):
            return PipelinePhase.REDUCE_FAILED
        if current in (
            PipelinePhase.FORMAT_RUNNING,
            PipelinePhase.REDUCE_COMPLETED,
            PipelinePhase.DIRECT_COMPLETED,
        ):
            return PipelinePhase.FORMAT_FAILED
        if current == PipelinePhase.FINALIZING:
            return PipelinePhase.INVARIANT_FAILED
        if current == PipelinePhase.QUALITY_FAILED:
            return PipelinePhase.QUALITY_FAILED
        if current == PipelinePhase.CANCELLED:
            return PipelinePhase.CANCELLED
        if current == PipelinePhase.INVARIANT_FAILED:
            return PipelinePhase.INVARIANT_FAILED
        return PipelinePhase.INVARIANT_FAILED

    async def _document_result(
        self,
        *,
        success: bool,
        state: DocumentPipelineState,
        artifacts: Optional[SummaryArtifactManager],
        message: str,
        summary: str = "",
    ) -> SummaryResponse:
        keep_partials = self._keep_partials()
        partial_available = False
        if keep_partials and artifacts is not None:
            try:
                partial_available = await artifacts.has_recoverable_partial()
            except Exception as exc:
                logger.error(
                    "Failed to inspect partial artifact: %s", exc, exc_info=True
                )
        state.diagnostics.partial_available = partial_available
        if success:
            state.diagnostics.phase = PipelinePhase.SUCCESS.value
        self.history_token_model.pipeline_status = job_status_for(success=success).value
        self.history_token_model.pipeline_phase = job_phase_for(
            state.phase, success=success
        ).value
        await self._persist_token_log()
        status = job_status_for(success=success).value
        job_phase = job_phase_for(state.phase, success=success).value
        return SummaryResponse(
            success=success,
            summary=summary if success else "",
            message=message,
            error_message=""
            if success
            else (state.diagnostics.error_message or message),
            phase=state.diagnostics.phase or state.phase.value,
            error_type=state.diagnostics.error_type,
            partial_available=partial_available,
            diagnostics=state.diagnostics.to_dict(),
            status=status,
            job_phase=job_phase,
        )

    def _validate_map_contract(self, map_results: List[Any], chunks: List[str]) -> None:
        if len(map_results) != len(chunks):
            raise InvariantViolationError(
                f"MAP result count mismatch: got {len(map_results)} results for {len(chunks)} chunks",
                phase=PipelinePhase.INVARIANT_FAILED.value,
            )
        for i, result in enumerate(map_results):
            if not isinstance(result, MapChunkResult):
                raise InvariantViolationError(
                    f"MAP result[{i}] is {type(result).__name__}, expected MapChunkResult",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                    input_type=type(result).__name__,
                )
            if result.chunk_id != i:
                raise InvariantViolationError(
                    f"MAP result[{i}] has chunk_id={result.chunk_id}",
                    phase=PipelinePhase.INVARIANT_FAILED.value,
                )
            result.validate_contract()

    async def _process_single_document(
        self,
        prompt: str,
        file_config: FileConfig,
        model: ModelType,
        prompt_config: PromptConfig,
        folder_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SummaryResponse:
        effective_folder_id = folder_id or self.history_token_model.folder_id
        effective_user_id = user_id or self.history_token_model.user_id

        if not effective_folder_id or not effective_user_id:
            for path_str in [file_config.summary_path, file_config.document_path]:
                if path_str:
                    parts = Path(path_str).parts
                    for i, part in enumerate(parts):
                        if part == "data" and len(parts) > i + 2:
                            if not effective_user_id:
                                effective_user_id = parts[i + 1]
                            if not effective_folder_id:
                                effective_folder_id = parts[i + 2]
                            break

        self.history_token_model.folder_id = effective_folder_id
        self.history_token_model.user_id = effective_user_id
        set_audit_run_id(effective_folder_id)

        # target_language: user-configured output + instruction language.
        # document_language lives only in history_token_model.language_input
        # (detected from source content) and must never select prompt modules.
        target_language = self._resolve_target_language(prompt_config)
        category = None
        style = None
        try:
            category = CategoryType(prompt_config.category)
            style = StyleType(prompt_config.style)
        except Exception:
            pass

        encoder = get_encoder(model)
        logger.info(f"Processing document: {file_config.document_path}")
        if self._pipeline_t0 is None:
            self._pipeline_t0 = time.time()
        state = DocumentPipelineState()
        state.set_phase(PipelinePhase.QUEUED)
        artifacts: Optional[SummaryArtifactManager] = None
        try:
            try:
                state.set_phase(PipelinePhase.INITIALIZING)
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
                    state.fail(PipelinePhase.INITIALIZING, e)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=None,
                        message=f"Path validation failed: {str(e)}",
                    )

                file_extension = (
                    file_config.document_path.split(".")[-1].lower()
                    if file_config.document_path
                    else ""
                )
                logger.debug(f"Detected file extension: {file_extension}")

                full_text = ""
                is_transcription_source = file_extension == "txt"
                if file_extension == "pdf":
                    logger.debug(f"Reading PDF: {file_config.document_path}")
                    try:
                        pdf = await self.directory_manager.read_pdf(
                            file_config.document_path, self.history_token_model
                        )
                        fragments = list(pdf)
                        full_text = "\n".join(fragments)
                        extraction = self.directory_manager.last_extraction_report
                        self.history_token_model.extraction_kind = "generation"
                        self.history_token_model.pages_total = extraction.pages_total
                        self.history_token_model.pages_extracted = (
                            extraction.pages_extracted
                        )
                        self.history_token_model.pages_empty = extraction.pages_empty
                        self.history_token_model.pages_ocr = extraction.pages_ocr
                        self.history_token_model.pages_ocr_failed = (
                            extraction.pages_ocr_failed
                        )
                        self.history_token_model.pages_dropped = (
                            extraction.pages_dropped
                        )
                        logger.info(
                            "Generation extraction vs estimation: generation uses OCR on empty pages; "
                            "estimation counts pages_total/pages_with_text without OCR. "
                            "pages_total=%s pages_extracted=%s pages_empty=%s "
                            "pages_ocr=%s pages_ocr_failed=%s pages_dropped=%s",
                            extraction.pages_total,
                            extraction.pages_extracted,
                            extraction.pages_empty,
                            extraction.pages_ocr,
                            extraction.pages_ocr_failed,
                            extraction.pages_dropped,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to read PDF {file_config.document_path}: {str(e)}",
                            exc_info=True,
                        )
                        state.fail(PipelinePhase.INITIALIZING, e)
                        return await self._document_result(
                            success=False,
                            state=state,
                            artifacts=None,
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
                        state.fail(PipelinePhase.INITIALIZING, e)
                        return await self._document_result(
                            success=False,
                            state=state,
                            artifacts=None,
                            message=f"Failed to read DOCX: {str(e)}",
                        )
                elif file_extension == "txt":
                    logger.debug(
                        f"Reading transcription text: {file_config.document_path}"
                    )
                    try:
                        full_text = await self.directory_manager.read_transcription(
                            file_config.document_path
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to read transcription {file_config.document_path}: {str(e)}",
                            exc_info=True,
                        )
                        state.fail(PipelinePhase.INITIALIZING, e)
                        return await self._document_result(
                            success=False,
                            state=state,
                            artifacts=None,
                            message=f"Failed to read transcription: {str(e)}",
                        )
                else:
                    logger.error(f"Unsupported file type: {file_extension}")
                    state.fail(
                        PipelinePhase.INITIALIZING,
                        ValueError(f"Unsupported file type: {file_extension}"),
                    )
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=None,
                        message=f"Unsupported file type: {file_extension}",
                    )

                dump_audit("00_INPUT", "full_document", full_text)

                logger.debug(f"Text extracted, length: {len(full_text)} characters")

                try:
                    logger.debug("Detecting document language")
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
                                f"Failed to set target_language input: {str(e)}",
                                exc_info=True,
                            )
                            self.history_token_model.language_input = LanguageType(
                                "en"
                            ).name.lower()

                        logger.info(f"Detected document language: {detected_language}")
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

                before_toc_strip = len(full_text)
                stripped_doc = ""
                if is_transcription_source:
                    toc_stats = {
                        "applied": False,
                        "reason": "transcription_source",
                        "chars_before": before_toc_strip,
                        "chars_after": before_toc_strip,
                        "drop_ratio": 0.0,
                    }
                else:
                    stripped_doc = strip_document_front_matter_toc(full_text)
                    toc_stats = last_toc_strip_stats()
                self.history_token_model.toc_chars_before = toc_stats["chars_before"]
                self.history_token_model.toc_chars_after = toc_stats["chars_after"]
                self.history_token_model.toc_drop_ratio = toc_stats["drop_ratio"]
                logger.info(
                    "TOC strip applied=%s reason=%s chars %s → %s drop_ratio=%.3f",
                    toc_stats["applied"],
                    toc_stats["reason"],
                    toc_stats["chars_before"],
                    toc_stats["chars_after"],
                    toc_stats["drop_ratio"],
                )
                if toc_stats["applied"] and stripped_doc:
                    full_text = stripped_doc
                    logger.info(
                        "Stripped front-matter TOC before chunking (%s → %s chars)",
                        before_toc_strip,
                        len(full_text),
                    )
                source_word_count = count_words(full_text)

                file_tokens = len(encoder.encode(full_text))
                self.history_token_model.num_tokens_file = file_tokens
                self.history_token_model.num_chars_file = len(full_text)
                logger.debug(
                    f"Set num_tokens_file: {file_tokens}, num_chars: {len(full_text)}"
                )

                model_cap = get_model_capabilities(model)
                overlap = self._chunk_overlap_ratio(model)
                chunks = await self.chunk_text(
                    full_text, model_cap.max_tokens_per_chunk, overlap, model
                )
                self.history_token_model.number_of_chunks = len(chunks)
                self._reset_provider_job_controls(model, n_chunks=len(chunks))
                logger.info(
                    f"Document split into {len(chunks)} chunks: "
                    f"chunk_size={model_cap.max_tokens_per_chunk}, "
                    f"overlap={overlap}"
                )

                artifacts = SummaryArtifactManager(file_config.summary_path)
                document_outline = extract_document_outline(full_text)
                if document_outline:
                    logger.info(
                        "Document outline extracted: %s headings (deterministic, no LLM)",
                        len(document_outline),
                    )
                else:
                    logger.info(
                        "No reliable document outline; REDUCE will not receive a coverage checklist"
                    )

                async def append_map_fragment(fragment: str) -> None:
                    """MAP progress: append one chunk summary; do not rejoin the full MAP output."""
                    try:
                        await artifacts.append_partial(fragment, separator="\n\n")
                    except Exception as exc:
                        logger.error(
                            "Failed to append MAP fragment to %s: %s",
                            artifacts.partial_path,
                            exc,
                            exc_info=True,
                        )

                final_summary: str = ""
                summary_on_disk = False
                try:
                    summary_level = SummaryLevel(self.history_token_model.summary_level)
                    policy = AdaptiveSaliencePolicy()
                    decision = policy.budget(
                        model, summary_level, file_tokens, target_language
                    )
                    self.history_token_model.route = decision.route
                    self.history_token_model.output_min_tokens = (
                        decision.output_min_tokens
                    )
                    self.history_token_model.output_target_tokens = (
                        decision.output_target_tokens
                    )
                    self.history_token_model.output_max_tokens = (
                        decision.output_max_tokens
                    )
                    self.history_token_model.output_hard_limit = (
                        decision.output_hard_limit
                    )
                    total_tokens_used = 0
                    map_success_word_count = 0
                    map_salvage_text = ""
                    map_salvage_tokens = 0

                    if decision.route == "direct":
                        # True single-pass: one LLM call on the full document.
                        state.set_phase(PipelinePhase.DIRECT_RUNNING)
                        logger.info(
                            "DIRECT route: single-pass summary for %s tokens "
                            "(skip MAP/REDUCE/FORMAT)",
                            file_tokens,
                        )
                        direct_prompt = await self.advanced_prompt_generator.get_direct_summary_prompt(
                            target_language, category, style, summary_level
                        )
                        (
                            final_summary,
                            total_tokens_used,
                        ) = await self.run_direct_summary(
                            full_text,
                            direct_prompt,
                            model,
                            target_language,
                            outline=document_outline,
                            output_target_tokens=decision.output_target_tokens,
                        )
                        # Persist immediately, then drop the in-memory copy before commit.
                        await artifacts.replace_partial(final_summary)
                        map_success_word_count = len(final_summary.split())
                        map_salvage_text = ""
                        map_salvage_tokens = 0
                        final_summary = ""
                        summary_on_disk = True
                        # Original document no longer needed after DIRECT write.
                        full_text = ""
                        state.set_phase(PipelinePhase.DIRECT_COMPLETED)
                    else:
                        # Hierarchical: free the full source once chunks exist.
                        full_text = ""
                        state.set_phase(PipelinePhase.MAP_RUNNING)
                        logger.info(
                            "HIERARCHICAL route: MAP→REDUCE for %s tokens",
                            file_tokens,
                        )
                        await artifacts.reset_partial()
                        map_prompt = (
                            await self.advanced_prompt_generator.get_map_prompt(
                                target_language, category, style, summary_level
                            )
                        )
                        checklist = resolve_language_prompts(
                            target_language
                        ).get_coverage_checklist(document_outline)
                        (
                            map_results,
                            total_tokens_used,
                        ) = await self.run_map_phase(
                            chunks,
                            map_prompt,
                            model,
                            target_language,
                            callback=append_map_fragment,
                        )

                        self._validate_map_contract(map_results, chunks)
                        # Chunk source strings no longer needed after MAP.
                        chunks.clear()

                        map_success_count = sum(
                            1 for item in map_results if item.status == "SUCCESS"
                        )
                        map_failed_count = sum(
                            1 for item in map_results if item.status == "FAILED"
                        )
                        state.diagnostics.map_success_count = map_success_count
                        state.diagnostics.map_failed_count = map_failed_count
                        state.set_phase(PipelinePhase.MAP_COMPLETED)

                        from core.brevio.services.provider_quota.policy import (
                            allow_map_original_text_fallback,
                        )

                        if map_failed_count and not allow_map_original_text_fallback():
                            failed_ids = [
                                item.chunk_id
                                for item in map_results
                                if item.status == "FAILED"
                            ]
                            raise MapPhaseFailedError(
                                f"MAP failed for {map_failed_count} chunk(s) "
                                f"{failed_ids}; refusing original_text fallback into REDUCE",
                                phase=PipelinePhase.MAP_FAILED.value,
                                map_failed_count=map_failed_count,
                                failed_chunk_ids=failed_ids,
                            )

                        map_success_word_count = sum(
                            len(item.summary_text.split())
                            for item in map_results
                            if item.status == "SUCCESS" and item.summary_text
                        )
                        map_salvage_parts = [
                            item.summary_text
                            for item in map_results
                            if item.status == "SUCCESS"
                            and item.summary_text
                            and not is_toc_map_stub(item.summary_text)
                        ]
                        map_salvage_text = "\n\n".join(map_salvage_parts)
                        map_salvage_tokens = (
                            len(encoder.encode(map_salvage_text))
                            if map_salvage_text
                            else 0
                        )
                        logger.info(
                            "MAP complete: results=%s success=%s failed=%s elapsed_s=%.2f api_requests=%s",
                            len(map_results),
                            map_success_count,
                            map_failed_count,
                            self._elapsed_s(),
                            self.history_token_model.api_request_count,
                        )
                        if self._keep_partials():
                            logger.debug(
                                "MAP completed (%s success / %s failed); "
                                "progress already on %s (no separate map snapshot)",
                                map_success_count,
                                map_failed_count,
                                artifacts.partial_path,
                            )

                        state.set_phase(PipelinePhase.REDUCE_RUNNING)
                        reduce_prompt = (
                            await self.advanced_prompt_generator.get_reduce_prompt(
                                target_language, category, style, summary_level
                            )
                        )
                        if checklist:
                            reduce_prompt = f"{reduce_prompt}\n\n{checklist}"
                        intermediate_reduce_prompt = (
                            await self.advanced_prompt_generator.get_reduce_prompt(
                                target_language, category, style, summary_level=None
                            )
                        )

                        reduced_summary, reduce_tokens = await self.run_reduce_phase(
                            map_results,
                            reduce_prompt,
                            model,
                            target_language,
                            force_reduce=False,
                            intermediate_reduce_prompt=intermediate_reduce_prompt,
                            assemble_sections=getattr(
                                decision, "requires_section_assembly", False
                            )
                            is True,
                        )
                        # Map results no longer needed after REDUCE consumed them.
                        for item in map_results:
                            item.summary_text = None
                            item.original_text = ""
                        map_results.clear()

                        reduced_tokens_count = len(encoder.encode(reduced_summary))
                        logger.info(
                            f"[COMPRESSION] input_tokens={file_tokens} output_tokens={reduced_tokens_count} budget_target={decision.output_target_tokens}"
                        )

                        is_valid, validation_errors = self._validate_global_structure(
                            reduced_summary
                        )
                        if not is_valid:
                            logger.warning(
                                f"Global structure validation failed: {validation_errors}"
                            )
                        reduced_summary = self._sanitize_structure(reduced_summary)

                        if (
                            not isinstance(reduced_summary, str)
                            or not reduced_summary.strip()
                        ):
                            raise InvariantViolationError(
                                "FORMAT only receives valid reduced text; REDUCE returned empty or non-string output",
                                phase=PipelinePhase.INVARIANT_FAILED.value,
                            )
                        # REPLACE (not append): REDUCE output supersedes MAP progress on disk.
                        await artifacts.replace_partial(reduced_summary)
                        state.set_phase(PipelinePhase.REDUCE_COMPLETED)

                        if self._should_skip_formatting(reduced_summary, model):
                            logger.info(
                                "FORMAT skipped (disabled by default or below threshold)"
                            )
                            final_summary = ""
                            summary_on_disk = True
                            formatting_tokens = 0
                            del reduced_summary
                        else:
                            state.set_phase(PipelinePhase.FORMAT_RUNNING)
                            logger.debug("Formatting summary")
                            formatting_prompt = (
                                await self.advanced_prompt_generator.get_format_prompt(
                                    target_language
                                )
                            )
                            (
                                final_summary,
                                formatting_tokens,
                            ) = await self.run_formatting_phase(
                                reduced_summary,
                                formatting_prompt,
                                model,
                                target_language,
                            )
                            del reduced_summary
                            await artifacts.replace_partial(final_summary)
                            final_summary = ""
                            summary_on_disk = True
                        total_tokens_used += reduce_tokens + formatting_tokens

                    if not summary_on_disk and (
                        not isinstance(final_summary, str) or not final_summary.strip()
                    ):
                        raise InvariantViolationError(
                            "SUCCESS requires non-empty formatted summary text",
                            phase=PipelinePhase.INVARIANT_FAILED.value,
                        )
                    if (
                        summary_on_disk
                        and not await artifacts.has_recoverable_partial()
                    ):
                        raise InvariantViolationError(
                            "SUCCESS requires non-empty .partial on disk before commit",
                            phase=PipelinePhase.INVARIANT_FAILED.value,
                        )

                    if final_summary:
                        (
                            is_valid_final,
                            final_validation_errors,
                        ) = self._validate_global_structure(final_summary)
                        if not is_valid_final:
                            logger.warning(
                                f"Final structural validation failed: {final_validation_errors}. Applying programmatic sanitize."
                            )
                            final_summary = self._sanitize_structure(final_summary)
                        await artifacts.replace_partial(final_summary)
                        final_summary = ""
                        summary_on_disk = True

                    state.set_phase(PipelinePhase.FINALIZING)
                    await self._enforce_artifact_quality_gate(
                        artifacts,
                        encoder=encoder,
                        file_tokens=file_tokens,
                        source_words=source_word_count,
                        map_words=map_success_word_count,
                        map_tokens=map_salvage_tokens,
                        map_salvage_text=map_salvage_text,
                        decision=decision,
                        summary_level=summary_level,
                    )
                    final_tokens = self.history_token_model.final_artifact_tokens

                    await artifacts.commit_final()
                    state.succeed()
                    logger.info(
                        "Summary committed to %s (partial promoted, in-memory body released)",
                        file_config.summary_path,
                    )

                    logger.debug("Saving token log")
                    try:
                        if not self.history_token_model.folder_id:
                            self.history_token_model.folder_id = effective_folder_id
                        if not self.history_token_model.user_id:
                            self.history_token_model.user_id = effective_user_id
                        if (
                            self.history_token_model.total_tokens_summary_output == 0
                            and final_tokens > 0
                        ):
                            self.history_token_model.total_tokens_summary_output = (
                                final_tokens
                            )
                    except Exception as log_error:
                        logger.error(
                            f"Failed to prepare token log: {str(log_error)}",
                            exc_info=True,
                        )

                    return await self._document_result(
                        success=True,
                        state=state,
                        artifacts=artifacts,
                        message=SummaryMessages.WRITE_SUMMARY.format(
                            file_config.summary_path
                        ),
                        # Body lives on disk; avoid retaining a second full copy in the response.
                        summary="",
                    )
                except asyncio.CancelledError as cancelled:
                    logger.info(
                        f"Document processing cancelled: {file_config.document_path}"
                    )
                    state.fail(PipelinePhase.CANCELLED, cancelled)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message="Processing cancelled",
                    )
                except TypeError as type_error:
                    invariant = InvariantViolationError(
                        f"Internal type contract violation after MAP: {type_error}",
                        phase=PipelinePhase.INVARIANT_FAILED.value,
                    )
                    invariant.__cause__ = type_error
                    logger.error(
                        "Internal type contract violation: %s",
                        type_error,
                        exc_info=True,
                    )
                    state.fail(PipelinePhase.INVARIANT_FAILED, invariant)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(invariant),
                    )
                except ArtifactQualityError as quality_err:
                    logger.error("Artifact quality gate failed: %s", quality_err)
                    state.fail(PipelinePhase.QUALITY_FAILED, quality_err)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(quality_err),
                    )
                except InvariantViolationError as invariant:
                    logger.error(
                        "Invariant violation (no silent fallback): %s", invariant
                    )
                    state.fail(PipelinePhase.INVARIANT_FAILED, invariant)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(invariant),
                    )
                except MapPhaseFailedError as map_failed:
                    logger.error(
                        "MAP failed without original_text fallback: %s", map_failed
                    )
                    state.fail(PipelinePhase.MAP_FAILED, map_failed)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(map_failed),
                    )
                except JobRequestBudgetExceededError as budget_err:
                    logger.error("Job provider request budget exceeded: %s", budget_err)
                    fail_phase = self._unexpected_failure_phase(state.phase)
                    state.fail(fail_phase, budget_err)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(budget_err),
                    )
                except (
                    QuotaPolicyMissingError,
                    ProviderQuotaUnavailableError,
                    QuotaAcquireTimeoutError,
                ) as quota_err:
                    logger.error("Provider quota control failed: %s", quota_err)
                    fail_phase = self._unexpected_failure_phase(state.phase)
                    state.fail(fail_phase, quota_err)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(quota_err),
                    )
                except ReduceConvergenceError as convergence:
                    logger.error("REDUCE failed to converge: %s", convergence)
                    state.fail(PipelinePhase.REDUCE_FAILED, convergence)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=str(convergence),
                    )
                except Exception as error:
                    fail_phase = self._unexpected_failure_phase(state.phase)
                    logger.error(
                        "Failed to generate summary for %s during %s: %s",
                        file_config.document_path,
                        fail_phase.value,
                        error,
                        exc_info=True,
                    )
                    state.fail(fail_phase, error)
                    return await self._document_result(
                        success=False,
                        state=state,
                        artifacts=artifacts,
                        message=f"Failed to generate summary: {error}",
                    )
            finally:
                try:
                    if artifacts is not None:
                        await artifacts.finalize(state.outcome, state.final_committed)
                except Exception as cleanup_error:
                    logger.error(
                        "Artifact finalize raised after document processing: %s",
                        cleanup_error,
                        exc_info=True,
                    )
                    if state.final_committed:
                        logger.error(
                            "Preserving committed summary.md despite cleanup failure: %s",
                            file_config.summary_path,
                        )
                    else:
                        raise
                logger.debug(f"Released file_semaphore for {file_config.document_path}")
        except asyncio.CancelledError:
            logger.info(f"Document processing cancelled: {file_config.document_path}")
            if state.outcome is None:
                state.fail(PipelinePhase.CANCELLED, asyncio.CancelledError())
            if artifacts is not None:
                await artifacts.finalize(state.outcome, state.final_committed)
            raise
        except ValueError as error:
            logger.error(
                f"Validation error for {file_config.document_path}: {str(error)}",
                exc_info=True,
            )
            if state.outcome is None:
                state.fail(PipelinePhase.INITIALIZING, error)
            if artifacts is not None:
                await artifacts.finalize(state.outcome, state.final_committed)
            return await self._document_result(
                success=False,
                state=state,
                artifacts=artifacts,
                message=f"Validation error: {str(error)}",
            )
        except Exception as error:
            logger.error(
                f"Error processing document {file_config.document_path}: {str(error)}",
                exc_info=True,
            )
            if state.outcome is None:
                fail_phase = self._unexpected_failure_phase(state.phase)
                state.fail(fail_phase, error)
            if artifacts is not None:
                await artifacts.finalize(state.outcome, state.final_committed)
            return await self._document_result(
                success=False,
                state=state,
                artifacts=artifacts,
                message=f"Error processing document: {str(error)}",
            )

    async def _process_single_transcription(
        self,
        prompt_config: PromptConfig,
        file_config: FileConfig,
        data_result: DataResult,
        folder_id: str | None = None,
        user_id: str | None = None,
    ) -> SummaryResponse:
        """Route a persisted transcription through the document MAP/REDUCE pipeline."""
        del data_result
        if not file_config.transcription_path:
            raise ValueError("transcription_path must be provided")
        if not file_config.document_path:
            file_config.document_path = file_config.transcription_path
        return await self.generate_summary_document(
            prompt_config,
            file_config,
            folder_id=folder_id,
            user_id=user_id,
        )

    async def generate_summary_document(
        self,
        prompt_config: PromptConfig,
        file_config: FileConfig,
        folder_id: str | None = None,
        user_id: str | None = None,
    ) -> SummaryResponse:
        self.history_token_model.folder_id = folder_id
        self.history_token_model.user_id = user_id
        logger.info(
            f"Starting summary generation for document: {file_config.document_path}"
        )
        self.client = await self.api_service._initialize_client(
            prompt_config.model, user_id=user_id
        )
        try:
            async with self.lifespan():
                results = await self.generate_summary_documents(
                    prompt_config,
                    [file_config],
                    folder_id=folder_id,
                    user_id=user_id,
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
            fail_phase = getattr(e, "phase", PipelinePhase.INITIALIZING.value)
            return SummaryResponse(
                success=False,
                summary="",
                message=f"Error generating summary: {str(e)}",
                error_message=str(e),
                phase=fail_phase,
                error_type=type(e).__name__,
                status=job_status_for(success=False).value,
                job_phase=job_phase_for(fail_phase, success=False).value,
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
                    prompt_config,
                    file_configs,
                    user_id=str(user_id),
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
