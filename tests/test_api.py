# tests/test_api.py
import json

import pytest
from pytest_httpx import HTTPXMock

from mhanndalorian_bot.api import API
from mhanndalorian_bot.attrs import (
    DEF_ID_ENUM_BY_LEADERBOARD_TYPE,
    EndPoint,
    GuildRaidDefId,
    LeaderboardType,
    TerritoryBattleDefId,
    TerritoryWarDefId,
)
from mhanndalorian_bot.exceptions import ValidationError

api_instance = API("mock_api_key", "123456789")

# (helper name, expected URL path) for every named endpoint helper taking only **kwargs
SIMPLE_HELPERS = [
    ("fetch_tw", "/api/tw"),
    ("fetch_raid", "/api/activeraid"),
    ("fetch_twlogs", "/api/twlogs"),
    ("fetch_tw_leaderboard", "/api/twleaderboard"),
    ("fetch_gac", "/api/gac"),
    ("fetch_inventory", "/api/inventory"),
    ("fetch_tb", "/api/tb"),
    ("fetch_tblogs", "/api/tblogs"),
    ("fetch_tb_history", "/api/tbleaderboardhistory"),
    ("fetch_arena", "/api/leaderboard"),
    ("fetch_squad_presets", "/api/squadpresets"),
    ("fetch_conquest", "/api/conquest"),
    ("fetch_events", "/api/events"),
]


def sent_payload(httpx_mock: HTTPXMock) -> dict:
    return json.loads(httpx_mock.get_requests()[0].content)


def test_mock_fetch_data_sync(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = api_instance.fetch_data(endpoint="mock_endpoint")
    assert response == {"success": True}


async def test_mock_fetch_data_async(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"success": True}, status_code=200)
    response = await api_instance.fetch_data_async(endpoint=EndPoint.TW)
    assert response == {"success": True}


@pytest.mark.parametrize("helper, path", SIMPLE_HELPERS)
def test_named_helpers_hit_expected_endpoint(httpx_mock: HTTPXMock, helper, path):
    """Every sync helper posts to its documented endpoint with enums defaulted to False."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    result = getattr(api_instance, helper)()
    assert result == {"ok": True}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == path
    assert sent_payload(httpx_mock)["payload"]["enums"] is False


@pytest.mark.parametrize("helper, path", SIMPLE_HELPERS)
async def test_named_helpers_async_hit_expected_endpoint(httpx_mock: HTTPXMock, helper, path):
    """Every async helper posts to its documented endpoint with enums defaulted to False."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    result = await getattr(api_instance, f"{helper}_async")()
    assert result == {"ok": True}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == path
    assert sent_payload(httpx_mock)["payload"]["enums"] is False


def test_fetch_player_by_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"name": "player"}}, status_code=200)
    result = api_instance.fetch_player("987654321")
    assert result == {"name": "player"}
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "987654321"


def test_fetch_player_by_player_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"name": "player"}}, status_code=200)
    result = api_instance.fetch_player(player_id="PID123")
    assert result == {"name": "player"}
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["playerId"] == "PID123"
    assert "allyCode" not in payload


def test_fetch_player_identity_mutually_exclusive():
    with pytest.raises(ValidationError, match="mutually exclusive"):
        api_instance.fetch_player("987654321", player_id="PID123")


def test_fetch_player_defaults_to_instance_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    api_instance.fetch_player()
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "123456789"


async def test_fetch_player_arena_async_by_player_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    await api_instance.fetch_player_arena_async(player_id="PID123")
    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/playerarena"
    assert sent_payload(httpx_mock)["payload"]["playerId"] == "PID123"


def test_fetch_player_arena_by_allycode(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_player_arena("987654321")
    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/playerarena"
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "987654321"


def test_fetch_guild(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"guild": {"name": "guild"}}}, status_code=200)
    result = api_instance.fetch_guild("GUILD_ID")
    assert result == {"name": "guild"}
    assert sent_payload(httpx_mock)["payload"]["guildId"] == "GUILD_ID"


