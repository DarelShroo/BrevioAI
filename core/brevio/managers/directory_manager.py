import logging
import os
import re
import shutil
from typing import Generator, Iterator, Optional

import pypdf
import tiktoken
from docx import Document

from core.brevio.constants.directory_messages import DirectoryMessages
from core.brevio.constants.summary_messages import SummaryMessages
from core.brevio.models.config_model import ConfigModel
from core.brevio.models.response_model import FolderResponse
from core.shared.models.history_token_model import HistoryTokenModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class DirectoryManager:
    def __init__(self, config: Optional[ConfigModel] = None) -> None:
        logger.info("DirectoryManager initialized")
        self._config: Optional[ConfigModel] = config if config else None

    def createFolder(self, path: Optional[str] = None) -> FolderResponse:
        if path is None:
            raise ValueError("El path no puede ser None.")
        try:
            os.makedirs(path, exist_ok=True)
            if os.path.exists(path):
                return FolderResponse(
                    success=True,
                    message=DirectoryMessages.SUCCESS_FOLDER_CREATED.format(path),
                )
            raise RuntimeError("La carpeta no se creó, la ruta puede ser incorrecta.")
        except OSError as e:
            raise OSError(f"Error al crear la carpeta: {e}")
        except Exception as e:
            raise RuntimeError(f"Error inesperado al crear la carpeta: {str(e)}") from e

    def deleteFolder(self) -> FolderResponse:
        folder: str = self._config.dest_folder if self._config else ""
        try:
            if not os.path.exists(folder):
                raise FileNotFoundError(
                    DirectoryMessages.ERROR_FOLDER_NOT_FOUND.format(folder)
                )
            else:
                shutil.rmtree(folder)
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

    def deleteFile(self, file_path: str) -> FolderResponse:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    DirectoryMessages.ERROR_FILE_NOT_FOUND.format(file_path)
                )
            else:
                os.remove(file_path)
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
        if not os.path.exists(transcription_path):
            raise FileNotFoundError(
                SummaryMessages.ERROR_READING_TRANSCRIPTION.format(transcription_path)
            )

    def read_transcription(self, transcription_path: str) -> str:
        try:
            with open(transcription_path, "r", encoding="utf-8") as file:
                transcription = file.read()

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

    def read_pdf_in_pieces(
        self,
        path: str,
        history_token_model: Optional[HistoryTokenModel],
        pieces_for_page: int = 1,
    ) -> Iterator[str]:
        try:
            with open(path, "rb") as archivo:
                lector = pypdf.PdfReader(archivo)
                total_paginas = len(lector.pages)
                logger.info(f"PDF tiene {total_paginas} páginas")

                for i in range(total_paginas):
                    pagina = lector.pages[i]
                    texto = pagina.extract_text() or ""
                    texto_limpio = re.sub(r"\n+", "\n", texto.strip())
                    if texto_limpio:
                        if history_token_model:
                            history_token_model.num_chars_file += len(texto_limpio)
                            encoder = tiktoken.encoding_for_model("gpt-4")
                            tokens = len(encoder.encode(texto_limpio))
                            history_token_model.num_tokens_file += tokens
                        logger.debug(
                            f"Página {i+1}: {len(texto_limpio)} caracteres, Texto: {texto_limpio[:100]}..."
                        )
                        yield texto_limpio
                    else:
                        logger.debug(f"Página {i+1} vacía")
        except Exception as e:
            raise RuntimeError(f"Error al leer el PDF en trozos: {str(e)}") from e

    def read_pdf(
        self, pdf_path: str, history_token_model: Optional[HistoryTokenModel]
    ) -> list[str]:
        try:
            fragments = list(self.read_pdf_in_pieces(pdf_path, history_token_model))
            if not fragments:
                raise ValueError("El PDF está vacío o no se pudo extraer texto")
            logger.info(
                f"PDF leído: {len(fragments)} fragmentos, Total caracteres: {sum(len(f) for f in fragments)}"
            )
            return fragments
        except Exception as e:
            raise RuntimeError(f"Error al leer el archivo PDF: {str(e)}") from e

    def read_docx(self, docx_path: str) -> Generator[str, None, None]:
        try:
            return self.read_docx_in_pieces(docx_path)
        except Exception as e:
            raise RuntimeError(f"Error al leer el archivo DOCX: {str(e)}") from e

    def read_docx_in_pieces(
        self, docx_path: str, paragraphs_per_chunk: int = 50
    ) -> Generator[str, None, None]:
        try:
            doc = Document(docx_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            total_paragraphs = len(paragraphs)
            logger.info(f"DOCX tiene {total_paragraphs} párrafos")

            for i in range(0, total_paragraphs, paragraphs_per_chunk):
                chunk_text = "".join(paragraphs[i : i + paragraphs_per_chunk])
                logger.debug(
                    f"Chunk {i//paragraphs_per_chunk+1}: {len(chunk_text)} caracteres"
                )
                yield chunk_text
        except Exception as e:
            raise RuntimeError(
                f"Error al leer el archivo DOCX en trozos: {str(e)}"
            ) from e

    def write_summary(self, summary: str, summary_path: str) -> None:
        try:
            with open(summary_path, "a", encoding="utf-8") as file:
                file.write(summary)
                file.write("\n")
            logger.info(f"Resumen escrito en {summary_path}")
        except Exception as e:
            raise RuntimeError(
                f"Error al escribir el resumen en {summary_path}: {str(e)}"
            ) from e
