from pymongo.database import Database

from core.brevio_api.core.database import DB


def get_db() -> Database:
    db = DB().database()
    return db
