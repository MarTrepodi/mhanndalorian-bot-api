import pytest
from pytest_httpx import HTTPXMock

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
    with pytest.raises(ValueError, match="Invalid allyCode"):
        response = registry_instance.fetch_player(allycode="invalid_allycode", hmac=True)


def test_register_player_valid_data(registry_instance):
    """Test registering a player with valid discord ID and allycode."""
    response = registry_instance.register_player(discord_id="123456789987654321", allycode="123-456-789", hmac=True)
    assert response is not None
    assert isinstance(response, dict)


def test_register_player_invalid_data(registry_instance):
    """Test registering a player with invalid data."""
    with pytest.raises(ValueError, match="Invalid"):
        response = registry_instance.register_player(discord_id="", allycode="invalid_allycode", hmac=True)


def test_verify_player_valid_data(registry_instance):
    """Test verifying a player with valid discord ID and allycode."""
    result = registry_instance.verify_player(discord_id="123456789987654321", allycode="123-456-789", primary=False, hmac=True)
    assert isinstance(result, bool)


def test_verify_player_invalid_data(registry_instance):
    """Test verifying a player with invalid data."""
    with pytest.raises(ValueError, match="Invalid"):
        result = registry_instance.verify_player(discord_id="", allycode="invalid_allycode", primary=False, hmac=True)
