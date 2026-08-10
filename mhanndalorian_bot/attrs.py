"""
Attribute definitions
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from typing import Any, overload

from mhanndalorian_bot.exceptions import ValidationError

__all__ = [
    "APIKey",
    "AllyCode",
    "AUTHENTICATED_ENDPOINTS",
    "NON_AUTHENTICATED_ENDPOINTS",
    "DEF_ID_ENUM_BY_LEADERBOARD_TYPE",
    "DefId",
    "GuildRaidDefId",
    "LeaderboardType",
    "EndPoint",
    "TerritoryBattleDefId",
    "TerritoryWarDefId",
]

logger = logging.getLogger(__name__)


class ManagedAttribute(ABC):
    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = "_" + name

    @overload
    def __get__(self, obj: None, objtype: type[Any] | None = None) -> "ManagedAttribute": ...

    @overload
    def __get__(self, obj: object, objtype: type[Any] | None = None) -> str: ...

    def __get__(self, obj: object | None, objtype: type[Any] | None = None) -> "ManagedAttribute | str":
        """Typed so `api.api_key` resolves to `str` rather than `Unknown`.

        Two overloads because class access and instance access return different things:
        `API.api_key` is the descriptor itself, `api.api_key` is the stored value. Without
        annotations a type checker gives up on both and an IDE offers nothing.
        """
        if obj is None:
            return self
        return getattr(obj, self.private_name)

    def __set__(self, obj: object, value: Any) -> None:
        self.validate(value)
        logger.debug(f"Setting {self.private_name!r} to {value!r} for object {obj!r}")
        setattr(obj, self.private_name, value)

    @abstractmethod
    def validate(self, value: Any) -> None:
        pass


class APIKey(ManagedAttribute):
    def __init__(self, api_key=None):
        self.api_key = api_key

    def validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"{value} must be a string, not type:{type(value)}")


class AllyCode(ManagedAttribute):
    """Descriptor for the 9-digit player allycode.

    Deliberately not a `str` subclass. It inherited `str` historically, which made the
    *descriptor object* itself a string of value `""` -- `isinstance(MBot.__dict__["allycode"],
    str)` was True -- while nothing ever used the string behaviour. The value it manages is a
    `str`; the descriptor is not.
    """

    def __init__(self, allycode=None):
        self.allycode = allycode

    def validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"{value} must be a string, not type:{type(value)}")
        if not value.isdigit() or len(value) != 9:
            raise ValidationError(f"Invalid allyCode ({value}): Value must be exactly 9 numerical characters.")


class EndPoint(Enum):
    """Enum class for MBot API endpoints"""

    # API endpoints
    TW = "tw"
    RAID = "activeraid"
    TWLOGS = "twlogs"
    TWLEADERBOARD = "twleaderboard"
    GAC = "gac"
    INVENTORY = "inventory"
    TB = "tb"
    TBLOGS = "tblogs"
    TBHISTORY = "tbleaderboardhistory"
    EVENTS = "events"
    LEADERBOARD = "leaderboard"
    ARENA = "leaderboard"  # intentional alias of LEADERBOARD (same API slug)
    PLAYER = "player"
    PLAYERARENA = "playerarena"
    GUILD = "guild"
    GUILDLEADERBOARD = "guildleaderboard"
    SQUADS = "squadpresets"
    CONQUEST = "conquest"

    # Player Registry endpoints
    FETCH = "database"
    REGISTER = "comlink"
    VERIFY = "comlink"  # intentional alias of REGISTER (same slug, disambiguated by payload 'method')

    @staticmethod
    def get_endpoints():
        """Return a list of all endpoint **names**, aliases included.

        This is 21 names over 19 distinct slugs (the 18 API spec paths plus the registry's
        ``comlink``): ``ARENA`` and ``LEADERBOARD`` share ``"leaderboard"``, and ``VERIFY``
        and ``REGISTER`` share ``"comlink"``. That is deliberate -- the aliases are part of
        the public surface, so a helper advertising "all endpoint names" has to list them,
        and dropping either would hide a name callers write in their own code.

        Callers who want the distinct slugs should iterate the enum instead, which skips
        aliases by definition: ``[member.value for member in EndPoint]``.
        """
        return [name for name, member in EndPoint.__members__.items()]

    @property
    def requires_discord_id(self) -> bool:
        """Whether this endpoint requires the ``x-discord-id`` header (spec v1.0.1)."""
        return self.value in NON_AUTHENTICATED_ENDPOINTS

    @property
    def is_authenticated(self) -> bool:
        """True if this endpoint uses the registered player's EA session and will break it."""
        return self.value in AUTHENTICATED_ENDPOINTS


