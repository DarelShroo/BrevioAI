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
            if os.path.exists(path):
                return FolderResponse(
                    False, 
                    DirectoryMessages.ERROR_FOLDER_ALREADY_EXISTS.format(path),
                )
            else:
                os.makedirs(path, exist_ok=True)
                if os.path.exists(path):
                    return FolderResponse(
                        True, 
                        DirectoryMessages.SUCCESS_FOLDER_CREATED.format(path)
                    )
                    
                print("No se ha creado la carpeta, revisa si la ruta es válida.")
                raise Exception("La carpeta no se creó, la ruta puede ser incorrecta.")
        except OSError as e:
            return FolderResponse(
                False, 
                DirectoryMessages.ERROR_FAILED_TO_CREATE_FOLDER.format(path, e)
            
        )
    def deleteFolder(self):
        folder = self._config.dest_folder
        try:
            if not os.path.exists(folder):
                return FolderResponse(
                    False, 
                    DirectoryMessages.ERROR_FOLDER_NOT_FOUND.format(folder)
                )
            else:
                shutil.rmtree(folder)
                return FolderResponse(
                    True, 
                    DirectoryMessages.SUCCES_DELETION.format(folder)
                )
        except OSError as e:
            return FolderResponse(
                False, 
                DirectoryMessages.ERROR_DELETION_FAILED.format(folder, e)
            )

    def deleteFile(self, file_path):
        try:
            if not os.path.exists(file_path):
                return FolderResponse(
                    False, 
                    DirectoryMessages.ERROR_FILE_NOT_FOUND.format(file_path)
                )
            else:
                os.remove(file_path)
                return FolderResponse(
                    True, 
                    DirectoryMessages.SUCCESS_FILE_DELETED.format(file_path)
                )
        except PermissionError:
            return FolderResponse(
                False, 
                DirectoryMessages.ERROR_PERMISSION_DENIED.format(file_path)
            )
        except OSError as e:
            return FolderResponse(
                False, 
                DirectoryMessages.ERROR_DELETION_FAILED.format(file_path, e)
            )

    def validate_paths(self, transcription_path):
        if not os.path.exists(transcription_path):
            return FolderResponse(
                False, 
                SummaryMessages.ERROR_READING_TRANSCRIPTION.format(transcription_path)
            )

    def read_transcription(self, transcription_path):
        try:
            with open(transcription_path, "r") as file:
                transcription = file.read()

            if not transcription.strip():
                return FolderResponse(
                    False, 
                    SummaryMessages.ERROR_EMPTY_TRANSCRIPTION
                )

            return transcription

        except Exception as e:
            return FolderResponse(
                False, 
                f"Error reading transcription: {str(e)}"
            )
    def read_pdf(self, pdf_path):
        return self._pdf_service.read_pdf_in_pieces(pdf_path)
    
    def read_docx(self, docx_path):
        return self.read_docx_in_pieces(docx_path)
    
    def read_docx_in_pieces(self, docx_path, paragraphs_per_chunk=50):
        try:
            doc = Document(docx_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            total_paragraphs = len(paragraphs)

            for i in range(0, total_paragraphs, paragraphs_per_chunk):
                chunk_text = "\n".join(paragraphs[i:i + paragraphs_per_chunk])
                yield chunk_text
        except Exception as e:
            #logger.error(f"Error reading DOCX in pieces: {e}", exc_info=True)
            raise

    def write_summary(self, summary, summary_path):
        try:
            with open(summary_path, "a", encoding="utf-8") as file:
                file.write(summary)
                file.write("\n")
        except Exception as e:
            #logger.error(f"Error writing summary to {summary_path}: {e}", exc_info=True)
            raise

