# coding=utf-8
"""
Utility functions
"""

from __future__ import absolute_import, annotations

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def func_timer(f):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug(f"  [ {f.__name__}() ] took: {(te - ts):.6f} seconds")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying DEBUG logging to a function if enabled in the MBot class"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        logger.debug(f"  [ function {f.__name__}() ] called with args: {args} and kwargs: {kw}")
        result = f(*args, **kw)
        return result

    return wrap


def calc_tw_score_total(zone_status_list: list) -> int:
    """
    Calculates the total TW score from a list of zone status dictionaries.

    The function takes a list of dictionaries containing zone status information
    from the `fetch_tw()` method and computes the sum of the scores present in the
    nested 'zoneStatus' key of each dictionary.

    Args:
        zone_status_list (list): A list of dictionaries where each dictionary
            contains a 'zoneStatus' key that itself contains another dictionary
            with a 'score' key.

    Returns:
        int: The total sum of scores extracted from the 'zoneStatus' key of each
        dictionary in the input list.

    Raises:
        TypeError: If the input `zone_status_list` is not a list.
    """
    if not isinstance(zone_status_list, list):
        raise TypeError("'zone_status' must be a list")

    return sum([int(score['zoneStatus']['score']) for score in zone_status_list])


def get_tw_opponent_url(tw_data: dict) -> str:
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
