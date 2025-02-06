from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure
import os
from pymongo.read_preferences import ReadPreference
from ..models.errors.connection_error import ConnectionError
from ..models.errors.authentication_error import AuthenticationError

_PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED


class DB:
    def __init__(self, uri: str = None):
        self.client = MongoClient(
            os.getenv("MONGODB_URI"),
            serverSelectionTimeoutMS=os.getenv("SERVER_SELECTION_TIMEOUT_MS"),
            connectTimeoutMS=os.getenv("CONNECT_TIMEOUT_MS"),
            socketTimeoutMS=os.getenv("SOCKET_TIMEOUT_MS")
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
