"""Unit tests for the typed Territory Battle activity helpers.

The record is a decoder: one ``TerritoryZoneData`` payload plus its envelope
becomes one flat :class:`~mhanndalorian_bot.helpers.TerritoryActivity`. The contracts
pinned here are the ones that are silent rather than loud — lineage that is
observed rather than guaranteed, scores that arrive as strings on the wire, an
Opaque Payload that cannot be typed, and the type gate living on the iterator
rather than on the parser.
"""

from __future__ import annotations

from typing import Any

from mhanndalorian_bot.helpers import (
    TERRITORY_ACTIVITY_TYPES,
    TerritoryActivity,
    TerritoryReconUnit,
    iter_activity_events,
    iter_territory_activities,
    parse_territory_activity,
)

CONFLICT = "tb3_mixed_phase01_conflict02"
STRIKE_CHILD = "tb3_mixed_phase01_conflict02_strike04"
EVENT_CHANNEL = "TZ-conflict-02"


# ── Builders ────────────────────────────────────────────────────────────


def zone_data(**overrides: Any) -> dict[str, Any]:
    """A ``TerritoryZoneData`` body — scores as strings, as they arrive live."""
    zone = {
        "zoneId": CONFLICT,
        "sourceZoneId": STRIKE_CHILD,
        "scoreDelta": "1500",
        "scoreTotal": "42000",
        "participationDelta": 1,
        "participationTotal": 9,
        "state": "TERRITORYZONESTATE_ACTIVE",
        "instanceType": 2,
        "notificationInstanceType": 1,
        "activityLogMessage": {
            "key": "TERRITORY_CHANNEL_ACTIVITY_STRIKE_LINKED_CONFLICT_CONTRIBUTION",
            "param": [{"key": "playerName", "value": "Kylo"}],
        },
        "guildId": "G-123",
        "mapId": "tb3_mixed",
        "mapInstanceId": "TB_EVENT_TB3_MIXED:O1785776400000",
    }
    zone.update(overrides)
    return zone


def raw_event(
    *,
    activity_type: str = "TERRITORY_CONFLICT_ACTIVITY",
    payload: Any = None,
    event_id: str = "e1",
    **envelope: Any,
) -> dict[str, Any]:
    """A raw Channel event envelope wrapping one activity payload."""
    event = {
        "id": event_id,
        "channelId": EVENT_CHANNEL,
        "authorId": "author-1",
        "authorName": "Kylo",
        "timestamp": "1754150400000",
        "data": [{"type": activity_type, "payload": {"zoneData": zone_data()} if payload is None else payload}],
    }
    event.update(envelope)
    return event


def one(raw: dict[str, Any]) -> TerritoryActivity | None:
    """Unpack a raw event and type its single activity."""
    (event,) = list(iter_activity_events([raw]))
    return parse_territory_activity(event)


# ── The decoded body ────────────────────────────────────────────────────


def test_a_conflict_activity_is_fully_typed():
    activity = one(raw_event())
    assert isinstance(activity, TerritoryActivity)
    assert activity.activity_type == "TERRITORY_CONFLICT_ACTIVITY"
    assert activity.zone_id == CONFLICT
    assert activity.source_zone_id == STRIKE_CHILD
    assert activity.participation_delta == 1
    assert activity.participation_total == 9


def test_scores_are_coerced_from_the_strings_they_arrive_as():
    activity = one(raw_event())
    assert activity.score_delta == 1500
    assert activity.score_total == 42000
    assert isinstance(activity.score_delta, int)


def test_the_envelope_provenance_is_carried_onto_the_record():
    activity = one(raw_event(event_id="e-prov"))
    assert activity.event_id == "e-prov"
    assert activity.channel_id == EVENT_CHANNEL
    assert activity.author_name == "Kylo"
    assert activity.timestamp == 1754150400000


def test_zone_state_and_instance_types_are_preserved_as_sent():
    """``TerritoryZoneState`` renders as a string with enums on, an int with them off."""
    activity = one(raw_event())
    assert activity.state == "TERRITORYZONESTATE_ACTIVE"
    assert activity.instance_type == 2
    assert activity.notification_instance_type == 1


def test_an_integer_state_rendering_survives():
    activity = one(raw_event(payload={"zoneData": zone_data(state=3)}))
    assert activity.state == 3


# ── Lineage ─────────────────────────────────────────────────────────────


def test_a_child_sourced_contribution_is_not_a_direct_deploy():
    activity = one(raw_event())
    assert activity.source_zone_id == STRIKE_CHILD
    assert activity.is_direct_deploy is False


def test_an_empty_source_zone_is_a_direct_deploy():
    activity = one(raw_event(payload={"zoneData": zone_data(sourceZoneId="")}))
    assert activity.source_zone_id == ""
    assert activity.is_direct_deploy is True


def test_a_self_sourced_recon_event_is_not_a_direct_deploy():
    """Recon read on its own zone's Channel self-pairs: source equals zone."""
    activity = one(raw_event(payload={"zoneData": zone_data(zoneId=CONFLICT, sourceZoneId=CONFLICT)}))
    assert activity.source_zone_id == activity.zone_id
    assert activity.is_direct_deploy is False


# ── The activity-log message ────────────────────────────────────────────


