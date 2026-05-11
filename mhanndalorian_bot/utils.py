"""
Utility functions
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any, Iterable

logger = logging.getLogger(__name__)

_SENSITIVE_ARG_NAMES = frozenset({"api_key", "apikey", "discord_id", "allycode", "authorization", "token"})


def _redact_value(name: str, value: Any) -> Any:
    """Replace sensitive values with a mask for logging. Non-sensitive values pass through unchanged."""
    if name.lower() in _SENSITIVE_ARG_NAMES and isinstance(value, str) and value:
        return f"***{value[-4:]}" if len(value) >= 4 else "***"
    return value


def _format_redacted_call(func, args: tuple, kwargs: dict[str, Any]) -> str:
    """Build a function-call string with sensitive arg values redacted."""
    try:
        import inspect
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)
        parts: list[str] = []
        for name, value in bound.arguments.items():
            if name == "self":
                parts.append("self")
                continue
            parts.append(f"{name}={_redact_value(name, value)!r}")
        return ", ".join(parts)
    except (TypeError, ValueError):
        return f"args={args!r}, kwargs={kwargs!r}"


def func_timer(f):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG"""

    @wraps(f)
    def wrap(*args, **kw):
        if not logger.isEnabledFor(logging.DEBUG):
            return f(*args, **kw)
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug(f"  [ {f.__name__}() ] took: {(te - ts):.6f} seconds")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying DEBUG logging to a function if enabled in the MBot class.

    Arguments matching known-sensitive names (api_key, discord_id, allycode, ...) are
    redacted before being logged so DEBUG output cannot leak secrets.
    """

    @wraps(f)
    def wrap(*args, **kw):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"  [ function {f.__name__}() ] called with {_format_redacted_call(f, args, kw)}")
        return f(*args, **kw)

    return wrap


def calc_tw_score_total(zone_status_list: Iterable[dict[str, Any]]) -> int:
    """
    Calculates the total TW score from a list of zone status dictionaries.

    The function takes an iterable of dictionaries containing zone status information
    from the `fetch_tw()` method and computes the sum of the scores present in the
    nested 'zoneStatus' key of each dictionary.

    Args:
        zone_status_list (Iterable[dict]): An iterable of dictionaries where each
            dictionary contains a 'zoneStatus' key that itself contains another
            dictionary with a 'score' key.

    Returns:
        int: The total sum of scores extracted from the 'zoneStatus' key of each
        dictionary in the input.

    Raises:
        TypeError: If the input `zone_status_list` is not a list.
    """
    if not isinstance(zone_status_list, list):
        raise TypeError("'zone_status' must be a list")

    return sum(int(item['zoneStatus']['score']) for item in zone_status_list)


def get_tw_opponent_url(tw_data: dict[str, Any]) -> str:
    """
    Generates and returns the URL for the opponent guild profile in a Territory War event.

    This method extracts the opponent's guild ID from the provided `tw_data` dictionary,
    validates its presence, and constructs a URL to their profile hosted on swgoh.gg. It
    is intended to handle data structures specific to game-related data in the scope of
    Territory War events.

    Args:
        tw_data (dict): A dictionary containing Territory War event information, which includes
            data about the participant guilds and their profiles.

    Returns:
        str: A string containing the constructed URL to the opponent guild's profile.

    Raises:
        TypeError: If the provided `tw_data` is not of type dictionary.
        ValueError: If the necessary 'awayGuild' profile information is missing from `tw_data`.
    """
    if not isinstance(tw_data, dict):
        raise TypeError("'tw_data' must be a dictionary")

    guild_id = tw_data.get('awayGuild', {}).get('profile', {}).get('id')

    if not guild_id:
        raise ValueError("'tw_data' does not contain 'awayGuild' profile information.")

    return f"https://swgoh.gg/g/{guild_id}/"
