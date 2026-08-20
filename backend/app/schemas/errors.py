"""
CONTRACT RULE #3: every error response, from every endpoint, has this exact
shape:

    { "error": { "code": "string", "message": "string" } }

No endpoint returns a bare string error or a differently-shaped error object.
This is enforced globally via the exception handlers registered in main.py —
individual routers should raise api_error.APIError(...) and let the handler
do the formatting, rather than building this shape by hand.
"""

from .base import CamelModel


class ErrorDetail(CamelModel):
    code: str
    message: str


class ErrorResponse(CamelModel):
    error: ErrorDetail
