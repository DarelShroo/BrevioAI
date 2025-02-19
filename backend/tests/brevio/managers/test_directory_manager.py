import pytest
from unittest.mock import MagicMock, mock_open, patch
import os
import shutil

from brevio.constants.directory_messages import DirectoryMessages
from brevio.managers.directory_manager import DirectoryManager

class TestDirectoryManager:
    """Pruebas para la clase DirectoryManager."""
    def test_create_folder_already_exists(self, mocker):
        """Debería retornar error si la carpeta ya existe."""
        mocker.patch("os.path.exists", return_value=True)
        dm = DirectoryManager()
        path = "/existing/folder"
        response = dm.createFolder(path)
        assert response.success is False
        assert response.message == DirectoryMessages.ERROR_FOLDER_ALREADY_EXISTS.format(path)

    def test_create_folder_success(self, mocker):
        """Debería crear la carpeta y retornar éxito."""
        mock_exists = mocker.patch("os.path.exists")
        mock_exists.side_effect = [False, True]
        mock_makedirs = mocker.patch("os.makedirs")
        dm = DirectoryManager()
        path = "/new/folder"
        response = dm.createFolder(path)
        mock_makedirs.assert_called_once_with(path, exist_ok=True)
        assert response.success is True
        assert response.message == DirectoryMessages.SUCCESS_FOLDER_CREATED.format(path)

    def test_create_folder_os_error(self, mocker):
        """Debería manejar errores del sistema al crear carpeta."""
        mocker.patch("os.path.exists", return_value=False)
        mocker.patch("os.makedirs", side_effect=OSError("Permiso denegado"))
        dm = DirectoryManager()
        path = "/invalid/folder"
        response = dm.createFolder(path)
        assert response.success is False
        assert "Permiso denegado" in response.message

    def test_create_folder_failure_raises_exception(self, mocker):
        """Debería lanzar excepción si la carpeta no se crea."""
        mock_exists = mocker.patch("os.path.exists")
        mock_exists.side_effect = [False, False]  # Simula fallo en creación
        mocker.patch("os.makedirs")
        dm = DirectoryManager()
        path = "/failed/folder"
        with pytest.raises(Exception, match="La carpeta no se creó"):
            dm.createFolder(path)

    def test_delete_folder_success(self, mocker):
        """Debería eliminar la carpeta correctamente."""
        mock_config = MagicMock(spec=Config)
        mock_config.dest_folder = "/test/folder"
        mocker.patch("os.path.exists", return_value=True)
        mock_rmtree = mocker.patch("shutil.rmtree")
        dm = DirectoryManager(config=mock_config)
        response = dm.deleteFolder()
        mock_rmtree.assert_called_once_with("/test/folder")
        assert response.success is True
        assert response.message == DirectoryMessages.SUCCES_DELETION.format("/test/folder")

    def test_delete_folder_not_found(self, mocker):
        """Debería retornar error si la carpeta no existe."""
        mock_config = MagicMock(spec=Config)
        mock_config.dest_folder = "/nonexistent/folder"
        mocker.patch("os.path.exists", return_value=False)
        dm = DirectoryManager(config=mock_config)
        response = dm.deleteFolder()
        assert response.success is False
        assert response.message == DirectoryMessages.ERROR_FOLDER_NOT_FOUND.format("/nonexistent/folder")

    def test_delete_folder_os_error(self, mocker):
        """Debería manejar errores al eliminar carpeta."""
        mock_config = MagicMock(spec=Config)
        mock_config.dest_folder = "/test/folder"
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("shutil.rmtree", side_effect=OSError("Error de permisos"))
        dm = DirectoryManager(config=mock_config)
        response = dm.deleteFolder()
        assert response.success is False
        assert "Error de permisos" in response.message

    def test_delete_file_success(self, mocker):
        """Debería eliminar el archivo correctamente."""
        mocker.patch("os.path.exists", return_value=True)
        mock_remove = mocker.patch("os.remove")
        dm = DirectoryManager()
        file_path = "/test/file.txt"
        response = dm.deleteFile(file_path)
        mock_remove.assert_called_once_with(file_path)
        assert response.success is True
        assert response.message == DirectoryMessages.SUCCESS_FILE_DELETED.format(file_path)

    def test_delete_file_not_found(self, mocker):
        """Debería retornar error si el archivo no existe."""
        mocker.patch("os.path.exists", return_value=False)
        dm = DirectoryManager()
        file_path = "/nonexistent/file.txt"
        response = dm.deleteFile(file_path)
        assert response.success is False
        assert response.message == DirectoryMessages.ERROR_FILE_NOT_FOUND.format(file_path)

    def test_delete_file_permission_error(self, mocker):
        """Debería manejar errores de permisos al eliminar archivo."""
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("os.remove", side_effect=PermissionError())
        dm = DirectoryManager()
        file_path = "/restricted/file.txt"
        response = dm.deleteFile(file_path)
        assert response.success is False
        assert response.message == DirectoryMessages.ERROR_PERMISSION_DENIED.format(file_path)

    def test_delete_file_os_error(self, mocker):
        """Debería manejar otros errores al eliminar archivo."""
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("os.remove", side_effect=OSError("Archivo en uso"))
        dm = DirectoryManager()
        file_path = "/inuse/file.txt"
        response = dm.deleteFile(file_path)
        assert response.success is False
        assert "Archivo en uso" in response.message

    def test_validate_paths_exists(self, mocker):
        """Debería retornar None si la ruta existe."""
        mocker.patch("os.path.exists", return_value=True)
        dm = DirectoryManager()
        assert dm.validate_paths("/valid/path") is None

    def test_validate_paths_not_exists(self, mocker):
        """Debería retornar error si la ruta no existe."""
        mocker.patch("os.path.exists", return_value=False)
        dm = DirectoryManager()
        path = "/invalid/path"
        response = dm.validate_paths(path)
        assert response.success is False
        assert response.message == SummaryMessages.ERROR_READING_TRANSCRIPTION.format(path)

    def test_read_transcription_success(self, mocker):
        """Debería leer el contenido del archivo correctamente."""
        mock_file = mock_open(read_data="Contenido de prueba")
        mocker.patch("builtins.open", mock_file)
        dm = DirectoryManager()
        path = "/transcription.txt"
        result = dm.read_transcription(path)
        assert result == "Contenido de prueba"

    def test_read_transcription_empty(self, mocker):
        """Debería retornar error si el archivo está vacío."""
        mock_file = mock_open(read_data="")
        mocker.patch("builtins.open", mock_file)
        dm = DirectoryManager()
        path = "/empty.txt"
        response = dm.read_transcription(path)
        assert response.success is False
        assert response.message == SummaryMessages.ERROR_EMPTY_TRANSCRIPTION

    def test_read_transcription_file_not_found(self, mocker):
        """Debería manejar error de archivo no encontrado."""
        mocker.patch("builtins.open", side_effect=FileNotFoundError())
        dm = DirectoryManager()
        path = "/nonexistent.txt"
        response = dm.read_transcription(path)
        assert response.success is False
        assert "Error reading transcription" in response.message

    def test_read_transcription_other_error(self, mocker):
        """Debería manejar otros errores al leer el archivo."""
        mocker.patch("builtins.open", side_effect=Exception("Error inesperado"))
        dm = DirectoryManager()
        path = "/error.txt"
        response = dm.read_transcription(path)
        assert response.success is False
        assert "Error inesperado" in response.message

    def test_write_summary_success(self, mocker):
        """Debería escribir el resumen en el archivo correctamente."""
        mock_file = mock_open()
        mocker.patch("builtins.open", mock_file)
        dm = DirectoryManager()
        summary = "Resumen de prueba"
        path = "/summary.txt"
        dm.write_summary(summary, path)
        mock_file.assert_called_once_with(path, "w")
        handle = mock_file()
        handle.write.assert_called_once_with(summary)