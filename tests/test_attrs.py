"""Tests for enums and attribute helpers in attrs.py."""

from mhanndalorian_bot.attrs import AUTHENTICATED_ENDPOINTS, AllyCode, EndPoint, LeaderboardType


def test_endpoint_aliases():
    """ARENA and VERIFY are intentional aliases sharing another member's slug."""
    assert EndPoint.ARENA is EndPoint.LEADERBOARD
    assert EndPoint.VERIFY is EndPoint.REGISTER


def test_new_endpoints_present():
    assert EndPoint.GUILDLEADERBOARD.value == "guildleaderboard"
    assert EndPoint.PLAYERARENA.value == "playerarena"
    assert EndPoint.EVENTS.value == "events"


def test_get_endpoints_includes_aliases():
    names = EndPoint.get_endpoints()
    for expected in ("TW", "ARENA", "LEADERBOARD", "GUILDLEADERBOARD", "PLAYERARENA", "REGISTER", "VERIFY"):
        assert expected in names


def test_get_endpoints_is_names_not_slugs():
    """21 names over 19 distinct slugs, as the docstring promises; iterating skips aliases."""
    names = EndPoint.get_endpoints()
    slugs = [member.value for member in EndPoint]

    assert len(names) == 21
    assert len(set(names)) == 21, "names are unique even though two pairs share a slug"
    assert len(slugs) == len(set(slugs)) == 19, "18 spec paths plus the registry's 'comlink'"
    assert set(slugs) == {member.value for member in EndPoint.__members__.values()}
    assert {"LEADERBOARD", "ARENA"} <= set(names) and {"REGISTER", "VERIFY"} <= set(names)


def test_leaderboard_type_values():
    assert LeaderboardType.UNSPECIFIED == 0
    assert LeaderboardType.GUILD_RAID_ALL_COMP_PTS == 1
    assert LeaderboardType.GUILD_GALACTIC_POWER == 3
    assert LeaderboardType.GUILD_TERRITORY_BATTLE_STARS == 4
    assert LeaderboardType.GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER == 5
    assert LeaderboardType.GUILD_RAID_HIGH_WATERMARK == 6
    # 2 is intentionally absent from the API contract
    assert 2 not in [member.value for member in LeaderboardType]


def test_authenticated_endpoints_complete():
    """All 13 session-breaking endpoint slugs are tracked."""
    assert AUTHENTICATED_ENDPOINTS == frozenset(
        {
            "activeraid",
            "conquest",
            "events",
            "gac",
            "inventory",
            "leaderboard",
            "squadpresets",
            "tb",
            "tbleaderboardhistory",
            "tblogs",
            "tw",
            "twleaderboard",
            "twlogs",
        }
    )


def test_endpoint_is_authenticated_property():
    assert EndPoint.TW.is_authenticated is True
    assert EndPoint.INVENTORY.is_authenticated is True
    assert EndPoint.PLAYER.is_authenticated is False
    assert EndPoint.GUILDLEADERBOARD.is_authenticated is False
    assert EndPoint.PLAYERARENA.is_authenticated is False
    assert EndPoint.FETCH.is_authenticated is False


# --- descriptor shape ---------------------------------------------------------------------------


def test_allycode_descriptor_is_not_a_string():
    """AllyCode inherited `str`, which made the descriptor object itself a string of value "".

    Nothing used the string behaviour; it only confused the MRO and any type checker reading it.
    The managed *value* is a str -- the descriptor is not.
    """
    from mhanndalorian_bot.base import MBot

    descriptor = MBot.__dict__["allycode"]
    assert isinstance(descriptor, AllyCode)
    assert not isinstance(descriptor, str)
    assert str not in type(descriptor).__mro__


def test_dead_attribute_classes_are_gone():
    """Headers, Payload, Debug and HMAC were never instantiated anywhere.

    `self.headers` / `self.payload` are plain dicts and `MBot.debug` / `MBot.hmac` are plain
    class attributes, so these four were unreachable code exported in __all__.
    """
    from mhanndalorian_bot import attrs

    for name in ("Headers", "Payload", "Debug", "HMAC"):
        assert not hasattr(attrs, name), f"{name} should have been removed"
        assert name not in attrs.__all__
