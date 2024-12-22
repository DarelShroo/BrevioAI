import subprocess

from ..constants.download_messages import DownloadMessages
class Download:
    def __init__(self, url, dest_folder):
        self._url = url
        self._dest_folder = dest_folder

    def download(self):
        try:
            command = [
                "yt-dlp",
                "-f",
                "bestaudio",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--output",
                f"{self._dest_folder}/%(autonumber)s.%(ext)s",
                self._url
            ]

            subprocess.run(command, check=True)
            return DownloadMessages.SUCCESS_DOWNLOAD

        except subprocess.CalledProcessError as e:
            return DownloadMessages.ERROR_DOWNLOADING.format(e)
        