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
        if isinstance(endpoint, EndPoint):
            endpoint = f"/api/{endpoint.value}"
        elif isinstance(endpoint, str):
            endpoint = f"/api/{endpoint}"

        method = method.upper() if method else "POST"

        if isinstance(hmac, bool):
            signed = hmac
        else:
            signed = self.hmac

        if payload is not None:
            payload = payload
        else:
            payload = self.payload

        self.logger.debug(f"Endpoint: {endpoint}, Method: {method}, HMAC: {signed}")
        self.logger.debug(f"  Payload: {payload}")

        if signed:
            self.logger.debug(f"Calling HMAC signing method ...")
            self.sign(method=method, endpoint=endpoint, payload=payload)

        result = self.client.post(endpoint, json=payload)

        self.logger.debug(f"HTTP request headers: {result.request.headers}")
        self.logger.debug(f"API instance headers attribute: {self.headers}")

        if result.status_code == 200:
            return result.json()
        else:
            raise RuntimeError(f"Unexpected result: {result.content.decode()}")

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

    def fetch_raid(self):
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        return self.fetch_data(EndPoint.RAID)

    def fetch_player(self, allycode: Optional[str] = None):
        """Return data from the PLAYER endpoint for the provided allycode"""
        if allycode is None:
            allycode = self.allycode
        else:
            if not isinstance(allycode, str):
                raise TypeError("allycode must be a string")
            self.allycode = allycode

        player = self.fetch_data(EndPoint.PLAYER, payload={"payload": {"allyCode": allycode}})

        if isinstance(player, dict):
            if 'events' in player:
                return player['events']
            else:
                return player
        else:
            return player

    def fetch_guild(self, guild_id: str):
        """Return data from the GUILD endpoint for the provided guild"""
        if not isinstance(guild_id, str):
            raise TypeError("guild_id must be a string")

        guild = self.fetch_data(EndPoint.GUILD, payload={"guildId": guild_id})

        if isinstance(guild, dict):
            if 'events' in guild:
                if 'guild' in guild['events']:
                    return guild['events']['guild']
            else:
                return guild
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
        if isinstance(endpoint, EndPoint):
            endpoint = f"/api/{endpoint.value}"
        elif isinstance(endpoint, str):
            endpoint = f"/api/{endpoint}"

        method = method.upper() if method else "POST"

        if isinstance(hmac, bool):
            signed = hmac
        else:
            signed = self.hmac

        if payload is not None:
            payload = payload
        else:
            payload = self.payload

        self.logger.debug(f"Endpoint: {endpoint}, Method: {method}, HMAC: {signed}")
        self.logger.debug(f"  Payload: {payload}")

        if signed:
            self.sign(method=method, endpoint=endpoint, payload=payload)

        result = await self.aclient.post(endpoint, json=payload)

        if result.status_code == 200:
            return result.json()
        else:
            raise RuntimeError(f"Unexpected result: {result.content.decode()}")

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

    async def fetch_raid_async(self):
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        return await self.fetch_data_async(EndPoint.RAID)

    async def fetch_player_async(self, allycode: Optional[str] = None):
        """Return data from the PLAYER endpoint for the provided allycode"""
        if allycode is None:
            allycode = self.allycode
        else:
            if not isinstance(allycode, str):
                raise TypeError("allycode must be a string")
            self.allycode = allycode

        player = await self.fetch_data_async(EndPoint.PLAYER, payload={"payload": {"allyCode": allycode}})

        if isinstance(player, dict):
            if 'events' in player:
                return player['events']
            else:
                return player
        else:
            return player

    async def fetch_guild_async(self, guild_id: str):
        """Return data from the GUILD endpoint for the provided guild"""
        if not isinstance(guild_id, str):
            raise TypeError("guild_id must be a string")

        guild = await self.fetch_data_async(EndPoint.GUILD, payload={"guildId": guild_id})

        if isinstance(guild, dict):
            if 'events' in guild:
                if 'guild' in guild['events']:
                    return guild['events']['guild']
            else:
                return guild
        else:
            return guild
