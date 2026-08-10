"""Unit tests for the MBot event adapter, spine, and convenience wrappers.

``normalize_events`` is the one piece of genuinely new code in the territory
parsing layer: it bridges MBot's ``info``/``payload`` response shape onto the
flat event contract the ported decoders expect (see
``docs/adr/0002-normalize-event-shape-adapter.md``). The decoders themselves are
exercised verbatim in ``test_tb_helpers`` and ``test_war_helpers``; here we pin
the adapter, re-confirm the spine on flat input, check the wrappers delegate
after normalizing, and lock an end-to-end golden run against a real capture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mhanndalorian_bot.helpers import (
    ActivityEvent,
    BattleLog,
    TerritoryActivity,
    battle_log,
    defending_squads,
    iter_activity_events,
    normalize_events,
    territory_activities,
)

FIXTURE = Path(__file__).parent / "fixtures" / "twlogs_slice.json"

# The frozen result of running the committed golden slice through the correlator.
# The slice is the first 300 events (by timestamp) of a real TW capture, with the
# unread ``warSquad.squad`` / ``warSquad.crewInfo`` blobs stripped; stripping them
# leaves every outcome unchanged (that equivalence is what keeps the fixture at
# ~270 KB instead of 13 MB).
GOLDEN_BATTLES = 72
GOLDEN_OUTCOMES = {"won": 46, "repulse": 22, "orphaned_win": 3, "obscured": 1}
GOLDEN_DEFENDING_SQUADS = 161


# ── Builders (MBot's on-the-wire shape: envelope under ``info``) ─────────────


def mbot_event(
    *,
    type_: str = "TERRITORY_WAR_CONFLICT_ACTIVITY",
    event_id: str = "e1",
    channel_id: str = "TZ-conflict-01",
    payload: dict[str, Any] | None = None,
    **envelope: Any,
) -> dict[str, Any]:
    """One event exactly as ``/twlogs`` and ``/tblogs`` deliver it."""
    info = {
        "data": [{"type": type_}],
        "id": event_id,
        "correlationId": "",
        "channelId": channel_id,
        "eventType": 2,
        "eventSubtype": "",
        "timestamp": "1765126564945",
        "authorId": "a1",
        "authorName": "Kylo",
        "message": "",
    }
    info.update(envelope)
    return {"info": info, "payload": payload if payload is not None else {"zoneData": {}}}


def twlogs_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    """A ``/twlogs`` response — events under the ``data`` key."""
    return {"code": 0, "instanceId": "TERRITORY_WAR_EVENT_C:O1", "data": events}


def tblogs_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    """A ``/tblogs`` response — events under the ``event`` key."""
    return {"code": 0, "instanceId": "TERRITORY_BATTLE_EVENT_O:1", "event": events}


# ── normalize_events ────────────────────────────────────────────────────────


def test_it_lifts_the_info_envelope_to_the_top_level():
    flat = normalize_events(twlogs_response([mbot_event(event_id="x9")]))
    assert len(flat) == 1
    event = flat[0]
    assert event["id"] == "x9"
    assert event["channelId"] == "TZ-conflict-01"
    assert event["authorName"] == "Kylo"
    # ``info`` itself is gone — its fields are now top-level.
    assert "info" not in event


def test_it_reattaches_the_event_level_payload_to_the_data_item():
    payload = {"zoneData": {"zoneId": "z1", "scoreDelta": "10"}, "warSquad": None}
    flat = normalize_events(twlogs_response([mbot_event(payload=payload)]))
    (item,) = flat[0]["data"]
    assert item["type"] == "TERRITORY_WAR_CONFLICT_ACTIVITY"
    assert item["payload"] is payload


def test_it_reads_the_tw_data_key():
    assert len(normalize_events(twlogs_response([mbot_event(), mbot_event()]))) == 2


def test_it_reads_the_tb_event_key():
    assert len(normalize_events(tblogs_response([mbot_event(), mbot_event()]))) == 2


def test_a_bare_list_of_events_is_accepted():
    flat = normalize_events([mbot_event(event_id="bare")])
    assert flat[0]["id"] == "bare"


def test_an_already_flat_event_passes_through_untouched():
    flat = {"id": "f1", "channelId": "c", "data": [{"type": "T", "payload": {"zoneData": {}}}]}
    assert normalize_events([flat]) == [flat]


def test_normalize_is_idempotent():
    once = normalize_events(twlogs_response([mbot_event(), mbot_event(event_id="e2")]))
    assert normalize_events(once) == once


def test_garbage_input_yields_an_empty_list_rather_than_raising():
    assert normalize_events(None) == []
    assert normalize_events(42) == []
    assert normalize_events({"code": 0}) == []  # neither data nor event key
    assert normalize_events({"data": "not-a-list"}) == []


def test_a_non_dict_event_in_the_list_is_skipped():
    flat = normalize_events(twlogs_response([mbot_event(event_id="ok"), "junk", 7]))
    assert [e["id"] for e in flat] == ["ok"]


# ── iter_activity_events on the normalized (flat) stream ─────────────────────


def test_the_spine_types_a_decoded_payload_and_carries_the_envelope():
    payload = {"zoneData": {"zoneId": "z1"}}
    flat = normalize_events(twlogs_response([mbot_event(event_id="ev", payload=payload)]))
    (event,) = list(iter_activity_events(flat))
    assert isinstance(event, ActivityEvent)
    assert event.event_id == "ev"
    assert event.channel_id == "TZ-conflict-01"
    assert event.author_name == "Kylo"
    assert event.type == "TERRITORY_WAR_CONFLICT_ACTIVITY"
    assert event.payload is payload
    assert event.opaque is False


def test_the_spine_marks_a_non_dict_payload_opaque():
    flat = normalize_events(twlogs_response([mbot_event(payload=None)]))
    # payload defaults to a dict via the builder, so force a non-dict here:
    flat[0]["data"][0]["payload"] = "base64=="
    (event,) = list(iter_activity_events(flat))
    assert event.opaque is True
    assert event.payload is None
    assert event.raw == "base64=="


def test_the_types_filter_selects_on_the_item_type():
    flat = normalize_events(
        twlogs_response(
            [
                mbot_event(type_="TERRITORY_WAR_CONFLICT_ACTIVITY", event_id="w"),
                mbot_event(type_="TERRITORY_CONFLICT_ACTIVITY", event_id="b"),
            ]
        )
    )
    kept = list(iter_activity_events(flat, types="TERRITORY_CONFLICT_ACTIVITY"))
    assert [e.event_id for e in kept] == ["b"]


# ── Convenience wrappers ─────────────────────────────────────────────────────


def test_territory_activities_normalizes_then_types_tb_activity():
    zone = {"zoneId": "tb_conflict01", "scoreDelta": "500", "scoreTotal": "500"}
    resp = tblogs_response([mbot_event(type_="TERRITORY_CONFLICT_ACTIVITY", payload={"zoneData": zone})])
    acts = list(territory_activities(resp))
    assert len(acts) == 1
    assert isinstance(acts[0], TerritoryActivity)
    assert acts[0].zone_id == "tb_conflict01"
    assert acts[0].score_delta == 500


def test_battle_log_wrapper_returns_a_populated_log():
    log = battle_log(twlogs_response([mbot_event()]))
    assert isinstance(log, BattleLog)


def test_defending_squads_wrapper_returns_a_dict():
    assert isinstance(defending_squads(twlogs_response([mbot_event()])), dict)


# ── Golden end-to-end run against a real capture ─────────────────────────────


def test_golden_capture_reproduces_the_frozen_outcome_matrix():
    resp = json.loads(FIXTURE.read_text())
    log = battle_log(resp)

    outcomes: dict[str, int] = {}
    for battle in log.battles:
        outcomes[battle.outcome.value] = outcomes.get(battle.outcome.value, 0) + 1

    assert len(log.battles) == GOLDEN_BATTLES
    assert outcomes == GOLDEN_OUTCOMES
    assert len(defending_squads(resp)) == GOLDEN_DEFENDING_SQUADS


def test_golden_capture_has_no_opaque_events_because_the_backend_pre_decodes():
    resp = json.loads(FIXTURE.read_text())
    events = list(iter_activity_events(normalize_events(resp)))
    assert events, "fixture should contain events"
    assert all(not e.opaque for e in events)
