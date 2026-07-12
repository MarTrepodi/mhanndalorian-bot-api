"""SWGOH Mhanndalorian Bot Python client.

Public API:
    API       - authenticated endpoint client
    Registry  - player registry client
    EndPoint  - endpoint enum
    Exceptions - MBotError (base, subclasses RuntimeError), APIResponseError,
                 BadRequestError (400), AuthenticationError (401), AuthorizationError (403)

Logging:
    This package emits records under the ``mhanndalorian_bot`` logger hierarchy and attaches a
    :class:`logging.NullHandler` to the root package logger so importing the library never
    produces "no handler" warnings. Consumers control output by configuring handlers / levels
    on their own application loggers (e.g. ``logging.getLogger('mhanndalorian_bot').setLevel(
    logging.DEBUG)``). Sensitive values are redacted before emission; see ``MBot.sign`` and
    ``mhanndalorian_bot.utils.func_debug_logger``.
"""

import logging

from .api import API
from .attrs import EndPoint, LeaderboardType
from .exceptions import (
    APIResponseError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    MBotError,
)
from .registry import Registry

__all__ = [
    "API",
    "APIResponseError",
    "AuthenticationError",
    "AuthorizationError",
    "BadRequestError",
    "EndPoint",
    "LeaderboardType",
    "MBotError",
    "Registry",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())
