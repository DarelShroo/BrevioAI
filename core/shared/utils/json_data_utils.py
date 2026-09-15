import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)

DEFAULT_LOGS_PATH = str(
    Path(__file__).resolve().parents[2] / "brevio_api" / "logs" / "logs.json"
)


async def save_log_to_json(log_data: str, filename: str | None = None) -> None:
    if filename is None or filename == "./core/brevio_api/logs/logs.json":
        target_path = DEFAULT_LOGS_PATH
    else:
        target_path = str(Path(filename).resolve())

    log_data_dict = json.loads(log_data)
    if not isinstance(log_data_dict, dict):
        raise ValueError("log_data must be a JSON object (dictionary).")

    log_data_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_dir = os.path.dirname(target_path)
    await asyncio.to_thread(os.makedirs, log_dir, exist_ok=True)

    existing_logs = []

    if (
        await asyncio.to_thread(os.path.exists, target_path)
        and await asyncio.to_thread(os.path.getsize, target_path) > 0
    ):
        try:
            async with aiofiles.open(target_path, "r", encoding="utf-8") as f:
                file_content = (await f.read()).strip()
                if file_content:
                    existing_logs = json.loads(file_content)
                    if not isinstance(existing_logs, list):
                        existing_logs = [existing_logs]
        except Exception as e:
            logger.error(
                f"Error reading {target_path}: {str(e)}. Initializing new log array."
            )

    existing_logs.append(log_data_dict)

    try:
        async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(existing_logs, indent=4, ensure_ascii=False))
        logger.info(
            f"Log successfully added to {target_path}. Total logs: {len(existing_logs)}"
        )
    except Exception as e:
        logger.error(f"Error saving to {target_path}: {str(e)}")
