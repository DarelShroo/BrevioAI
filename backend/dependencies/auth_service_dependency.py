import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from pymongo.database import Database

from ..dependencies.db_dependency import get_db
from ..dependencies.token_dependency import get_token_service
from ..services.auth_service import AuthService
from ..services.token_service import TokenService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_auth_service(
    db: Annotated[Database, Depends(get_db)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> AuthService:
    try:
        if db is None:
            logger.error("Database dependency is None")
            raise ValueError("Database dependency not provided")
        if token_service is None:
            logger.error("TokenService dependency is None")
            raise ValueError("TokenService dependency not provided")

        logger.debug("Initializing AuthService with provided dependencies")

        auth_service = AuthService(db, token_service)
        logger.info("AuthService successfully initialized")
        return auth_service

    except ValueError as e:
        logger.error(f"Invalid dependency provided: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Invalid dependency: {str(e)}"
        ) from e
    except AttributeError as e:
        logger.error(f"Dependency configuration error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Dependency misconfiguration: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error initializing AuthService: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize authentication service: {str(e)}",
        ) from e
