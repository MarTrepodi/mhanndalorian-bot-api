"""Unit tests for Territory War Battle correlation.

:class:`~mhanndalorian_bot.helpers.BattleLog` performs no I/O, so these tests feed
it hand-built event dictionaries shaped like the sampled capture: every
``warSquad`` event carries the squad's complete current state, and the
correlator reconciles those snapshots rather than pairing transitions.

The outcome tests walk the four cells of the loss model in ADR 0003 — which
ends of a Battle were observed, not what happened — and the rest pin the two
properties that make a naive implementation quietly wrong:

- A Battle is keyed by ``(zone, squad, lock episode)``. The same Attacker
  assaults the same squad repeatedly, so two lock episodes are two Battles.
- ``successfulDefends`` is not monotonic. It is a floor, never a delta; the
  sequence ``1, 0, 2, 2`` below is the real one from the capture.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from mhanndalorian_bot.helpers import (
    Battle,
    BattleLog,
    BattleLogState,
    BattleOutcome,
    get_defending_squads,
)

ZONE = "tw_jakku01_phase01_conflict01"
OTHER_ZONE = "tw_jakku01_phase01_conflict02"
SQUAD = "squad-0001"
OTHER_SQUAD = "squad-0002"
ATTACKER = "Kylo"
DEFENDER = "Ahsoka"

SECOND = 1000  # envelope timestamps are milliseconds

# The three renderings of ``TerritoryZoneInstance.ZONE_INSTANCE_AWAY``: the name
# ``GET /enums`` gives it, the Enum Translation form (group name, underscore,
# value with its underscores removed — the value name already repeats the group,
# and the rule does not deduplicate) and the bare integer.
AWAY_NAME = "ZONE_INSTANCE_AWAY"
AWAY_TRANSLATED = "TERRITORYZONEINSTANCE_ZONEINSTANCEAWAY"
AWAY_INT = 3
HOME_NAME = "ZONE_INSTANCE_HOME"

WAR_ACTIVITY = "TERRITORY_WAR_CONFLICT_ACTIVITY"


def war_event(
    event_id: str,
    timestamp: int,
    *,
    status: Any = "SQUAD_LOCKED",
    zone_id: str = ZONE,
    squad_id: str = SQUAD,
    author: str = ATTACKER,
    lock_name: str | None = None,
    defender: str | None = DEFENDER,
    defends: int = 0,
    power: int = 250_000,
    side: Any = AWAY_NAME,
) -> dict[str, Any]:
    """One Territory War Activity Event envelope carrying a squad snapshot."""
    squad: dict[str, Any] = {
        "squadId": squad_id,
        "squadStatus": status,
        "successfulDefends": defends,
        "power": power,
    }
    if defender is not None:
        squad["playerName"] = defender
    if lock_name is not None:
        squad["lockName"] = lock_name
    return {
        "id": event_id,
        "authorId": f"author-{author}",
        "authorName": author,
        "correlationId": f"corr-{event_id}",
        "eventType": "GAME_ACTIVITY",
        "eventSubtype": "TERRITORY_WAR",
        "message": "",
        "timestamp": timestamp,
        "data": [
            {
                "type": WAR_ACTIVITY,
                "payload": {
                    "zoneData": {"zoneId": zone_id, "notificationInstanceType": side},
                    "warSquad": squad,
                },
            }
        ],
    }


def score_event(event_id: str, timestamp: int) -> dict[str, Any]:
    """A score event: ``scoreDelta`` and no ``warSquad``. Not a Battle."""
    return {
        "id": event_id,
        "authorName": "",
        "timestamp": timestamp,
        "data": [
            {
                "type": "TERRITORY_WAR_SCORE_ACTIVITY",
                "payload": {
                    "zoneData": {"zoneId": ZONE, "notificationInstanceType": AWAY_NAME},
                    "scoreDelta": 1400,
                },
            }
        ],
    }


def opaque_event(event_id: str, timestamp: int) -> dict[str, Any]:
    """An Opaque Payload: envelope only, and no channel id to attribute it by."""
    return {
        "id": event_id,
        "authorName": "Rey",
        "timestamp": timestamp,
        "data": [{"type": WAR_ACTIVITY, "payload": "CgtTUVVBRF9MT0NLRUQ=", "error": "decode"}],
    }


def empty_envelope_event(event_id: str, timestamp: int) -> dict[str, Any]:
    """An opaque record the server supplied nothing for: no ``payload``, no ``raw``, no ``error``."""
    return {
        "id": event_id,
        "authorName": "Rey",
        "timestamp": timestamp,
        "data": [{"type": WAR_ACTIVITY}],
    }


# ── The four cells of the loss model ────────────────────────────────────


def test_lock_then_defeat_is_a_win():
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 80 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert (battle.zone_id, battle.squad_id) == (ZONE, SQUAD)
    assert battle.attacker == ATTACKER
    assert battle.defender == DEFENDER
    assert (battle.opened_at, battle.closed_at) == (1 * SECOND, 80 * SECOND)


def test_lock_then_release_is_a_repulse():
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_AVAILABLE", defends=1),
        ]
    )
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.REPULSE
    assert battle.attacker == ATTACKER
    assert (battle.opened_at, battle.closed_at) == (1 * SECOND, 60 * SECOND)


def test_defeat_with_no_observed_lock_is_an_orphaned_win():
    """The engagement fell outside the reader's earliest Read Position."""
    log = BattleLog()
    log.add([war_event("e1", 80 * SECOND, status="SQUAD_DEFEATED")])
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.ORPHANED_WIN
    assert battle.opened_at is None  # a real win with no measurable duration
    assert battle.closed_at == 80 * SECOND
    assert battle.attacker == ATTACKER  # the envelope's author