def test_fetch_guild_leaderboard(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {"leaderboard": []}}, status_code=200)
    result = api_instance.fetch_guild_leaderboard(
        LeaderboardType.GUILD_RAID_HIGH_WATERMARK, count=10, def_id="GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"
    )
    assert result == {"data": {"leaderboard": []}}

    request = httpx_mock.get_requests()[0]
    assert request.url.path == "/api/guildleaderboard"
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == 6
    assert payload["count"] == 10
    assert payload["defId"] == "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"


async def test_fetch_guild_leaderboard_async_accepts_int(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    await api_instance.fetch_guild_leaderboard_async(3)
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == 3
    assert payload["count"] == 50
    assert "defId" not in payload


# --- /guildleaderboard oneOf coupling -------------------------------------------------------
# Spec v1.0.1 GuildLeaderboardRequest: types 0/1/3 take no defId; types 4, 5 and 6 each require
# a defId drawn from their own distinct enum.

NO_DEF_ID_TYPES = [
    LeaderboardType.UNSPECIFIED,
    LeaderboardType.GUILD_RAID_ALL_COMP_PTS,
    LeaderboardType.GUILD_GALACTIC_POWER,
]

DEF_ID_MEMBERS = (
    [(LeaderboardType.GUILD_TERRITORY_BATTLE_STARS, member) for member in TerritoryBattleDefId]
    + [(LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER, member) for member in TerritoryWarDefId]
    + [(LeaderboardType.GUILD_RAID_HIGH_WATERMARK, member) for member in GuildRaidDefId]
)


def test_def_id_enum_mapping_covers_exactly_types_4_5_6():
    """The coupling table matches the spec's oneOf branches, and the enums are reachable."""
    assert set(DEF_ID_ENUM_BY_LEADERBOARD_TYPE) == {
        LeaderboardType.GUILD_TERRITORY_BATTLE_STARS,
        LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER,
        LeaderboardType.GUILD_RAID_HIGH_WATERMARK,
    }
    assert {member.value for member in TerritoryBattleDefId} == {"t01D", "t04D", "t05D"}
    assert {member.value for member in TerritoryWarDefId} == {"TERRITORY_WAR_LEADERBOARD"}
    assert len(GuildRaidDefId) == 14
    assert all(member.value.startswith("GUILD:RAIDS:NORMAL_DIFF:") for member in GuildRaidDefId)

    for leaderboard_type in NO_DEF_ID_TYPES:
        assert leaderboard_type.def_id_enum is None
        assert leaderboard_type.requires_def_id is False
    for leaderboard_type in DEF_ID_ENUM_BY_LEADERBOARD_TYPE:
        assert leaderboard_type.requires_def_id is True


@pytest.mark.parametrize("leaderboard_type", NO_DEF_ID_TYPES)
def test_guild_leaderboard_types_without_def_id(httpx_mock: HTTPXMock, leaderboard_type):
    """Types 0/1/3 are valid with no defId, and none is emitted."""
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_guild_leaderboard(leaderboard_type)
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == int(leaderboard_type)
    assert "defId" not in payload


@pytest.mark.parametrize("leaderboard_type, def_id", DEF_ID_MEMBERS)
def test_guild_leaderboard_accepts_every_legal_def_id_member(httpx_mock: HTTPXMock, leaderboard_type, def_id):
    """Every legal (leaderboardType, defId) pair in the spec is accepted as an enum member."""
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_guild_leaderboard(leaderboard_type, def_id=def_id)
    payload = sent_payload(httpx_mock)["payload"]
    assert payload["leaderboardType"] == int(leaderboard_type)
    assert payload["defId"] == def_id.value


@pytest.mark.parametrize("leaderboard_type, def_id", DEF_ID_MEMBERS)
def test_guild_leaderboard_accepts_raw_def_id_string(httpx_mock: HTTPXMock, leaderboard_type, def_id):
    """The raw string value is accepted anywhere the enum member is, as EndPoint already allows."""
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_guild_leaderboard(leaderboard_type, def_id=def_id.value)
    assert sent_payload(httpx_mock)["payload"]["defId"] == def_id.value


async def test_guild_leaderboard_async_enforces_coupling(httpx_mock: HTTPXMock):
    """The async twin resolves enum members and rejects a missing defId identically."""
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    await api_instance.fetch_guild_leaderboard_async(
        LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER,
        def_id=TerritoryWarDefId.TERRITORY_WAR_LEADERBOARD,
    )
    assert sent_payload(httpx_mock)["payload"]["defId"] == "TERRITORY_WAR_LEADERBOARD"

    with pytest.raises(ValidationError, match="requires a def_id"):
        await api_instance.fetch_guild_leaderboard_async(LeaderboardType.GUILD_RAID_HIGH_WATERMARK)


@pytest.mark.parametrize(
    "leaderboard_type",
    [
        LeaderboardType.GUILD_TERRITORY_BATTLE_STARS,
        LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER,
        LeaderboardType.GUILD_RAID_HIGH_WATERMARK,
    ],
)
def test_guild_leaderboard_missing_def_id_rejected(leaderboard_type):
    """Types 4/5/6 declare defId required; omitting it must fail locally, not as a server 400."""
    with pytest.raises(ValidationError, match="requires a def_id"):
        api_instance.fetch_guild_leaderboard(leaderboard_type)


@pytest.mark.parametrize(
    "leaderboard_type, def_id",
    [
        # A member of another leaderboard type's enum
        (LeaderboardType.GUILD_TERRITORY_BATTLE_STARS, GuildRaidDefId.RANCOR_DIFF01),
        (LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER, TerritoryBattleDefId.T01D),
        (LeaderboardType.GUILD_RAID_HIGH_WATERMARK, TerritoryWarDefId.TERRITORY_WAR_LEADERBOARD),
        # The same mistake spelled as a raw string
        (LeaderboardType.GUILD_TERRITORY_BATTLE_STARS, "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01"),
        (LeaderboardType.GUILD_RAID_HIGH_WATERMARK, "t04D"),
        # Not a legal value for any type
        (LeaderboardType.GUILD_TERRITORY_BATTLE_STARS, "not-an-enum-value"),
        (LeaderboardType.GUILD_RAID_HIGH_WATERMARK, "GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF99"),
        (LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER, ""),
    ],
)
def test_guild_leaderboard_wrong_def_id_rejected(leaderboard_type, def_id):
    """A defId outside the enum coupled to the leaderboard type is rejected before the request."""
    with pytest.raises(ValidationError, match="invalid def_id"):
        api_instance.fetch_guild_leaderboard(leaderboard_type, def_id=def_id)


@pytest.mark.parametrize("leaderboard_type", NO_DEF_ID_TYPES)
def test_guild_leaderboard_def_id_rejected_for_types_without_one(leaderboard_type):
    """Types 0/1/3 define no defId; supplying one is caller confusion, not a valid request."""
    with pytest.raises(ValidationError, match="does not accept a def_id"):
        api_instance.fetch_guild_leaderboard(leaderboard_type, def_id="t01D")


def test_guild_leaderboard_def_id_wrong_python_type_rejected():
    with pytest.raises(ValidationError, match="def_id must be"):
        api_instance.fetch_guild_leaderboard(LeaderboardType.GUILD_TERRITORY_BATTLE_STARS, def_id=4)


@pytest.mark.parametrize("count", [0, 201, -5])
def test_fetch_guild_leaderboard_count_bounds(count):
    with pytest.raises(ValidationError, match="between 1 and 200"):
        api_instance.fetch_guild_leaderboard(LeaderboardType.GUILD_GALACTIC_POWER, count=count)


@pytest.mark.parametrize("count", [1, 200])
def test_fetch_guild_leaderboard_count_bounds_inclusive(httpx_mock: HTTPXMock, count):
    """1 and 200 are the spec's inclusive minimum and maximum."""
    httpx_mock.add_response(json={"data": {}}, status_code=200)
    api_instance.fetch_guild_leaderboard(LeaderboardType.GUILD_GALACTIC_POWER, count=count)
    assert sent_payload(httpx_mock)["payload"]["count"] == count


def test_fetch_guild_leaderboard_count_checked_before_def_id():
    """A bad count fails on count, even when the defId coupling is also unsatisfied."""
    with pytest.raises(ValidationError, match="between 1 and 200"):
        api_instance.fetch_guild_leaderboard(LeaderboardType.GUILD_RAID_HIGH_WATERMARK, count=0)


def test_fetch_guild_leaderboard_invalid_type():
    """An int outside the enum is caller input, so it surfaces as ValidationError, not a bare
    ValueError leaking out of the LeaderboardType() lookup."""
    with pytest.raises(ValidationError, match="invalid leaderboard_type 2"):
        api_instance.fetch_guild_leaderboard(2)  # 2 is not a valid LeaderboardType


def test_user_discord_id_injected_and_forces_hmac(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    api_instance.fetch_data(endpoint="tw", hmac=False, user_discord_id="123456789987654321")

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload["payload"]["userDiscordId"] == "123456789987654321"
    # HMAC signing was forced despite hmac=False
    assert "authorization" in request.headers
    assert "x-timestamp" in request.headers


def test_hmac_false_sends_api_key_header(httpx_mock: HTTPXMock):
    """After a signed request, an unsigned request must carry the plaintext api-key again."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    httpx_mock.add_response(json={"ok": True}, status_code=200)

    api_instance.fetch_data(endpoint="tw", hmac=True)
    api_instance.fetch_data(endpoint="tw", hmac=False)

    signed, unsigned = httpx_mock.get_requests()
    assert "authorization" in signed.headers
    assert unsigned.headers.get("api-key") == "mock_api_key"
    assert "authorization" not in unsigned.headers


# --- act-as-other-user reachability through every non-authenticated helper -------------------
# Every helper forwards its **kwargs to fetch_data unchanged, so user_discord_id, hmac and
# method reach the wire instead of being silently discarded, and a typo raises TypeError at the
# fetch_data signature instead of vanishing.

DISCORD_ID = "123456789987654321"

# (helper name, positional args) for the five non-authenticated endpoints
NON_AUTH_HELPERS = [
    ("fetch_data", (EndPoint.PLAYER,)),
    ("fetch_player", ("987654321",)),
    ("fetch_guild", ("GUILD_ID",)),
    ("fetch_player_arena", ("987654321",)),
    ("fetch_guild_leaderboard", (LeaderboardType.GUILD_GALACTIC_POWER,)),
]


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
def test_user_discord_id_reaches_wire_through_every_non_auth_helper(httpx_mock: HTTPXMock, helper, args):
    """user_discord_id survives the helper and lands in the request body as payload.userDiscordId."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    getattr(api_instance, helper)(*args, hmac=False, user_discord_id=DISCORD_ID)

    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content)["payload"]["userDiscordId"] == DISCORD_ID
    # userDiscordId forces HMAC signing even though hmac=False was passed through the helper
    assert "authorization" in request.headers
    assert "x-timestamp" in request.headers


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
async def test_user_discord_id_reaches_wire_through_every_non_auth_helper_async(httpx_mock: HTTPXMock, helper, args):
    """Async twins forward user_discord_id identically."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    await getattr(api_instance, f"{helper}_async")(*args, hmac=False, user_discord_id=DISCORD_ID)

    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content)["payload"]["userDiscordId"] == DISCORD_ID
    assert "authorization" in request.headers
    assert "x-timestamp" in request.headers


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
def test_unknown_keyword_raises_type_error(helper, args):
    """A misspelled keyword surfaces as TypeError at the fetch_data signature, not silence."""
    with pytest.raises(TypeError, match="user_discrod_id"):
        getattr(api_instance, helper)(*args, user_discrod_id=DISCORD_ID)


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
async def test_unknown_keyword_raises_type_error_async(helper, args):
    """Same for the async twins."""
    with pytest.raises(TypeError, match="user_discrod_id"):
        await getattr(api_instance, f"{helper}_async")(*args, user_discrod_id=DISCORD_ID)


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
def test_non_auth_helpers_default_enums_to_false(httpx_mock: HTTPXMock, helper, args):
    """Per-helper enums defaulting survives the wholesale **kwargs pass-through."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    getattr(api_instance, helper)(*args)
    assert sent_payload(httpx_mock)["payload"]["enums"] is False


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
def test_non_auth_helpers_forward_explicit_enums(httpx_mock: HTTPXMock, helper, args):
    """An explicit enums=True still overrides the default through the pass-through."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    getattr(api_instance, helper)(*args, enums=True)
    assert sent_payload(httpx_mock)["payload"]["enums"] is True


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
async def test_non_auth_helpers_forward_explicit_enums_async(httpx_mock: HTTPXMock, helper, args):
    """Async twins honour an explicit enums=True too."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    await getattr(api_instance, f"{helper}_async")(*args, enums=True)
    assert sent_payload(httpx_mock)["payload"]["enums"] is True


@pytest.mark.parametrize("helper, args", NON_AUTH_HELPERS)
def test_hmac_false_reaches_wire_through_every_non_auth_helper(httpx_mock: HTTPXMock, helper, args):
    """hmac= is honoured through the helpers: without user_discord_id it downgrades to api-key."""
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    getattr(api_instance, helper)(*args, hmac=False)

    request = httpx_mock.get_requests()[0]
    assert request.headers.get("api-key") == "mock_api_key"
    assert "authorization" not in request.headers


def test_fetch_player_forwards_method(httpx_mock: HTTPXMock):
    """method= is no longer swallowed; it reaches fetch_data (which signs with it)."""
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    api_instance.fetch_player("987654321", method="post")
    assert httpx_mock.get_requests()[0].url.path == "/api/player"


def test_fetch_player_duplicate_payload_keyword_rejected():
    """The helper owns the payload argument; supplying a second one is an error, not a silent win."""
    with pytest.raises(TypeError, match="payload"):
        api_instance.fetch_player("987654321", payload={"payload": {"allyCode": "000"}})


# --- per-call allycode cleansing parity ------------------------------------------------------
# _verify_allycode used to check only "is a non-empty string", so a dashed or malformed allycode
# supplied per call reached the wire untouched, while the same value through the constructor was
# cleansed to 9 digits. Both doors now run cleanse_allycode.

DASHED_ALLYCODE = "123-456-789"
CLEANSED_ALLYCODE = "123456789"

# Every public entry point that accepts a per-call allycode
ALLYCODE_HELPERS = ["fetch_player", "fetch_player_arena"]


def test_constructor_allycode_is_cleansed():
    assert API("mock_api_key", DASHED_ALLYCODE).allycode == CLEANSED_ALLYCODE


@pytest.mark.parametrize("helper", ALLYCODE_HELPERS)
def test_per_call_dashed_allycode_is_normalised(httpx_mock: HTTPXMock, helper):
    """A dashed allycode passed per call is stripped before it reaches the wire."""
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    getattr(api_instance, helper)(DASHED_ALLYCODE)
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == CLEANSED_ALLYCODE


@pytest.mark.parametrize("helper", ALLYCODE_HELPERS)
async def test_per_call_dashed_allycode_is_normalised_async(httpx_mock: HTTPXMock, helper):
    """The async twins share the identity builder, so they normalise identically."""
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    await getattr(api_instance, f"{helper}_async")(DASHED_ALLYCODE)
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == CLEANSED_ALLYCODE


def test_both_doors_send_the_same_allycode(httpx_mock: HTTPXMock):
    """Same value, same fate: the constructor door and the per-call door converge on one payload."""
    constructor_client = API("mock_api_key", DASHED_ALLYCODE)
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    httpx_mock.add_response(json={"events": {}}, status_code=200)

    constructor_client.fetch_player()  # cleansed at construction
    api_instance.fetch_player(DASHED_ALLYCODE)  # cleansed at call time

    via_constructor, via_call = (json.loads(req.content)["payload"]["allyCode"] for req in httpx_mock.get_requests())
    assert via_constructor == via_call == CLEANSED_ALLYCODE


MALFORMED_ALLYCODES = ["not-a-code", "12345678", "1234567890", "12345678a", "123-456-78", "   "]


@pytest.mark.parametrize("helper", ALLYCODE_HELPERS)
@pytest.mark.parametrize("bad_allycode", MALFORMED_ALLYCODES)
def test_malformed_per_call_allycode_rejected_before_any_request(httpx_mock: HTTPXMock, helper, bad_allycode):
    """A malformed per-call allycode fails locally as ValidationError -- no request is issued."""
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
        getattr(api_instance, helper)(bad_allycode)
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("bad_allycode", MALFORMED_ALLYCODES)
async def test_malformed_per_call_allycode_rejected_async(httpx_mock: HTTPXMock, bad_allycode):
    with pytest.raises(ValidationError, match="Value must be exactly 9 numerical characters."):
        await api_instance.fetch_player_async(bad_allycode)
    assert httpx_mock.get_requests() == []


def test_per_call_allycode_rejection_matches_the_constructor_rejection():
    """Both doors reject with the same exception type and the same message."""
    with pytest.raises(ValidationError) as via_constructor:
        API("mock_api_key", "not-a-code")
    with pytest.raises(ValidationError) as via_call:
        api_instance.fetch_player("not-a-code")
    assert str(via_constructor.value) == str(via_call.value)


def test_non_string_per_call_allycode_rejected(httpx_mock: HTTPXMock):
    """A non-string allycode is a ValidationError too, not a TypeError."""
    with pytest.raises(ValidationError, match="must be a string"):
        api_instance.fetch_player(123456789)
    assert httpx_mock.get_requests() == []


def test_empty_per_call_allycode_falls_back_to_the_instance_allycode(httpx_mock: HTTPXMock):
    """An empty allycode means 'not supplied', so the documented default applies rather than a raise."""
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    api_instance.fetch_player("")
    assert sent_payload(httpx_mock)["payload"]["allyCode"] == "123456789"


def test_player_id_path_is_untouched_by_allycode_cleansing(httpx_mock: HTTPXMock):
    """playerId is an opaque token and must not be run through the allycode rules."""
    httpx_mock.add_response(json={"events": {}}, status_code=200)
    api_instance.fetch_player(player_id="P-123-abc")
    assert sent_payload(httpx_mock)["payload"]["playerId"] == "P-123-abc"


# --- guild_id: no cleansing to mirror --------------------------------------------------------
# Spec v1.0.1 declares guildId as {"type": "string", "example": "B2-VYdu3SEevuO3NTCW52Q"} with no
# pattern, length or format. Dashes are content, not formatting, so there is no normalisation step
# and no format rule the spec would support. Non-empty string is the whole contract.


def test_guild_id_dashes_are_preserved(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": {"guild": {"name": "guild"}}}, status_code=200)
    api_instance.fetch_guild("B2-VYdu3SEevuO3NTCW52Q")
    assert sent_payload(httpx_mock)["payload"]["guildId"] == "B2-VYdu3SEevuO3NTCW52Q"


@pytest.mark.parametrize(
    "bad_guild_id, message", [("", "cannot be empty"), (12345, "must be a string"), (None, "must be a string")]
)
def test_guild_id_rejected_as_validation_error(httpx_mock: HTTPXMock, bad_guild_id, message):
    with pytest.raises(ValidationError, match=message):
        api_instance.fetch_guild(bad_guild_id)
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("bad_guild_id, message", [("", "cannot be empty"), (12345, "must be a string")])
async def test_guild_id_rejected_as_validation_error_async(httpx_mock: HTTPXMock, bad_guild_id, message):
    with pytest.raises(ValidationError, match=message):
        await api_instance.fetch_guild_async(bad_guild_id)
    assert httpx_mock.get_requests() == []
