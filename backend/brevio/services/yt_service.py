import asyncio
import os
from typing import Any, Dict, List, Optional
import yt_dlp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pydantic import HttpUrl
import logging

class YTService:
    def __init__(self):
        self.executor = ProcessPoolExecutor(max_workers=4)
        self.download_executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def download(self, url: HttpUrl, dest_folder: str, mp3_id: Optional[str] = None) -> str:
        try:
            self.logger.info(f"Iniciando descarga de {url} a {dest_folder}")
            await asyncio.get_running_loop().run_in_executor(
                self.download_executor, self._sync_download, str(url), dest_folder, mp3_id
            )
            self.logger.info(f"Descarga exitosa de {url}")
            return "Descarga exitosa"
        except Exception as e:
            self.logger.error(f"Error en descarga de {url}: {str(e)}")
            return f"Error en descarga: {str(e)}"

    def _sync_download(self, url: str, dest_folder: str, mp3_id: Optional[str] = None):
        try:
            os.makedirs(dest_folder, exist_ok=True)
            
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
        
        
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Iniciando descarga con yt_dlp para {url}")
                ydl.download([url])
        except Exception as e:
            print(f"Error descargando el archivo {url}: {e}")

    async def process_video(self, video_id: int, url: str, dest_folder: str, mp3_id: Optional[str] = None):
        try:
            self.logger.info(f"Procesando video {video_id}...")
            await self.download(url, dest_folder, mp3_id)
            self.logger.info(f"Video {video_id} procesado con éxito.")
        except Exception as e:
            self.logger.error(f"Error procesando video {video_id}: {str(e)}")

    async def process_videos(self, videos: list):
        self.logger.info(f"Iniciando procesamiento de {len(videos)} videos")
        tasks = []
        for video in videos:
            video_id = video.get('id')
            url = video.get('url')
            dest_folder = video.get('dest_folder')
            mp3_id = video.get('mp3_id')
            tasks.append(self.process_video(video_id, url, dest_folder, mp3_id))
        
        await asyncio.gather(*tasks)
        self.logger.info("Procesamiento de videos completado")

    async def count_media_in_yt_playlist(self, url: str) -> int:
        try:
            self.logger.info(f"Contando medios en la lista de reproducción: {url}")
            result = await asyncio.get_running_loop().run_in_executor(
                self.executor, sync_extract_count, url
            )
            self.logger.info(f"Conteo exitoso: {result} elementos")
            return result
        except Exception as e:
            self.logger.error(f"Error contando medios en la lista de reproducción: {str(e)}")
            raise Exception(f"Error inesperado: {str(e)}")

    async def get_video_duration(self, url: str) -> Optional[float]:
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, sync_get_video_duration, url
        )

    async def get_media_duration(self, url: str) -> Dict[str, List[Dict[str, Any]]]:
        durations = []

        if await self.is_youtube_playlist(url):
            urls = await self.get_video_urls_from_playlist(url)
            if urls:
                durations_list = await asyncio.gather(*[self.get_video_duration(u) for u in urls])

                durations = [
                    {"url": u, "duration": d}
                    for u, d in zip(urls, durations_list)
                    if d is not None
                ]
        else:
            duration = await self.get_video_duration(url)
            if duration is not None:
                durations.append({"url": url, "duration": duration})
        return {"durations": durations}

    def _parse_duration(self, info):
        if 'duration' in info:
            return info['duration']
        return None

    async def is_youtube_playlist(self, url: str) -> bool:
        return "list=" in url

    async def get_video_urls_from_playlist(self, url: str) -> List[str]:
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                return [entry['url'] for entry in info['entries']]
            return []
        
def sync_extract_count(url: str) -> int:
    ydl_opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "force_generic_extractor": True,
        "ignoreerrors": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return len(info.get('entries', [])) if 'entries' in info else 1
    except Exception as e:
        print(f"Error extrayendo información de la lista de reproducción {url}: {e}")
        return 0



def sync_get_video_duration(url: str) -> Optional[float]:
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'ignoreerrors': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info.get('duration')
    except Exception as e:
        print(f"Error obteniendo duración de {url}: {e}")
        return None
