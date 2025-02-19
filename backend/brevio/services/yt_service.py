import yt_dlp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any

class YTService:
    def __init__(self):
        self.executor = ThreadPoolExecutor()

    # Métodos asíncronos que envuelven operaciones bloqueantes

    async def is_youtube_playlist(self, url: str) -> bool:
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, self._sync_is_youtube_playlist, url
        )

    def _sync_is_youtube_playlist(self, url: str) -> bool:
        try:
            result = self._extract_info(url)
            return 'entries' in result and isinstance(result['entries'], list)
        except Exception as e:
            print(f"Error verificando URL {url}: {e}")
            return False

    async def get_video_urls_from_playlist(self, playlist_url: str) -> List[str]:
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, self._sync_get_video_urls_from_playlist, playlist_url
        )

    def _sync_get_video_urls_from_playlist(self, playlist_url: str) -> List[str]:
        try:
            result = self._extract_playlist_info(playlist_url)
            return self._process_playlist_entries(result)
        except Exception as e:
            print(f"Error obteniendo videos de {playlist_url}: {e}")
            return []

    async def count_media_in_yt_playlist(self, url: str) -> int:
        try:
            return await asyncio.get_running_loop().run_in_executor(
                self.executor, self._sync_extract_count, url
            )
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return 0

    def _sync_extract_count(self, url: str) -> int:
        ydl_opts = {
            "quiet": True,
            "extract_flat": "in_playlist",
            "force_generic_extractor": True,
            "ignoreerrors": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return len(info.get('entries', [])) if 'entries' in info else 1

    async def get_video_duration(self, url: str) -> Optional[float]:
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, self._sync_get_video_duration, url
        )

    def _sync_get_video_duration(self, url: str) -> Optional[float]:
        try:
            result = self._extract_video_info(url)
            return self._parse_duration(result)
        except Exception as e:
            print(f"Error obteniendo duración de {url}: {e}")
            return None

    async def get_media_duration(self, url: str) -> Dict[str, List[Dict[str, Any]]]:
        durations = []
        if await self.is_youtube_playlist(url):
            urls = await self.get_video_urls_from_playlist(url)
            if urls:
                # Ejecutamos en paralelo la obtención de la duración de cada video
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
    
    async def get_media_info(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'ignoreerrors': True,
            }
            loop = asyncio.get_running_loop()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info:
                    return None

                return {
                    "title": info.get("title"),
                    "duration": info.get("duration")
                }
        except Exception as e:
            print(f"Error obteniendo información del video {url}: {e}")
            return None

    async def download(self, url: str, dest_folder: str, mp3_id: Optional[str] = None) -> str:
        try:
            await asyncio.get_running_loop().run_in_executor(
                self.executor, self._sync_download, url, dest_folder, mp3_id
            )
            return "Descarga exitosa"
        except Exception as e:
            return f"Error en descarga: {str(e)}"

    def _sync_download(self, url: str, dest_folder: str, mp3_id: Optional[str] = None):
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
            ydl.download([url])

    def _extract_info(self, url: str) -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({'quiet': True, 'ignoreerrors': True}) as ydl:
            return ydl.extract_info(url, download=False)

    def _extract_playlist_info(self, url: str) -> Dict[str, Any]:
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _extract_video_info(self, url: str) -> Dict[str, Any]:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _process_playlist_entries(self, result: Dict[str, Any]) -> List[str]:
        urls = []
        for entry in result.get('entries', []):
            if not entry:
                continue
            url_val = entry.get('url') or entry.get('webpage_url')
            if url_val:
                urls.append(url_val)
            elif 'id' in entry:
                urls.append(f"https://youtube.com/watch?v={entry['id']}")
        return urls

    def _parse_duration(self, result: Dict[str, Any]) -> Optional[float]:
        if duration := result.get('duration'):
            return round(duration / 60, 2)
        return None

    def _process_videos(self, urls: List[str]) -> List[Dict[str, Any]]:
        # Versión síncrona (por si se necesita)
        videos = []
        for url in urls:
            duration = self._sync_get_video_duration(url)
            if duration is not None:
                videos.append({"url": url, "duration": duration})
        return videos
