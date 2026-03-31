import logging

from beanie import init_beanie

from core.brevio_api.core.database import AsyncDB
from core.brevio_api.models.odm import FolderEntryDocument, UserDocument

logger = logging.getLogger(__name__)

_odm_initialized = False


async def init_odm(async_db: AsyncDB, database_name: str = "brevio") -> None:
    global _odm_initialized

    if _odm_initialized:
        return

    db = async_db.database(database_name)
    await init_beanie(
        database=db,
        document_models=[UserDocument, FolderEntryDocument],
    )
    _odm_initialized = True
    logger.info("Beanie ODM initialized for database '%s'", database_name)
