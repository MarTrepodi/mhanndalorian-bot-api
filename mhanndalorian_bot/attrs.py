"""
Attribute definitions
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

__all__ = ["APIKey", "AllyCode", "Debug", "HMAC", "Headers", "Payload", "EndPoint"]

from mhanndalorian_bot.config import Config

logger: logging.Logger = Config.logger


class ManagedAttribute(ABC):

    def __set_name__(self, owner, name):
        self.private_name = '_' + name

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


class DiscordId(ManagedAttribute):

    def __init__(self, allycode=None):
        self.allycode = allycode

    def validate(self, value):
        if not isinstance(value, str):
            raise AttributeError(f"{value} must be a string, not type:{type(value)}")
        value = value.replace('-', '') if '-' in value else value


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

    pop = delete_header


class Payload(dict):

    def __getitem__(self, key):
        return super().get(key, None)


class EndPoint(Enum):
    """Enum class for MBot API endpoints"""
    # API endpoints
    TW = 'tw'
    RAID = 'activeraid'
    TWLOGS = 'twlogs'
    TWLEADERBOARD = 'twleaderboard'
    GAC = "gac"
    INVENTORY = "inventory"
    TB = "tb"
    TBLOGS = "tblogs"
    TBHISTORY = "tbleaderboardhistory"
    EVENTS = "events"
    LEADERBOARD = "leaderboard"
    ARENA = "leaderboard"
    PLAYER = "player"
    GUILD = "guild"

    # Player Registry endpoints
    FETCH = "database"
    REGISTER = "comlink"
    VERIFY = "comlink"

    @staticmethod
    def get_endpoints():
        """Return a list of all endpoint names"""
        return [name for name, member in EndPoint.__members__.items()]
