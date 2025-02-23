# tests/test_api.py
import pytest
from pytest_httpx import HTTPXMock

from mhanndalorian_bot.api import API
from mhanndalorian_bot.attrs import EndPoint

api_instance = API("mock_api_key", "123456789")


def test_mock_fetch_data_sync(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = api_instance.fetch_data(endpoint="mock_endpoint")
    assert response == {"success": True}


@pytest.mark.asyncio
async def test_mock_fetch_data_async(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = await api_instance.fetch_data_async(endpoint=EndPoint.TW)
    assert response == {"success": True}
