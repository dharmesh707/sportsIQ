"""
Central error handling. This is what GUARANTEES contract rule #3 - every
error response has the { "error": { "code", "message" } } shape - no matter
where in the app the error originates (a router raising on purpose, a bad
request FastAPI itself rejects, or an unhandled 500).

Codes match API_CONTRACT_final.md section 8's closed, extend-only list
exactly (uppercase): UNAUTHORIZED, INVALID_CREDENTIALS,
EMAIL_ALREADY_REGISTERED, VALIDATION_ERROR, NOT_FOUND,
UNSUPPORTED_SPORT_TYPE, VIDEO_PROCESSING_FAILED, INTERNAL_ERROR.
If you need a new code, add it to that file in the same PR - don't invent
one here that isn't documented there, and don't add one to this file's
fallback logic that isn't in the contract's list.

Usage in routers/services:
    from app.utils.errors import APIError
    raise APIError(status_code=404, code="NOT_FOUND",
                    message="No analysis found with that id.")

Do NOT raise a bare fastapi.HTTPException with a plain string detail - that
produces {"detail": "..."} which violates the contract shape. If you must
raise HTTPException for some reason, its handler below still reshapes it
into one of the contract's existing codes based on status code (see
_code_for_status), but prefer APIError directly so the `code` field is
chosen deliberately.
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("sportsiq")


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _code_for_status(status_code: int) -> str:
    """Maps a bare HTTPException's status code to the closest contract code -
    only used as a fallback when something raises HTTPException directly
    instead of APIError. Stays within section 8's closed list, no new codes."""
    return {
        401: "UNAUTHORIZED",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
    }.get(status_code, "INTERNAL_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Catches FastAPI/Starlette-raised HTTPExceptions (e.g. 404 from an
        # unmatched route, or a bare HTTPException some code raises) and
        # reshapes them into the contract's error envelope, using an
        # already-documented code rather than inventing a new one.
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(_code_for_status(exc.status_code), detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        # Pydantic/FastAPI request validation failures (bad body, missing
        # field, wrong type) also get reshaped instead of FastAPI's default
        # {"detail": [...]} array format.
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "Invalid request.")
        message = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("VALIDATION_ERROR", message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "INTERNAL_ERROR", "Something went wrong. Please try again."
            ),
        )
