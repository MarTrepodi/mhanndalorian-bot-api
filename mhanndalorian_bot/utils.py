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
