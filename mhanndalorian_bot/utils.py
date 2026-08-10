"""
Utility functions
"""

from __future__ import annotations

import inspect
import logging
import sys
import time
from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any

from mhanndalorian_bot.exceptions import ValidationError

logger = logging.getLogger(__name__)

_SENSITIVE_ARG_NAMES = frozenset({"api_key", "apikey", "discord_id", "allycode", "authorization", "token"})

_REDACTION_MASK = "***"


def redact_secret(value: str) -> str:
    """Mask a secret for logging, revealing at most ``len(value) // 4`` trailing characters.

    The revealed tail is *proportional* to the secret's length rather than a fixed width. A
    fixed last-four tail leaks half a short secret -- a 9-digit allycode logged as ``***6789``
    puts 4 of its 9 digits in the clear -- while contributing nothing extra to a long API key.
    Scaling with length means short secrets protect themselves, long secrets stay
    distinguishable from one another in DEBUG output, and there is no magic constant to
    revisit when key lengths change.

    Examples:
        ``"abc"`` (3) -> ``"***"``; ``"123456789"`` (9) -> ``"***89"``;
        ``"12345678abcdefgh"`` (16) -> ``"***efgh"``; a 40-character key reveals 10.
    """
    tail = len(value) // 4
    return f"{_REDACTION_MASK}{value[-tail:]}" if tail else _REDACTION_MASK


def _redact_value(name: str, value: Any) -> Any:
    """Replace sensitive values with a mask for logging. Non-sensitive values pass through unchanged."""
    if name.lower() in _SENSITIVE_ARG_NAMES and isinstance(value, str) and value:
        return redact_secret(value)
    return value


def _format_redacted_call(func, args: tuple, kwargs: dict[str, Any]) -> str:
    """Build a function-call string with sensitive arg values redacted."""
    try:
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


def _mark_coroutine_function(wrapper: Callable[..., Any]) -> Callable[..., Any]:
    """Flag ``wrapper`` as a coroutine function for introspecting callers.

    ``functools.wraps`` copies ``__name__``/``__doc__``/``__wrapped__`` but not the
    ``CO_COROUTINE`` code flag, and ``inspect.iscoroutinefunction`` does not follow
    ``__wrapped__``. The async wrappers below are declared with ``async def``, so they
    already carry ``CO_COROUTINE`` and are reported correctly by
    ``inspect.iscoroutinefunction`` on every supported interpreter (3.10+).

    On Python 3.12+ we additionally set the explicit marker via
    ``inspect.markcoroutinefunction``. It is what keeps the classification intact if a
    third-party ``functools.wraps``-style decorator is layered on top: ``wraps`` copies
    ``__dict__``, so the marker propagates where the code flag cannot. The call is a
    no-op on 3.10/3.11 where the API does not exist -- no fallback is needed there
    because the ``async def`` code flag alone already answers ``iscoroutinefunction``.
    """
    if sys.version_info >= (3, 12):
        inspect.markcoroutinefunction(wrapper)
    return wrapper


def func_timer(f):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG.

    Works on both plain functions and coroutine functions. For a coroutine function the
    elapsed time covers the awaited work; a synchronous wrapper would only have timed the
    creation of the coroutine object and reported a plausible-looking microsecond duration.

    Timing uses :func:`time.perf_counter`, not :func:`time.time`. The wall clock is
    NTP-adjustable and can step backwards mid-call, which in a timer yields a negative or
    wildly wrong duration; ``perf_counter`` is monotonic and is the correct clock for
    measuring an elapsed interval.

    Known gap: async *generator* functions (``inspect.isasyncgenfunction``) fall through to
    the synchronous wrapper below, which times only the creation of the generator object --
    the same class of bug the coroutine branch above exists to fix. There are no async
    generators in this package today. Closing the gap needs an ``async def`` wrapper that
    re-yields, and a naive ``async for`` re-yield silently drops ``asend()`` values and
    ``athrow()`` propagation, so it is named here rather than half-fixed.
    """

    if inspect.iscoroutinefunction(f):

        @wraps(f)
        async def async_wrap(*args, **kw):
            if not logger.isEnabledFor(logging.DEBUG):
                return await f(*args, **kw)
            ts = time.perf_counter()
            result = await f(*args, **kw)
            te = time.perf_counter()
            logger.debug(f"  [ {f.__name__}() ] took: {(te - ts):.6f} seconds")
            return result

        return _mark_coroutine_function(async_wrap)

    @wraps(f)
    def wrap(*args, **kw):
        if not logger.isEnabledFor(logging.DEBUG):
            return f(*args, **kw)
        ts = time.perf_counter()
        result = f(*args, **kw)
        te = time.perf_counter()
        logger.debug(f"  [ {f.__name__}() ] took: {(te - ts):.6f} seconds")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying DEBUG logging to a function if enabled in the MBot class.

    Arguments matching known-sensitive names (api_key, discord_id, allycode, ...) are
    redacted before being logged so DEBUG output cannot leak secrets.

    Like :func:`func_timer` this dispatches to an async wrapper for coroutine functions, so
    the decorated result stays a coroutine function. That preserves introspection and keeps
    decorator stacking honest: ``@func_timer`` above ``@func_debug_logger`` (as used in
    ``base.py``) would otherwise see a plain function and fall back to the sync timing path.

    Async *generator* functions (``inspect.isasyncgenfunction``) take the synchronous branch.
    That happens to behave correctly here -- the call is logged, and the generator object is
    returned untouched -- but it is incidental, not designed. See :func:`func_timer` for the
    same gap where it does cause a wrong result.
    """

    if inspect.iscoroutinefunction(f):

        @wraps(f)
        async def async_wrap(*args, **kw):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  [ function {f.__name__}() ] called with {_format_redacted_call(f, args, kw)}")
            return await f(*args, **kw)

        return _mark_coroutine_function(async_wrap)

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
        ValidationError: If the input `zone_status_list` is not a list.
    """
    if not isinstance(zone_status_list, list):
        raise ValidationError("'zone_status' must be a list")

    return sum(int(item["zoneStatus"]["score"]) for item in zone_status_list)


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
        ValidationError: If the provided `tw_data` is not a dictionary, or the necessary
            'awayGuild' profile information is missing from it.
    """
    if not isinstance(tw_data, dict):
        raise ValidationError("'tw_data' must be a dictionary")

    guild_id = tw_data.get("awayGuild", {}).get("profile", {}).get("id")

    if not guild_id:
        raise ValidationError("'tw_data' does not contain 'awayGuild' profile information.")

    return f"https://swgoh.gg/g/{guild_id}/"
