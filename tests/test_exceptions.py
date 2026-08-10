"""Tests for the exception hierarchy and non-200 response handling."""

import pytest
from pytest_httpx import HTTPXMock

import mhanndalorian_bot
from mhanndalorian_bot import (
    API,
    APIResponseError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    MBotError,
    Registry,
    ValidationError,
)

STATUS_TO_EXC = [
    (400, BadRequestError),
    (401, AuthenticationError),
    (403, AuthorizationError),
    (500, APIResponseError),
]


@pytest.fixture
def api_instance():
    return API(api_key="test_api_key", allycode="123456789", discord_id="123456789012345678")


@pytest.fixture
def registry_instance():
    return Registry(api_key="test_api_key", allycode="123456789", discord_id="123456789987654321")


def test_hierarchy_is_runtime_error_compatible():
    """All exceptions must remain catchable as RuntimeError."""
    for exc_cls in (
        MBotError,
        APIResponseError,
        BadRequestError,
        AuthenticationError,
        AuthorizationError,
        ValidationError,
    ):
        assert issubclass(exc_cls, RuntimeError)
        assert issubclass(exc_cls, MBotError)


def test_validation_error_is_a_sibling_of_api_response_error():
    """ValidationError sits directly under MBotError, not under the response-error branch.

    An input rejected locally carries no status_code / endpoint / response_text, so it must
    not be catchable as APIResponseError.
    """
    assert issubclass(ValidationError, MBotError)
    assert not issubclass(ValidationError, APIResponseError)
    assert ValidationError.__bases__ == (MBotError,)


def test_validation_error_does_not_subclass_valueerror_or_typeerror():
    """The v0.11.0 breaking change, pinned: `except ValueError:` no longer catches."""
    assert not issubclass(ValidationError, ValueError)
    assert not issubclass(ValidationError, TypeError)

    with pytest.raises(ValidationError):
        try:
            API.cleanse_allycode("not-a-code")
        except (ValueError, TypeError) as exc:  # pragma: no cover - must not be reached
            raise AssertionError(f"ValidationError was caught as {type(exc).__name__}") from exc


def test_validation_error_exported_from_package_root():
    assert mhanndalorian_bot.ValidationError is ValidationError
    assert "ValidationError" in mhanndalorian_bot.__all__


@pytest.mark.parametrize("status_code, exc_cls", STATUS_TO_EXC)
def test_fetch_data_raises_mapped_exception(httpx_mock: HTTPXMock, api_instance, status_code, exc_cls):
    httpx_mock.add_response(status_code=status_code, text="error body")
    with pytest.raises(exc_cls) as exc_info:
        api_instance.fetch_data(endpoint="tw")

    exc = exc_info.value
    assert exc.status_code == status_code
    assert exc.endpoint == "/api/tw"
    assert exc.response_text == "error body"


@pytest.mark.parametrize("status_code, exc_cls", STATUS_TO_EXC)
async def test_fetch_data_async_raises_mapped_exception(httpx_mock: HTTPXMock, api_instance, status_code, exc_cls):
    httpx_mock.add_response(status_code=status_code, text="error body")
    with pytest.raises(exc_cls) as exc_info:
        await api_instance.fetch_data_async(endpoint="tw")
    assert exc_info.value.status_code == status_code


def test_registry_fetch_player_raises(httpx_mock: HTTPXMock, registry_instance):
    httpx_mock.add_response(status_code=401, text="unauthorized")
    with pytest.raises(AuthenticationError):
        registry_instance.fetch_player(allycode="123456789")


async def test_registry_fetch_player_async_raises(httpx_mock: HTTPXMock, registry_instance):
    """fetch_player_async now raises on error instead of returning an error dict."""
    httpx_mock.add_response(status_code=401, text="unauthorized")
    with pytest.raises(AuthenticationError):
        await registry_instance.fetch_player_async(allycode="123456789")


def test_registry_verify_player_raises_on_http_error(httpx_mock: HTTPXMock, registry_instance):
    """verify_player now raises on HTTP errors; False strictly means 'not verified'."""
    httpx_mock.add_response(status_code=403, text="forbidden")
    with pytest.raises(AuthorizationError):
        registry_instance.verify_player(discord_id="123456789987654321", allycode="123456789")


async def test_registry_verify_player_async_raises_on_http_error(httpx_mock: HTTPXMock, registry_instance):
    httpx_mock.add_response(status_code=403, text="forbidden")
    with pytest.raises(AuthorizationError):
        await registry_instance.verify_player_async(discord_id="123456789987654321", allycode="123456789")


def test_exceptions_catchable_as_runtime_error(httpx_mock: HTTPXMock, api_instance):
    """Existing user code with `except RuntimeError` must keep working."""
    httpx_mock.add_response(status_code=401)
    with pytest.raises(RuntimeError):
        api_instance.fetch_data(endpoint="tw")
