import logging
from typing import List

from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder

logger = logging.getLogger(__name__)


class TextChunker:
    @staticmethod
    def chunk_text(
        text: str, chunk_size: int, overlap: float, model: ModelType
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
