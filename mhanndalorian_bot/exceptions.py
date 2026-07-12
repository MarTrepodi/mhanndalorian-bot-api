"""
Exception hierarchy for mhanndalorian_bot

All exceptions subclass :class:`MBotError`, which itself subclasses :class:`RuntimeError`
so existing ``except RuntimeError`` handlers continue to work.
"""

from __future__ import annotations

from typing import NoReturn

import httpx

__all__ = [
    "APIResponseError",
    "AuthenticationError",
    "AuthorizationError",
    "BadRequestError",
    "MBotError",
    "raise_for_response",
]


class MBotError(RuntimeError):
    """Base exception for all mhanndalorian_bot errors."""


class APIResponseError(MBotError):
    """Non-200 HTTP response from the Mhanndalorian Bot API.

    Attributes
        status_code: HTTP status code of the response, if available
        endpoint: API endpoint path the request was sent to, if available
        response_text: Raw response body text, if available
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        response_text: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.response_text = response_text


class BadRequestError(APIResponseError):
    """HTTP 400: invalid parameters, malformed JSON, or payload validation failure."""


class AuthenticationError(APIResponseError):
    """HTTP 401: missing or invalid API key or HMAC signature."""


class AuthorizationError(APIResponseError):
    """HTTP 403: credentials not authorized for this account or endpoint."""


_STATUS_MAP: dict[int, type[APIResponseError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: AuthorizationError,
}


def raise_for_response(response: httpx.Response, endpoint: str) -> NoReturn:
    """Raise the exception mapped to the status code of a non-200 ``httpx.Response``"""
    exc_cls = _STATUS_MAP.get(response.status_code, APIResponseError)
    raise exc_cls(
        f"Unexpected result from {endpoint}: HTTP {response.status_code}: {response.text}",
        status_code=response.status_code,
        endpoint=endpoint,
        response_text=response.text,
    )
