"""Tests for the HMAC request signing implementation in MBot.sign()."""

import hashlib
import hmac as _hmac
import json
import logging

from mhanndalorian_bot.base import MBot

API_KEY = "test_api_key"
TIMESTAMP = "1700000000000"
ENDPOINT = "/api/tw"
PAYLOAD = {"payload": {"allyCode": "123456789", "enums": False}}


def expected_signature(api_key: str, timestamp: str, method: str, endpoint: str, payload: dict) -> str:
    """Independently compute the signature the server expects."""
    payload_str = json.dumps(payload, separators=(",", ":"))
    payload_digest = hashlib.md5(payload_str.encode()).hexdigest()
    hmac_obj = _hmac.new(key=api_key.encode(), digestmod=hashlib.sha256)
    hmac_obj.update(timestamp.encode())
    hmac_obj.update(method.upper().encode())
    hmac_obj.update(endpoint.encode())
    hmac_obj.update(payload_digest.encode())
    return hmac_obj.hexdigest()


def test_sign_deterministic_vector():
    """sign() must produce the documented HMAC-SHA256 signature for a known input."""
    bot = MBot(api_key=API_KEY, allycode="123456789")
    bot.sign(method="post", endpoint=ENDPOINT, payload=PAYLOAD, timestamp=TIMESTAMP)

    assert bot.headers["Authorization"] == expected_signature(API_KEY, TIMESTAMP, "POST", ENDPOINT, PAYLOAD)
    assert bot.headers["x-timestamp"] == TIMESTAMP
    assert "api-key" not in bot.headers
    assert bot.client.headers["Authorization"] == bot.headers["Authorization"]
    assert bot.aclient.headers["Authorization"] == bot.headers["Authorization"]


def test_sign_no_secrets_in_debug_logs(caplog):
    """DEBUG logging must not leak the API key or any HMAC signature material."""
    bot = MBot(api_key=API_KEY, allycode="123456789")
    with caplog.at_level(logging.DEBUG):
        bot.sign(method="POST", endpoint=ENDPOINT, payload=PAYLOAD, timestamp=TIMESTAMP)

    signature = bot.headers["Authorization"]
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert API_KEY not in log_text
    assert signature not in log_text


def test_sign_uses_default_payload():
    """When no payload is given, sign() signs the instance default payload."""
    bot = MBot(api_key=API_KEY, allycode="123456789")
    bot.sign(method="POST", endpoint=ENDPOINT, timestamp=TIMESTAMP)
    assert bot.headers["Authorization"] == expected_signature(
        API_KEY, TIMESTAMP, "POST", ENDPOINT, {"payload": {"allyCode": "123456789"}}
    )


def test_api_key_header_restored_after_signed_request():
    """An unsigned request after a signed one must send the plaintext api-key header again."""
    bot = MBot(api_key=API_KEY, allycode="123456789")
    bot.sign(method="POST", endpoint=ENDPOINT, payload=PAYLOAD, timestamp=TIMESTAMP)
    assert "api-key" not in bot.headers

    bot._ensure_api_key_header()
    assert bot.headers["api-key"] == API_KEY
    assert bot.client.headers["api-key"] == API_KEY
    assert bot.aclient.headers["api-key"] == API_KEY
