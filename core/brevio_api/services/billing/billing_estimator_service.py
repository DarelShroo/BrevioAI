import logging
from enum import Enum
from math import ceil
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastapi import HTTPException

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel
from core.shared.utils.model_tokens_utils import get_encoder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


class BillingEstimatorService:
    def __init__(self, model: ModelType = ModelType.GPT_4O_MINI):
        self.model: ModelType = model
        self.max_tokens_per_chunk: int = 4096
        self.tokens_overheads: int = 100
        self._percent_chunk_overlap: float = 0.2
        self.overlap: float = self.max_tokens_per_chunk * self._percent_chunk_overlap
        self.min_tokens_postprocess: int = 1000
        self.encoder = get_encoder(model)
        self.max_chunks_per_group = 4
        self.context_token_limit = 100

    async def summary_tokens_predict(
        self,
        file_tokens: int,
        language_input: LanguageType,
        language_output: LanguageType,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        summary_level: SummaryLevel,
        history: Optional[HistoryTokenModel] = None,
    ) -> Dict[str, int]:
        apg = AdvancedPromptGenerator()
        chunks = self.split_into_chunks(file_tokens, self.max_tokens_per_chunk)
        num_chunks = len(chunks)

        # generate prompt
        prompt = await apg.generate_prompt(
            category, style, output_format, language_output, summary_level
        )
        prompt_tokens = len(self.encoder.encode(prompt))

        # summary chunk prompt
        without_previous_context = ""
        summary_chunk_prompt = await apg.get_summary_chunk_prompt(
            without_previous_context, language_output
        )
        summary_chunk_prompt_tokens = len(self.encoder.encode(summary_chunk_prompt))

        # postprocess prompt
        postprocess_prompt = await apg.get_postprocess_prompt(language_output)
        postprocess_prompt_tokens = len(self.encoder.encode(postprocess_prompt))

        result: list = []

        for index, chunk in enumerate(
            chunks[: min(len(chunks), self.max_chunks_per_group)]
        ):
            print(chunk, prompt_tokens)
            chunks[index] = chunk + prompt_tokens

        if len(chunks) > self.max_chunks_per_group:
            for index, chunk in enumerate(chunks[self.max_chunks_per_group :]):
                system_prompt_tokens = (
                    prompt_tokens
                    + summary_chunk_prompt_tokens
                    + self.context_token_limit
                )
                chunks[index] = chunk + system_prompt_tokens
                print(chunk, system_prompt_tokens)

        print(sum(chunks))

        # print(chunks)
        # print(sum(chunks))
        return {
            "summary_input_token": 2,
            "summary_output_token": 2,
            "postprocess_input_token": 2,
            "postprocess_output_token": 2,
        }

    def split_into_chunks(self, total: int, max_size: int) -> List[int]:
        chunks = []
        while total > 0:
            chunk = min(max_size, total)
            chunks.append(chunk)
            total -= chunk
        return chunks
