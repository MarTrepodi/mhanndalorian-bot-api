"""
Base class definition for core object for storing and sharing information for use by all modules
"""

from __future__ import absolute_import, annotations

import hashlib
import hmac
import logging
import time
from json import dumps
from typing import Any, Optional

import httpx
from sentinels import Sentinel

from .attrs import APIKey, AllyCode, Debug, EndPoint, HMAC, Headers, Payload

# Define sentinels used in parameter checking
NotSet = Sentinel('NotSet')


class MBot:
    """Base class for MBot modules

    Args
        api_key: MHanndalorian Bot API key as a string
        allycode: Player allycode as a string

    Keyword Args
        api_host: Optional host URL for MHanndalorian Bot API, defaults to https://mhanndalorianbot.work/
        hmac: Boolean flag indicating whether the endpoints should use HMAC signature authentication, Default: True
    """

    api_host: str = "https://mhanndalorianbot.work"
    logger: logging.Logger = logging.getLogger("mbot")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    debug = Debug(False)
    hmac = HMAC(True)
    api_key: str = APIKey()
    allycode: str = AllyCode()

    client: httpx.Client = httpx.Client(base_url=f"{api_host}", timeout=15, verify=False)
    aclient: httpx.AsyncClient = httpx.AsyncClient(base_url=f"{api_host}", timeout=15, verify=False)

    def __init__(self, api_key: str, allycode: str, *, api_host: Optional[str] = None, hmac: Optional[bool] = True):

        self.api_key = api_key
        self.allycode = allycode
        self.headers = Headers({"Content-Type": "application/json", "api-key": self.api_key})
        self.payload = Payload({"payload": {"allyCode": self.allycode}})

        # self.set_api_key(api_key)
        # self.set_allycode(allycode)

        if isinstance(api_host, str):
            self.set_api_host(api_host)

        if isinstance(hmac, bool):
            self.hmac = hmac

    @staticmethod
    def cleanse_allycode(allycode: str) -> str:
        """Remove any dashes from provided string and verify the result contains exactly 9 digits"""
        if not isinstance(allycode, str):
            raise ValueError(f"{allycode} must be a string, not type:{type(allycode)}")

        allycode = allycode.replace('-', '') if '-' in allycode else allycode

        if not allycode.isdigit() or len(allycode) != 9:
            raise ValueError(f"Invalid allyCode ({allycode}): Value must be exactly 9 numerical characters.")

        return allycode

    @staticmethod
    def cleanse_discord_id(discord_id: str) -> str:
        """Validate that discord ID is an 18 character string of only numerical digits"""
        if not isinstance(discord_id, str):
            raise ValueError(f"{discord_id} must be a string, not type: {type(discord_id)}")

        if not discord_id.isdigit() or len(discord_id) != 18:
            raise ValueError(f"Invalid Discord ID ({discord_id}): Value must be exactly 18 numerical characters.")

        return discord_id

    def get_api_key(self):
        """Return masked API key for logging purposes."""
        return f"{'*' * 6 + self.api_key[-8:]}"

    def set_api_key(self, api_key: str):
        """Set the api_key value for the container class and update relevant attributes (including headers)"""

        if not isinstance(api_key, str):
            raise ValueError("api_key must be a string")

        setattr(self, "api_key", api_key)

        self.headers["api-key"] = self.api_key
        self.payload["payload"]["allyCode"] = self.allycode
        self.client.headers = self.headers
        self.aclient.headers = self.headers

    def set_allycode(self, allycode: str):
        """Set the allycode value for the container class and update relevant attributes"""

        allycode = self.cleanse_allycode(allycode)

        setattr(self, "allycode", allycode)

        self.payload["payload"]["allyCode"] = allycode

    @classmethod
    def set_api_host(cls, api_host: str):
        """Set the api_host value for the container class and update relevant attributes"""

        if not isinstance(api_host, str):
            raise ValueError("api_host must be a string")

        setattr(cls, "api_host", api_host)

        cls.client.base_url = f"{api_host}/api/"
        cls.aclient.base_url = f"{api_host}/api/"

    @classmethod
    def set_client(cls, **kwargs: Any):
        """Set the client values for the container class and update relevant attributes"""
        for key, value in kwargs.items():
            setattr(cls.client, key, value)

    def sign(self, method: str, endpoint: str | EndPoint, payload: dict[str, Any] | Sentinel = NotSet, *,
             timestamp: str = None, api_key: str = None) -> None:
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
        # Removing 'api-key' header. This signals to the API that the request is HMAC signed
        if 'api-key' in self.headers:
            del self.headers['api-key']
            self.logger.debug("'api-key' header removed")

        # Get current unix timestamp in milliseconds
        if timestamp:
            req_time = timestamp
        else:
            req_time = str(int(time.time() * 1000))

        # Set the timestamp header for the API
        self.headers['x-timestamp'] = req_time
        self.logger.debug(f"'x-timestamp' header set to {self.headers['x-timestamp']}")

        # Create empty HMAC object using SHA256 algorithm
        if api_key:
            self.logger.debug(f"Using provided API key: [{self.get_api_key()}]")
            a_key = api_key.encode()
        else:
            self.logger.debug(f"Using API key from container class: [{self.get_api_key()}]")
            a_key = self.api_key.encode()
        hmac_obj = hmac.new(key=a_key, digestmod=hashlib.sha256)
        self.logger.debug(f"HMAC Hexdigest (base): {hmac_obj.hexdigest()}")

        # Add the timestamp to the HMAC object
        hmac_obj.update(req_time.encode())
        self.logger.debug(f"HMAC Hexdigest (timestamp): {hmac_obj.hexdigest()}")

        # Add the HTTP request method in all caps to the HMAC object
        hmac_obj.update(method.upper().encode())
        self.logger.debug(f"HMAC Hexdigest (HTTP method): {hmac_obj.hexdigest()}")

        # Add the API endpoint path to the HMAC object
        if isinstance(endpoint, EndPoint):
            endpoint = endpoint.value
        hmac_obj.update(endpoint.encode())
        self.logger.debug(f"HMAC Hexdigest (endpoint): {hmac_obj.hexdigest()}")

        # Create a serialized string of the payload object
        payload = self.payload if payload is NotSet else payload
        payload_str = dumps(payload, separators=(',', ':'))
        self.logger.debug(f"Payload string: {payload_str}")

        # Generate MD5 hash of the payload string
        payload_hash_digest = hashlib.md5(payload_str.encode()).hexdigest()
        self.logger.debug(f"Payload hash digest: {payload_hash_digest}")

        # Add the payload MD5 hash to the HMAC object
        hmac_obj.update(payload_hash_digest.encode())
        self.logger.debug(f"HMAC Hexdigest (payload): {hmac_obj.hexdigest()}")

        # Add the HMAC signature to the HTTP headers
        self.headers['Authorization'] = hmac_obj.hexdigest()
        self.client.headers = self.headers
        self.aclient.headers = self.headers
        self.logger.debug(f"HTTP client headers updated with HMAC signature: {self.client.headers}")
