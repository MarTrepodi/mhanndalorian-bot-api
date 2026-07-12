"""
Attribute definitions
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from typing import Any

__all__ = [
    "APIKey",
    "AllyCode",
    "AUTHENTICATED_ENDPOINTS",
    "Debug",
    "HMAC",
    "Headers",
    "LeaderboardType",
    "Payload",
    "EndPoint",
]

logger = logging.getLogger(__name__)


class ManagedAttribute(ABC):
    def __set_name__(self, owner, name):
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        self.validate(value)
        logger.debug(f"Setting {self.private_name!r} to {value!r} for object {obj!r}")
        setattr(obj, self.private_name, value)

    @abstractmethod
    def validate(self, value):
        pass


class APIKey(ManagedAttribute):
    def __init__(self, api_key=None):
        self.api_key = api_key

    def validate(self, value):
        if not isinstance(value, str):
            raise AttributeError(f"{value} must be a string, not type:{type(value)}")


class AllyCode(ManagedAttribute, str):
    def __init__(self, allycode=None):
        self.allycode = allycode

    def validate(self, value):
        if not isinstance(value, str):
            raise AttributeError(f"{value} must be a string, not type:{type(value)}")
        if not value.isdigit() or len(value) != 9:
            raise AttributeError(f"Invalid allyCode ({value}): Value must be exactly 9 numerical characters.")


class Debug(ManagedAttribute):
    def __init__(self, debug: bool = False):
        self.debug = debug

    def validate(self, value):
        if not isinstance(value, bool):
            raise AttributeError(f"{value} must be a boolean, not type:{type(value)}")


class HMAC(ManagedAttribute):
    def __init__(self, hmac: bool = True):
        self.hmac = hmac

    def validate(self, value):
        if not isinstance(value, bool):
            raise AttributeError(f"{value} must be a boolean, not type:{type(value)}")


class Headers(dict):
    def __getitem__(self, key):
        return super().get(key, None)

    def add_header(self, key: str, value: Any):
        """Add a header and append value if already exists"""
        if key in self:
            self[key] += f",{value}"
        else:
            self[key] = value

    push = add_header

    def delete_header(self, key: str):
        """Delete header if exists"""
        if key in self:
            del self[key]


class Payload(dict):
    def __getitem__(self, key):
        return super().get(key, None)


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
        """Return a list of all endpoint names"""
        return [name for name, member in EndPoint.__members__.items()]

    @property
    def is_authenticated(self) -> bool:
        """True if this endpoint uses the registered player's EA session (may interrupt active game sessions)."""
        return self.value in AUTHENTICATED_ENDPOINTS


class LeaderboardType(IntEnum):
    """Guild leaderboard types accepted by the GUILDLEADERBOARD endpoint"""

    UNSPECIFIED = 0
    GUILD_RAID_ALL_COMP_PTS = 1
    GUILD_GALACTIC_POWER = 3
    GUILD_TERRITORY_BATTLE_STARS = 4
    GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER = 5
    GUILD_RAID_HIGH_WATERMARK = 6


# Endpoints that authenticate as the registered player and use their EA session.
# Calling them may interrupt an active in-game session for that player.
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
