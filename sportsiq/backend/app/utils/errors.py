"""
Central error handling. This is what GUARANTEES contract rule #3 — every
error response has the { "error": { "code", "message" } } shape — no matter
where in the app the error originates (a router raising on purpose, a bad
request FastAPI itself rejects, or an unhandled 500).

Usage in routers/services:

    from app.utils.errors import APIError

    raise APIError(status_code=404, code="analysis_not_found",
                    message="No analysis found with that id.")

Do NOT raise a bare fastapi.HTTPException with a plain string detail — that
produces {"detail": "..."} which violates the contract shape. If you must
raise HTTPException for some reason, its handler below still reshapes it,
but prefer APIError directly so the `code` field is meaningful instead of
defaulting to "http_error".
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
        # reshapes them into the contract's error envelope.
        detail = exc.detail if isinstance(exc.detail, str) else "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", detail),
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
            content=_error_body("validation_error", message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "internal_error", "Something went wrong. Please try again."
            ),
        )
