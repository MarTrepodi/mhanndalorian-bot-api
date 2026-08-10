"""Tests for utility helpers in utils.py."""

import asyncio
import inspect
import logging

import pytest

from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.exceptions import ValidationError
from mhanndalorian_bot.utils import (
    _redact_value,
    calc_tw_score_total,
    func_debug_logger,
    func_timer,
    get_tw_opponent_url,
    redact_secret,
)

UTILS_LOGGER = "mhanndalorian_bot.utils"
SLEEP = 0.02


def _timed_seconds(caplog, func_name):
    """Extract the duration func_timer logged for ``func_name`` from captured records."""
    lines = [rec.message for rec in caplog.records if f"{func_name}()" in rec.message and "took:" in rec.message]
    assert lines, f"expected a func_timer log line for {func_name}(), got {[r.message for r in caplog.records]}"
    # Line format: "  [ func_name() ] took: 0.012345 seconds"
    return float(lines[-1].split("took:")[1].strip().split()[0])


def test_calc_tw_score_total():
    zones = [
        {"zoneStatus": {"score": "100"}},
        {"zoneStatus": {"score": 250}},
        {"zoneStatus": {"score": "0"}},
    ]
    assert calc_tw_score_total(zones) == 350


def test_calc_tw_score_total_requires_list():
    with pytest.raises(ValidationError, match="must be a list"):
        calc_tw_score_total({"zoneStatus": {"score": 1}})


def test_get_tw_opponent_url():
    tw_data = {"awayGuild": {"profile": {"id": "abc123"}}}
    assert get_tw_opponent_url(tw_data) == "https://swgoh.gg/g/abc123/"


def test_get_tw_opponent_url_requires_dict():
    with pytest.raises(ValidationError, match="must be a dictionary"):
        get_tw_opponent_url(["not", "a", "dict"])


def test_get_tw_opponent_url_missing_guild():
    with pytest.raises(ValidationError, match="awayGuild"):
        get_tw_opponent_url({"homeGuild": {}})


def test_redact_value_masks_sensitive_names():
    assert _redact_value("api_key", "supersecretkey") == "***key"  # 14 chars -> tail of 3
    assert _redact_value("allycode", "123456789") == "***89"  # 9 chars -> tail of 2
    assert _redact_value("token", "abc") == "***"


def test_redact_value_reveals_at_most_a_quarter_of_the_secret():
    """Regression: a fixed last-4 tail put 4 of a 9-digit allycode's digits in the clear."""
    for secret in ("1", "ab", "abc"):
        assert _redact_value("token", secret) == "***", f"{secret!r} must reveal nothing"

    long_key = "0123456789abcdef0123456789abcdef01234567"  # 40 chars -> tail of 10
    assert len(long_key) == 40
    assert _redact_value("api_key", long_key) == "***ef01234567"


def test_redact_secret_scales_with_length():
    assert redact_secret("") == "***"
    assert redact_secret("abcd") == "***d"
    assert redact_secret("12345678abcdefgh") == "***efgh"
    # The revealed tail never exceeds a quarter of the secret, at any length.
    for length in range(0, 65):
        secret = "x" * length
        assert len(redact_secret(secret)) - 3 == length // 4


def test_redact_value_passes_through_non_sensitive():
    assert _redact_value("endpoint", "/api/tw") == "/api/tw"
    assert _redact_value("count", 50) == 50


def test_human_time_seconds_and_milliseconds():
    assert MBot.human_time(0.5) == "1970-01-01 00:00:00"
    assert MBot.human_time(1700000000) == "2023-11-14 22:13:20"
    assert MBot.human_time(1700000000000) == "2023-11-14 22:13:20"


def test_human_time_invalid():
    with pytest.raises(ValidationError, match="valid integer or float"):
        MBot.human_time("not-a-time")


# ── func_timer ─────────────────────────────────────────────────────────────


def test_func_timer_sync_logs_elapsed_time(caplog):
    @func_timer
    def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG, logger=UTILS_LOGGER):
        assert add(2, 3) == 5

    assert _timed_seconds(caplog, "add") >= 0.0


def test_func_timer_sync_leaves_plain_function_plain():
    @func_timer
    def add(a, b):
        return a + b

    assert not inspect.iscoroutinefunction(add)


