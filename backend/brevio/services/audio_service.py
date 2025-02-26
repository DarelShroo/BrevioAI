import asyncio
import subprocess
from typing import Any, Dict, Optional

class AudioService:

    async def get_media_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["ffmpeg", "-i", file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            )

            title = file_path.split('/')[-1].replace('.mp3', '')

            for line in result.stderr.split('\n'):
                if 'Duration' in line:
                    duration_str = line.split(',')[0].split('Duration:')[1].strip()
                    hours, minutes, seconds = map(float, duration_str.split(':'))
                    duration = (hours * 3600 + minutes * 60 + seconds) / 60
                    return {"title": title, "duration": duration}

            return None

        except Exception as e:
            print(f"Error: {e}")
            return None