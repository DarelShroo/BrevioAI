import asyncio
import logging
import re
import subprocess
from typing import Any, Dict, Optional

import yt_dlp
from pydantic import HttpUrl

logger = logging.getLogger(__name__)


class AudioService:
    async def get_media_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Processing media file: {file_path}")
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["ffmpeg", "-i", file_path, "-hide_banner"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            )

            title = file_path.split("/")[-1].replace(".mp3", "")
            logger.debug(f"Extracted title: {title}")

            for line in result.stderr.split("\n"):
                match = re.search(r"Duration:\s(\d+):(\d+):([\d.]+)", line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    duration = (hours * 3600 + minutes * 60 + seconds) / 60
                    logger.debug(f"Calculated duration: {duration} minutes")
                    return {"title": title, "duration": duration}

            logger.warning(f"No duration found in file: {file_path}")
            return None

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            raise Exception(
                f"Ha ocurrido un error inesperado al obtener información del video {file_path}"
            )

    async def get_media_info_yt(self, url: HttpUrl) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Fetching YouTube media info from URL: {url}")
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "ignoreerrors": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(
                    ydl.extract_info, str(url), download=False
                )
                if not info:
                    logger.warning(f"No info extracted from YouTube URL: {url}")
                    return None

                result = {"title": info.get("title"), "duration": info.get("duration")}
                logger.debug(f"Extracted YouTube info: {result}")
                return result

        except Exception as e:
            logger.error(
                f"Error fetching YouTube info from {url}: {str(e)}", exc_info=True
            )
            raise Exception(
                f"Ha ocurrido un error inesperado al obtener información del video {url}"
            )
