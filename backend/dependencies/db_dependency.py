from pymongo.database import Database

from ..core.database import DB


def get_db() -> Database:
    db = DB().database()
    return db