def test_a_keyed_message_is_not_structural_and_keeps_its_params():
    activity = one(raw_event())
    assert activity.message_key == "TERRITORY_CHANNEL_ACTIVITY_STRIKE_LINKED_CONFLICT_CONTRIBUTION"
    assert activity.is_structural is False
    assert activity.message_params == ({"key": "playerName", "value": "Kylo"},)


def test_an_empty_key_is_structural():
    activity = one(raw_event(payload={"zoneData": zone_data(activityLogMessage={"key": "EMPTY"})}))
    assert activity.message_key == "EMPTY"
    assert activity.is_structural is True


def test_a_missing_message_is_structural_with_no_params():
    zone = zone_data()
    del zone["activityLogMessage"]
    activity = one(raw_event(payload={"zoneData": zone}))
    assert activity.message_key == ""
    assert activity.message_params == ()
    assert activity.is_structural is True


# ── Recon units ─────────────────────────────────────────────────────────


def test_recon_units_are_typed():
    payload = {
        "zoneData": zone_data(),
        "platoonId": "plt-1",
        "units": [
            {"unitIdentifier": "HERMITYODA", "level": 85, "tier": 13, "unitRelicTier": 9, "squadId": "sq-1"},
            {"unitIdentifier": "GRANDMASTERYODA", "level": 85, "tier": "GEARLEVEL_THIRTEEN", "squadId": "sq-1"},
        ],
    }
    activity = one(raw_event(activity_type="TERRITORY_RECON_ACTIVITY", payload=payload))
    assert activity.platoon_id == "plt-1"
    assert len(activity.units) == 2
    first = activity.units[0]
    assert isinstance(first, TerritoryReconUnit)
    assert (first.unit_id, first.level, first.tier, first.relic_tier, first.squad_id) == (
        "HERMITYODA",
        85,
        13,
        9,
        "sq-1",
    )
    # An enum-rendered tier survives as its string, and an absent relic tier is None.
    assert activity.units[1].tier == "GEARLEVEL_THIRTEEN"
    assert activity.units[1].relic_tier is None


def test_a_non_recon_activity_has_no_units_or_platoon():
    activity = one(raw_event())
    assert activity.units == ()
    assert activity.platoon_id == ""


# ── What cannot be typed returns None ───────────────────────────────────


def test_an_opaque_payload_cannot_be_typed():
    opaque = raw_event(payload=None)
    opaque["data"] = [{"type": "TERRITORY_CONFLICT_ACTIVITY", "payload": "CgtTUVVBRF9M", "error": "failed to decode"}]
    assert one(opaque) is None


def test_a_map_activity_has_no_zone_body():
    """``TERRITORY_MAP_ACTIVITY`` carries ``mapData``, not ``zoneData``."""
    payload = {"mapData": {"mapId": "tb3_mixed", "instanceId": "TB...", "forceRefresh": True}}
    assert one(raw_event(activity_type="TERRITORY_MAP_ACTIVITY", payload=payload)) is None


def test_a_payload_without_a_zone_data_dict_is_none():
    assert one(raw_event(payload={"zoneData": "not-a-dict"})) is None


# ── parse does not gate on type; the iterator does ──────────────────────


def test_parse_types_a_war_conflict_activity_because_it_carries_zone_data():
    """The parser is lenient — the ``warSquad`` is simply not represented here."""
    activity = one(raw_event(activity_type="TERRITORY_WAR_CONFLICT_ACTIVITY"))
    assert activity is not None
    assert activity.activity_type == "TERRITORY_WAR_CONFLICT_ACTIVITY"


def test_iter_defaults_to_the_four_battle_families():
    events = [
        raw_event(activity_type="TERRITORY_CONFLICT_ACTIVITY", event_id="a"),
        raw_event(activity_type="TERRITORY_COVERT_ACTIVITY", event_id="b"),
        raw_event(activity_type="TERRITORY_WAR_CONFLICT_ACTIVITY", event_id="c"),
    ]
    types = [a.activity_type for a in iter_territory_activities(events)]
    assert types == ["TERRITORY_CONFLICT_ACTIVITY", "TERRITORY_COVERT_ACTIVITY"]
    assert "TERRITORY_WAR_CONFLICT_ACTIVITY" not in types


def test_iter_with_types_none_types_every_zone_body():
    events = [
        raw_event(activity_type="TERRITORY_COVERT_ACTIVITY", event_id="a"),
        raw_event(activity_type="TERRITORY_WAR_CONFLICT_ACTIVITY", event_id="b"),
    ]
    types = {a.activity_type for a in iter_territory_activities(events, types=None)}
    assert types == {"TERRITORY_COVERT_ACTIVITY", "TERRITORY_WAR_CONFLICT_ACTIVITY"}


def test_iter_skips_what_cannot_be_typed():
    opaque = raw_event(event_id="op")
    opaque["data"] = [{"type": "TERRITORY_CONFLICT_ACTIVITY", "payload": "CgtT", "error": "x"}]
    good = raw_event(event_id="ok")
    activities = list(iter_territory_activities([opaque, good]))
    assert [a.event_id for a in activities] == ["ok"]


def test_the_exported_family_tuple_is_the_four_battle_types():
    assert TERRITORY_ACTIVITY_TYPES == (
        "TERRITORY_CONFLICT_ACTIVITY",
        "TERRITORY_STRIKE_ACTIVITY",
        "TERRITORY_RECON_ACTIVITY",
        "TERRITORY_COVERT_ACTIVITY",
    )
