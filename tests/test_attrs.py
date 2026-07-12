"""Tests for enums and attribute helpers in attrs.py."""

from mhanndalorian_bot.attrs import AUTHENTICATED_ENDPOINTS, EndPoint, LeaderboardType


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
