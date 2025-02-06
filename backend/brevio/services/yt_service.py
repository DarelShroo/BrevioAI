import subprocess
from ..constants.download_messages import DownloadMessages
from datetime import timedelta
from ..utils.utils import parse_duration

class YTService:
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

    def count_media_in_yt_playlist(url: str):
        command = ["yt-dlp", "--get-id", "--flat-playlist", url]
        try:
            result = subprocess.run(
                command, check=True, stdout=subprocess.PIPE, text=True)
            video_ids = result.stdout.strip().split("\n")
            return len(video_ids)
        except subprocess.CalledProcessError as e:
            print("Error al ejecutar yt-dlp:", e)
            return 0

    def get_media_duration(url: str):
        command = ["yt-dlp", "--get-duration", "--skip-download", url]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                print("El comando falló.")
                return None

            duration = result.stdout.strip()
            parts = list(map(int, duration.split(":")))

            if len(parts) == 3:
                hours, minutes, seconds = parts
            elif len(parts) == 2:
                hours = 0
                minutes, seconds = parts
            else:
                print("Formato de duración inesperado:", duration)
                return None

            return hours * 60 + minutes + (seconds / 60)
        except Exception as e:
            print("Error:", e)
            return None
