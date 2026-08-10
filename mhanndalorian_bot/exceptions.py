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
    "SessionBreakWarning",
    "ValidationError",
    "raise_for_response",
]


class SessionBreakWarning(UserWarning):
    """Emitted when a call to an authenticated endpoint will end the player's game session.

    Spec v1.0.1 tags 13 endpoints Authenticated -- "Will break the session of the user." This is a
    real, user-visible consequence for a bot polling on a timer, so the library says so at runtime
    rather than only in a docstring.

    Silence it the usual way::

        warnings.filterwarnings("ignore", category=SessionBreakWarning)
    """


class MBotError(RuntimeError):
    """Base exception for all mhanndalorian_bot errors."""


class ValidationError(MBotError):
    """Caller-supplied input rejected locally, before any request left the client.

    Covers every deliberate rejection of an argument value the library makes on the
    caller's behalf: allycodes, Discord IDs, guild IDs, API keys, API hosts, leaderboard
    types, ``count`` bounds, ``defId`` coupling, and the helper functions in
    :mod:`mhanndalorian_bot.utils`.

    .. warning::
       This is **not** a subclass of :class:`ValueError` or :class:`TypeError`. Callers
       upgrading from <= 0.10.x must catch :class:`ValidationError` (or
       :class:`MBotError`) where they previously caught ``ValueError``/``TypeError``.

    A ``TypeError`` raised by Python itself against a method signature -- an unknown
    keyword argument, a missing positional -- is a programming error rather than bad
    input, and is deliberately left as a plain ``TypeError``.
    """


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


# Deliberately broader than spec v1.0.1, which documents 400 only on /guildleaderboard (401
# and 403 are documented on most paths). Mapping 400 globally is intentional: any endpoint can
# reject a malformed body, and a caller who catches BadRequestError should not have to know
# which path the spec happened to enumerate it on. Nothing here narrows by endpoint.
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
