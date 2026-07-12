"""Tests for utility helpers in utils.py."""

import pytest

from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.utils import _redact_value, calc_tw_score_total, get_tw_opponent_url


def test_calc_tw_score_total():
    zones = [
        {"zoneStatus": {"score": "100"}},
        {"zoneStatus": {"score": 250}},
        {"zoneStatus": {"score": "0"}},
    ]
    assert calc_tw_score_total(zones) == 350


def test_calc_tw_score_total_requires_list():
    with pytest.raises(TypeError, match="must be a list"):
        calc_tw_score_total({"zoneStatus": {"score": 1}})


def test_get_tw_opponent_url():
    tw_data = {"awayGuild": {"profile": {"id": "abc123"}}}
    assert get_tw_opponent_url(tw_data) == "https://swgoh.gg/g/abc123/"


def test_get_tw_opponent_url_requires_dict():
    with pytest.raises(TypeError, match="must be a dictionary"):
        get_tw_opponent_url(["not", "a", "dict"])


def test_get_tw_opponent_url_missing_guild():
    with pytest.raises(ValueError, match="awayGuild"):
        get_tw_opponent_url({"homeGuild": {}})


def test_redact_value_masks_sensitive_names():
    assert _redact_value("api_key", "supersecretkey") == "***tkey"
    assert _redact_value("allycode", "123456789") == "***6789"
    assert _redact_value("token", "abc") == "***"


def test_redact_value_passes_through_non_sensitive():
    assert _redact_value("endpoint", "/api/tw") == "/api/tw"
    assert _redact_value("count", 50) == 50


def test_human_time_seconds_and_milliseconds():
    assert MBot.human_time(0.5) == "1970-01-01 00:00:00"
    assert MBot.human_time(1700000000) == "2023-11-14 22:13:20"
    assert MBot.human_time(1700000000000) == "2023-11-14 22:13:20"


def test_human_time_invalid():
    with pytest.raises(ValueError):
        MBot.human_time("not-a-time")
