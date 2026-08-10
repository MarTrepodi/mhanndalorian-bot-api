import json

import pytest
from pytest_httpx import HTTPXMock

from mhanndalorian_bot.exceptions import ValidationError
from mhanndalorian_bot.registry import Registry


@pytest.fixture(scope="package", autouse=True)
def registry_instance():
    """Fixture to create a Registry instance for testing."""
    return Registry(api_key="test_api_key", allycode="123456789", discord_id="123456789987654321")


def test_mock_fetch_player_valid_allycode(httpx_mock: HTTPXMock, registry_instance):
    """Test fetching a player with a valid allycode."""
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = registry_instance.fetch_player(allycode="123-456-789", hmac=True)
    assert response is not None
    assert isinstance(response, dict)


def test_fetch_player_invalid_allycode(httpx_mock: HTTPXMock, registry_instance):
    """Test fetching a player with an invalid allycode."""
    with pytest.raises(ValidationError, match="Invalid allyCode"):
        registry_instance.fetch_player(allycode="invalid_allycode", hmac=True)


def test_register_player_valid_data(httpx_mock: HTTPXMock, registry_instance):
    """Test registering a player with valid discord ID and allycode."""
    httpx_mock.add_response(
        json={"unlockedPlayerPortrait": "portrait", "unlockedPlayerTitle": "title"}, status_code=200
    )
    response = registry_instance.register_player(discord_id="123456789987654321", allycode="123-456-789", hmac=True)
    assert response == {"unlockedPlayerPortrait": "portrait", "unlockedPlayerTitle": "title"}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/comlink"
    sent = json.loads(request.content)
    assert sent == {
        "discordId": "123456789987654321",
        "method": "registration",
        "payload": {"allyCode": "123456789"},
        "enums": False,
    }
    assert "authorization" in request.headers
    assert "x-timestamp" in request.headers


def test_register_player_invalid_data(registry_instance):
    """Test registering a player with invalid data."""
    with pytest.raises(ValidationError, match="Invalid"):
        registry_instance.register_player(discord_id="", allycode="invalid_allycode", hmac=True)


def test_verify_player_valid_data(httpx_mock: HTTPXMock, registry_instance):
    """Test verifying a player with valid discord ID and allycode."""
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    result = registry_instance.verify_player(
        discord_id="123456789987654321",
        allycode="123-456-789",
        primary=False,
        hmac=True,
    )
    assert result is True

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/comlink"
    sent = json.loads(request.content)
    assert sent == {
        "discordId": "123456789987654321",
        "method": "verification",
        "payload": {"allyCode": "123456789"},
        "enums": False,
        "primary": False,
    }


def test_verify_player_not_verified(httpx_mock: HTTPXMock, registry_instance):
    """A 200 response without verified=True means the player is not verified."""
    httpx_mock.add_response(json={"verified": False}, status_code=200)
    result = registry_instance.verify_player(discord_id="123456789987654321", allycode="123-456-789")
    assert result is False


def test_verify_player_invalid_data(registry_instance):
    """Test verifying a player with invalid data."""
    with pytest.raises(ValidationError, match="Invalid"):
        registry_instance.verify_player(discord_id="", allycode="invalid_allycode", primary=False, hmac=True)


# --- primary tri-state ---------------------------------------------------------------------------
# The registry assigns primary=yes when a user has no other registered accounts, but only if the
# caller leaves `primary` unspecified. Sending false -- the pre-0.11.0 default -- silently opted
# first-time users out of that.


def test_verify_player_omits_primary_when_unspecified(httpx_mock: HTTPXMock, registry_instance):
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    registry_instance.verify_player(discord_id="123456789987654321", allycode="123-456-789")
    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert "primary" not in sent, "an unspecified primary must not reach the wire at all"


@pytest.mark.parametrize("value", [True, False])
def test_verify_player_sends_explicit_primary_as_a_json_boolean(httpx_mock: HTTPXMock, registry_instance, value):
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    registry_instance.verify_player(discord_id="123456789987654321", allycode="123-456-789", primary=value)
    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent["primary"] is value


async def test_verify_player_async_omits_primary_when_unspecified(httpx_mock: HTTPXMock, registry_instance):
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    await registry_instance.verify_player_async(discord_id="123456789987654321", allycode="123-456-789")
    assert "primary" not in json.loads(httpx_mock.get_requests()[0].content)


def test_all_comlink_payloads_carry_the_enums_flag(httpx_mock: HTTPXMock, registry_instance):
    """Every documented SWGOH-Registry snippet sends enums; /comlink has no OpenAPI spec to fall
    back on, so the README snippet is the only contract there is."""
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    registry_instance.register_player(discord_id="123456789987654321", allycode="123-456-789")
    httpx_mock.add_response(json={"verified": True}, status_code=200)
    registry_instance.verify_player(discord_id="123456789987654321", allycode="123-456-789")
    for req in httpx_mock.get_requests():
        assert json.loads(req.content)["enums"] is False


# --- x-discord-id enforcement on /database ------------------------------------------------------
# Registry does NOT require a discord_id at construction, and its methods bypass fetch_data, so the
# guard has to be applied on its own paths rather than inherited.


def test_registry_fetch_player_requires_a_discord_id():
    bare = Registry(api_key="test_api_key", allycode="123456789")
    with pytest.raises(ValidationError, match="requires a Discord ID"):
        bare.fetch_player(allycode="987654321")


async def test_registry_fetch_player_async_requires_a_discord_id():
    bare = Registry(api_key="test_api_key", allycode="123456789")
    with pytest.raises(ValidationError, match="requires a Discord ID"):
        await bare.fetch_player_async(allycode="987654321")


def test_registry_comlink_paths_are_not_gated(httpx_mock: HTTPXMock):
    """/comlink is absent from the spec and carries its Discord ID in the payload, so the
    header rule does not apply to it."""
    bare = Registry(api_key="test_api_key", allycode="123456789")
    httpx_mock.add_response(json={"verified": False}, status_code=200)
    bare.register_player(discord_id="123456789012345678", allycode="123456789")  # must not raise
