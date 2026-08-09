"""SWGOH Mhanndalorian Bot Python client.

Public API:
    API       - authenticated endpoint client
    Registry  - player registry client
    EndPoint  - endpoint enum
    LeaderboardType - guild leaderboard type enum, plus the defId enums coupled to it:
                 TerritoryBattleDefId (type 4), TerritoryWarDefId (type 5), GuildRaidDefId (type 6)
    Exceptions - MBotError (base, subclasses RuntimeError), APIResponseError,
                 BadRequestError (400), AuthenticationError (401), AuthorizationError (403),
                 ValidationError (local input rejected before a request was sent)

Breaking change in 0.11.0:
    Input validation raises ``ValidationError``, a sibling of ``APIResponseError`` under
    ``MBotError``. It does NOT subclass ``ValueError`` or ``TypeError``, so code written as
    ``except ValueError:`` around library calls no longer catches. Catch ``ValidationError``
    (or ``MBotError`` for everything the library raises).

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
from .attrs import (
    DefId,
    EndPoint,
    GuildRaidDefId,
    LeaderboardType,
    TerritoryBattleDefId,
    TerritoryWarDefId,
)
from .exceptions import (
    APIResponseError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    MBotError,
    ValidationError,
)
from .registry import Registry

__all__ = [
    "API",
    "APIResponseError",
    "AuthenticationError",
    "AuthorizationError",
    "BadRequestError",
    "DefId",
    "EndPoint",
    "GuildRaidDefId",
    "LeaderboardType",
    "MBotError",
    "Registry",
    "TerritoryBattleDefId",
    "TerritoryWarDefId",
    "ValidationError",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())
