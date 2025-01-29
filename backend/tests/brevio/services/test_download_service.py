from backend.brevio.services.yt_service import YTService
from backend.brevio.managers.directory_manager import DirectoryManager
def test_download_service():
    url = "https://www.youtube.com/shorts/YZmQRqtDluc"
    dest_folder = "./download_test"
    manager = DirectoryManager()
    
    manager.deleteFolder(dest_folder)
    download = YTService(url, dest_folder)
    result = download.download()

    manager_result = manager.validate_paths(dest_folder)

    assert result == "Download completed successfully."
    assert manager_result != False