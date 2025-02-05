# coding=utf-8
"""
Class definition for SWGOH MHanndalorian Bot player registry service
"""
from __future__ import absolute_import, annotations

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

from .base import MBot, EndPoint


class Registry(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot SWGOH player registry
    """

    def fetch_player(self, allycode: str, *, hmac: bool = False) -> Dict[Any, Any]:
        """Return player data from the provided allycode

            Args
                allycode: Player allycode as a string.

            Keyword Args
                hmac: Boolean flag to indicate use of HMAC request signing.

            Returns
                Dictionary from JSON response, if found. Else None.
        """

        allycode = self.cleanse_allycode(allycode)

        payload = {'user': [allycode], 'endpoint': 'find'}
        endpoint = f"/api/{EndPoint.FETCH.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_data = resp.json()
            if isinstance(resp_data, list) and len(resp_data) == 1:
                return resp_data[0]
            else:
                return resp_data
        else:
            return {"msg": "Unexpected result", "reason": resp.content.decode()}

    async def fetch_player_async(self, allycode: str, *, hmac: bool = False) -> Dict[Any, Any]:
        """Return player data from the provided allycode

            Args
                allycode: Player allycode as a string.

            Keyword Args
                hmac: Boolean flag to indicate use of HMAC request signing.

            Returns
                Dictionary from JSON response, if found. Else None.
        """

        allycode = self.cleanse_allycode(allycode)

        payload = {'user': [allycode], 'endpoint': 'find'}
        endpoint = f"/api/{EndPoint.FETCH.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        result: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if result.status_code == 200:
            resp_data = result.json()
            if isinstance(resp_data, list) and len(resp_data) == 1:
                return resp_data[0]
            else:
                return resp_data
        else:
            return {"msg": "Unexpected result", "reason": result.content.decode()}

    def register_player(self,
                        discord_id: str,
                        allycode: str, *, hmac: bool = False) -> Dict[str, Any]:
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

        payload = dict(discordId=discord_id, method="registration", payload={"allyCode": allycode})
        endpoint = f"/api/{EndPoint.REGISTER.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            return resp.json()
        else:
            return {"msg": "Unexpected result", "reason": resp.content.decode()}

    async def register_player_async(self,
                                    discord_id: str,
                                    allycode: str, *, hmac: bool = False) -> Dict[Any, Any]:
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

        payload = dict(discordId=discord_id, method="registration", payload={"allyCode": allycode})
        endpoint = f"/api/{EndPoint.REGISTER.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        result: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if result.status_code == 200:
            return result.json()
        else:
            return {"msg": "Unexpected result", "reason": result.content.decode()}

    def verify_player(self,
                      discord_id: str,
                      allycode: str, *,
                      primary: bool = False, hmac: bool = False) -> bool:
        """Perform player portrait and title verification after register_player() has been called.

            Args
                discord_id: Discord user ID as a string.
                allycode: Player allycode as a string.

            Keyword Args
                primary: Boolean indicating whether this allycode should be used as the primary for the discord ID
                            in cases where multiple allycodes are registered to the same discord ID.
                hmac: Boolean flag to indicate use of HMAC request signing.

            Returns
                True if successful, False otherwise
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload = dict(discordId=discord_id, method="verification", primary=primary, payload={"allyCode": allycode})
        endpoint = f"/api/{EndPoint.VERIFY.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        resp: httpx.Response = self.client.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_json = resp.json()
            if 'verified' in resp_json:
                return resp_json['verified']

        return False

    async def verify_player_async(self,
                                  discord_id: str,
                                  allycode: str, *,
                                  primary: bool = False, hmac: bool = False) -> bool:
        """Perform player portrait and title verification

            Args
                discord_id: Discord user ID as a string
                allycode: Player allycode as a string

            Keyword Args
                primary: Boolean indicating whether this allycode should be used as the primary for the discord ID
                            in cases where multiple allycodes are registered to the same discord ID
                hmac: Boolean flag to indicate use of HMAC request signing. Default: False.

            Returns
                True if successful, False otherwise
        """

        allycode = self.cleanse_allycode(allycode)
        discord_id = self.cleanse_discord_id(discord_id)

        payload = dict(discordId=discord_id, method="verification", primary=primary, payload={"allyCode": allycode})
        endpoint = f"/api/{EndPoint.VERIFY.value}"

        if hmac or self.hmac is True:
            self.sign(method='POST', endpoint=endpoint, payload=payload)

        resp: httpx.Response = await self.aclient.post(endpoint, json=payload)

        if resp.status_code == 200:
            resp_json = resp.json()
            if 'verified' in resp_json:
                return resp_json['verified']

        return False
