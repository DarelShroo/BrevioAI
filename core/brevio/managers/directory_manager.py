import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generator, Optional

if TYPE_CHECKING:
    from core.shared.models.history_token_model import HistoryTokenModel
try:
    import aiofiles
except ImportError:
    raise ImportError("aiofiles is not installed")
import markdown
from bs4 import BeautifulSoup, Tag
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from core.brevio.constants.directory_messages import DirectoryMessages
from core.brevio.constants.summary_messages import SummaryMessages
from core.brevio.models.config_model import ConfigModel
from core.brevio.models.response_model import FolderResponse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@dataclass
class ExtractionReport:
    extractor: str = "generation"
    pages_total: int = 0
    pages_extracted: int = 0
    pages_empty: int = 0
    pages_ocr: int = 0
    pages_ocr_failed: int = 0
    pages_dropped: int = 0
    characters_extracted: int = 0
    tokens_extracted: int = 0
    notes: list[str] = field(default_factory=list)


class DirectoryManager:
    def __init__(self, config: Optional[ConfigModel] = None) -> None:
        logger.info("DirectoryManager initialized")
        self._config: Optional[ConfigModel] = config if config else None
        self.last_extraction_report = ExtractionReport()

    async def createFolder(self, path: Optional[str] = None) -> FolderResponse:
        if path is None:
            raise ValueError("El path no puede ser None.")
        try:
            await asyncio.to_thread(__import__("os").makedirs, path, exist_ok=True)
            exists = await asyncio.to_thread(__import__("os").path.exists, path)
            if exists:
                return FolderResponse(
                    success=True,
                    message=DirectoryMessages.SUCCESS_FOLDER_CREATED.format(path),
                )
            raise RuntimeError("La carpeta no se creó, la ruta puede ser incorrecta.")
        except OSError as e:
            raise OSError(f"Error al crear la carpeta: {e}")
        except Exception as e:
            raise RuntimeError(f"Error inesperado al crear la carpeta: {str(e)}") from e

    async def deleteFolder(self) -> FolderResponse:
        folder: str = self._config.dest_folder if self._config else ""
        try:
            exists = await asyncio.to_thread(__import__("os").path.exists, folder)
            if not exists:
                raise FileNotFoundError(
                    DirectoryMessages.ERROR_FOLDER_NOT_FOUND.format(folder)
                )
            await asyncio.to_thread(__import__("shutil").rmtree, folder)
            return FolderResponse(
                success=True,
                message=DirectoryMessages.SUCCES_DELETION.format(folder),
            )
        except OSError as e:
            raise OSError(f"Error al eliminar la carpeta: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(
                f"Error inesperado al eliminar la carpeta: {str(e)}"
            ) from e

    async def deleteFile(self, file_path: str) -> FolderResponse:
        try:
            exists = await asyncio.to_thread(__import__("os").path.exists, file_path)
            if not exists:
                raise FileNotFoundError(
                    DirectoryMessages.ERROR_FILE_NOT_FOUND.format(file_path)
                )
            await asyncio.to_thread(__import__("os").remove, file_path)
            return FolderResponse(
                success=True,
                message=DirectoryMessages.SUCCESS_FILE_DELETED.format(file_path),
            )
        except PermissionError:
            raise PermissionError(
                DirectoryMessages.ERROR_PERMISSION_DENIED.format(file_path)
            )
        except OSError as e:
            raise OSError(f"Error al eliminar el archivo: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(
                f"Error inesperado al eliminar el archivo: {str(e)}"
            ) from e

    async def validate_paths(self, transcription_path: str) -> None:
        exists = await asyncio.to_thread(
            __import__("os").path.exists, transcription_path
        )
        if not exists:
            raise FileNotFoundError(
                SummaryMessages.ERROR_READING_TRANSCRIPTION.format(transcription_path)
            )

    async def read_transcription(self, transcription_path: str) -> str:
        try:
            async with aiofiles.open(transcription_path, "r", encoding="utf-8") as f:
                transcription = await f.read()

            if not transcription.strip():
                raise ValueError(SummaryMessages.ERROR_EMPTY_TRANSCRIPTION)

            logger.info(f"Transcripción leída: {len(transcription)} caracteres")
            return transcription
        except FileNotFoundError:
            raise FileNotFoundError(
                f"El archivo de transcripción no se encontró en la ruta: {transcription_path}"
            )
        except ValueError as e:
            raise ValueError(f"Transcripción vacía: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error al leer la transcripción: {str(e)}") from e

    async def read_pdf_in_pieces(
        self,
        path: str,
        history_token_model: Optional["HistoryTokenModel"] = None,
        pieces_for_page: int = 1,
    ) -> AsyncGenerator[str, None]:
        def blocking_read() -> list[str]:
            import re

            import pypdf
            import tiktoken

            lector = pypdf.PdfReader(path)
            if getattr(lector, "is_encrypted", False):
                try:
                    decrypted = lector.decrypt("")
                    if not decrypted:
                        raise ValueError("El archivo PDF está protegido con contraseña o encriptado.")
                except Exception:
                    raise ValueError("El archivo PDF está protegido con contraseña o encriptado.")

            total_paginas = len(lector.pages)
            if total_paginas == 0:
                raise ValueError("El archivo PDF está vacío o no contiene páginas.")
            logger.info(f"PDF tiene {total_paginas} páginas")
            encoder = tiktoken.encoding_for_model("gpt-4")
            report = ExtractionReport(
                extractor="generation",
                pages_total=total_paginas,
            )

            fragments = []
            for i, pagina in enumerate(lector.pages):
                page_no = i + 1
                texto = pagina.extract_text() or ""
                texto_limpio = re.sub(r"\n+", "\n", texto.strip())
                used_ocr = False

                if not texto_limpio:
                    report.pages_empty += 1
                    try:
                        import pytesseract
                        from pdf2image import convert_from_path

                        logger.debug(f"Intentando OCR en la página {page_no}")
                        images = convert_from_path(
                            path, first_page=page_no, last_page=page_no
                        )
                        if images:
                            texto = pytesseract.image_to_string(
                                images[0], lang="spa+eng"
                            )
                            texto_limpio = re.sub(r"\n+", "\n", texto.strip())
                            used_ocr = True
                            if texto_limpio:
                                report.pages_ocr += 1
                            else:
                                report.pages_ocr_failed += 1
                                report.notes.append(
                                    f"page {page_no}: OCR returned empty"
                                )
                    except Exception as e:
                        report.pages_ocr_failed += 1
                        report.notes.append(f"page {page_no}: OCR failed ({e})")
                        logger.warning(f"OCR falló en la página {page_no}: {e}")

                if not texto_limpio:
                    marker = (
                        f"[página {page_no}: texto no extraíble"
                        + (
                            "; OCR falló"
                            if report.notes and str(page_no) in report.notes[-1]
                            else ""
                        )
                        + "]"
                    )
                    fragments.append(marker)
                    report.pages_dropped += 1
                    report.pages_extracted += 1
                    report.characters_extracted += len(marker)
                    if history_token_model:
                        history_token_model.num_chars_file += len(marker)
                        history_token_model.num_tokens_file += len(
                            encoder.encode(marker)
                        )
                    continue

                if history_token_model:
                    history_token_model.num_chars_file += len(texto_limpio)
                    history_token_model.num_tokens_file += len(
                        encoder.encode(texto_limpio)
                    )
                fragments.append(texto_limpio)
                report.pages_extracted += 1
                report.characters_extracted += len(texto_limpio)
                if used_ocr:
                    logger.info("OCR recovered page %s", page_no)

            report.tokens_extracted = (
                history_token_model.num_tokens_file if history_token_model else 0
            )
            self.last_extraction_report = report
            logger.info(
                "PDF extraction report extractor=%s pages_total=%s pages_extracted=%s "
                "pages_empty=%s pages_ocr=%s pages_ocr_failed=%s pages_dropped=%s "
                "characters_extracted=%s tokens_extracted=%s",
                report.extractor,
                report.pages_total,
                report.pages_extracted,
                report.pages_empty,
                report.pages_ocr,
                report.pages_ocr_failed,
                report.pages_dropped,
                report.characters_extracted,
                report.tokens_extracted,
            )
            return fragments

        fragments = await asyncio.to_thread(blocking_read)
        for fragment in fragments:
            yield fragment

    async def read_pdf(
        self, pdf_path: str, history_token_model: Optional["HistoryTokenModel"]
    ) -> list[str]:
        fragments = []
        async for fragment in self.read_pdf_in_pieces(pdf_path, history_token_model):
            fragments.append(fragment)

        if not fragments:
            raise ValueError("El PDF está vacío o no se pudo extraer texto")

        has_substantive = any(
            not (f.startswith("[página ") and "texto no extraíble" in f)
            for f in fragments
        )
        if not has_substantive:
            raise ValueError("El archivo PDF no contiene texto extraíble o procesable.")

        logger.info(
            f"PDF leído: {len(fragments)} fragmentos, Total caracteres: {sum(len(f) for f in fragments)} "
            f"(estimation vs generation: generation keeps pages_total="
            f"{self.last_extraction_report.pages_total}, pages_extracted="
            f"{self.last_extraction_report.pages_extracted}, pages_empty="
            f"{self.last_extraction_report.pages_empty})"
        )
        return fragments

    async def read_docx(self, docx_path: str) -> str:
        def blocking_read() -> str:
            doc = Document(docx_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            total_paragraphs = len(paragraphs)
            logger.info(f"DOCX tiene {total_paragraphs} párrafos")
            text = "\n".join(paragraphs).strip()
            if not text:
                raise ValueError("El archivo DOCX está vacío o no contiene texto legible.")
            return text

        return await asyncio.to_thread(blocking_read)

    async def write_summary(self, summary: str, summary_path: str) -> None:
        try:
            async with aiofiles.open(summary_path, "a", encoding="utf-8") as f:
                await f.write(summary + "\n")
            logger.info(f"Resumen escrito en {summary_path}")
        except Exception as e:
            raise RuntimeError(
                f"Error al escribir el resumen en {summary_path}: {str(e)}"
            ) from e

    def _add_toc(self, doc: DocumentType) -> None:
        logger.debug("Adding table of contents to DOCX")
        doc.add_heading("Índice", level=1)
        paragraph = doc.add_paragraph()
        run = paragraph.add_run()
        fld_char = OxmlElement("w:fldChar")
        fld_char.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_char)
        instr_text = OxmlElement("w:instrText")
        instr_text.text = 'TOC \\o "1-3" \\h \\z \\u'
        run._r.append(instr_text)
        fld_char = OxmlElement("w:fldChar")
        fld_char.set(qn("w:fldCharType"), "end")
        run._r.append(fld_char)
        doc.add_paragraph(
            "Nota: Haga clic derecho en el índice y seleccione 'Actualizar campo' al abrir en Word."
        )

    async def create_docx_version(self, md_path: Optional[str]) -> Optional[str]:
        if md_path is None:
            logger.error("No path provided for DOCX conversion")
            return None

        docx_path = md_path.replace(".md", ".docx")

        async def blocking_create_docx() -> None:
            async with aiofiles.open(md_path, "r", encoding="utf-8") as f:
                md_content = await f.read()

            doc = Document()
            self._add_toc(doc)
            doc.add_page_break()

            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, "html.parser")

            for element in soup:
                if isinstance(element, Tag):
                    if element.name in ["h1", "h2", "h3"]:
                        level = int(element.name[1])
                        heading = doc.add_heading(
                            element.get_text().strip(), level=level
                        )
                        heading.style = f"Heading {level}"
                    elif element.name == "p":
                        doc.add_paragraph(element.get_text().strip())
                    elif element.name == "ul":
                        for item in element.find_all("li", recursive=False):
                            doc.add_paragraph(
                                item.get_text().strip(), style="List Bullet"
                            )
                    elif element.name == "ol":
                        counter = 1
                        for item in element.find_all("li", recursive=False):
                            text = item.get_text().strip()
                            doc.add_paragraph(f"{counter}. {text}", style="List Number")
                            counter += 1

            doc.save(docx_path)

        await blocking_create_docx()

        logger.info(f"DOCX version created: {docx_path}")
        return docx_path

    async def create_pdf_version(
        self,
        md_path: Optional[str],
        document_id: Optional[str] = None,
    ) -> Optional[str]:
        if md_path is None:
            logger.error("No path provided for PDF conversion")
            return None

        from core.brevio.services.pdf_export import export_markdown_file_to_pdf

        pdf_path = await asyncio.to_thread(
            export_markdown_file_to_pdf,
            md_path,
            document_id=document_id,
        )
        logger.info("PDF version created: %s", pdf_path)
        return pdf_path
