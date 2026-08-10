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

When to use API vs Registry:
    ``API`` reads SWGOH game data for a player or guild. ``Registry`` reads and writes the
    SWGOH Player Registry, which maps Discord users to allycodes -- registration, portrait
    and title verification, and lookup. They share a base class and a credential set, so a
    consumer needing both constructs both.

Session-breaking endpoints:
    Thirteen endpoints authenticate as the registered player and **break that player's active
    game session** -- ``tw``, ``twlogs``, ``twleaderboard``, ``tb``, ``tblogs``,
    ``tbleaderboardhistory``, ``activeraid``, ``gac``, ``inventory``, ``leaderboard``,
    ``squadpresets``, ``conquest``, ``events``. The other five (``player``, ``playerarena``,
    ``guild``, ``guildleaderboard``, ``database``) do not. This matters for bots polling on a
    timer: each poll of an authenticated endpoint ejects the player from the game. Check with
    ``EndPoint.<MEMBER>.is_authenticated``.

Recommended lifecycle:
    ``API`` and ``Registry`` hold open httpx clients. Short scripts can let process exit
    reclaim them, but long-running services should use the context manager::

        with API(api_key=..., allycode=...) as api:
            data = api.fetch_inventory()

        async with API(api_key=..., allycode=...) as api:
            data = await api.fetch_inventory_async()

    ``close()`` / ``aclose()`` are available for callers managing lifecycle by hand.

Breaking changes in 0.11.0:
    1. Input validation raises ``ValidationError``, a sibling of ``APIResponseError`` under
       ``MBotError``. It does NOT subclass ``ValueError`` or ``TypeError``, so code written as
       ``except ValueError:`` around library calls no longer catches. Catch ``ValidationError``
       (or ``MBotError`` for everything the library raises).
    2. ``fetch_player`` and ``fetch_guild`` no longer strip the response envelope. They were the
       only two helpers that ever did. Reach through ``["events"]`` (and ``["guild"]``) now.
    3. ``Registry.verify_player(primary=...)`` defaults to ``None`` rather than ``False``; the key
       is omitted from the payload so the registry applies its own default (primary=yes for a
       user with no other registered accounts). The old default silently opted first-time users
       out of being primary.
    4. Discord IDs of 17-20 digits are accepted, not exactly 18. This only widens what is allowed
       -- but note the old rule rejected every account created since ~July 2022 (19 digits),
       making Registry unusable for those users.

    Calls to the 13 authenticated endpoints now emit ``SessionBreakWarning``, once per endpoint
    per process. Not breaking, but visible; silence with ``warnings.filterwarnings``.

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
    SessionBreakWarning,
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
    "SessionBreakWarning",
    "Registry",
    "TerritoryBattleDefId",
    "TerritoryWarDefId",
    "ValidationError",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())
