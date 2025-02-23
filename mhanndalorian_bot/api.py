# coding=utf-8
"""
Class definition for SWGOH MHanndalorian Bot API module
"""

from __future__ import absolute_import, annotations

import logging
from typing import Any, Dict, Optional

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
    def fetch_data(self, endpoint: str | EndPoint,
                   *, method: Optional[str] = None, hmac: Optional[bool] = None) -> Dict[Any, Any]:
        """Return data from the provided API endpoint using standard synchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication

            Returns
                Dictionary from JSON response, if found.
        """
        if isinstance(endpoint, EndPoint):
            endpoint = f"/api/{endpoint.value}"

        method = method.upper() if method else "POST"

        if isinstance(hmac, bool):
            signed = hmac
        else:
            signed = self.hmac

        self.logger.debug(f"Endpoint: {endpoint}, Method: {method},  HMAC: {signed}")

        if signed:
            self.logger.debug(f"Calling HMAC signing method ...")
            self.sign(method=method, endpoint=endpoint, payload=self.payload)

        result = self.client.post(endpoint, json=self.payload)

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

    # Async methods
    @func_timer
    async def fetch_data_async(self, endpoint: str | EndPoint,
                               *, method: Optional[str] = None, hmac: Optional[bool] = None) -> Dict[Any, Any]:
        """Return data from the provided API endpoint using asynchronous HTTP requests

            Args
                endpoint: API endpoint as a string or EndPoint enum

            Keyword Args
                method: HTTP method as a string, defaults to POST
                hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication

            Returns
                httpx.Response object
        """
        if isinstance(endpoint, EndPoint):
            endpoint = f"/api/{endpoint.value}"

        method = method.upper() if method else "POST"

        if isinstance(hmac, bool):
            signed = hmac
        else:
            signed = self.hmac

        if signed:
            self.sign(method=method, endpoint=endpoint, payload=self.payload)

        result = await self.aclient.post(endpoint, json=self.payload)

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
