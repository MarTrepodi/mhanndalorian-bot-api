# coding=utf-8
"""
Class definition for SWGOH MHanndalorian Bot API module
"""

from __future__ import absolute_import, annotations

import logging
from typing import Any, AnyStr, Dict, Optional, Union

from mhanndalorian_bot.attrs import EndPoint
from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.utils import func_timer


class API(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot authenticated
    endpoints for SWGOH. See https://mhanndalorianbot.work/api.html for more information.
    """

    logger = logging.getLogger(__name__)

    @staticmethod
    def _resolve_endpoint(ep: Union[EndPoint, str]) -> str:
        """Convert the given endpoint to its string representation."""
        return f"/api/{ep.value}" if isinstance(ep, EndPoint) else f"/api/{ep}"

    @staticmethod
    def _verify_allycode(allycode: str) -> str:
        """Verify that the provided allycode is a string and is not empty."""
        if not isinstance(allycode, str):
            raise TypeError("allycode must be a string")
        if not allycode:
            raise ValueError("allycode cannot be empty")
        return allycode

    @staticmethod
    def _verify_guild_id(guild_id: str) -> str:
        """Verify that the provided guild_id is a string and is not empty."""
        if not isinstance(guild_id, str):
            raise TypeError("guild_id must be a string")
        if not guild_id:
            raise ValueError("guild_id cannot be empty")
        return guild_id

    @func_timer
    def fetch_data(
            self,
            endpoint: Union[EndPoint, AnyStr],
            *,
            method: Optional[str] = None,
            hmac: Optional[bool] = None,
            payload: Optional[dict] = None
            ) -> Dict[Any, Any]:
        """Return data from the provided API endpoint using standard synchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
                payload: Dictionary of payload data to be sent with the request, defaults to empty dict.

            Returns
                Dictionary from JSON response, if found.
        """

        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = payload or self.payload

        self.logger.debug(
                f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                + f"Payload: {payload}"
                )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)

        # HTTP call happens here
        result = self.client.post(endpoint, json=payload)

        self.logger.debug(
                f"HTTP request completed - Status: {result.status_code}, Headers: {result.request.headers}"
                )

        if result.status_code == 200:
            return result.json()
        else:
            raise RuntimeError(f"Unexpected result: {result.content.decode()}")

    def fetch_tw_leaderboard(self):
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event"""
        return self.fetch_data(EndPoint.TWLEADERBOARD)

    def fetch_twlogs(self):
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event"""
        return self.fetch_data(EndPoint.TWLOGS)

    def fetch_tblogs(self):
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event"""
        return self.fetch_data(EndPoint.TBLOGS)

    def fetch_inventory(self):
        """Return data from the player INVENTORY endpoint"""
        return self.fetch_data(EndPoint.INVENTORY)

    def fetch_arena(self):
        """Return data from the player squad and fleet arena endpoint"""
        return self.fetch_data(EndPoint.ARENA)

    def fetch_tb(self):
        """Return data from the TB endpoint for the currently active Territory Battle guild event"""
        return self.fetch_data(EndPoint.TB)

    def fetch_tw(self):
        """Return data from the TW endpoint for the currently active Territory War guild event"""
        return self.fetch_data(EndPoint.TW)

    def fetch_raid(self):
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        return self.fetch_data(EndPoint.RAID)

    def fetch_player(self, allycode: Optional[str] = None):
        """Return data from the PLAYER endpoint for the provided allycode"""
        validated_allycode = self._verify_allycode(allycode) if allycode else self.allycode
        player = self.fetch_data(EndPoint.PLAYER, payload={"payload": {"allyCode": validated_allycode}})

        if isinstance(player, dict) and 'events' in player:
            return player['events']
        else:
            return player

    def fetch_guild(self, guild_id: str):
        """Return data from the GUILD endpoint for the provided guild"""
        validated_guild_id = self._verify_guild_id(guild_id)
        guild = self.fetch_data(EndPoint.GUILD, payload={"guildId": validated_guild_id})

        if isinstance(guild, dict) and 'events' in guild and 'guild' in guild['events']:
            return guild['events']['guild']
        else:
            return guild

    # Async methods
    @func_timer
    async def fetch_data_async(
            self,
            endpoint: str | EndPoint,
            *,
            method: Optional[str] = None,
            hmac: Optional[bool] = None,
            payload: Optional[dict] = None
            ) -> Dict[Any, Any]:
        """Return data from the provided API endpoint using asynchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
                payload: Dictionary of payload data to be sent with the request, defaults to empty dict.

            Returns
                httpx.Response object
        """
        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = payload or self.payload

        self.logger.debug(
                f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                + f"Payload: {payload}"
                )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)

        result = await self.aclient.post(endpoint, json=payload)

        self.logger.debug(
                f"HTTP request completed - Status: {result.status_code}, Headers: {result.request.headers}"
                )

        if result.status_code == 200:
            return result.json()
        else:
            raise RuntimeError(f"Unexpected result: {result.content.decode()}")

    async def fetch_tw_leaderboard_async(self):
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event"""
        return await self.fetch_data_async(EndPoint.TWLEADERBOARD)

    async def fetch_twlogs_async(self):
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event"""
        return await self.fetch_data_async(EndPoint.TWLOGS)

    async def fetch_tblogs_async(self):
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event"""
        return await self.fetch_data_async(EndPoint.TBLOGS)

    async def fetch_inventory_async(self):
        """Return data from the player INVENTORY endpoint"""
        return await self.fetch_data_async(EndPoint.INVENTORY)

    async def fetch_arena_async(self):
        """Return data from the player squad and fleet arena endpoint"""
        return await self.fetch_data_async(EndPoint.ARENA)

    async def fetch_tb_async(self):
        """Return data from the TB endpoint for the currently active Territory Battle guild event"""
        return await self.fetch_data_async(EndPoint.TB)

    async def fetch_tw_async(self):
        """Return data from the TW endpoint for the currently active Territory War guild event"""
        return await self.fetch_data_async(EndPoint.TW)

    async def fetch_raid_async(self):
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        return await self.fetch_data_async(EndPoint.RAID)

    async def fetch_player_async(self, allycode: Optional[str] = None):
        """Return data from the PLAYER endpoint for the provided allycode"""
        validated_allycode = self._verify_allycode(allycode) if allycode else self.allycode
        player = await self.fetch_data_async(EndPoint.PLAYER, payload={"payload": {"allyCode": validated_allycode}})

        if isinstance(player, dict) and 'events' in player:
            return player['events']
        else:
            return player

    async def fetch_guild_async(self, guild_id: str):
        """Return data from the GUILD endpoint for the provided guild"""
        validated_guild_id = self._verify_guild_id(guild_id)
        guild = await self.fetch_data_async(EndPoint.GUILD, payload={"guildId": validated_guild_id})

        if isinstance(guild, dict) and 'events' in guild and 'guild' in guild['events']:
            return guild['events']['guild']
        else:
            return guild
