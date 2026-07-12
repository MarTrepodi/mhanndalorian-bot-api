# tests/test_api.py
import json

import pytest
from pytest_httpx import HTTPXMock

from mhanndalorian_bot.api import API
from mhanndalorian_bot.attrs import EndPoint, LeaderboardType

api_instance = API("mock_api_key", "123456789")

# (helper name, expected URL path) for every named endpoint helper taking only **kwargs
SIMPLE_HELPERS = [
    ("fetch_tw", "/api/tw"),
    ("fetch_raid", "/api/activeraid"),
    ("fetch_twlogs", "/api/twlogs"),
    ("fetch_tw_leaderboard", "/api/twleaderboard"),
    ("fetch_gac", "/api/gac"),
    ("fetch_inventory", "/api/inventory"),
    ("fetch_tb", "/api/tb"),
    ("fetch_tblogs", "/api/tblogs"),
    ("fetch_tb_history", "/api/tbleaderboardhistory"),
    ("fetch_arena", "/api/leaderboard"),
    ("fetch_squad_presets", "/api/squadpresets"),
    ("fetch_conquest", "/api/conquest"),
    ("fetch_events", "/api/events"),
]


def sent_payload(httpx_mock: HTTPXMock) -> dict:
    return json.loads(httpx_mock.get_requests()[0].content)


def test_mock_fetch_data_sync(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = api_instance.fetch_data(endpoint="mock_endpoint")
    assert response == {"success": True}


async def test_mock_fetch_data_async(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = await api_instance.fetch_data_async(endpoint=EndPoint.TW)
    assert response == {"success": True}


@pytest.mark.parametrize("helper, path", SIMPLE_HELPERS)
def test_named_helpers_hit_expected_endpoint(httpx_mock: HTTPXMock, helper, path):
    """Every sync helper posts to its documented endpoint with enums defaulted to False."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    result = getattr(api_instance, helper)()
    assert result == {"ok": True}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == path
    assert sent_payload(httpx_mock)["payload"]["enums"] is False


@pytest.mark.parametrize("helper, path", SIMPLE_HELPERS)
async def test_named_helpers_async_hit_expected_endpoint(httpx_mock: HTTPXMock, helper, path):
    """Every async helper posts to its documented endpoint with enums defaulted to False."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    result = await getattr(api_instance, f"{helper}_async")()
    assert result == {"ok": True}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == path
    assert sent_payload(httpx_mock)["payload"]["enums"] is False


def test_fetch_player_by_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"name": "player"}}, status_code=200)
    result = api_instance.fetch_player("987654321")
    assert result == {"name": "player"}
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "987654321"


def test_fetch_player_by_player_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"name": "player"}}, status_code=200)
    result = api_instance.fetch_player(player_id="PID123")
    assert result == {"name": "player"}
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["playerId"] == "PID123"
    assert "allyCode" not in payload


def test_fetch_player_identity_mutually_exclusive():
    with pytest.raises(ValueError, match="mutually exclusive"):
        api_instance.fetch_player("987654321", player_id="PID123")


def test_fetch_player_defaults_to_instance_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    api_instance.fetch_player()
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "123456789"


async def test_fetch_player_arena_async_by_player_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    await api_instance.fetch_player_arena_async(player_id="PID123")
    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/playerarena"
    assert sent_payload(httpx_mock)["payload"]["playerId"] == "PID123"


def test_fetch_player_arena_by_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_player_arena("987654321")
    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/playerarena"
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "987654321"


def test_fetch_guild(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"guild": {"name": "guild"}}}, status_code=200)
    result = api_instance.fetch_guild("GUILD_ID")
    assert result == {"name": "guild"}
    assert sent_payload(httpx_mock)["payload"]["guildId"] == "GUILD_ID"


def test_fetch_guild_leaderboard(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {"leaderboard": []}}, status_code=200)
    result = api_instance.fetch_guild_leaderboard(
        LeaderboardType.GUILD_RAID_HIGH_WATERMARK, count=10, def_id="GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"
    )
    assert result == {"data": {"leaderboard": []}}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/guildleaderboard"
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == 6
    assert payload["count"] == 10
    assert payload["defId"] == "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"


async def test_fetch_guild_leaderboard_async_accepts_int(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    await api_instance.fetch_guild_leaderboard_async(3)
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == 3
    assert payload["count"] == 50
    assert "defId" not in payload


@pytest.mark.parametrize("count", [0, 201, -5])
def test_fetch_guild_leaderboard_count_bounds(count):
    with pytest.raises(ValueError, match="between 1 and 200"):
        api_instance.fetch_guild_leaderboard(LeaderboardType.GUILD_GALACTIC_POWER, count=count)


def test_fetch_guild_leaderboard_invalid_type():
    with pytest.raises(ValueError):
        api_instance.fetch_guild_leaderboard(2)  # 2 is not a valid LeaderboardType


def test_user_discord_id_injected_and_forces_hmac(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    api_instance.fetch_data(endpoint="tw", hmac=False, user_discord_id="123456789987654321")

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload["payload"]["userDiscordId"] == "123456789987654321"
    # HMAC signing was forced despite hmac=False
    assert "authorization" in request.headers
    assert "x-timestamp" in request.headers


def test_hmac_false_sends_api_key_header(httpx_mock: HTTPXMock):
    """After a signed request, an unsigned request must carry the plaintext api-key again."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    httpx_mock.add_response(json={"ok": True}, status_code=200)

    api_instance.fetch_data(endpoint="tw", hmac=True)
    api_instance.fetch_data(endpoint="tw", hmac=False)

    signed, unsigned = httpx_mock.get_requests()
    assert "authorization" in signed.headers
    assert unsigned.headers.get("api-key") == "mock_api_key"
    assert "authorization" not in unsigned.headers
