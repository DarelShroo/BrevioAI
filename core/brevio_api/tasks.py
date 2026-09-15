import asyncio
import logging
from typing import List, Tuple

from asgiref.sync import async_to_sync
from bson import ObjectId, errors
from celery import shared_task

from core.brevio.enums.extension import (
    document_extension_values,
    media_extension_values,
)
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.services.brevio_service import BrevioService
from core.shared.enums.model import ModelType
from core.shared.models.brevio.brevio_generate import BrevioGenerate

logger = logging.getLogger(__name__)


@shared_task(name="core.brevio_api.tasks.process_summary_task")
def process_summary_task(
    files: List[Tuple[str, bytes]],
    language: str,
    model: str,
    category: str,
    style: str,
    format: str,
    summary_level: str,
    _current_user: str,
    is_media: bool = False,
    folder_entry_id: str | None = None,
    transcription_provider: str | None = None,
    transcription_model: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    _ = max_output_tokens
    _ = temperature
    allowed_extensions = (
        media_extension_values() if is_media else document_extension_values()
    )
    files_filtered = [
        (name, content)
        for name, content in files
        if any(name.lower().endswith(f".{ext.lower()}") for ext in allowed_extensions)
    ]

    if not files_filtered:
        logger.error("No se encontraron archivos válidos para procesar")
        raise ValueError("No se encontraron archivos válidos para procesar")

    prompt_config = PromptConfig(
        model=ModelType(model),
        category=category,
        style=style,
        format=OutputFormatType(format),
        language=LanguageType(language),
        summary_level=SummaryLevel(summary_level),
        reasoning_effort=reasoning_effort,
    )

    brevio_service = BrevioService()

    service_method = (
        brevio_service.generate_summary_documents
        if not is_media
        else brevio_service.generate_summary_media_upload
    )

    try:
        result = async_to_sync(service_method)(
            files_filtered,
            _current_user,
            prompt_config,
            folder_entry_id=folder_entry_id,
            **(
                {
                    "transcription_provider": transcription_provider,
                    "transcription_model": transcription_model,
                }
                if is_media
                else {}
            ),
        )
    except Exception as e:
        logger.error(f"Error al procesar la tarea de resumen: {str(e)}")
        raise

    return {
        "message": f"Resumen generado exitosamente para el usuario {_current_user}",
        "folder_entry_id": folder_entry_id,
        "result": result,
    }


@shared_task(name="core.brevio_api.tasks.generate_summary_task")
def generate_summary_task(brevio_generate_dict: dict, user_id: str) -> dict:
    try:
        brevio_generate_dict["prompt_config"]["id"] = ObjectId(
            brevio_generate_dict["prompt_config"]["id"]
        )
    except errors.InvalidId:
        raise ValueError("El valor de prompt_config.id no es un ObjectId válido")

    brevio_generate = BrevioGenerate(**brevio_generate_dict)
    brevio_service = BrevioService()

    try:
        result = asyncio.run(
            _wrapped_generate(brevio_service, brevio_generate, user_id)
        )
        return result
    except Exception as exc:
        logger.error(
            f"[ERROR] Falló generación de resumen para usuario {user_id}: {exc}"
        )
        raise


async def _wrapped_generate(
    service: BrevioService,
    brevio_generate: BrevioGenerate,
    user_id: str,
) -> dict:
    try:
        return await service.generate(brevio_generate, user_id)
    finally:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.debug(f"Cancelando {len(tasks)} tareas pendientes...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("Tareas pendientes canceladas.")
