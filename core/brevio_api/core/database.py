import logging
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.read_preferences import ReadPreference

logger = logging.getLogger(__name__)

_PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED


class AsyncDB:
    def __init__(self, uri: Optional[str] = None) -> None:
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

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
                f"Initializing MongoDB async client with URI: {connection_uri[:20]}..."
            )

            self.client = AsyncIOMotorClient(
                connection_uri,
                serverSelectionTimeoutMS=server_selection_timeout,
                connectTimeoutMS=connect_timeout,
                socketTimeoutMS=socket_timeout,
            )

        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            raise ValueError(f"Invalid configuration: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error during async MongoDB initialization: {str(e)}",
                exc_info=True,
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

    async def verify_connection(self) -> None:
        try:
            if not self.client:
                raise RuntimeError("MongoDB client not initialized")
            logger.debug("Verifying MongoDB async connection with ping command")
            await self.client.admin.command("ping")
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

    def get_client(self) -> AsyncIOMotorClient:
        if not self.client:
            logger.error("MongoDB async client instance not initialized")
            raise RuntimeError("MongoDB client not initialized")
        return self.client

    def database(self, database_name: str = "brevio") -> AsyncIOMotorDatabase:
        if not self.client:
            raise RuntimeError("MongoDB client not initialized")
        if not isinstance(database_name, str) or not database_name.strip():
            raise ValueError("Database name must be a non-empty string")

        try:
            self.db = self.client.get_database(
                database_name, read_preference=_PRIMARY_PREFERRED
            )
            logger.info(f"Successfully accessed database: {database_name}")
            return self.db
        except OperationFailure as e:
            logger.error(f"Permission denied for database {database_name}: {str(e)}")
            raise PermissionError(
                f"No permission to access database {database_name}: {str(e)}"
            ) from None
        except Exception as e:
            logger.error(
                f"Unexpected error accessing database {database_name}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to access database {database_name}: {str(e)}")

    async def close(self) -> None:
        try:
            if self.client:
                logger.info("Closing MongoDB async client connection...")
                self.client.close()
                self.client = None
                self.db = None
                logger.info("MongoDB connection closed successfully")
            else:
                logger.warning("MongoDB client was already None, nothing to close")
        except Exception as e:
            logger.error(
                f"Error while closing MongoDB connection: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Failed to close MongoDB connection: {str(e)}") from e
