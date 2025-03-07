import asyncio
import os
from typing import Optional
import yt_dlp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pydantic import HttpUrl

class YTService:
    def __init__(self):
        self.executor = ProcessPoolExecutor(max_workers=4)  # Limita el número de procesos concurrentes
        self.download_executor = ThreadPoolExecutor(max_workers=4)  # Limita el número de hilos concurrentes

    async def download(self, url: HttpUrl, dest_folder: str, mp3_id: Optional[str] = None) -> str:
        try:
            await asyncio.get_running_loop().run_in_executor(
                self.download_executor, self._sync_download, str(url), dest_folder, mp3_id
            )
            return "Descarga exitosa"
        except Exception as e:
            return f"Error en descarga: {str(e)}"

    def _sync_download(self, url: str, dest_folder: str, mp3_id: Optional[str] = None):
        os.makedirs(dest_folder, exist_ok=True)  # Crea las carpetas si no existen
        
        outtmpl = f"{dest_folder}/{mp3_id}.%(ext)s" if mp3_id else f"{dest_folder}/%(autonumber)s.%(ext)s"

        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': outtmpl,
            'quiet': True,
            'ignoreerrors': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Error descargando el archivo {url}: {e}")

    async def process_video(self, video_id: int, url: str, dest_folder: str, mp3_id: Optional[str] = None):
        try:
            print(f"Procesando video {video_id}...")
            await self.download(url, dest_folder, mp3_id)
            print(f"Video {video_id} procesado con éxito.")
        except Exception as e:
            print(f"Error procesando video {video_id}: {str(e)}")

    async def process_videos(self, videos: list):
        tasks = []
        for video in videos:
            video_id = video.get('id')
            url = video.get('url')
            dest_folder = video.get('dest_folder')
            mp3_id = video.get('mp3_id')
            tasks.append(self.process_video(video_id, url, dest_folder, mp3_id))
        
        await asyncio.gather(*tasks)