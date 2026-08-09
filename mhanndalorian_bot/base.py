"""
Base class definition for core object for storing and sharing information for use by all modules
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import logging
import os
import time
from json import dumps
from typing import Any

import httpx
from sentinels import Sentinel

from mhanndalorian_bot.attrs import AllyCode, APIKey, EndPoint
from mhanndalorian_bot.exceptions import ValidationError
from mhanndalorian_bot.utils import func_debug_logger, func_timer, redact_secret

NotSet = Sentinel("NotSet")

_REDACTED = "[REDACTED]"
_SENSITIVE_HEADER_KEYS = frozenset({"api-key", "authorization", "x-discord-id"})

# Spec v1.0.1 info.description: "Send `Content-Type: application/json` and
# `Accept-Encoding: br,gzip,deflate`." Sent verbatim rather than left to httpx's default
# (which is derived from the installed decoders and orders gzip first). Advertising `br`
# is only safe because the `httpx[brotli]` extra is a hard dependency -- see pyproject.toml.
ACCEPT_ENCODING = "br,gzip,deflate"


def _redact_headers(headers: dict[str, str] | httpx.Headers) -> dict[str, str]:
    """Return a copy of headers with sensitive values replaced by a redaction marker."""
    redacted: dict[str, str] = {}
    for key, value in dict(headers).items():
        redacted[key] = _REDACTED if key.lower() in _SENSITIVE_HEADER_KEYS else value
    return redacted


class MBot:
    """Base class for MBot modules

    Args
        api_key: MHanndalorian Bot API key as a string. Falls back to the MHANN_API_KEY
                 environment variable when not provided.
        allycode: Player allycode as a string. Falls back to the MHANN_ALLYCODE
                  environment variable when not provided.
        discord_id: Discord user ID as a string. This is used to identify the source of requests made on behalf
                    of another player. Falls back to the MHANN_DISCORD_ID environment variable when not provided.

    Keyword Args
        api_host: Optional host URL for MHanndalorian Bot API, defaults to https://mhanndalorianbot.work/
        hmac: Boolean flag indicating whether the endpoints should use HMAC signature authentication, Default: True
        debug: Boolean flag indicating whether debug logging should be enabled, Default: False
        verify: TLS verification setting forwarded to httpx clients. True (default) uses the system trust
                store; pass a path to a CA bundle for custom certs, or False to disable verification
                (NOT recommended).
        timeout: Request timeout in seconds forwarded to the httpx clients, Default: 75.0
        retries: Number of connection-level retries for failed connection attempts, Default: 0.
                 Applies to connection establishment only; failed responses are never retried.
    """

    api_host: str = "https://mhanndalorianbot.work"
    logger: logging.Logger = logging.getLogger(__name__)

    debug = False
    hmac = True
    api_key = APIKey()
    allycode = AllyCode()

    def __init__(
        self,
        api_key: str | None = None,
        allycode: str | None = None,
        discord_id: str | None = None,
        *,
        api_host: str | None = None,
        hmac: bool | None = True,
        debug: bool | None = False,
        verify: bool | str = True,
        timeout: float = 75.0,
        retries: int = 0,
    ):

        api_key = api_key or os.environ.get("MHANN_API_KEY")
        allycode = allycode or os.environ.get("MHANN_ALLYCODE")
        discord_id = discord_id or os.environ.get("MHANN_DISCORD_ID")

        if not api_key:
            raise ValidationError("api_key is required (argument or MHANN_API_KEY environment variable)")
        if not allycode:
            raise ValidationError("allycode is required (argument or MHANN_ALLYCODE environment variable)")

        self.headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept-Encoding": ACCEPT_ENCODING,
        }
        self.payload: dict[str, Any] = {"payload": {"allyCode": ""}}

        if isinstance(api_host, str):
            self.api_host = api_host

        self._timeout = timeout
        self._retries = retries
        self._verify: bool | str = verify
        self._build_clients()

        self.set_api_key(api_key)
        self.set_allycode(allycode)

        if discord_id:
            self.set_discord_id(discord_id)

        if debug is not None:
            self.debug = debug

        if isinstance(hmac, bool):
            self.hmac = hmac

    def _build_clients(self) -> None:
        """Construct the instance httpx clients from the stored timeout/retries/verify settings."""
        client_kwargs: dict[str, Any] = {
            "base_url": self.api_host,
            "timeout": self._timeout,
            "verify": self._verify,
            "headers": self.headers,
        }
        if self._retries > 0:
            self.client = httpx.Client(transport=httpx.HTTPTransport(retries=self._retries), **client_kwargs)
            self.aclient = httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=self._retries), **client_kwargs)
        else:
            self.client = httpx.Client(**client_kwargs)
            self.aclient = httpx.AsyncClient(**client_kwargs)

    def __enter__(self) -> MBot:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    async def __aenter__(self) -> MBot:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def close(self) -> None:
        """Close the synchronous HTTP client."""
        self.client.close()

    async def aclose(self) -> None:
        """Close the asynchronous HTTP client."""
        await self.aclient.aclose()

    @staticmethod
    def human_time(unix_time: int | float) -> str:
        """Convert unix time to human-readable string

        Args:
            unix_time (int|float): standard unix time in seconds or milliseconds

        Returns:
            str: human-readable time string

        Raises:
            ValidationError: if `unix_time` is not a non-zero int or float.

        Notes:
            If the provided unix time is invalid or an error occurs, the default time string returned
            is 1970-01-01 00:00:00

        """
        if not isinstance(unix_time, (int, float)) or not unix_time:
            err_msg = "A valid integer or float 'unix_time' argument is required."
            raise ValidationError(err_msg)
        from datetime import datetime, timezone

        if isinstance(unix_time, float):
            unix_time = int(unix_time)
        if len(str(unix_time)) >= 13:
            unix_time /= 1000
        return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    @func_debug_logger
    def cleanse_allycode(allycode: str) -> str:
        """Remove any dashes from provided string and verify the result contains exactly 9 digits

        Raises:
            ValidationError: if the value is not a string, or is not exactly 9 digits once
                             dashes are stripped.
        """
        if not isinstance(allycode, str):
            raise ValidationError(f"{allycode} must be a string, not type:{type(allycode)}")

        allycode = allycode.replace("-", "")

        if not allycode.isdigit() or len(allycode) != 9:
            raise ValidationError(f"Invalid allyCode ({allycode}): Value must be exactly 9 numerical characters.")

        return allycode

    @staticmethod
    @func_debug_logger
    def cleanse_discord_id(discord_id: str) -> str:
        """Validate that discord ID is an 18 character string of only numerical digits

        Raises:
            ValidationError: if the value is not a string of exactly 18 digits.
        """
        if not isinstance(discord_id, str):
            raise ValidationError(f"{discord_id} must be a string, not type: {type(discord_id)}")

        if not discord_id.isdigit() or len(discord_id) != 18:
            raise ValidationError(f"Invalid Discord ID ({discord_id}): Value must be exactly 18 numerical characters.")

        return discord_id

    def get_api_key(self) -> str:
        """Return the stored API key masked for logging purposes.

        Reveals at most ``len(api_key) // 4`` trailing characters -- see
        :func:`mhanndalorian_bot.utils.redact_secret`. A 16-character key logs as
        ``***efgh``; anything under 4 characters logs as ``***``.
        """
        return redact_secret(self.api_key)

    @func_debug_logger
    def set_api_key(self, api_key: str) -> None:
        """Set the api_key value for the container class and update relevant attributes (including headers)"""

        if not isinstance(api_key, str):
            raise ValidationError("api_key must be a string")

        self.api_key = api_key

        self.headers["api-key"] = self.api_key
        self.client.headers = self.headers
        self.aclient.headers = self.headers

    @func_debug_logger
    def set_allycode(self, allycode: str) -> None:
        """Set the allycode value for the container class and update relevant attributes"""

        allycode = self.cleanse_allycode(allycode)

        self.allycode = allycode

        self.payload["payload"]["allyCode"] = allycode

    @func_debug_logger
    def set_discord_id(self, discord_id: str) -> None:
        """Set the discord_id value for the container class and update relevant attributes"""

        discord_id = self.cleanse_discord_id(discord_id)

        self.headers["x-discord-id"] = discord_id

    @func_debug_logger
    def set_api_host(self, api_host: str) -> None:
        """Set the api_host value for the container class and update relevant attributes"""

        if not isinstance(api_host, str):
            raise ValidationError("api_host must be a string")

        self.api_host = api_host

        self.client.base_url = f"{api_host}"
        self.aclient.base_url = f"{api_host}"

    def set_verify(self, verify: bool | str) -> None:
        """Rebuild the HTTP clients with the specified TLS verification setting.

        Args:
            verify: True (default) uses the system trust store, False disables verification
                    (NOT recommended), or a string path to a CA bundle for custom certs.

        Note:
            The previous async client is closed best-effort; if called while async requests
            are in flight, call ``aclose()`` first.
        """
        self.client.close()
        self._verify = verify
        self._build_clients()

    def _ensure_api_key_header(self) -> None:
        """Re-assert the ``api-key`` header on both HTTP clients.

        ``sign()`` removes the plaintext ``api-key`` header when building an HMAC-signed
        request, so an unsigned request issued afterwards must restore it first. Stale
        HMAC headers from a previous signed request are dropped.
        """
        self.headers.pop("Authorization", None)
        self.headers.pop("x-timestamp", None)
        self.headers["api-key"] = self.api_key
        self.client.headers = self.headers
        self.aclient.headers = self.headers

    @func_debug_logger
    def set_client(self, **kwargs: Any) -> None:
        """Set the client values for the container class and update relevant attributes"""
        for key, value in kwargs.items():
            setattr(self.client, key, value)

    @func_timer
    @func_debug_logger
    def sign(
        self,
        method: str,
        endpoint: str | EndPoint,
        payload: dict[str, Any] | Sentinel = NotSet,
        *,
        timestamp: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Create HMAC signature for request

        Args
            method: HTTP method as a string
            endpoint: API endpoint path as a string or EndPoint enum instance
            payload: Dictionary containing API endpoint payload data.
                     This will be converted to a JSON string and hashed.
                     If no payload is provided, a default containing the currently set allyCode will be used.

        Keyword Args
            timestamp: Optional timestamp string to use instead of generating a new one. (primarily for testing)
            api_key: Optional API key to use instead of the one set in the container class. (primarily for testing)
        """
        debug_enabled = self.logger.isEnabledFor(logging.DEBUG)

        if "api-key" in self.headers:
            del self.headers["api-key"]
            if debug_enabled:
                self.logger.debug("'api-key' header removed")

        if timestamp:
            req_time = timestamp
        else:
            req_time = str(int(time.time() * 1000))

        self.headers["x-timestamp"] = req_time
        if debug_enabled:
            self.logger.debug(f"'x-timestamp' header set to {self.headers['x-timestamp']}")

        if api_key:
            if debug_enabled:
                self.logger.debug(f"Using provided API key: [{redact_secret(api_key)}]")
            a_key = api_key.encode()
        else:
            if debug_enabled:
                self.logger.debug(f"Using API key from container class: [{self.get_api_key()}]")
            a_key = self.api_key.encode()
        hmac_obj = _hmac.new(key=a_key, digestmod=hashlib.sha256)

        hmac_obj.update(req_time.encode())
        hmac_obj.update(method.upper().encode())

        if isinstance(endpoint, EndPoint):
            endpoint = endpoint.value
        hmac_obj.update(endpoint.encode())

        payload = self.payload if payload is NotSet else payload
        payload_str = dumps(payload, separators=(",", ":"))

        payload_hash_digest = hashlib.md5(payload_str.encode()).hexdigest()
        if debug_enabled:
            self.logger.debug(f"Payload hash digest: {payload_hash_digest}")

        hmac_obj.update(payload_hash_digest.encode())

        self.headers["Authorization"] = hmac_obj.hexdigest()
        self.client.headers = self.headers
        self.aclient.headers = self.headers
        if debug_enabled:
            self.logger.debug(
                f"HTTP client headers updated with HMAC signature: {_redact_headers(self.client.headers)}"
            )
