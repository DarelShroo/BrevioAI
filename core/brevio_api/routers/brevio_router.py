import base64
from typing import Dict, List, Optional, Tuple, cast

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from pydantic import HttpUrl

from core.brevio.enums.extension import ExtensionType, media_extension_values
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.credential_resolver import CredentialResolver
from core.brevio.services.processing_preflight import (
    PreflightDecision,
    ProcessingPreflight,
)
from core.brevio.services.summary_providers.access_policy import SummaryAccessPolicy
from core.brevio.services.transcription.catalog import (
    build_transcription_providers_payload,
)
from core.brevio_api.celery import celery_app
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.credential_resolver_dependency import (
    get_credential_resolver,
)
from core.brevio_api.dependencies.estimation_service_dependency import (
    get_estimation_service,
)
from core.brevio_api.dependencies.library_folder_service_dependency import (
    library_folder_service_dependency,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.brevio.document_processing_request import (
    DocumentProcessingRequest,
)
from core.brevio_api.models.brevio.responses.brevio_responses import (
    CategoryStyles,
    CategoryStylesDataResponse,
    CountMediaDataResponse,
    CountMediaResponse,
    CountMediaTimeDataResponse,
    CountMediaTimeResponse,
    LanguagesDataResponse,
    LanguagesResponse,
    ModelsDataResponse,
    ModelsResponse,
    OutputFormatDataResponse,
    ProcessingMessageData,
    ProcessingMessageResponse,
    SummaryLevelDataResponse,
    TranscriptionProvidersDataResponse,
    TranscriptionProvidersResponse,
)
from core.brevio_api.models.brevio.responses.estimate_documents_response import (
    ChunkingEstimate,
    CreditsEstimate,
    DocumentExtractionMetadata,
    EstimatedDocument,
    EstimateDocumentsData,
    EstimateDocumentsResponse,
    EstimationResult,
    EstimationWarning,
    InputTokensEstimate,
    ModelEstimate,
    OutputTokensEstimate,
    PricingEstimate,
    TokenizationMetadata,
)
from core.brevio_api.models.brevio.url_yt import UrlYT
from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.services.estimation.estimation_service import EstimationService
from core.brevio_api.services.library_folder_service import LibraryFolderService
from core.brevio_api.tasks import generate_summary_task, process_summary_task
from core.brevio_api.utils.extension_validator import validate_file_extension
from core.brevio_api.utils.language_utils import language_from_form
from core.brevio_api.utils.upload_security import read_uploads_limited
from core.shared.enums.model import ModelType
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.utils.generation_params import (
    GenerationParamError,
    validate_generation_params,
)
from core.shared.utils.model_capabilities import get_model_capabilities
from core.shared.utils.model_catalog import (
    build_models_payload,
    catalog_entry_for_model,
)
from core.shared.utils.pricing_registry import get_pricing_snapshot
from core.shared.utils.source_names import names_for_batch


class BrevioRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/brevio", tags=["brevio"])
        self._register_routes()

    @staticmethod
    def _validate_document_files(files: List[UploadFile]) -> None:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one document file is required",
            )
        valid_document_extensions = [
            ExtensionType.DOCX.value,
            ExtensionType.PDF.value,
        ]
        for uploaded_file in files:
            validate_file_extension(uploaded_file, valid_document_extensions)

    @staticmethod
    def _validate_generation_params(
        model: ModelType,
        *,
        reasoning_effort: Optional[str] = None,
    ) -> None:
        try:
            validate_generation_params(
                model,
                reasoning_effort=reasoning_effort,
            )
        except GenerationParamError as exc:
            raise CodedHTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                ApiErrorCode.GENERATION_PARAM_INVALID,
                str(exc),
            ) from exc

    @staticmethod
    async def _preflight(
        *,
        source_type: str,
        user_id: str,
        model: ModelType,
        resolver: CredentialResolver,
        brevio_service: BrevioService | None = None,
        transcription_provider: Optional[str] = None,
        transcription_model: Optional[str] = None,
    ) -> PreflightDecision:
        credits = 0.0
        getter = getattr(brevio_service, "get_user_credits", None)
        if callable(getter):
            credits = float(await getter(user_id) or 0)
        return await ProcessingPreflight(resolver).ensure(
            source_type=source_type,
            user_id=user_id,
            model=model,
            user_credits=credits,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
        )

    @staticmethod
    async def _job_identity(
        files: List[Tuple[str, bytes]],
        user_id: str,
        library_folder_id: Optional[str],
        folder_name: Optional[str],
        library_folders: LibraryFolderService,
        kind: str,
        entry_name: Optional[str] = None,
    ) -> Tuple[Optional[str], str, str]:
        folder_oid = await library_folders.resolve_destination(
            user_id, library_folder_id, folder_name
        )
        display_name, original_name = names_for_batch(
            [name for name, _ in files],
            kind=kind,
            entry_name=entry_name,
        )
        return (
            str(folder_oid) if folder_oid is not None else None,
            display_name,
            original_name,
        )

    def _register_routes(self) -> None:
        @self.router.get(
            "/languages",
            response_model=LanguagesDataResponse,
            description="Get a list of supported languages for processing",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_languages(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> LanguagesDataResponse:
            languages = brevio_service.get_languages()
            response = LanguagesDataResponse(
                data=LanguagesResponse(languages=languages),
            )
            return response

        @self.router.get(
            "/models",
            response_model=ModelsDataResponse,
            description="Get a list of available AI models",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_models(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> ModelsDataResponse:
            models = brevio_service.get_models()
            payload = build_models_payload(models)
            payload["environment"] = SummaryAccessPolicy().environment
            response = ModelsDataResponse(
                data=ModelsResponse(**payload),
            )
            return response

        @self.router.get(
            "/transcription-providers",
            response_model=TranscriptionProvidersDataResponse,
            description="List transcription providers and whether the current environment may select them",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_transcription_providers(
            verify_api_key: str = Depends(verify_api_key),
        ) -> TranscriptionProvidersDataResponse:
            payload = build_transcription_providers_payload()
            return TranscriptionProvidersDataResponse(
                data=TranscriptionProvidersResponse(**payload)
            )

        @self.router.get(
            "/categories-styles",
            response_model=CategoryStylesDataResponse,
            description="Get available categories and their associated styles",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_categories_styles(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CategoryStylesDataResponse:
            all_categories_styles = (
                await brevio_service.get_all_category_style_combinations()
            )
            categories_styles = CategoryStyles(
                advanced_content_combinations=all_categories_styles
            )
            response = CategoryStylesDataResponse(data=categories_styles)
            return response

        @self.router.get(
            "/output-formats",
            response_model=OutputFormatDataResponse,
            description="Get available output formats",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_formats(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> OutputFormatDataResponse:
            formats = brevio_service.get_all_formats()
            response = OutputFormatDataResponse(data=formats)
            return response

        @self.router.get(
            "/summary-levels",
            response_model=SummaryLevelDataResponse,
            description="Get available summary levels",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_summary_levels(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> SummaryLevelDataResponse:
            summary_levels = brevio_service.get_all_summary_levels()
            response = SummaryLevelDataResponse(data=summary_levels)
            return response

        @self.router.post(
            "/count-yt-videos",
            response_model=CountMediaDataResponse,
            description="Count the number of videos in a YouTube playlist (authenticated users)",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Unauthorized"},
                422: {"description": "Invalid URL format"},
            },
        )
        async def count_media_in_yt_playlist(
            http_request: Request,
            request: UrlYT,
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CountMediaDataResponse:
            from core.brevio_api.services.anti_abuse import enforce_youtube_rate_limit

            enforce_youtube_rate_limit(http_request, str(_current_user))
            result = await brevio_service.count_media_in_yt_playlist(
                HttpUrl(request.url)
            )
            if not isinstance(result, int):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid response format from brevio service",
                )
            response = CountMediaDataResponse(
                data=CountMediaResponse(count=result),
            )
            return response

        @self.router.post(
            "/count-time-yt-video",
            response_model=CountMediaTimeDataResponse,
            description="Get the total duration of a YouTube video in seconds (authenticated users)",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Unauthorized"},
                422: {"description": "Invalid URL format"},
            },
        )
        async def get_total_duration(
            http_request: Request,
            request: UrlYT,
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CountMediaTimeDataResponse:
            from core.brevio_api.services.anti_abuse import enforce_youtube_rate_limit

            enforce_youtube_rate_limit(http_request, str(_current_user))
            try:
                duration_data = await brevio_service.get_total_duration(request.url)
                if not isinstance(duration_data, int):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid response format from brevio service",
                    )
                return CountMediaTimeDataResponse(
                    data=CountMediaTimeResponse(time=duration_data),
                )
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred",
                )

        @self.router.post(
            "/summary-media",
            response_model=ProcessingMessageResponse,
            description="""
                Generate summaries from media files (MP3, M4A, WAV, MP4).
                The process runs in the background and results will be available asynchronously.
            """,
            status_code=status.HTTP_202_ACCEPTED,
            responses={
                401: {"description": "Unauthorized"},
                415: {"description": "Unsupported media type"},
                422: {"description": "Validation error"},
            },
        )
        async def generate_summary_media(
            request: Request,
            files: List[UploadFile] = File(...),
            language: LanguageType = Depends(language_from_form),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            summary_level: SummaryLevel = Form(...),
            library_folder_id: Optional[str] = Form(None),
            folder_name: Optional[str] = Form(None),
            name: Optional[str] = Form(None),
            transcription_provider: Optional[str] = Form(None),
            transcription_model: Optional[str] = Form(None),
            reasoning_effort: Optional[str] = Form(None),
            idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
            credential_resolver: CredentialResolver = Depends(get_credential_resolver),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> JSONResponse:
            from core.brevio_api.services.anti_abuse import (
                enforce_job_create_rate_limit,
                enforce_media_rate_limit,
                enforce_upload_rate_limit,
            )

            enforce_media_rate_limit(request, str(_current_user))
            enforce_upload_rate_limit(request, str(_current_user))
            enforce_job_create_rate_limit(request, str(_current_user))
            valid_media_extensions = media_extension_values()
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="At least one media file is required",
                )
            for uploaded_file in files:
                validate_file_extension(
                    uploaded_file,
                    valid_media_extensions,
                    code=ApiErrorCode.MEDIA_FORMAT_NOT_ALLOWED,
                )
            self._validate_generation_params(
                model,
                reasoning_effort=reasoning_effort,
            )

            decision = await self._preflight(
                source_type="media",
                user_id=str(_current_user),
                model=model,
                resolver=credential_resolver,
                brevio_service=brevio_service,
                transcription_provider=transcription_provider,
                transcription_model=transcription_model,
            )
            selected_provider = decision.transcription_provider
            selected_transcription_model = decision.transcription_model

            file_data_list = await read_uploads_limited(files)

            folder_id, display_name, original_name = await self._job_identity(
                file_data_list,
                str(_current_user),
                library_folder_id,
                folder_name,
                library_folders,
                "media",
                entry_name=name,
            )

            from core.brevio.models.prompt_config_model import PromptConfig as PC

            prompt = PC(
                model=model,
                category=category,
                style=style,
                format=format,
                language=language,
                summary_level=summary_level,
                reasoning_effort=reasoning_effort,
            )
            job_id, created = await brevio_service.admit_summary_job_with_files(
                str(_current_user),
                file_data_list,
                prompt_config=prompt,
                source_type="media",
                name=display_name,
                original_name=original_name,
                library_folder_id=folder_id,
                idempotency_key=(idempotency_key or "").strip() or None,
                transcription_provider=selected_provider,
                transcription_model=selected_transcription_model,
            )

            task_id = None
            if created:
                # FASE 6: fair scheduler registers + dispatches; no direct Celery delay.
                try:
                    await brevio_service.dispatch_waiting_jobs()
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning(
                        "event=dispatch_after_admit_failed job_id=%s",
                        job_id,
                        exc_info=True,
                    )
            else:
                # Idempotent replay: do not re-enqueue a known job.
                task_id = None

            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content={
                    **response.model_dump(exclude_none=True),
                    "task_id": task_id,
                    "folder_entry_id": job_id,
                    "job_id": job_id,
                },
                status_code=status.HTTP_202_ACCEPTED,
            )

        @self.router.post(
            "/summary-documents",
            response_model=ProcessingMessageResponse,
            description="""
                Generate summaries from document files (PDF, DOCX).
                The process runs in the background and results will be available asynchronously.
            """,
            status_code=status.HTTP_202_ACCEPTED,
            responses={
                401: {"description": "Unauthorized"},
                415: {"description": "Unsupported media type"},
                422: {"description": "Validation error"},
            },
        )
        async def generate_summary_documents(
            request: Request,
            files: List[UploadFile] = File(...),
            language: LanguageType = Depends(language_from_form),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            summary_level: SummaryLevel = Form(...),
            library_folder_id: Optional[str] = Form(None),
            folder_name: Optional[str] = Form(None),
            name: Optional[str] = Form(None),
            reasoning_effort: Optional[str] = Form(None),
            idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
            credential_resolver: CredentialResolver = Depends(get_credential_resolver),
            library_folders: LibraryFolderService = Depends(
                library_folder_service_dependency
            ),
        ) -> JSONResponse:
            from core.brevio_api.services.anti_abuse import (
                enforce_job_create_rate_limit,
                enforce_upload_rate_limit,
            )

            enforce_upload_rate_limit(request, str(_current_user))
            enforce_job_create_rate_limit(request, str(_current_user))
            self._validate_document_files(files)
            self._validate_generation_params(
                model,
                reasoning_effort=reasoning_effort,
            )

            await self._preflight(
                source_type="documents",
                user_id=str(_current_user),
                model=model,
                resolver=credential_resolver,
                brevio_service=brevio_service,
            )

            file_data_list = await read_uploads_limited(files)

            folder_id, display_name, original_name = await self._job_identity(
                file_data_list,
                str(_current_user),
                library_folder_id,
                folder_name,
                library_folders,
                "document",
                entry_name=name,
            )

            from core.brevio.models.prompt_config_model import PromptConfig as PC

            prompt = PC(
                model=model,
                category=category,
                style=style,
                format=format,
                language=language,
                summary_level=summary_level,
                reasoning_effort=reasoning_effort,
            )
            job_id, created = await brevio_service.admit_summary_job_with_files(
                str(_current_user),
                file_data_list,
                prompt_config=prompt,
                source_type="documents",
                name=display_name,
                original_name=original_name,
                library_folder_id=folder_id,
                idempotency_key=(idempotency_key or "").strip() or None,
            )

            task_id = None
            if created:
                # admit_summary_job_with_files already registered + dispatched.
                try:
                    await brevio_service.dispatch_waiting_jobs()
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning(
                        "event=dispatch_after_admit_failed job_id=%s",
                        job_id,
                        exc_info=True,
                    )

            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content={
                    **response.model_dump(exclude_none=True),
                    "task_id": task_id,
                    "folder_entry_id": job_id,
                    "job_id": job_id,
                },
                status_code=status.HTTP_202_ACCEPTED,
            )

        @self.router.post(
            "/estimate-documents",
            response_model=EstimateDocumentsResponse,
            description="Estimate document processing locally without calling the LLM",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Unauthorized"},
                415: {"description": "Unsupported media type"},
                422: {"description": "Validation error"},
            },
        )
        async def estimate_documents(
            http_request: Request,
            files: List[UploadFile] = File(...),
            request: DocumentProcessingRequest = Depends(
                DocumentProcessingRequest.from_form
            ),
            _current_user: ObjectId = Depends(get_current_user),
            estimation_service: EstimationService = Depends(get_estimation_service),
        ) -> EstimateDocumentsResponse:
            from core.brevio_api.services.anti_abuse import (
                enforce_estimation_rate_limit,
                enforce_upload_rate_limit,
            )

            enforce_estimation_rate_limit(http_request, str(_current_user))
            enforce_upload_rate_limit(http_request, str(_current_user))
            self._validate_document_files(files)

            files_data = await read_uploads_limited(files)
            outcome = await estimation_service.estimate(request, files_data)
            model_capabilities = get_model_capabilities(request.model)
            model_catalog = catalog_entry_for_model(request.model)
            pricing_snapshot = get_pricing_snapshot(request.model)

            documents = [
                EstimatedDocument(
                    filename=document.filename,
                    tokens=tokens,
                    extraction=DocumentExtractionMetadata(
                        status=document.extraction_status,
                        pages_total=document.pages_total,
                        pages_with_text=document.pages_with_text,
                        pages_without_text=document.pages_without_text,
                    ),
                )
                for document, tokens in outcome.document_token_counts
            ]

            response = EstimateDocumentsResponse(
                data=EstimateDocumentsData(
                    can_process=outcome.can_process,
                    reason=outcome.reason,
                    estimation=EstimationResult(
                        input_tokens=InputTokensEstimate(
                            prompt_template=outcome.prompt_template_tokens,
                            documents_content=outcome.total_document_tokens,
                            structural=outcome.structural_tokens,
                            total=outcome.total_input_tokens,
                        ),
                        output_tokens=OutputTokensEstimate(
                            minimum=outcome.output_minimum_tokens,
                            expected=outcome.output_expected_tokens,
                            max_ceiling=outcome.output_max_tokens,
                        ),
                        total_tokens_worst_case=(
                            outcome.total_input_tokens
                            + (
                                outcome.output_max_tokens
                                * max(1, outcome.chunking_calls)
                            )
                        ),
                    ),
                    documents=documents,
                    tokenization=TokenizationMetadata(
                        method=outcome.tokenization_method,
                        confidence=outcome.tokenization_confidence,
                        estimated_error_margin=outcome.tokenization_error_margin,
                    ),
                    model=ModelEstimate(
                        name=request.model.value,
                        provider=model_capabilities.provider,
                        access=model_catalog.access.value,
                        requires_api_key=model_catalog.requires_api_key,
                        context_limit=model_capabilities.context_window,
                        max_output_tokens=outcome.output_max_tokens,
                        supports_chunking=model_capabilities.supports_chunking,
                    ),
                    pricing=PricingEstimate(
                        model=request.model.value,
                        provider_cost_currency=pricing_snapshot.currency,
                        platform_currency=pricing_snapshot.platform_currency,
                        expected_cost=outcome.platform_expected_cost,
                        max_cost=outcome.platform_max_cost,
                        pricing_version=pricing_snapshot.pricing_version,
                    ),
                    credits=CreditsEstimate(
                        expected=outcome.expected_credits,
                        maximum=outcome.maximum_credits,
                    ),
                    chunking=ChunkingEstimate(
                        required=outcome.chunking_required,
                        calls=outcome.chunking_calls,
                    ),
                    estimation_id=outcome.estimation_id,
                    estimated_at=outcome.estimated_at,
                    warnings=[
                        EstimationWarning(**warning) for warning in outcome.warnings
                    ],
                )
            )
            return response

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(
            request: Request,
            brevio_generate: BrevioGenerate,
            idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
            _current_user: ObjectId = Depends(get_current_user),
            credential_resolver: CredentialResolver = Depends(get_credential_resolver),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> JSONResponse:
            from datetime import datetime, timezone

            from core.shared.enums.job_status import JobStatus

            self._validate_generation_params(
                brevio_generate.prompt_config.model,
                reasoning_effort=brevio_generate.prompt_config.reasoning_effort,
            )
            decision = await self._preflight(
                source_type="youtube",
                user_id=str(_current_user),
                model=brevio_generate.prompt_config.model,
                resolver=credential_resolver,
                brevio_service=brevio_service,
                transcription_provider=brevio_generate.transcription_provider,
                transcription_model=brevio_generate.transcription_model,
            )
            payload = brevio_generate.model_dump(mode="json")
            payload["transcription_provider"] = decision.transcription_provider
            payload["transcription_model"] = decision.transcription_model

            key = (idempotency_key or "").strip() or None
            if key:
                existing = await brevio_service.find_job_by_idempotency(
                    str(_current_user), key
                )
                if existing:
                    response = ProcessingMessageResponse(data=ProcessingMessageData())
                    return JSONResponse(
                        content={
                            **response.model_dump(exclude_none=True),
                            "task_id": None,
                            "folder_entry_id": existing,
                            "job_id": existing,
                        },
                        status_code=status.HTTP_202_ACCEPTED,
                    )

            from core.brevio_api.models.errors.api_codes import ApiErrorCode
            from core.brevio_api.models.errors.provider_errors import ProviderError
            from core.brevio_api.services.anti_abuse import enforce_youtube_rate_limit
            from core.brevio_api.services.billing.product_limit_service import (
                AdmissionRequest,
                ProductLimitError,
                measure_documents,
            )

            enforce_youtube_rate_limit(request, str(_current_user))

            # FASE 7: commercial admit BEFORE FolderEntry insert (no spam FAILED docs).
            job_id = str(ObjectId())
            products = await brevio_service._get_product_limit_service()
            user = await brevio_service.ensure_user_plan(str(_current_user))
            plan = products.resolve_user_plan(user)
            has_byok = await brevio_service._user_has_byok(
                str(_current_user), brevio_generate.prompt_config.model
            )
            try:
                admission = await products.admit(
                    AdmissionRequest(
                        user_id=str(_current_user),
                        job_id=job_id,
                        source_type="youtube",
                        model=brevio_generate.prompt_config.model,
                        has_byok=has_byok,
                        documents=measure_documents([], source_type="youtube"),
                    ),
                    plan=plan,
                )
            except ProductLimitError:
                raise

            meta = brevio_service._prompt_metadata(
                brevio_generate.prompt_config, "youtube"
            )
            try:
                created_id = await brevio_service.create_summary_job(
                    str(_current_user),
                    status=JobStatus.QUEUED.value,
                    queued_at=datetime.now(timezone.utc),
                    idempotency_key=key,
                    job_payload=payload,
                    transcription_provider=decision.transcription_provider,
                    transcription_model=decision.transcription_model,
                    reasoning_effort=brevio_generate.prompt_config.reasoning_effort,
                    plan_snapshot=admission.snapshot.model_dump(mode="json"),
                    job_id=job_id,
                    **meta,
                )
            except Exception:
                await products.release_admission(job_id)
                raise
            if created_id != job_id:
                # Idempotency raced — release provisional admit for unused id.
                await products.release_admission(job_id)
                job_id = created_id

            user_service = await brevio_service._get_user_service()
            try:
                await brevio_service.reserve_credits_for_admitted_job(
                    user_id=str(_current_user),
                    job_id=job_id,
                    prompt_config=brevio_generate.prompt_config,
                    source_type="youtube",
                    files_data=None,
                )
            except ProviderError as credit_err:
                await products.release_admission(job_id)
                await user_service.fail_processing_results(job_id, credit_err)
                from core.brevio_api.models.errors.api_codes import CodedHTTPException

                raise CodedHTTPException(
                    status_code=402,
                    code=ApiErrorCode.CREDIT_LIMIT,
                    detail=str(credit_err.message),
                ) from credit_err
            await products.commit_admission(job_id)
            try:
                await brevio_service.schedule_or_dispatch(job_id)
            except Exception:
                import logging

                logging.getLogger(__name__).warning(
                    "event=schedule_youtube_failed job_id=%s", job_id, exc_info=True
                )
                raise

            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content={
                    **response.model_dump(exclude_none=True),
                    "task_id": None,
                    "folder_entry_id": job_id,
                    "job_id": job_id,
                },
                status_code=status.HTTP_202_ACCEPTED,
            )

        @self.router.get(
            "/download/{folder_entry_id}",
            description="Download summary file in specified format (.md, .docx, .pdf, .txt). Generates format on demand.",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Unauthorized"},
                403: {"description": "Forbidden"},
                404: {"description": "Not Found"},
            },
        )
        async def download_summary(
            folder_entry_id: str,
            format: str = Query("md"),
            result_index: Optional[int] = Query(None),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> FileResponse:
            (
                file_path,
                filename,
                media_type,
            ) = await brevio_service.download_summary_file(
                user_id=str(_current_user),
                folder_entry_id=folder_entry_id,
                requested_format=format,
                result_index=result_index,
            )

            return FileResponse(
                path=file_path,
                filename=filename,
                media_type=media_type,
            )


brevio_router = BrevioRoutes().router
