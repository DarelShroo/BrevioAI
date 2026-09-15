from datetime import datetime, timedelta, timezone

from starlette.responses import Response

from core.shared.utils.environment import env_override_bool, is_production_environment

ACCESS_COOKIE_NAME = "brevio_access"
REFRESH_COOKIE_NAME = "brevio_refresh"
ACCESS_COOKIE_PATH = "/"
REFRESH_COOKIE_PATH = "/auth"


def cookie_secure() -> bool:
    explicit = env_override_bool("COOKIE_SECURE")
    if explicit is not None:
        return explicit
    return is_production_environment()


def _expires_at(max_age: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=max_age)


def _apply_cookie(
    response: Response,
    *,
    key: str,
    value: str,
    max_age: int,
    path: str,
) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        expires=_expires_at(max_age),
        path=path,
        domain=None,
        secure=cookie_secure(),
        httponly=True,
        samesite="strict",
    )


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_max_age: int,
    refresh_max_age: int,
) -> None:
    _apply_cookie(
        response,
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        path=ACCESS_COOKIE_PATH,
    )
    _apply_cookie(
        response,
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_max_age,
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    secure = cookie_secure()
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path=ACCESS_COOKIE_PATH,
        domain=None,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=None,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