def test_lock_with_no_close_ages_into_obscured():
    log = BattleLog(stale_after=10)
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])

    # Still inside the horizon: a live assault must not be reported as lost.
    assert log.battles == []

    # An unrelated event later in the feed advances the log's clock past it.
    log.add([war_event("e2", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD)])
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.OBSCURED
    assert battle.opened_at == 1 * SECOND
    assert battle.closed_at is None


def test_an_aged_lock_still_resolves_when_its_close_arrives_late():
    log = BattleLog(stale_after=10)
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD),
        ]
    )
    assert [b.outcome for b in log.battles] == [BattleOutcome.OBSCURED]

    log.add([war_event("e3", 110 * SECOND, status="SQUAD_DEFEATED")])
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert battle.closed_at == 110 * SECOND


def test_a_lock_taken_over_by_a_different_attacker_obscures_the_first_episode():
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 40 * SECOND, status="SQUAD_LOCKED", author="Rey", lock_name="Rey"),
            war_event("e3", 90 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    assert [(b.attacker, b.outcome) for b in log.battles] == [
        (ATTACKER, BattleOutcome.OBSCURED),
        ("Rey", BattleOutcome.WON),
    ]


# ── A Battle is keyed by lock episode, never by attacker ────────────────


def test_a_relock_by_the_same_attacker_in_the_same_zone_is_two_battles():
    """The same Attacker assaults the same squad repeatedly; the capture shows it."""
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_AVAILABLE", defends=1),
            war_event("e3", 120 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER, defends=1),
            war_event("e4", 200 * SECOND, status="SQUAD_DEFEATED", defends=1),
        ]
    )
    battles = log.battles
    assert len(battles) == 2
    assert [b.outcome for b in battles] == [BattleOutcome.REPULSE, BattleOutcome.WON]
    assert {b.attacker for b in battles} == {ATTACKER}
    assert [b.opened_at for b in battles] == [1 * SECOND, 120 * SECOND]


def test_repeated_lock_snapshots_of_one_episode_are_one_battle():
    """Events are snapshots; a re-sent lock extends the episode rather than opening one."""
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 30 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e3", 60 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    (battle,) = log.battles
    assert battle.opened_at == 1 * SECOND


def test_the_same_squad_id_in_two_zones_is_two_battles():
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 2 * SECOND, status="SQUAD_LOCKED", zone_id=OTHER_ZONE, lock_name=ATTACKER),
            war_event("e3", 60 * SECOND, status="SQUAD_DEFEATED"),
            war_event("e4", 61 * SECOND, status="SQUAD_DEFEATED", zone_id=OTHER_ZONE),
        ]
    )
    assert {(b.zone_id, b.outcome) for b in log.battles} == {
        (ZONE, BattleOutcome.WON),
        (OTHER_ZONE, BattleOutcome.WON),
    }


