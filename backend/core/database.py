import logging
import os
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure
from pymongo.read_preferences import ReadPreference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

_PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED


class DB:
    def __init__(self, uri: Optional[str] = None) -> None:
        self.db: Optional[Database] = None

        self.client: MongoClient

        try:
            connection_uri = uri or os.getenv("MONGODB_URI")
            if not connection_uri:
                raise ValueError("MONGODB_URI environment variable not set")

            server_selection_timeout = self._get_env_int(
                "SERVER_SELECTION_TIMEOUT_MS", 30000
            )
            connect_timeout = self._get_env_int("CONNECT_TIMEOUT_MS", 20000)
            socket_timeout = self._get_env_int("SOCKET_TIMEOUT_MS", 60000)

            logger.info(
                f"Initializing MongoDB client with URI: {connection_uri[:20]}..."
            )

            self.client = MongoClient(
                connection_uri,
                serverSelectionTimeoutMS=server_selection_timeout,
                connectTimeoutMS=connect_timeout,
                socketTimeoutMS=socket_timeout,
            )
            self._verify_connection()

        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            raise ValueError(f"Invalid configuration: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error during initialization: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Failed to initialize MongoDB client: {str(e)}")

    def _get_env_int(self, var_name: str, default: int) -> int:
        try:
            value = os.getenv(var_name)
            return int(value) if value is not None else default
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid integer for {var_name}: {str(e)}. Using default: {default}"
            )
            return default

    def _verify_connection(self) -> None:
        try:
            logger.debug("Verifying MongoDB connection with ping command")
            self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise ConnectionError(f"Cannot connect to MongoDB: {str(e)}") from None
        except OperationFailure as e:
            if e.code == 18:
                logger.error("Authentication failed: Invalid credentials")
                raise PermissionError("Invalid MongoDB credentials") from None
            logger.error(f"Operation failure during connection verification: {str(e)}")
            raise RuntimeError(f"Operation failed during connection: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error verifying connection: {str(e)}", exc_info=True
            )
            raise RuntimeError(
                f"Unexpected error during connection verification: {str(e)}"
            ) from e

    def get_client(self) -> MongoClient:
        try:
            return self.client
        except AttributeError:
            logger.error("MongoClient instance not initialized")
            raise RuntimeError("MongoDB client not initialized")

    def database(self, database: str = "brevio") -> Database:
        try:
            if not isinstance(database, str) or not database.strip():
                raise ValueError("Database name must be a non-empty string")

            logger.debug(f"Accessing database: {database}")
            # Asignar a self.db el valor obtenido de la conexión
            self.db = self.client.get_database(
                database, read_preference=_PRIMARY_PREFERRED
            )
            logger.info(f"Successfully accessed database: {database}")
            return self.db

        except OperationFailure as e:
            logger.error(f"Permission denied for database {database}: {str(e)}")
            raise PermissionError(
                f"No permission to access database {database}: {str(e)}"
            ) from None
        except ValueError as e:
            logger.error(f"Invalid database name: {str(e)}")
            raise ValueError(f"Invalid database name: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error accessing database {database}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to access database {database}: {str(e)}")
