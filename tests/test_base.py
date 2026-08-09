import json
import logging

import httpx
import pytest
from pytest_httpx import HTTPXMock

from mhanndalorian_bot.api import API
from mhanndalorian_bot.base import ACCEPT_ENCODING, MBot
from mhanndalorian_bot.exceptions import ValidationError

# httpx prefers brotlicffi when both are present; mirror that so the test compresses with
# whichever implementation the runtime decoder is actually using.
try:  # pragma: no cover - only one branch runs per interpreter
    import brotlicffi as _brotli
except ImportError:  # pragma: no cover
    import brotli as _brotli


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
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
        MBot.cleanse_allycode("12345678")


def test_cleanse_allycode_with_non_digit_characters():
    """Test invalid allycode with non-digit characters."""
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
        MBot.cleanse_allycode("12345678a")


def test_cleanse_discord_id_valid():
    """Test valid Discord ID cleansing."""
    result = MBot.cleanse_discord_id("123456789012345678")
    assert result == "123456789012345678"


def test_cleanse_discord_id_invalid_length():
    """Test invalid Discord ID with incorrect length."""
    with pytest.raises(ValidationError, match="Value must be exactly 18 numerical characters."):
        MBot.cleanse_discord_id("12345678")


def test_cleanse_discord_id_with_non_digit_characters():
    """Test invalid Discord ID with non-digit characters."""
    with pytest.raises(ValidationError, match="Value must be exactly 18 numerical characters."):
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
    with pytest.raises(ValidationError, match="api_key must be a string"):
        bot.set_api_key(12345678)


def test_get_api_key_masks_proportionally():
    """Reveals at most len // 4 trailing characters, never a fixed last-4 tail."""
    bot = make_bot()
    assert bot.get_api_key() == "***efgh"  # 16 chars -> tail of 4

    bot.set_api_key("shortkey")  # 8 chars -> tail of 2
    assert bot.get_api_key() == "***ey"

    bot.set_api_key("tiny")  # 4 chars -> tail of 1
    assert bot.get_api_key() == "***y"

    bot.set_api_key("abc")  # under 4 chars -> nothing revealed
    assert bot.get_api_key() == "***"


def test_sign_debug_logging_does_not_leak_api_key(caplog):
    """Regression: both DEBUG lines in sign() route the key through the proportional mask."""
    bot = make_bot(api_key="0123456789abcdef")

    with caplog.at_level(logging.DEBUG, logger="mhanndalorian_bot.base"):
        bot.sign(method="POST", endpoint="/api/inventory", timestamp="1700000000000")
        bot.sign(method="POST", endpoint="/api/inventory", timestamp="1700000000000", api_key="fedcba9876543210")

    messages = [rec.message for rec in caplog.records if "API key" in rec.message]
    assert len(messages) == 2, f"expected both sign() API-key DEBUG lines, got {messages}"

    container_line, provided_line = messages
    assert container_line == "Using API key from container class: [***cdef]"
    # The provided key is masked too -- and it is the *provided* key that gets reported.
    assert provided_line == "Using provided API key: [***3210]"

    joined = " ".join(rec.message for rec in caplog.records)
    assert "0123456789abcdef" not in joined
    assert "fedcba9876543210" not in joined
    assert "89abcdef" not in joined, "the old last-4-style tail must not reappear"


def test_set_allycode_valid():
    """Test setting a valid allycode."""
    bot = make_bot()
    bot.set_allycode("987-654-321")
    assert bot.allycode == "987654321"
    assert bot.payload["payload"]["allyCode"] == "987654321"


def test_set_allycode_invalid():
    """Test setting an invalid allycode."""
    bot = make_bot()
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
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
    with pytest.raises(ValidationError, match="api_key is required"):
        MBot(allycode="123456789")