def test_a_squad_with_no_player_name_does_not_merge_into_a_phantom_defender():
    """Keying on a missing name would collapse every nameless squad into one."""
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER, defender=None),
            war_event("e2", 2 * SECOND, status="SQUAD_LOCKED", squad_id=OTHER_SQUAD, lock_name=ATTACKER, defender=None),
            war_event("e3", 60 * SECOND, status="SQUAD_DEFEATED", defender=None),
            war_event("e4", 61 * SECOND, status="SQUAD_DEFEATED", squad_id=OTHER_SQUAD, defender=None),
        ]
    )
    assert len(log.battles) == 2
    assert {b.squad_id for b in log.battles} == {SQUAD, OTHER_SQUAD}
    assert {b.defender for b in log.battles} == {None}


def test_a_release_without_an_observed_lock_opens_nothing():
    """Your own guild's defensive deployments carry a warSquad just like an assault."""
    log = BattleLog()
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_AVAILABLE")])
    assert log.battles == []
    assert (ZONE, SQUAD) in log.squads


# ── successfulDefends is a floor, never a delta ─────────────────────────


NON_MONOTONIC = (1, 0, 2, 2)  # the real sequence from the capture


def test_a_non_monotonic_defend_count_never_goes_negative():
    log = BattleLog()
    readings = []
    for index, defends in enumerate(NON_MONOTONIC):
        log.add([war_event(f"e{index}", (index + 1) * SECOND, status="SQUAD_AVAILABLE", defends=defends)])
        record = log.squads[(ZONE, SQUAD)]
        readings.append(record["successful_defends"])
        assert record["successful_defends"] >= 0

    # A floor: highest reading ever seen, never differenced between observations.
    assert readings == [1, 1, 2, 2]
    assert log.squads[(ZONE, SQUAD)]["held"] is True


def test_a_squad_that_never_defended_is_not_held():
    log = BattleLog()
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_AVAILABLE", defends=0)])
    record = log.squads[(ZONE, SQUAD)]
    assert record["successful_defends"] == 0
    assert record["held"] is False


def test_held_lives_on_the_squad_and_not_on_a_battle():
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_AVAILABLE", defends=3),
        ]
    )
    assert not hasattr(log.battles[0], "held")
    assert log.squads[(ZONE, SQUAD)]["successful_defends"] == 3


def test_squad_records_carry_the_reconciled_snapshot():
    log = BattleLog()
    log.add([war_event("e1", 5 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER, defends=2, power=310_000)])
    record = log.squads[(ZONE, SQUAD)]
    assert record["zone_id"] == ZONE
    assert record["squad_id"] == SQUAD
    assert record["defender"] == DEFENDER
    assert record["power"] == 310_000
    assert record["status"] == "SQUAD_LOCKED"
    assert record["side"] == "away"
    assert record["last_seen"] == 5 * SECOND


def test_the_squad_table_is_a_copy():
    log = BattleLog()
    log.add([war_event("e1", 1 * SECOND)])
    log.squads[(ZONE, SQUAD)]["defender"] = "tampered"
    assert log.squads[(ZONE, SQUAD)]["defender"] == DEFENDER


# ── Idempotence, ordering and non-Battle traffic ────────────────────────


def test_duplicate_events_are_idempotent():
    page = [
        war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
        war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
    ]
    log = BattleLog()
    log.add(page)
    once = log.battles

    log.add(page)
    log.add(page)

    assert log.battles == once
    assert len(log.battles) == 1


def test_a_page_that_carries_a_defeat_ahead_of_its_lock_still_correlates():
    """The Read Position bound tracks server batching, not per-event timestamps."""
    log = BattleLog()
    log.add(
        [
            war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
        ]
    )
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert (battle.opened_at, battle.closed_at) == (1 * SECOND, 60 * SECOND)