async def test_func_timer_async_times_the_awaited_work(caplog):
    """Regression: a sync wrapper would time coroutine *creation* and report microseconds."""

    @func_timer
    async def slow():
        await asyncio.sleep(SLEEP)
        return "done"

    with caplog.at_level(logging.DEBUG, logger=UTILS_LOGGER):
        assert await slow() == "done"

    seconds = _timed_seconds(caplog, "slow")
    assert seconds >= SLEEP * 0.75, f"recorded {seconds}s, expected at least the {SLEEP}s sleep"


async def test_func_timer_async_preserves_coroutine_introspection():
    """functools.wraps drops CO_COROUTINE, so the wrapper must be an async def (and marked on 3.12+)."""

    @func_timer
    async def endpoint():
        return "payload"

    assert inspect.iscoroutinefunction(endpoint)
    assert inspect.isawaitable(coro := endpoint())
    assert await coro == "payload"


async def test_func_timer_async_is_silent_when_debug_disabled(caplog):
    @func_timer
    async def echo(value):
        return value

    with caplog.at_level(logging.INFO, logger=UTILS_LOGGER):
        assert await echo("ok") == "ok"

    assert not [rec for rec in caplog.records if "took:" in rec.message]


# ── func_debug_logger ──────────────────────────────────────────────────────


async def test_func_debug_logger_async_awaits_and_redacts(caplog):
    @func_debug_logger
    async def fetch(allycode, count):
        await asyncio.sleep(0)
        return f"{allycode}:{count}"

    with caplog.at_level(logging.DEBUG, logger=UTILS_LOGGER):
        assert await fetch("123456789", 5) == "123456789:5"

    messages = [rec.message for rec in caplog.records if "fetch()" in rec.message]
    assert messages, "expected a func_debug_logger call line"
    assert "***89" in messages[-1]
    assert "6789" not in messages[-1]
    assert "123456789" not in messages[-1]


async def test_func_debug_logger_async_preserves_coroutine_introspection():
    @func_debug_logger
    async def endpoint():
        return "payload"

    assert inspect.iscoroutinefunction(endpoint)
    assert await endpoint() == "payload"


def test_func_debug_logger_sync_leaves_plain_function_plain():
    @func_debug_logger
    def endpoint():
        return "payload"

    assert not inspect.iscoroutinefunction(endpoint)
    assert endpoint() == "payload"


async def test_stacked_decorators_on_coroutine_still_time_awaited_work(caplog):
    """Mirrors base.py's ``@func_timer`` over ``@func_debug_logger`` stack."""

    @func_timer
    @func_debug_logger
    async def slow(allycode):
        await asyncio.sleep(SLEEP)
        return allycode

    assert inspect.iscoroutinefunction(slow)

    with caplog.at_level(logging.DEBUG, logger=UTILS_LOGGER):
        assert await slow("123456789") == "123456789"

    seconds = _timed_seconds(caplog, "slow")
    assert seconds >= SLEEP * 0.75, f"recorded {seconds}s, expected at least the {SLEEP}s sleep"


# --- decorator type preservation ----------------------------------------------------------------
# func_timer and func_debug_logger were unannotated, which erased the signature of all 17 public
# methods they decorate: a type checker reported them as `Unknown`, so an IDE offered no
# parameters, no return type and no completion. These pin the properties that fix relies on.


def test_func_timer_preserves_the_wrapped_signature():
    import inspect

    def sample(a: int, b: str = "x") -> float:
        return 1.0

    assert inspect.signature(func_timer(sample)) == inspect.signature(sample)


def test_func_debug_logger_preserves_the_wrapped_signature():
    import inspect

    def sample(a: int, *, b: str = "x") -> float:
        return 1.0

    assert inspect.signature(func_debug_logger(sample)) == inspect.signature(sample)


def test_decorators_survive_a_callable_without_a_dunder_name():
    """Callable[P, R] carries no __name__; a partial or callable instance must not crash logging."""
    import functools
    import logging

    def sample(a: int) -> int:
        return a

    partial = functools.partial(sample)
    assert not hasattr(partial, "__name__")
    logging.getLogger("mhanndalorian_bot.utils").setLevel(logging.DEBUG)
    assert func_timer(partial)(3) == 3
    assert func_debug_logger(partial)(4) == 4
