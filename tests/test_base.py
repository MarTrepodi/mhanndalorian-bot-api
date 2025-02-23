import pytest

from mhanndalorian_bot.base import MBot


def test_cleanse_allycode_valid():
    """Test valid allycode cleansing."""
    result = MBot.cleanse_allycode("123-456-789")
    assert result == "123456789"


def test_cleanse_allycode_invalid_length():
    """Test invalid allycode with incorrect length."""
    with pytest.raises(ValueError, match="Value must be exactly 9 numerical characters."):
        MBot.cleanse_allycode("12345678")


def test_cleanse_allycode_with_non_digit_characters():
    """Test invalid allycode with non-digit characters."""
    with pytest.raises(ValueError, match="Value must be exactly 9 numerical characters."):
        MBot.cleanse_allycode("12345678a")


def test_cleanse_discord_id_valid():
    """Test valid Discord ID cleansing."""
    result = MBot.cleanse_discord_id("123456789012345678")
    assert result == "123456789012345678"


def test_cleanse_discord_id_invalid_length():
    """Test invalid Discord ID with incorrect length."""
    with pytest.raises(ValueError, match="Value must be exactly 18 numerical characters."):
        MBot.cleanse_discord_id("12345678")


def test_cleanse_discord_id_with_non_digit_characters():
    """Test invalid Discord ID with non-digit characters."""
    with pytest.raises(ValueError, match="Value must be exactly 18 numerical characters."):
        MBot.cleanse_discord_id("12345678901234567a")


def test_set_api_key_valid():
    """Test setting a valid API key."""
    bot = MBot(api_key="12345678abcdefgh", allycode="123456789")
    bot.set_api_key("newapikey")
    assert bot.api_key == "newapikey"
    assert bot.headers["api-key"] == "newapikey"


def test_set_api_key_invalid_type():
    """Test setting an invalid API key with a non-string type."""
    bot = MBot(api_key="12345678abcdefgh", allycode="123456789")
    with pytest.raises(ValueError, match="api_key must be a string"):
        bot.set_api_key(12345678)


def test_set_allycode_valid():
    """Test setting a valid allycode."""
    bot = MBot(api_key="12345678abcdefgh", allycode="123456789")
    bot.set_allycode("987-654-321")
    assert bot.allycode == "987654321"
    assert bot.payload["payload"]["allyCode"] == "987654321"


def test_set_allycode_invalid():
    """Test setting an invalid allycode."""
    bot = MBot(api_key="12345678abcdefgh", allycode="123456789")
    with pytest.raises(ValueError, match="Value must be exactly 9 numerical characters."):
        bot.set_allycode("98765")


def test_set_api_host_valid():
    """Test setting a valid API host."""
    bot = MBot(api_key="12345678abcdefgh", allycode="123456789")
    bot.set_api_host("https://testhost.com")
    assert bot.api_host == "https://testhost.com"


def test_set_api_host_invalid_type():
    """Test setting an invalid API host with a non-string type."""
    with pytest.raises(TypeError, match="api_host"):
        MBot.set_api_host(12345)