def test_score_events_are_ignored_rather_than_rejected():
    log = BattleLog()
    log.add(
        [
            score_event("s1", 1 * SECOND),
            war_event("e1", 2 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    assert len(log.battles) == 1
    assert list(log.squads) == [(ZONE, SQUAD)]


def test_opaque_payloads_are_counted_and_never_fabricate_an_outcome():
    log = BattleLog()
    log.add([opaque_event("o1", 1 * SECOND), opaque_event("o2", 2 * SECOND)])
    assert log.opaque == 2
    assert log.battles == []
    assert log.squads == {}


def test_an_empty_envelope_is_not_counted_as_an_opaque_payload():
    """``opaque`` counts content the server could not hand over, not content it never had.

    An opaque record with ``raw`` and ``error`` both unset means the server
    supplied nothing to decode, so nothing was lost. Counting it would inflate
    the number the docs offer as the signal that the correlation is thin rather
    than the war quiet.
    """
    log = BattleLog()
    log.add([empty_envelope_event("m1", 1 * SECOND), empty_envelope_event("m2", 2 * SECOND)])
    assert log.opaque == 0
    assert log.battles == []
    assert log.squads == {}


def test_an_undecodable_payload_still_counts_beside_an_empty_envelope():
    """The two are distinguished rather than merged: only the undecodable one is a loss."""
    log = BattleLog()
    log.add(
        [
            opaque_event("o1", 1 * SECOND),
            empty_envelope_event("m1", 2 * SECOND),
            # ``raw`` without ``error``: the server had the bytes and could not
            # decode them, which is a loss just as much as a reported failure.
            {
                "id": "o2",
                "authorName": "Rey",
                "timestamp": 3 * SECOND,
                "data": [{"type": WAR_ACTIVITY, "payload": None, "raw": "CgtTUVVBRF9MT0NLRUQ="}],
            },
        ]
    )
    assert log.opaque == 2


def test_an_empty_page_is_a_no_op():
    log = BattleLog()
    log.add([])
    assert log.battles == []


# ── BattleLogState round trip ───────────────────────────────────────────


def resumable_log() -> BattleLog:
    """A log with one closed Battle, one open lock and a couple of squads."""
    log = BattleLog(stale_after=10)
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED", defends=2),
            war_event("e3", 70 * SECOND, status="SQUAD_LOCKED", squad_id=OTHER_SQUAD, lock_name="Rey", author="Rey"),
            opaque_event("o1", 71 * SECOND),
        ]
    )
    return log


def test_state_survives_a_json_round_trip():
    original = resumable_log()

    encoded = json.dumps(dataclasses.asdict(original.state))
    restored = BattleLog(stale_after=10, state=BattleLogState.from_dict(json.loads(encoded)))

    assert restored.battles == original.battles
    assert restored.squads == original.squads
    assert restored.opaque == original.opaque
    assert dataclasses.asdict(restored.state) == dataclasses.asdict(original.state)


def test_a_restored_log_resolves_the_lock_it_was_holding():
    """A restart that dropped open locks would manufacture Orphaned Wins."""
    encoded = json.dumps(dataclasses.asdict(resumable_log().state))
    restored = BattleLog(stale_after=10, state=BattleLogState.from_dict(json.loads(encoded)))

    restored.add([war_event("e4", 120 * SECOND, status="SQUAD_DEFEATED", squad_id=OTHER_SQUAD, author="Rey")])

    outcomes = [b.outcome for b in restored.battles]
    assert outcomes.count(BattleOutcome.WON) == 2
    assert BattleOutcome.ORPHANED_WIN not in outcomes


def test_a_restored_log_stays_idempotent_across_the_restart():
    log = resumable_log()
    encoded = json.dumps(dataclasses.asdict(log.state))
    restored = BattleLog(stale_after=10, state=BattleLogState.from_dict(json.loads(encoded)))

    restored.add([war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED", defends=2)])

    assert restored.battles == log.battles


def test_state_from_dict_ignores_unknown_keys_and_fills_missing_ones():
    state = BattleLogState.from_dict({"version": 1, "latest_timestamp": 42, "somethingNew": ["x"]})
    assert state.latest_timestamp == 42
    assert state.battles == []
    assert state.seen == []
    assert not hasattr(state, "somethingNew")


def test_state_is_a_copy_of_the_log():
    log = resumable_log()
    state = log.state
    state.battles.clear()
    state.seen.clear()
    assert log.state.battles
    assert log.state.seen


def test_a_serialised_battle_carries_the_outcome_as_a_plain_string():
    state = resumable_log().state
    assert {entry["outcome"] for entry in state.battles} == {"won"}
    assert isinstance(json.dumps(dataclasses.asdict(state)), str)


def test_battle_outcome_values_are_the_four_documented_strings():
    assert {outcome.value for outcome in BattleOutcome} == {"won", "repulse", "orphaned_win", "obscured"}


def test_a_battle_is_frozen_derived_data_with_no_raw_payload():
    battle: Any = Battle(zone_id=ZONE, squad_id=SQUAD, outcome=BattleOutcome.WON)
    with pytest.raises(dataclasses.FrozenInstanceError):
        battle.zone_id = "elsewhere"
    # Retention is bounded by design: derived fields only, never a payload.
    assert {f.name for f in dataclasses.fields(Battle)} == {
        "zone_id",
        "squad_id",
        "defender",
        "attacker",
        "opened_at",
        "closed_at",
        "outcome",
    }


# ── get_defending_squads ────────────────────────────────────────────────


# ── Reordering across a page boundary repairs, never duplicates ─────────


def reordered_event(
    event_id: str,
    timestamp: int,
    status: str,
    squad_id: str = "sq1",
    key: str = "EMPTY",
) -> dict[str, Any]:
    """The reported reproduction's envelope, shaped exactly as it was filed."""
    return {
        "id": event_id,
        "authorName": "atk",
        "authorId": "a1",
        "timestamp": str(timestamp),
        "data": [
            {
                "type": WAR_ACTIVITY,
                "payload": {
                    "zoneData": {
                        "zoneId": "z1",
                        "activityLogMessage": {"key": key},
                        "notificationInstanceType": AWAY_NAME,
                    },
                    "warSquad": {
                        "squadId": squad_id,
                        "playerName": "def",
                        "squadStatus": status,
                        "successfulDefends": 1,
                        "lockName": "",
                    },
                },
            }
        ],
    }


def test_the_reported_cross_page_reordering_yields_one_won_battle():
    """The verified reproduction: the defeat page, then the lock page behind it."""
    log = BattleLog()
    log.add([reordered_event("e2", 2000, "SQUAD_DEFEATED", key="TERRITORY_CHANNEL_ACTIVITY_CONFLICT_SQUAD_WIN")])
    log.add([reordered_event("e1", 1000, "SQUAD_LOCKED")])
    log.add([reordered_event("e9", 2_000_000, "SQUAD_LOCKED", "sq2")])  # advance the clock

    assert [(b.outcome.value, b.squad_id) for b in log.battles] == [("won", "sq1")]


def test_a_lock_arriving_a_page_late_repairs_its_orphaned_win():
    """The Read Position bound tracks server batching, so a page can arrive behind."""
    log = BattleLog(stale_after=10)
    log.add([war_event("e2", 2 * SECOND, status="SQUAD_DEFEATED")])
    assert [b.outcome for b in log.battles] == [BattleOutcome.ORPHANED_WIN]

    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])

    # Bottom-left of the quadrant to top-left: both ends turned out observable.
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert (battle.opened_at, battle.closed_at) == (1 * SECOND, 2 * SECOND)
    assert battle.attacker == ATTACKER
    assert battle.defender == DEFENDER


def test_a_repaired_orphan_leaves_no_second_episode_to_age_out():
    """Opening a fresh episode instead would count one engagement twice."""
    log = BattleLog(stale_after=10)
    log.add([war_event("e2", 2 * SECOND, status="SQUAD_DEFEATED")])
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    log.add([war_event("e9", 2_000 * SECOND, status="SQUAD_LOCKED", squad_id=OTHER_SQUAD, lock_name="Rey")])

    assert [(b.outcome, b.squad_id) for b in log.battles] == [(BattleOutcome.WON, SQUAD)]
    assert log.state.open_locks[0]["squad_id"] == OTHER_SQUAD


def test_a_late_lock_does_not_repair_a_win_that_closed_before_it():
    """That Orphaned Win belongs to an earlier engagement, not to this lock."""
    log = BattleLog(stale_after=10)
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_DEFEATED")])
    log.add([war_event("e2", 5 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])

    outcomes = [b.outcome for b in log.battles]
    assert outcomes == [BattleOutcome.ORPHANED_WIN]
    assert log.state.open_locks[0]["opened_at"] == 5 * SECOND


def test_an_older_snapshot_does_not_roll_the_squad_status_back():
    """A stale status would make the next defeat read as the first one seen."""
    log = BattleLog()
    log.add([war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED")])
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    assert log.squads[(ZONE, SQUAD)]["status"] == "SQUAD_DEFEATED"


# ── Every status comparison goes through the normaliser ─────────────────


DEFEATED_RENDERINGS = ("SQUAD_DEFEATED", "TERRITORYWARSQUADSTATUS_SQUADDEFEATED", 3)


@pytest.mark.parametrize("rendering", DEFEATED_RENDERINGS)
def test_a_restored_defeated_status_blocks_a_duplicate_orphan_in_every_rendering(rendering: Any):
    """`_restore` merges persisted records verbatim, so any rendering can come back."""
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    state = dataclasses.asdict(log.state)
    for record in state["squads"]:
        record["status"] = rendering
    restored = BattleLog(state=BattleLogState.from_dict(json.loads(json.dumps(state))))

    # A re-sent defeat snapshot for a squad already known defeated.
    restored.add([war_event("e3", 61 * SECOND, status="SQUAD_DEFEATED")])

    assert [b.outcome for b in restored.battles] == [BattleOutcome.WON]


@pytest.mark.parametrize("rendering", ("SQUAD_LOCKED", "TERRITORYWARSQUADSTATUS_SQUADLOCKED", 2))
def test_a_lock_is_recognised_in_every_rendering(rendering: Any):
    log = BattleLog()
    log.add(
        [
            war_event("e1", 1 * SECOND, status=rendering, lock_name=ATTACKER),
            war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
        ]
    )
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert battle.opened_at == 1 * SECOND


# ── side comes from a TerritoryZoneInstance table, not a suffix ─────────


@pytest.mark.parametrize(
    ("rendering", "expected"),
    [
        (AWAY_NAME, "away"),
        (AWAY_TRANSLATED, "away"),
        (AWAY_INT, "away"),
        (HOME_NAME, "home"),
        ("TERRITORYZONEINSTANCE_ZONEINSTANCEHOME", "home"),
        (2, "home"),
        # A zone instance that names no side, in all three renderings.
        ("ZONE_INSTANCE_BATTLE", None),
        (1, None),
        ("TerritoryZoneInstance_DEFAULT", None),
        (0, None),
        # Suffix matching would answer "away"/"home" to all of these.
        ("SOME_OTHER_ENUM_AWAY", None),
        ("PLAYERSTATUS_HOME", None),
        ("AWAY", None),
        # bool is an int subclass; True is not ZONE_INSTANCE_BATTLE.
        (True, None),
        (99, None),
        (None, None),
    ],
)
def test_side_is_read_from_a_zone_instance_table_and_never_a_suffix(rendering: Any, expected: str | None):
    log = BattleLog()
    log.add([war_event("e1", 1 * SECOND, side=rendering)])
    assert log.squads[(ZONE, SQUAD)]["side"] == expected


# ── Correlation is gated on the payload's type discriminator ────────────


def test_a_non_war_payload_shaped_like_an_engagement_is_filtered_by_its_type():
    """Shape is not the discriminator: a Territory Battle family carries zoneData too."""
    event = war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)
    event["data"][0]["type"] = "TERRITORY_CONFLICT_ACTIVITY"

    log = BattleLog()
    log.add([event])

    assert log.battles == []
    assert log.squads == {}


def test_an_opaque_payload_of_another_type_is_not_counted_as_war_activity():
    """A thin correlation is a claim about Territory War, not about the whole feed."""
    event = opaque_event("o1", 1 * SECOND)
    event["data"][0]["type"] = "TERRITORY_STRIKE_ACTIVITY"

    log = BattleLog()
    log.add([event])

    assert log.opaque == 0


# ── Retention is bounded, and enforced rather than asserted ─────────────


def test_seen_ids_are_pruned_once_they_can_no_longer_recur():
    log = BattleLog(stale_after=10)
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    assert log.state.seen == ["e1"]

    # Two ageing windows on, the id is retired: the per-poll checkpoint must not
    # grow with the length of the war.
    log.add([war_event("e2", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD)])
    assert log.state.seen == ["e2"]


def test_an_event_older_than_the_retention_horizon_is_ignored():
    """A replay whose id has been retired must not open a second episode.

    Pruning the seen-id table is what keeps the checkpoint bounded, but it means
    the log can no longer recognise anything from before the horizon. Applying
    such an event would count one engagement twice — here, a second Obscured
    Battle for a lock already reported. Nothing that old can be a live update:
    the server's update batching recurs in seconds, three orders of magnitude
    inside the horizon.
    """
    log = BattleLog(stale_after=10)
    lock = war_event("e1", 100 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)
    log.add([lock])

    # Advance the clock two ageing windows on, which retires the lock's id.
    log.add([war_event("e2", 200 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD)])
    assert log.state.seen == ["e2"]
    assert [b.outcome for b in log.battles] == [BattleOutcome.OBSCURED]

    # The same envelope re-delivered. Its id is forgotten, so only its timestamp
    # can reject it.
    log.add([lock])
    assert [b.outcome for b in log.battles] == [BattleOutcome.OBSCURED]


def test_an_event_inside_the_retention_horizon_is_still_applied():
    """The staleness guard must not swallow ordinary out-of-order arrivals.

    A page can carry a defeat ahead of the lock it resolves, so a slightly older
    event is normal traffic rather than a replay.
    """
    log = BattleLog(stale_after=10)
    log.add([war_event("e1", 100 * SECOND, status="SQUAD_DEFEATED")])
    assert [b.outcome for b in log.battles] == [BattleOutcome.ORPHANED_WIN]

    # Five seconds older than the log's clock — well inside the horizon, so it
    # repairs the Orphaned Win rather than being discarded.
    log.add([war_event("e2", 95 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.WON
    assert battle.opened_at == 95 * SECOND


def test_pruning_does_not_reintroduce_duplicates_inside_the_retention_window():
    """Dedupe is mandatory, so nothing is retired while it can still come back."""
    page = [
        war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
        war_event("e2", 60 * SECOND, status="SQUAD_DEFEATED"),
    ]
    log = BattleLog()
    log.add(page)
    log.add(page)

    assert len(log.battles) == 1
    assert log.state.seen == ["e1", "e2"]


def test_an_aged_lock_is_evicted_from_the_open_table_rather_than_held_forever():
    log = BattleLog(stale_after=10)
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    assert len(log.state.open_locks) == 1

    log.add([war_event("e2", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD)])

    assert log.state.open_locks == []
    # Relocated, not lost: it still reports as Obscured.
    assert [b.outcome for b in log.battles] == [BattleOutcome.OBSCURED]


def test_a_pruned_open_lock_is_still_resolved_by_a_close_arriving_later():
    """Eviction costs memory, never accuracy."""
    log = BattleLog(stale_after=10)
    log.add(
        [
            war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER),
            war_event("e2", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD),
        ]
    )
    assert log.state.open_locks == []

    log.add([war_event("e3", 110 * SECOND, status="SQUAD_AVAILABLE", defends=1)])

    (battle,) = log.battles
    assert battle.outcome is BattleOutcome.REPULSE
    assert (battle.opened_at, battle.closed_at) == (1 * SECOND, 110 * SECOND)


def test_the_checkpoint_stays_bounded_over_a_long_war():
    log = BattleLog(stale_after=10)
    for index in range(200):
        log.add(
            [
                war_event(
                    f"e{index}",
                    (index + 1) * 60 * SECOND,
                    status="SQUAD_AVAILABLE",
                    squad_id=f"squad-{index:04d}",
                )
            ]
        )

    state = log.state
    assert len(state.seen) == 1  # only the newest poll's ids can still recur
    assert state.open_locks == []


def test_get_defending_squads_matches_the_correlator_table():
    events = [
        war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER, defends=2),
        war_event("e2", 2 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD, defender="Ezra", defends=0),
        score_event("s1", 3 * SECOND),
    ]
    squads = get_defending_squads(events)

    log = BattleLog()
    log.add(events)
    assert squads == log.squads

    assert sorted(record["defender"] for record in squads.values() if record["held"]) == [DEFENDER]


# ── Malformed and partial payloads are skipped, never guessed at ────────


def test_a_payload_whose_zone_or_squad_is_not_an_object_is_skipped():
    """The server declares objects here; a scalar is unusable, not a Battle.

    Correlation reads ``zoneId`` and ``squadId`` out of these, so a string or a
    list where an object belongs has nothing to key on. Skipping is the same
    answer given to a score event: not every payload describes a Battle.
    """
    log = BattleLog()
    for broken in ("a string", ["a", "list"], 7):
        event = war_event("e1", 1 * SECOND, status="SQUAD_LOCKED")
        event["data"][0]["payload"]["zoneData"] = broken
        log.add([event])

        event = war_event("e2", 2 * SECOND, status="SQUAD_LOCKED")
        event["data"][0]["payload"]["warSquad"] = broken
        log.add([event])

    assert log.battles == []
    assert log.squads == {}


def test_a_payload_missing_its_zone_or_squad_id_is_skipped():
    """A Battle is identified by zone and squad, so neither half is optional."""
    log = BattleLog()

    no_zone = war_event("e1", 1 * SECOND, status="SQUAD_LOCKED")
    no_zone["data"][0]["payload"]["zoneData"].pop("zoneId")
    log.add([no_zone])

    no_squad = war_event("e2", 2 * SECOND, status="SQUAD_LOCKED")
    no_squad["data"][0]["payload"]["warSquad"].pop("squadId")
    log.add([no_squad])

    assert log.battles == []
    assert log.squads == {}


def test_an_attacker_seen_later_in_an_episode_is_backfilled():
    """A lock whose first snapshot named nobody is still attributable.

    ``lockName`` is empty on some snapshots, and the envelope author is the
    Attacker. Taking the first non-empty reading rather than the first reading
    means an episode that opened anonymously is not stuck that way.
    """
    log = BattleLog()
    opening = war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", author="", lock_name="")
    opening["authorName"] = ""
    log.add([opening])
    assert log.state.open_locks[0]["attacker"] in (None, "")

    # A later snapshot of the same episode names the Attacker.
    log.add([war_event("e2", 2 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    log.add([war_event("e3", 3 * SECOND, status="SQUAD_DEFEATED")])

    (battle,) = log.battles
    assert battle.attacker == ATTACKER
    assert battle.opened_at == 1 * SECOND


def test_a_late_close_resolves_the_newest_obscured_episode():
    """With two Obscured episodes for one squad, the close ends the later one.

    The earlier episode was already superseded by the second lock; attributing
    the close to it would report a Battle that ended before its successor began.
    """
    log = BattleLog(stale_after=10)
    # Two lock episodes, separated by a takeover, both aged into OBSCURED.
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER)])
    log.add([war_event("e2", 5 * SECOND, status="SQUAD_LOCKED", lock_name="Rey")])
    log.add([war_event("e3", 100 * SECOND, status="SQUAD_AVAILABLE", squad_id=OTHER_SQUAD)])
    assert [b.outcome for b in log.battles] == [BattleOutcome.OBSCURED, BattleOutcome.OBSCURED]

    log.add([war_event("e4", 110 * SECOND, status="SQUAD_DEFEATED")])
    resolved = [b for b in log.battles if b.outcome is BattleOutcome.WON]
    assert len(resolved) == 1
    assert resolved[0].opened_at == 5 * SECOND


def test_a_boolean_where_a_number_belongs_reads_as_the_default():
    """``bool`` is an ``int`` subclass, so ``True`` would otherwise count as 1.

    A defend count of ``True`` reading as one defend would mark a squad Held on
    the strength of a type error. The guard is cheap and the alternative is a
    wrong claim about a player.
    """
    log = BattleLog()
    log.add([war_event("e1", 1 * SECOND, status="SQUAD_LOCKED", lock_name=ATTACKER, defends=True)])

    (record,) = log.squads.values()
    assert record["successful_defends"] == 0
    assert record["held"] is False


def test_a_restored_obscured_battle_that_already_closed_is_not_resolved_again():
    """Repair skips a candidate that is not actually open.

    ``BattleLogState`` is plain data a caller persists and hands back, so it can
    arrive carrying an Obscured entry that already has a ``closed_at`` — from an
    older release, or from a file edited by hand. Resolving it a second time
    would overwrite a recorded outcome with a later, unrelated close.
    """
    state = BattleLogState()
    state.battles = [
        {
            "zone_id": ZONE,
            "squad_id": SQUAD,
            "defender": DEFENDER,
            "attacker": ATTACKER,
            "opened_at": 1 * SECOND,
            "closed_at": 50 * SECOND,
            "outcome": BattleOutcome.OBSCURED.value,
        }
    ]
    log = BattleLog(state=state)

    log.add([war_event("e1", 200 * SECOND, status="SQUAD_DEFEATED")])

    # The restored entry keeps its own close; the new defeat is reported
    # separately as an Orphaned Win rather than folded into it.
    outcomes = sorted(b.outcome.value for b in log.battles)
    assert outcomes == ["obscured", "orphaned_win"]
    obscured = next(b for b in log.battles if b.outcome is BattleOutcome.OBSCURED)
    assert obscured.closed_at == 50 * SECOND
