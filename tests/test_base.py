import httpx
import pytest

from mhanndalorian_bot.base import MBot


def make_bot(**kwargs) -> MBot:
    kwargs.setdefault("api_key", "12345678abcdefgh")
    kwargs.setdefault("allycode", "123456789")
    return MBot(**kwargs)


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
    bot = make_bot()
    bot.set_api_key("newapikey")
    assert bot.api_key == "newapikey"
    assert bot.headers["api-key"] == "newapikey"


def test_set_api_key_invalid_type():
    """Test setting an invalid API key with a non-string type."""
    bot = make_bot()
    with pytest.raises(ValueError, match="api_key must be a string"):
        bot.set_api_key(12345678)


def test_set_allycode_valid():
    """Test setting a valid allycode."""
    bot = make_bot()
    bot.set_allycode("987-654-321")
    assert bot.allycode == "987654321"
    assert bot.payload["payload"]["allyCode"] == "987654321"


def test_set_allycode_invalid():
    """Test setting an invalid allycode."""
    bot = make_bot()
    with pytest.raises(ValueError, match="Value must be exactly 9 numerical characters."):
        bot.set_allycode("98765")


def test_set_api_host_valid():
    """Test setting a valid API host."""
    bot = make_bot()
    bot.set_api_host("https://testhost.com")
    assert bot.api_host == "https://testhost.com"


def test_set_api_host_invalid_type():
    """Test setting an invalid API host with a non-string type."""
    with pytest.raises(TypeError, match="api_host"):
        MBot.set_api_host(12345)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("MHANN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key is required"):
        MBot(allycode="123456789")


def test_missing_allycode_raises(monkeypatch):
    monkeypatch.delenv("MHANN_ALLYCODE", raising=False)
    with pytest.raises(ValueError, match="allycode is required"):
        MBot(api_key="12345678abcdefgh")


def test_env_var_credential_fallback(monkeypatch):
    monkeypatch.setenv("MHANN_API_KEY", "env_api_key")
    monkeypatch.setenv("MHANN_ALLYCODE", "987654321")
    monkeypatch.setenv("MHANN_DISCORD_ID", "123456789987654321")

    bot = MBot()
    assert bot.api_key == "env_api_key"
    assert bot.allycode == "987654321"
    assert bot.headers["x-discord-id"] == "123456789987654321"


def test_arguments_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("MHANN_API_KEY", "env_api_key")
    monkeypatch.setenv("MHANN_ALLYCODE", "987654321")

    bot = MBot(api_key="explicit_key", allycode="111111111")
    assert bot.api_key == "explicit_key"
    assert bot.allycode == "111111111"


def test_instances_are_isolated():
    """Two instances must not share headers, payloads, or HTTP clients."""
    bot_a = make_bot(api_key="key_aaaa", allycode="111111111")
    bot_b = make_bot(api_key="key_bbbb", allycode="222222222")

    assert bot_a.client is not bot_b.client
    assert bot_a.aclient is not bot_b.aclient
    assert bot_a.headers is not bot_b.headers
    assert bot_a.headers["api-key"] == "key_aaaa"
    assert bot_b.headers["api-key"] == "key_bbbb"
    assert bot_a.client.headers["api-key"] == "key_aaaa"
    assert bot_b.client.headers["api-key"] == "key_bbbb"

    bot_a.set_allycode("333333333")
    assert bot_b.payload["payload"]["allyCode"] == "222222222"


def test_timeout_and_retries_plumbing():
    bot = make_bot(timeout=10.0, retries=2)
    assert bot.client.timeout == httpx.Timeout(10.0)
    assert isinstance(bot.client._transport, httpx.HTTPTransport)
    assert isinstance(bot.aclient._transport, httpx.AsyncHTTPTransport)

    default_bot = make_bot()
    assert default_bot.client.timeout == httpx.Timeout(75.0)


def test_context_manager_closes_client():
    with make_bot() as bot:
        assert not bot.client.is_closed
    assert bot.client.is_closed


async def test_async_context_manager_closes_aclient():
    async with make_bot() as bot:
        assert not bot.aclient.is_closed
    assert bot.aclient.is_closed


def test_set_verify_rebuilds_clients():
    bot = make_bot()
    old_client = bot.client
    bot.set_verify(False)
    assert bot.client is not old_client
    assert bot.client.headers["api-key"] == "12345678abcdefgh"
    assert str(bot.client.base_url).startswith("https://mhanndalorianbot.work")
