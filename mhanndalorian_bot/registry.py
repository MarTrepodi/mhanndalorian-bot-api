"""
Class definition for SWGOH MHanndalorian Bot player registry service
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

from mhanndalorian_bot.attrs import EndPoint
from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.exceptions import ValidationError, raise_for_response
from mhanndalorian_bot.utils import func_timer


class Registry(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot SWGOH player registry
    """

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        api_key: str | None = None,
        allycode: str | None = None,
        discord_id: str | None = None,
        *,
        api_host: str = "https://mhanndalorianbot.work",
        hmac: bool = True,
        debug: bool = False,
        verify: bool | str = True,
        timeout: float = 75.0,
        retries: int = 0,
    ):
        super().__init__(
            api_key=api_key,
            allycode=allycode,
            discord_id=discord_id,
            api_host=api_host,
            hmac=hmac,
            debug=debug,
            verify=verify,
            timeout=timeout,
            retries=retries,
        )

    @func_timer
    def validate_arguments(self, allycode: str | None, discord_id: str | None) -> str:
        """Validate provided arguments for the player registry service

        Raises:
            ValidationError: if neither or both identifiers are supplied, or either is malformed.
        """
        if not allycode and not discord_id:
            raise ValidationError("At least one of allycode or discord_id must be provided.")

        if allycode and discord_id:
            raise ValidationError("Only one of allycode or discord_id can be provided.")

        cleansed_allycode = self.cleanse_allycode(allycode) if allycode else None
        cleansed_discord_id = self.cleanse_discord_id(discord_id) if discord_id else None

        identifier = cleansed_allycode or cleansed_discord_id
        assert identifier is not None  # guaranteed by the checks above
        return identifier

    @func_timer
    def fetch_player(
        self, *, allycode: str | None = None, discord_id: str | None = None, hmac: bool = False
    ) -> dict[Any, Any]:
        """Return player data from the provided allycode

        Keyword Args
            allycode: Player allycode as a string.
            discord_id: Discord user ID as a string.
            hmac: Boolean flag to indicate use of HMAC request signing.

        Returns
            Dictionary from JSON response, if found. Else None.
        """

        self._require_discord_id(EndPoint.FETCH)
        user_identifier = self.validate_arguments(allycode, discord_id)
        payload = {"user": [user_identifier], "endpoint": "find"}
        endpoint = f"/api/{EndPoint.FETCH.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_data = resp.json()
            if isinstance(resp_data, list) and len(resp_data) == 1:
                return resp_data[0]
            return resp_data
        raise_for_response(resp, endpoint)

    @func_timer
    def register_player(self, discord_id: str, allycode: str, *, hmac: bool = False) -> dict[str, Any]:
        """Register a player in the registry

        Args
            discord_id: Discord user ID as a string
            allycode: Player allycode as a string

        Keyword Args
            hmac: Boolean flag to indicate use of HMAC request signing.

        Returns
            Dict containing `unlockedPlayerPortrait` and `unlockedPlayerTitle` keys, if successful
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload = dict(discordId=discord_id, method="registration", payload={"allyCode": allycode}, enums=False)
        endpoint = f"/api/{EndPoint.REGISTER.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            return resp.json()
        raise_for_response(resp, endpoint)

    @func_timer
    def verify_player(self, discord_id: str, allycode: str, *, primary: bool | None = None, hmac: bool = False) -> bool:
        """Perform player portrait and title verification after register_player() has been called.

        Args
            discord_id: Discord user ID as a string.
            allycode: Player allycode as a string.

        Keyword Args
            primary: Whether this allycode should be the primary for the discord ID when several are
                        registered to it. Leave as None (the default) to let the registry decide: it
                        assigns primary=yes when the user has no other registered accounts. Pass True
                        or False to state it explicitly..
            hmac: Boolean flag to indicate use of HMAC request signing.

        Returns
            True if the player is verified, False otherwise

        Raises
            APIResponseError: if the HTTP request itself fails (non-200 response)
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload: dict[str, Any] = dict(
            discordId=discord_id, method="verification", payload={"allyCode": allycode}, enums=False
        )
        # `primary` is omitted entirely when None so the registry applies its documented default:
        # a user with no other registered accounts gets primary=yes. Sending `false` here -- as
        # this library did before 0.11.0 -- silently opted first-time users out of that.
        if primary is not None:
            payload["primary"] = primary
        endpoint = f"/api/{EndPoint.VERIFY.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_json = resp.json()
            return bool(resp_json.get("verified", False))
        raise_for_response(resp, endpoint)

    # Async methods
    @func_timer
    async def fetch_player_async(
        self, *, allycode: str | None = None, discord_id: str | None = None, hmac: bool = False
    ) -> dict[Any, Any]:
        """Return player data from the provided allycode

        Keyword Args
            allycode: Player allycode as a string.
            discord_id: Discord user ID as a string.
            hmac: Boolean flag to indicate use of HMAC request signing.

        Returns
            Dictionary from JSON response, if found. Else None.
        """

        self._require_discord_id(EndPoint.FETCH)
        user_identifier = self.validate_arguments(allycode, discord_id)
        payload = {"user": [user_identifier], "endpoint": "find"}
        endpoint = f"/api/{EndPoint.FETCH.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        result: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if result.status_code == 200:
            resp_data = result.json()
            if isinstance(resp_data, list) and len(resp_data) == 1:
                return resp_data[0]
            return resp_data
        raise_for_response(result, endpoint)

    @func_timer
    async def register_player_async(self, discord_id: str, allycode: str, *, hmac: bool = False) -> dict[Any, Any]:
        """Register a player in the registry

        Args
            discord_id: Discord user ID as a string.
            allycode: Player allycode as a string.

        Keyword Args
            hmac: Boolean flag to indicate use of HMAC request signing.

        Returns
            Dict containing `unlockedPlayerPortrait` and `unlockedPlayerTitle` keys, if successful.
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload = dict(discordId=discord_id, method="registration", payload={"allyCode": allycode}, enums=False)
        endpoint = f"/api/{EndPoint.REGISTER.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        resp: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if resp.status_code == 200:
            return resp.json()
        raise_for_response(resp, endpoint)

    @func_timer
    async def verify_player_async(
        self, discord_id: str, allycode: str, *, primary: bool | None = None, hmac: bool = False
    ) -> bool:
        """Perform player portrait and title verification

        Args
            discord_id: Discord user ID as a string
            allycode: Player allycode as a string

        Keyword Args
            primary: Whether this allycode should be the primary for the discord ID when several are
                        registered to it. Leave as None (the default) to let the registry decide: it
                        assigns primary=yes when the user has no other registered accounts. Pass True
                        or False to state it explicitly.
            hmac: Boolean flag to indicate use of HMAC request signing. Default: False.

        Returns
            True if the player is verified, False otherwise

        Raises
            APIResponseError: if the HTTP request itself fails (non-200 response)
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload: dict[str, Any] = dict(
            discordId=discord_id, method="verification", payload={"allyCode": allycode}, enums=False
        )
        # `primary` is omitted entirely when None so the registry applies its documented default:
        # a user with no other registered accounts gets primary=yes. Sending `false` here -- as
        # this library did before 0.11.0 -- silently opted first-time users out of that.
        if primary is not None:
            payload["primary"] = primary
        endpoint = f"/api/{EndPoint.VERIFY.value}"

        if hmac or self.hmac is True:
            self.sign(method="POST", endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        resp: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_json = resp.json()
            return bool(resp_json.get("verified", False))
        raise_for_response(resp, endpoint)
