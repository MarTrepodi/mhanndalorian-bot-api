"""
Class definition for SWGOH MHanndalorian Bot API module
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from mhanndalorian_bot.attrs import EndPoint
from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.utils import func_timer


def _payload_with_enums(payload: dict[str, Any], enums: bool) -> dict[str, Any]:
    """Return a deep copy of ``payload`` with the ``enums`` flag set under ``payload.payload``.

    Does not mutate the caller's dictionary.
    """
    new_payload = copy.deepcopy(payload)
    new_payload.setdefault('payload', {})['enums'] = enums
    return new_payload


class API(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot authenticated
    endpoints for SWGOH. See https://mhanndalorianbot.work/api.html for more information.
    """

    logger = logging.getLogger(__name__)

    @staticmethod
    def _resolve_endpoint(ep: EndPoint | str) -> str:
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
            endpoint: EndPoint | str,
            *,
            method: str | None = None,
            hmac: bool | None = None,
            payload: dict[str, Any] | None = None,
            enums: bool = False
            ) -> dict[Any, Any]:
        """Return data from the provided API endpoint using standard synchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
                payload: Dictionary of payload data to be sent with the request, defaults to empty dict.
                enums: Boolean flag indicating whether to return enum values instead of enum names.

            Returns
                Dictionary from JSON response, if found.
        """

        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = _payload_with_enums(payload or self.payload, enums)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                    f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                    + f"Payload: {payload}"
                    )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)

        result = self.client.post(endpoint, json=payload)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"HTTP request completed - Status: {result.status_code}")

        if result.status_code == 200:
            return result.json()
        raise RuntimeError(f"Unexpected result: {result.content.decode()}")

    def fetch_tw_leaderboard(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.TWLEADERBOARD, **kwargs)

    def fetch_twlogs(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.TWLOGS, **kwargs)

    def fetch_tblogs(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.TBLOGS, **kwargs)

    def fetch_inventory(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player INVENTORY endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.INVENTORY, **kwargs)

    def fetch_arena(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player squad and fleet arena endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.ARENA, **kwargs)

    def fetch_tb(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TB endpoint for the currently active Territory Battle guild event"""
        return self.fetch_data(EndPoint.TB, **kwargs)

    def fetch_tb_history(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLEADERBOARDHISTORY endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.TBHISTORY, **kwargs)

    def fetch_tw(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TW endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.TW, **kwargs)

    def fetch_raid(self, **kwargs) -> dict[Any, Any]:
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.RAID, **kwargs)

    def fetch_player(self, allycode: str | None = None, **kwargs) -> dict[Any, Any]:
        """Return data from the PLAYER endpoint for the provided allycode"""
        validated_allycode = self._verify_allycode(allycode) if allycode else self.allycode
        enums = kwargs.setdefault('enums', False)
        player = self.fetch_data(
                endpoint=EndPoint.PLAYER,
                payload={"payload": {"allyCode": validated_allycode}},
                enums=enums
                )

        if isinstance(player, dict) and 'events' in player:
            return player['events']
        return player

    def fetch_guild(self, guild_id: str, **kwargs) -> dict[Any, Any]:
        """Return data from the GUILD endpoint for the provided guild"""
        validated_guild_id = self._verify_guild_id(guild_id)
        enums = kwargs.setdefault('enums', False)
        guild = self.fetch_data(
                endpoint=EndPoint.GUILD,
                payload={"payload": {"guildId": validated_guild_id}},
                enums=enums
                )

        if isinstance(guild, dict) and 'events' in guild and 'guild' in guild['events']:
            return guild['events']['guild']
        return guild

    def fetch_squad_presets(self, **kwargs) -> dict[Any, Any]:
        """Return data from the SQUADPRESETS endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.SQUADS, **kwargs)

    def fetch_gac(self, **kwargs) -> dict[Any, Any]:
        """Return data from the GAC endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.GAC, **kwargs)

    def fetch_conquest(self, **kwargs) -> dict[Any, Any]:
        """Return data from the CONQUEST endpoint"""
        kwargs.setdefault('enums', False)
        return self.fetch_data(EndPoint.CONQUEST, **kwargs)

    # Async methods
    @func_timer
    async def fetch_data_async(
            self,
            endpoint: str | EndPoint,
            *,
            method: str | None = None,
            hmac: bool | None = None,
            payload: dict[str, Any] | None = None,
            enums: bool = False
            ) -> dict[Any, Any]:
        """Return data from the provided API endpoint using asynchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
                payload: Dictionary of payload data to be sent with the request, defaults to empty dict.
                enums: Boolean flag indicating whether to return enum values instead of enum names.

            Returns
                Dictionary from JSON response.
        """
        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = _payload_with_enums(payload or self.payload, enums)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                    f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                    + f"Payload: {payload}"
                    )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)

        result = await self.aclient.post(endpoint, json=payload)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"HTTP request completed - Status: {result.status_code}")

        if result.status_code == 200:
            return result.json()
        raise RuntimeError(f"Unexpected result: {result.content.decode()}")

    async def fetch_tw_leaderboard_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.TWLEADERBOARD, **kwargs)

    async def fetch_twlogs_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.TWLOGS, **kwargs)

    async def fetch_tblogs_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.TBLOGS, **kwargs)

    async def fetch_inventory_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player INVENTORY endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.INVENTORY, **kwargs)

    async def fetch_arena_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player squad and fleet arena endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.ARENA, **kwargs)

    async def fetch_tb_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TB endpoint for the currently active Territory Battle guild event"""
        return await self.fetch_data_async(EndPoint.TB, **kwargs)

    async def fetch_tb_history_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLEADERBOARDHISTORY endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.TBHISTORY, **kwargs)

    async def fetch_tw_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TW endpoint for the currently active Territory War guild event"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.TW, **kwargs)

    async def fetch_raid_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.RAID, **kwargs)

    async def fetch_player_async(self, allycode: str | None = None, **kwargs) -> dict[Any, Any]:
        """Return data from the PLAYER endpoint for the provided allycode"""
        validated_allycode = self._verify_allycode(allycode) if allycode else self.allycode
        enums = kwargs.setdefault('enums', False)
        player = await self.fetch_data_async(
                endpoint=EndPoint.PLAYER,
                payload={"payload": {"allyCode": validated_allycode}},
                enums=enums
                )

        if isinstance(player, dict) and 'events' in player:
            return player['events']
        return player

    async def fetch_guild_async(self, guild_id: str, **kwargs) -> dict[Any, Any]:
        """Return data from the GUILD endpoint for the provided guild"""
        validated_guild_id = self._verify_guild_id(guild_id)
        enums = kwargs.setdefault('enums', False)
        guild = await self.fetch_data_async(
                endpoint=EndPoint.GUILD,
                payload={"payload": {"guildId": validated_guild_id}},
                enums=enums
                )

        if isinstance(guild, dict) and 'events' in guild and 'guild' in guild['events']:
            return guild['events']['guild']
        return guild

    async def fetch_squad_presets_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the SQUADPRESETS endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.SQUADS, **kwargs)

    async def fetch_gac_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the GAC endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.GAC, **kwargs)

    async def fetch_conquest_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the CONQUEST endpoint"""
        kwargs.setdefault('enums', False)
        return await self.fetch_data_async(EndPoint.CONQUEST, **kwargs)
