import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.shared.models.user.data_result import DataResult


@pytest.mark.asyncio
async def test_directory_manager_pdf_and_docx_creation(tmp_path):
    directory_manager = DirectoryManager()
    md_file = tmp_path / "summary.md"
    md_file.write_text(
        "# Test Summary\n\n- Point 1\n- Point 2\n\nParagraph text here.",
        encoding="utf-8",
    )

    # Test DOCX creation
    docx_path = await directory_manager.create_docx_version(str(md_file))
    assert docx_path is not None
    assert os.path.exists(docx_path)
    assert docx_path.endswith(".docx")

    # Test PDF creation
    pdf_path = await directory_manager.create_pdf_version(str(md_file))
    assert pdf_path is not None
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")


@pytest.mark.asyncio
async def test_download_summary_file_on_the_fly(tmp_path):
    from core.brevio_api.services.brevio_service import BrevioService

    service = BrevioService()
    user_id = str(ObjectId())
    folder_entry_id = str(ObjectId())

    summary_dir = tmp_path / "summary_output"
    summary_dir.mkdir(parents=True, exist_ok=True)
    md_file = summary_dir / "summary.md"
    md_file.write_text("# Summary\n\nSample summary content", encoding="utf-8")

    # Use model_construct to bypass data/ path validation during tests
    result_item = DataResult.model_construct(download_location=str(summary_dir))

    folder_entry = FolderEntry(
        _id=ObjectId(folder_entry_id), user_id=ObjectId(user_id), results=[result_item]
    )

    mock_repo = AsyncMock()
    mock_repo.get_folder_entry_by_id.return_value = folder_entry

    with patch.object(service, "_get_user_service") as mock_get_user_service:
        mock_user_service = MagicMock()
        mock_user_service._folder_entry_repo = mock_repo
        mock_get_user_service.return_value = mock_user_service

        # 1. Download MD format
        path_md, filename_md, media_md = await service.download_summary_file(
            user_id=user_id,
            folder_entry_id=folder_entry_id,
            requested_format="md",
        )
        assert os.path.exists(path_md)
        assert media_md == "text/markdown"

        # 2. Download DOCX format (generated on the fly)
        path_docx, filename_docx, media_docx = await service.download_summary_file(
            user_id=user_id,
            folder_entry_id=folder_entry_id,
            requested_format="docx",
        )
        assert os.path.exists(path_docx)
        assert (
            media_docx
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # 3. Download PDF format (generated on the fly)
        path_pdf, filename_pdf, media_pdf = await service.download_summary_file(
            user_id=user_id,
            folder_entry_id=folder_entry_id,
            requested_format="pdf",
        )
        assert os.path.exists(path_pdf)
        assert media_pdf == "application/pdf"

        # 4. Download TXT format (generated on the fly)
        path_txt, filename_txt, media_txt = await service.download_summary_file(
            user_id=user_id,
            folder_entry_id=folder_entry_id,
            requested_format="txt",
        )
        assert os.path.exists(path_txt)
        assert media_txt == "text/plain"


@pytest.mark.asyncio
async def test_download_requires_result_index_for_multi_result_entries(tmp_path):
    from fastapi import HTTPException

    from core.brevio_api.services.brevio_service import BrevioService

    service = BrevioService()
    user_id = str(ObjectId())
    folder_entry_id = str(ObjectId())

    summary_dir_a = tmp_path / "a"
    summary_dir_b = tmp_path / "b"
    summary_dir_a.mkdir()
    summary_dir_b.mkdir()
    (summary_dir_a / "summary.md").write_text("# A", encoding="utf-8")
    (summary_dir_b / "summary.md").write_text("# B", encoding="utf-8")

    folder_entry = FolderEntry(
        _id=ObjectId(folder_entry_id),
        user_id=ObjectId(user_id),
        name="Mi carpeta",
        results=[
            DataResult.model_construct(
                name="a.pdf",
                status="COMPLETED",
                download_location=str(summary_dir_a),
            ),
            DataResult.model_construct(
                name="b.pdf",
                status="COMPLETED",
                download_location=str(summary_dir_b),
            ),
        ],
    )

    mock_repo = AsyncMock()
    mock_repo.get_folder_entry_by_id.return_value = folder_entry

    with patch.object(service, "_get_user_service") as mock_get_user_service:
        mock_user_service = MagicMock()
        mock_user_service._folder_entry_repo = mock_repo
        mock_get_user_service.return_value = mock_user_service

        with pytest.raises(HTTPException) as ambiguous:
            await service.download_summary_file(
                user_id=user_id,
                folder_entry_id=folder_entry_id,
                requested_format="md",
                result_index=None,
            )
        assert ambiguous.value.status_code == 422

        path_b, filename_b, _ = await service.download_summary_file(
            user_id=user_id,
            folder_entry_id=folder_entry_id,
            requested_format="md",
            result_index=1,
        )
        assert os.path.exists(path_b)
        assert path_b.startswith(str(summary_dir_b))
