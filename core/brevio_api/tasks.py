import asyncio
import logging
from typing import List, Tuple

from asgiref.sync import async_to_sync
from bson import ObjectId, errors
from celery import shared_task

from core.brevio.enums.extension import ExtensionType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker
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
) -> str:
    allowed_extensions = (
        [ExtensionType.MP3.value]
        if is_media
        else [ExtensionType.DOCX.value, ExtensionType.PDF.value]
    )
    files_filtered = [
        (name, content)
        for name, content in files
        if any(name.lower().endswith(ext.lower()) for ext in allowed_extensions)
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
    )

    _usage_cost_tracker = UsageCostTracker()
    brevio_service = BrevioService()

    service_method = (
        brevio_service.generate_summary_documents
        if not is_media
        else brevio_service.generate_summary_media_upload
    )

    try:
        async_to_sync(service_method)(
            files_filtered, _current_user, prompt_config, _usage_cost_tracker
        )
    except Exception as e:
        logger.error(f"Error al procesar la tarea de resumen: {str(e)}")
        raise

    return f"Resumen generado exitosamente para el usuario {_current_user}"


@shared_task(name="core.brevio_api.tasks.generate_summary_task")
def generate_summary_task(brevio_generate_dict: dict, user_id: str) -> dict:
    try:
        brevio_generate_dict["prompt_config"]["id"] = ObjectId(
            brevio_generate_dict["prompt_config"]["id"]
        )
    except errors.InvalidId:
        raise ValueError("El valor de prompt_config.id no es un ObjectId válido")

    usage_cost_tracker = UsageCostTracker()
    brevio_generate = BrevioGenerate(**brevio_generate_dict)
    brevio_service = BrevioService()

    try:
        result = asyncio.run(
            _wrapped_generate(
                brevio_service, brevio_generate, user_id, usage_cost_tracker
            )
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
    usage_cost_tracker: UsageCostTracker,
) -> dict:
    try:
        return await service.generate(brevio_generate, user_id, usage_cost_tracker)
    finally:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.debug(f"Cancelando {len(tasks)} tareas pendientes...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("Tareas pendientes canceladas.")
