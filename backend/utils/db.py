from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure
import os
from pymongo.read_preferences import ReadPreference

_PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED


class DB:
    def __init__(self, uri: str = None):
        self.uri = uri or os.getenv(
            "MONGODB_URI", "mongodb://appUser:appPassword@localhost:27017/brevio?authSource=brevio")
        self.client = MongoClient(
            self.uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000
        )
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.client.admin.command('ping')
        except ConnectionFailure:
            raise ConnectionError("No se pudo conectar a MongoDB") from None
        except OperationFailure as e:
            if e.code == 18:
                raise AuthenticationError(
                    "Credenciales inválidas para MongoDB") from None
            raise

    def get_client(self) -> MongoClient:
        return self.client

    def database(self, database: str = 'brevio') -> Database:
        try:
            return self.client.get_database(
                database,
                read_preference=_PRIMARY_PREFERRED
            )
        except OperationFailure as e:
            raise PermissionError(f"Sin permisos para acceder a la base de datos {
                                  database}") from None

# Clases personalizadas para manejo de errores


class ConnectionError(Exception):
    pass


class AuthenticationError(Exception):
    pass