def test_missing_allycode_raises(monkeypatch):
    monkeypatch.delenv("MHANN_ALLYCODE", raising=False)
    with pytest.raises(ValidationError, match="allycode is required"):
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
    old_aclient = bot.aclient
    bot.set_verify(False)
    assert bot.client is not old_client
    assert bot.aclient is not old_aclient
    assert bot.client.headers["api-key"] == "12345678abcdefgh"
    # Assert scheme and host separately rather than str(base_url).startswith(...):
    # a prefix check also passes for https://mhanndalorianbot.work.example.com,
    # so it would not catch a rebuild that corrupted the host into something
    # merely prefixed by the real one.
    assert bot.client.base_url.scheme == "https"
    assert bot.client.base_url.host == "mhanndalorianbot.work"
    # set_verify rebuilds both clients; the async one needs the same guarantee.
    assert bot.aclient.base_url.scheme == "https"
    assert bot.aclient.base_url.host == "mhanndalorianbot.work"


def test_api_key_descriptor_rejects_non_string():
    """The managed attribute's own gate raises ValidationError, not the old bare AttributeError."""
    bot = make_bot()
    with pytest.raises(ValidationError, match="must be a string"):
        bot.api_key = 12345


def test_allycode_descriptor_does_not_cleanse():
    """The descriptor is the raw 9-digit gate; set_allycode is the door that cleanses first."""
    bot = make_bot()
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
        bot.allycode = "123-456-789"

    bot.set_allycode("123-456-789")
    assert bot.allycode == "123456789"


# ── Accept-Encoding (spec v1.0.1 info.description) ────────────────────────────


def test_accept_encoding_header_is_set_on_instance_and_clients():
    """The spec asks for `br,gzip,deflate` verbatim, not httpx's decoder-derived default."""
    bot = make_bot()
    assert ACCEPT_ENCODING == "br,gzip,deflate"
    assert bot.headers["Accept-Encoding"] == ACCEPT_ENCODING
    assert bot.client.headers["accept-encoding"] == ACCEPT_ENCODING
    assert bot.aclient.headers["accept-encoding"] == ACCEPT_ENCODING


def test_accept_encoding_survives_header_rewrites():
    """set_api_key / sign / _ensure_api_key_header all reassign client.headers wholesale."""
    bot = make_bot()
    bot.set_api_key("rotated_key")
    bot.sign(method="POST", endpoint="/api/inventory", timestamp="1700000000000")
    assert bot.client.headers["accept-encoding"] == ACCEPT_ENCODING
    assert bot.aclient.headers["accept-encoding"] == ACCEPT_ENCODING


def test_accept_encoding_reaches_the_wire_sync(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    API("mock_api_key", "123456789").fetch_data(endpoint="mock_endpoint")
    assert httpx_mock.get_requests()[0].headers["accept-encoding"] == ACCEPT_ENCODING


async def test_accept_encoding_reaches_the_wire_async(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    await API("mock_api_key", "123456789").fetch_data_async(endpoint="mock_endpoint")
    assert httpx_mock.get_requests()[0].headers["accept-encoding"] == ACCEPT_ENCODING


def test_brotli_encoded_response_is_actually_decoded(httpx_mock: HTTPXMock):
    """Advertising `br` is only honest if the decoder is installed on this interpreter.

    This is the guard on the `httpx[brotli]` extra: if it ever stops resolving on one of the
    CI Python versions, this fails there rather than at runtime against the live API.
    """
    body = json.dumps({"payload": {"enums": True}, "ok": True}).encode()
    compressed = _brotli.compress(body)
    assert compressed != body

    # `stream=` rather than `content=`: pytest-httpx reuses one Response object and "unreads"
    # it by dropping _content, but httpx caches the decoder from the eager read `content=`
    # triggers, so the second pass hits an already-finished decoder. Reproduces with gzip too
    # -- nothing to do with brotli.
    httpx_mock.add_response(
        status_code=200,
        stream=httpx.ByteStream(compressed),
        headers={"Content-Encoding": "br", "Content-Type": "application/json"},
    )
    result = API("mock_api_key", "123456789").fetch_data(endpoint="mock_endpoint")
    assert result == {"payload": {"enums": True}, "ok": True}
