# coding=utf-8
"""
Class definition for SWGOH MHanndalorian Bot API module
"""

from __future__ import absolute_import, annotations

from typing import Any, Dict, Optional

from .base import EndPoint, MBot


class API(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot authenticated
    endpoints for SWGOH. See https://mhanndalorianbot.work/api.html for more information.
    """

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
            return {"msg": "Unexpected result", "reason": result.content.decode()}

    def fetch_twlogs(self):
        return self.fetch_data(EndPoint.TWLOGS)

    def fetch_tblogs(self):
        return self.fetch_data(EndPoint.TBLOGS)

    def fetch_inventory(self):
        return self.fetch_data(EndPoint.INVENTORY)

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
            return {"msg": "Unexpected result", "reason": result.content.decode()}
