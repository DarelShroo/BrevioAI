import os
import shutil
from docx import Document
from backend.brevio.services.pdf_service import PdfService
from ..constants.directory_messages import DirectoryMessages
from ..constants.summary_messages import SummaryMessages
from ..models.config_model import ConfigModel as Config
from ..models.response_model import FolderResponse

class DirectoryManager:
    def __init__(self, config: Config = None):
        self._config = config if config else None
        self._pdf_service = PdfService()

    def createFolder(self, path=None):
        try:
            os.makedirs(path, exist_ok=True)
            if os.path.exists(path):
                return FolderResponse(
                    True, 
                    DirectoryMessages.SUCCESS_FOLDER_CREATED.format(path)
                )
            raise RuntimeError("La carpeta no se creó, la ruta puede ser incorrecta.")
        except OSError as e:
            raise OSError(f"Error al crear la carpeta: {e}")
        except Exception as e:
            raise RuntimeError(f"Error inesperado al crear la carpeta: {str(e)}") from e
        
    def deleteFolder(self):
        folder = self._config.dest_folder
        try:
            if not os.path.exists(folder):
                raise FileNotFoundError(DirectoryMessages.ERROR_FOLDER_NOT_FOUND.format(folder))
            else:
                shutil.rmtree(folder)
                return FolderResponse(
                    True, 
                    DirectoryMessages.SUCCESS_DELETION.format(folder)
                )
        except OSError as e:
            raise OSError(f"Error al eliminar la carpeta: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Error inesperado al eliminar la carpeta: {str(e)}") from e

    def deleteFile(self, file_path):
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(DirectoryMessages.ERROR_FILE_NOT_FOUND.format(file_path))
            else:
                os.remove(file_path)
                return FolderResponse(
                    True, 
                    DirectoryMessages.SUCCESS_FILE_DELETED.format(file_path)
                )
        except PermissionError:
            raise PermissionError(DirectoryMessages.ERROR_PERMISSION_DENIED.format(file_path))
        except OSError as e:
            raise OSError(f"Error al eliminar el archivo: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Error inesperado al eliminar el archivo: {str(e)}") from e

    def validate_paths(self, transcription_path):
        if not os.path.exists(transcription_path):
            raise FileNotFoundError(SummaryMessages.ERROR_READING_TRANSCRIPTION.format(transcription_path))

    def read_transcription(self, transcription_path):
        try:
            with open(transcription_path, "r") as file:
                transcription = file.read()

            if not transcription.strip():
                raise ValueError(SummaryMessages.ERROR_EMPTY_TRANSCRIPTION)

            return transcription

        except FileNotFoundError:
            raise FileNotFoundError(f"El archivo de transcripción no se encontró en la ruta: {transcription_path}")
        except ValueError as e:
            raise ValueError(f"Transcripción vacía: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error al leer la transcripción: {str(e)}") from e

    def read_pdf(self, pdf_path):
        try:
            return self._pdf_service.read_pdf_in_pieces(pdf_path)
        except Exception as e:
            raise RuntimeError(f"Error al leer el archivo PDF: {str(e)}") from e
    
    def read_docx(self, docx_path):
        try:
            return self.read_docx_in_pieces(docx_path)
        except Exception as e:
            raise RuntimeError(f"Error al leer el archivo DOCX: {str(e)}") from e
    
    def read_docx_in_pieces(self, docx_path, paragraphs_per_chunk=50):
        try:
            doc = Document(docx_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            total_paragraphs = len(paragraphs)

            for i in range(0, total_paragraphs, paragraphs_per_chunk):
                chunk_text = "\n".join(paragraphs[i:i + paragraphs_per_chunk])
                yield chunk_text
        except Exception as e:
            raise RuntimeError(f"Error al leer el archivo DOCX en trozos: {str(e)}") from e

    def write_summary(self, summary, summary_path):
        try:
            with open(summary_path, "a", encoding="utf-8") as file:
                file.write(summary)
                file.write("\n")
        except Exception as e:
            raise RuntimeError(f"Error al escribir el resumen en {summary_path}: {str(e)}") from e