class LeaderboardType(IntEnum):
    """Guild leaderboard types accepted by the GUILDLEADERBOARD endpoint"""

    UNSPECIFIED = 0
    GUILD_RAID_ALL_COMP_PTS = 1
    GUILD_GALACTIC_POWER = 3
    GUILD_TERRITORY_BATTLE_STARS = 4
    GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER = 5
    GUILD_RAID_HIGH_WATERMARK = 6

    @property
    def def_id_enum(self) -> type[Enum] | None:
        """The enum of legal ``defId`` values for this leaderboard type.

        ``None`` for the types that take no ``defId`` (0, 1 and 3).
        """
        return DEF_ID_ENUM_BY_LEADERBOARD_TYPE.get(self)

    @property
    def requires_def_id(self) -> bool:
        """True if the API requires a ``defId`` alongside this leaderboard type."""
        return self in DEF_ID_ENUM_BY_LEADERBOARD_TYPE


class TerritoryBattleDefId(Enum):
    """Legal ``defId`` values for ``LeaderboardType.GUILD_TERRITORY_BATTLE_STARS`` (type 4).

    The API spec pins the raw tokens without describing which Territory Battle each maps to,
    so the member names mirror the tokens verbatim.
    """

    T01D = "t01D"
    T04D = "t04D"
    T05D = "t05D"


class TerritoryWarDefId(Enum):
    """Legal ``defId`` values for ``LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER`` (type 5)."""

    TERRITORY_WAR_LEADERBOARD = "TERRITORY_WAR_LEADERBOARD"


class GuildRaidDefId(Enum):
    """Legal ``defId`` values for ``LeaderboardType.GUILD_RAID_HIGH_WATERMARK`` (type 6)."""

    RANCOR_DIFF01 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"
    RANCOR_DIFF02 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF02"
    RANCOR_DIFF03 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF03"
    RANCOR_DIFF04 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF04"
    RANCOR_DIFF05 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF05"
    RANCOR_DIFF06 = "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF06"
    AAT_DIFF06 = "GUILD:RAIDS:NORMAL_DIFF:AAT:DIFF06"
    AAT_HEROIC80 = "GUILD:RAIDS:NORMAL_DIFF:AAT:HEROIC80"
    SITH_RAID_DIFF06 = "GUILD:RAIDS:NORMAL_DIFF:SITH_RAID:DIFF06"
    SITH_RAID_HEROIC85 = "GUILD:RAIDS:NORMAL_DIFF:SITH_RAID:HEROIC85"
    KRAYTDRAGON_DIFF01 = "GUILD:RAIDS:NORMAL_DIFF:KRAYTDRAGON:DIFF01"
    ROTJ_SPEEDERBIKE = "GUILD:RAIDS:NORMAL_DIFF:ROTJ:SPEEDERBIKE"
    NABOO_NABOO = "GUILD:RAIDS:NORMAL_DIFF:NABOO:NABOO"
    ORDER66_DIFF01 = "GUILD:RAIDS:NORMAL_DIFF:ORDER66:DIFF01"


# Any of the three per-leaderboard-type ``defId`` enums; use for annotations accepting a defId.
DefId = TerritoryBattleDefId | TerritoryWarDefId | GuildRaidDefId

# The spec's /guildleaderboard oneOf: leaderboard types 4, 5 and 6 each require a defId drawn
# from their own distinct enum. Types 0, 1 and 3 are absent here - they accept no defId at all.
DEF_ID_ENUM_BY_LEADERBOARD_TYPE: dict[LeaderboardType, type[Enum]] = {
    LeaderboardType.GUILD_TERRITORY_BATTLE_STARS: TerritoryBattleDefId,
    LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER: TerritoryWarDefId,
    LeaderboardType.GUILD_RAID_HIGH_WATERMARK: GuildRaidDefId,
}


# Endpoints that authenticate as the registered player and use their EA session.
# Calling them will break that player's active in-game session.
AUTHENTICATED_ENDPOINTS: frozenset[str] = frozenset(
    {
        "activeraid",
        "conquest",
        "events",
        "gac",
        "inventory",
        "leaderboard",
        "squadpresets",
        "tb",
        "tbleaderboardhistory",
        "tblogs",
        "tw",
        "twleaderboard",
        "twlogs",
    }
)


# The five endpoints spec v1.0.1 tags "Non-authenticated". Every one of them requires the
# `x-discord-id` header: /player and /guild were both observed returning 400 without it and 200
# with it, and the spec states the rule for all five.
#
# Deliberately an explicit set rather than "any slug not in AUTHENTICATED_ENDPOINTS". `comlink` is
# absent from the OpenAPI spec entirely and carries its Discord ID in the payload instead, and
# callers may pass an undocumented slug straight to fetch_data -- neither should be gated by a rule
# derived from an endpoint list they are not part of.
NON_AUTHENTICATED_ENDPOINTS: frozenset[str] = frozenset(
    {"database", "guild", "guildleaderboard", "player", "playerarena"}
)
