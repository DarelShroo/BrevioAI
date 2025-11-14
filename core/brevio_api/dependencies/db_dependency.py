from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio_api.core.database import AsyncDB


def get_db() -> AsyncIOMotorDatabase:
    db = AsyncDB().database()
    return db
