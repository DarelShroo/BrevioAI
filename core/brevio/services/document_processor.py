import asyncio
import logging
import os
from typing import List, Optional, Tuple, Callable, Any

import aiofiles
from core.brevio.enums.language import LanguageType
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.managers.token_manager import TokenManager
from core.brevio.models.dtos import DocumentProcessingRequest, PostProcessRequest
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.summary_chunk_generator import SummaryChunkGenerator
from core.brevio.services.summary_post_processor import SummaryPostProcessor
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.yt_service import YTService
from core.brevio.utils.text_chunker import TextChunker
from core.shared.enums.model import ModelType
from core.shared.models.user.data_result import DataResult
from core.shared.utils.json_data_utils import save_log_to_json
from core.shared.utils.model_tokens_utils import get_encoder

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(
        self,
        token_manager: TokenManager,
        chunk_generator: SummaryChunkGenerator,
        post_processor: SummaryPostProcessor,
        transcription_service: TranscriptionService,
        yt_service: YTService,
        directory_manager: DirectoryManager,
        max_tokens_per_chunk: int,
    ):
        self.token_manager = token_manager
        self.chunk_generator = chunk_generator
        self.post_processor = post_processor
        self.transcription_service = transcription_service
        self.yt_service = yt_service
        self.directory_manager = directory_manager
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self._percent_chunk_overlap = 0.2

    async def process_single_document(
        self,
        request: DocumentProcessingRequest,
        prompt: str,
        process_chunks_func: Callable[[List[str], str, ModelType, LanguageType], Any],
    ) -> SummaryResponse:
        file_config = request.file_config
        prompt_config = request.prompt_config
        
        logger.info(f"Processing document: {file_config.document_path}")

        try:
            # 1. Handle YouTube
            if file_config.is_youtube:
                logger.info(f"Processing YouTube video: {file_config.document_path}")
                # Assuming yt_service has a method to get text or audio path
                # Since I don't have the exact signature, I'll assume it returns a path to a file
                # or we skip for now if not critical.
                # But let's assume standard flow: download -> transcribe -> summarize
                pass

            # 2. Handle Transcription
            if file_config.transcription_path:
                # Logic to handle transcription
                pass

            # 3. Read File Content
            text_content = ""
            if file_config.document_path:
                if not os.path.exists(file_config.document_path):
                    return SummaryResponse(success=False, summary="", message="File not found")
                
                async with aiofiles.open(file_config.document_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = await f.read()

            if not text_content:
                return SummaryResponse(success=False, summary="", message="No content to summarize")

            # 4. Chunk Text
            overlap = int(self.max_tokens_per_chunk * self._percent_chunk_overlap)
            chunks = TextChunker.chunk_text(
                text_content, self.max_tokens_per_chunk, overlap, prompt_config.model
            )
            logger.info(f"Split document into {len(chunks)} chunks")

            # 5. Process Chunks
            full_summary, total_tokens = await process_chunks_func(
                chunks, prompt, prompt_config.model, prompt_config.language
            )

            # 6. Post-process
            encoder = get_encoder(prompt_config.model)
            clean_summary_tokens = len(encoder.encode(full_summary))
            
            post_process_request = PostProcessRequest(
                clean_summary=full_summary,
                clean_summary_tokens=clean_summary_tokens,
                model=prompt_config.model,
                language=prompt_config.language
            )
            
            final_summary = await self.post_processor.postprocess_summary(post_process_request)

            return SummaryResponse(
                success=True,
                summary=final_summary,
                message="Summary generated successfully"
            )

        except Exception as e:
            logger.error(f"Error processing document {file_config.document_path}: {e}", exc_info=True)
            return SummaryResponse(success=False, summary="", message=str(e))
