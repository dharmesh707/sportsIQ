from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db as _get_db
from app.models.user import User
from app.utils.errors import APIError
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(_get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise APIError(401, "UNAUTHORIZED", "Missing or invalid Authorization header.")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise APIError(401, "UNAUTHORIZED", "Invalid or expired token.")

    user = db.get(User, user_id)
    if user is None:
        raise APIError(401, "UNAUTHORIZED", "User no longer exists.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


