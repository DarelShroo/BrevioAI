import asyncio
import io
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple

import pypdf

from core.brevio.managers.directory_manager import DirectoryManager


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    extension: str
    text: str
    extraction_status: str
    pages_total: int = 0
    pages_with_text: int = 0
    pages_without_text: int = 0
    extractor: str = "estimation"


class DocumentExtractionService:
    def __init__(self) -> None:
        self._directory_manager = DirectoryManager()

    async def extract_documents(
        self,
        files_data: List[Tuple[str, bytes]],
    ) -> List[ExtractedDocument]:
        tasks = [
            self._extract_single_document(filename, content)
            for filename, content in files_data
        ]
        return await asyncio.gather(*tasks)

    async def _extract_single_document(
        self,
        filename: str,
        content: bytes,
    ) -> ExtractedDocument:
        extension = Path(filename).suffix.lower().lstrip(".")

        if extension == "pdf":
            return await self._extract_pdf(filename, content)

        if extension == "docx":
            return await self._extract_docx(filename, content)

        if extension == "txt":
            text = content.decode("utf-8", errors="ignore")
            return ExtractedDocument(
                filename=filename,
                extension=extension,
                text=self._normalize_text(text),
                extraction_status="complete" if text.strip() else "empty",
            )

        if extension == "md":
            text = content.decode("utf-8", errors="ignore")
            return ExtractedDocument(
                filename=filename,
                extension=extension,
                text=self._normalize_text(text),
                extraction_status="complete" if text.strip() else "empty",
            )

        return ExtractedDocument(
            filename=filename,
            extension=extension,
            text="",
            extraction_status="unsupported",
        )

    async def _extract_docx(self, filename: str, content: bytes) -> ExtractedDocument:
        with TemporaryDirectory(prefix="brevio-estimate-") as temp_dir:
            temp_path = Path(temp_dir) / filename
            await asyncio.to_thread(temp_path.write_bytes, content)
            text = await self._directory_manager.read_docx(str(temp_path))

        normalized_text = self._normalize_text(text)
        return ExtractedDocument(
            filename=filename,
            extension="docx",
            text=normalized_text,
            extraction_status="complete" if normalized_text else "empty",
        )

    async def _extract_pdf(self, filename: str, content: bytes) -> ExtractedDocument:
        reader = await asyncio.to_thread(self._load_pdf_reader, content)
        pages_total = len(reader.pages)

        fragments: List[str] = []
        pages_with_text = 0
        pages_without_text = 0
        scanned_pages = 0

        for page in reader.pages:
            text = page.extract_text() or ""
            normalized = self._normalize_text(text)
            if normalized:
                pages_with_text += 1
                fragments.append(normalized)
            else:
                pages_without_text += 1
                if self._page_looks_scanned(page):
                    scanned_pages += 1

        full_text = "\n".join(fragments).strip()
        status = self._get_pdf_status(
            pages_total,
            pages_with_text,
            pages_without_text,
            scanned_pages,
        )

        return ExtractedDocument(
            filename=filename,
            extension="pdf",
            text=full_text,
            extraction_status=status,
            pages_total=pages_total,
            pages_with_text=pages_with_text,
            pages_without_text=pages_without_text,
        )

    def _load_pdf_reader(self, content: bytes) -> pypdf.PdfReader:
        return pypdf.PdfReader(io.BytesIO(content))

    def _get_pdf_status(
        self,
        pages_total: int,
        pages_with_text: int,
        pages_without_text: int,
        scanned_pages: int,
    ) -> str:
        if pages_total == 0:
            return "empty"

        if pages_with_text == 0:
            return "ocr_required" if scanned_pages > 0 else "empty"

        if pages_without_text > 0:
            return "partial"

        return "complete"

    def _page_looks_scanned(self, page: object) -> bool:
        try:
            resources = getattr(page, "get", lambda *_: None)("/Resources")
            if resources is None:
                return False

            xobject = resources.get("/XObject") if hasattr(resources, "get") else None
            if xobject is None:
                return False

            keys = list(xobject.keys()) if hasattr(xobject, "keys") else []
            return bool(keys)
        except Exception:
            return False

    def _normalize_text(self, text: str) -> str:
        no_cr = text.replace("\r\n", "\n").replace("\r", "\n")
        no_extra_blank_lines = re.sub(r"\n{3,}", "\n\n", no_cr)
        no_extra_spaces = re.sub(r"[ \t]+", " ", no_extra_blank_lines)
        return no_extra_spaces.strip()
