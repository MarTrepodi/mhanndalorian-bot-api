"""Territory War Battle correlation over a feed that is lossy by construction.

A Battle is one Attacker's assault on one defending squad in one zone, bounded
by that squad's lock. This module folds a stream of Activity Events into those
Battles, and it is built around three properties of the feed that make the
obvious implementation wrong:

1. **Events are snapshots, not transitions.** Every event carrying a
   ``warSquad`` carries that squad's complete current state — ``squadId``,
   ``squadStatus``, ``successfulDefends``, ``lockName`` and ``power`` — in 66 of
   66 sampled events. So the correlator reconciles snapshots: a gap means
   intermediate states were missed, not that the accumulated state is wrong, and
   any single event fully resynchronises a squad. Pairing transitions is what
   makes a gap fatal rather than merely lossy.
2. **Loss is invisible at the envelope.** Event ids are opaque rather than
   ordinal, so there is no sequence signal and a dropped event leaves no gap to
   notice. (The envelope does name a ``channelId``, so an Opaque Payload is
   attributable to its zone — but a Battle turns on squad state, which an
   unreadable payload does not carry, so that does not help here.) Loss is only
   ever inferred from state discontinuity, which is why an open lock with no
   observed close ages into :attr:`BattleOutcome.OBSCURED` on a timer instead of
   waiting forever.
3. **A Battle's outcome records which of its ends were observed**, not what
   happened. That yields four values, exhaustive by construction:

   ==================== ================= ====================
   ..                   closing observed  closing not observed
   ==================== ================= ====================
   opening observed     ``WON``/``REPULSE`` ``OBSCURED``
   opening not observed ``ORPHANED_WIN``  *(invisible)*
   ==================== ================= ====================

See ``docs/adr/0008-battle-outcomes-are-a-loss-model.md``, which is binding for
everything here.

:class:`BattleLog` performs no I/O and therefore has no ``async_`` twin. Feed it
the raw event dictionaries from :attr:`~swgoh_comlink.helpers.ChannelRead.events`
however you obtained them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, fields, replace
from enum import Enum
from typing import Any

from ._events import ActivityEvent, iter_activity_events

__all__ = [
    "Battle",
    "BattleLog",
    "BattleLogState",
    "BattleOutcome",
    "get_defending_squads",
]

# Mirror of the game ``TerritoryWarSquadStatus`` enum, confirmed against
# ``GET /enums`` on 2026-08-02. Kept private: nothing in the public surface
# hands an integer status back, so a caller never needs the mapping to read a
# result. The zero value carries the group name in the game data itself.
_SQUAD_STATUS: dict[str, int] = {
    "TerritoryWarSquadStatus_DEFAULT": 0,
    "SQUAD_AVAILABLE": 1,
    "SQUAD_LOCKED": 2,
    "SQUAD_DEFEATED": 3,
}

_AVAILABLE = _SQUAD_STATUS["SQUAD_AVAILABLE"]
_LOCKED = _SQUAD_STATUS["SQUAD_LOCKED"]
_DEFEATED = _SQUAD_STATUS["SQUAD_DEFEATED"]

# Prefix an Enum Translation response puts in front of a value name: the group
# name, an underscore, then the value with its own underscores removed —
# ``SQUAD_LOCKED`` renders as ``TERRITORYWARSQUADSTATUS_SQUADLOCKED``.
_SQUAD_STATUS_GROUP = "TERRITORYWARSQUADSTATUS"

# Mirror of the game ``TerritoryZoneInstance`` enum. ``notificationInstanceType``
# is declared as a ``TerritoryZoneInstance`` by the Comlink API description
# (``docs/ref/openapi.json``, ``TerritoryZoneData.notificationInstanceType``) —
# the same group ``updateTerritoryOrders`` takes as ``zoneInstance`` and the same
# one ``TERRITORY_ZONE_INSTANCE`` in ``_territory.py`` mirrors from
# ``GET /enums`` (``BATTLE`` 1, ``HOME`` 2, ``AWAY`` 3). So the integer rendering
# of this field is read from a confirmed table rather than guessed at.
_ZONE_INSTANCE: dict[str, int] = {
    "TerritoryZoneInstance_DEFAULT": 0,
    "ZONE_INSTANCE_BATTLE": 1,
    "ZONE_INSTANCE_HOME": 2,
    "ZONE_INSTANCE_AWAY": 3,
}

# ``ZONE_INSTANCE_AWAY`` renders as ``TERRITORYZONEINSTANCE_ZONEINSTANCEAWAY``:
# the value name already repeats the group, and the rule does not deduplicate.
_ZONE_INSTANCE_GROUP = "TERRITORYZONEINSTANCE"

# Only two of the four zone instances name a side of a war map. ``BATTLE`` and
# the group's zero value name no side, so they yield ``None`` rather than being
# forced into one — a mislabelled side mislabels every squad in a zone.
_SIDE_OF_ZONE_INSTANCE: dict[int, str] = {
    _ZONE_INSTANCE["ZONE_INSTANCE_HOME"]: "home",
    _ZONE_INSTANCE["ZONE_INSTANCE_AWAY"]: "away",
}

# The payload ``type`` discriminator a Territory War engagement carries. It is
# the only ``TERRITORY_WAR_*`` activity type in the API description; the
# Territory Battle families (``TERRITORY_CONFLICT_ACTIVITY`` and friends) are a
# different game mode and are not correlated here.
_ACTIVITY_TYPE = "TERRITORY_WAR_CONFLICT_ACTIVITY"

# Milliseconds per second. Envelope timestamps are milliseconds; ``stale_after``
# is seconds, because a caller reasons about a lock in seconds.
_MILLISECONDS = 1000

# How many ageing windows an observation is kept for before it is retired. Two:
# one window for an open lock to become reportable as Obscured, and a second
# before the log stops holding it. See :meth:`BattleLog._prune`.
_RETENTION_WINDOWS = 2


def _fold(name: str) -> str:
    """Fold an enum value name to its comparison key: upper case, no underscores."""
    return name.strip().replace("_", "").upper()


def _rendering_keys(names: Mapping[str, int], group: str) -> dict[str, int]:
    """Map every rendering of every value name in *names* to its integer value.

    Built from the enum mirror so that adding an entry there is the only edit a
    new value needs. Folding erases the underscores, so the canonical name and
    the translated one differ only by the *group* prefix.
    """
    keys: dict[str, int] = {}
    for name, value in names.items():
        keys[_fold(name)] = value
        keys[group + _fold(name)] = value
    return keys


_SQUAD_STATUS_KEYS: dict[str, int] = _rendering_keys(_SQUAD_STATUS, _SQUAD_STATUS_GROUP)
_SQUAD_STATUS_NAMES: dict[int, str] = {value: name for name, value in _SQUAD_STATUS.items()}

_ZONE_INSTANCE_KEYS: dict[str, int] = _rendering_keys(_ZONE_INSTANCE, _ZONE_INSTANCE_GROUP)
_ZONE_INSTANCE_NAMES: dict[int, str] = {value: name for name, value in _ZONE_INSTANCE.items()}


def _normalize(value: Any, keys: Mapping[str, int], names: Mapping[int, str]) -> int | None:
    """Return the integer enum value for any of a value's three renderings.

    ``GET /enums`` names a value ``SQUAD_LOCKED``; an Enum Translation response
    renders it ``TERRITORYWARSQUADSTATUS_SQUADLOCKED``; with translation off the
    field is the bare integer ``2``. All three normalise to ``2``, which is what
    lets this module compare integers and never string literals.

    Args:
        value: The field in any rendering.
        keys: The folded-rendering table from :func:`_rendering_keys`.
        names: The integer-to-canonical-name table for the same enum.

    Returns:
        The integer value, or ``None`` when the rendering is not a known one.
    """
    if isinstance(value, bool):
        # ``bool`` is an ``int`` subclass; ``True`` is not ``SQUAD_LOCKED``.
        return None
    if isinstance(value, int):
        return value if value in names else None
    if isinstance(value, str):
        return keys.get(_fold(value))
    return None


def _normalize_squad_status(value: Any) -> int | None:
    """Return the integer ``TerritoryWarSquadStatus`` for any of its three renderings.

    Every status comparison in this module goes through here, including the ones
    reading a status back out of a restored :class:`BattleLogState`: a persisted
    record is merged verbatim, so its ``status`` may carry any of the three
    renderings and a literal comparison would silently mis-answer.

    Args:
        value: A ``squadStatus`` in any rendering.

    Returns:
        The integer value, or ``None`` when the rendering is not a known status.
        Unknown input is not an error: a value the server adds after this release
        must leave the correlator reconciling what it does understand.
    """
    return _normalize(value, _SQUAD_STATUS_KEYS, _SQUAD_STATUS_NAMES)


def _normalize_zone_instance(value: Any) -> int | None:
    """Return the integer ``TerritoryZoneInstance`` for any of its three renderings.

    Args:
        value: A ``notificationInstanceType`` in any rendering — ``3``,
            ``"ZONE_INSTANCE_AWAY"`` or ``"TERRITORYZONEINSTANCE_ZONEINSTANCEAWAY"``.

    Returns:
        The integer value, or ``None`` when the rendering is not a known zone
        instance.
    """
    return _normalize(value, _ZONE_INSTANCE_KEYS, _ZONE_INSTANCE_NAMES)


def _as_int(value: Any, default: int = 0) -> int:
    """Return *value* as an int, or *default* when it is not one. Timestamps arrive as strings."""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any) -> str:
    """Return *value* when it is a non-empty string, else ``""``."""
    return value if isinstance(value, str) else ""


def _side_of(zone_data: Mapping[str, Any]) -> str | None:
    """Return ``"home"``/``"away"`` for a zone payload, or ``None`` when unreadable.

    Read from ``notificationInstanceType``, never ``instanceType``: score events
    are filed under ``instanceType: HOME`` while describing away-map activity, so
    ``instanceType`` splits a single Battle across both sides.

    The field is a ``TerritoryZoneInstance``, so it goes through
    :func:`_normalize_zone_instance` rather than being suffix-matched. Suffix
    matching answers ``"home"`` for any rendering merely ending in those letters
    and cannot read the integer rendering at all, and side is not a field worth
    guessing at: it labels every squad in a zone at once.
    """
    instance = _normalize_zone_instance(zone_data.get("notificationInstanceType"))
    return None if instance is None else _SIDE_OF_ZONE_INSTANCE.get(instance)


class BattleOutcome(str, Enum):
    """Which ends of a Battle this reader observed.

    The values are exhaustive by construction rather than by enumeration: a
    Battle has two ends, each either observed or not, and the fourth combination
    — neither end observed — is invisible and so has no value here.

    Attributes:
        WON: Both ends observed, and the squad was defeated.
        REPULSE: Both ends observed, and the squad returned to available rather
            than falling. The episode behind a Held squad's count, and the only
            form of it attributable to a named Attacker and a time.
        ORPHANED_WIN: The defeat was observed but the engagement was not, having
            fallen outside the reader's earliest Read Position. A real win — it
            simply has no measurable duration.
        OBSCURED: The engagement was observed and no close ever was. Distinct
            from a win or a Repulse, which were both seen resolving, and from an
            Orphaned Win, which was seen only closing.
    """

    WON = "won"
    REPULSE = "repulse"
    ORPHANED_WIN = "orphaned_win"
    OBSCURED = "obscured"


@dataclass(frozen=True)
class Battle:
    """One correlated assault on one defending squad in one zone.

    A Battle is keyed by zone, squad and lock episode — never by the Attacker,
    who assaults the same squad repeatedly, and never by player, because a
    ``warSquad`` sometimes arrives with no player at all and keying on a missing
    name merges every such squad into one phantom Defender.

    Only derived fields are held; no raw payload is retained, which is what keeps
    a long war's log bounded while letting the reader pass everything through
    untouched.

    Held is deliberately absent. It is a property of the squad — its own running
    defend count, which includes defends from before this reader subscribed — and
    so it lives on :attr:`BattleLog.squads`, not on an episode.

    Attributes:
        zone_id: The zone the squad is defending, from ``zoneData.zoneId``.
        squad_id: The defending squad's ``squadId``.
        defender: The player whose squad was attacked — the owner of the
            ``warSquad``, not the event's author. ``None`` when no event carried
            a name.
        attacker: The player who launched the Battle — the squad's ``lockName``
            while the lock held, falling back to the Activity Event's author.
            ``None`` when neither was present.
        opened_at: Millisecond timestamp of the first observed lock, or ``None``
            for an :attr:`~BattleOutcome.ORPHANED_WIN`.
        closed_at: Millisecond timestamp of the observed close, or ``None`` for
            an :attr:`~BattleOutcome.OBSCURED` Battle.
        outcome: Which ends were observed; see :class:`BattleOutcome`.
    """

    zone_id: str = ""
    squad_id: str = ""
    defender: str | None = None
    attacker: str | None = None
    opened_at: int | None = None
    closed_at: int | None = None
    outcome: BattleOutcome = BattleOutcome.OBSCURED


@dataclass
class BattleLogState:
    """A :class:`BattleLog`'s whole memory, as plain JSON-serialisable data.

    Persisting this is not an optimisation. A restart that drops open locks
    converts every in-flight Battle into an Orphaned Win — manufacturing exactly
    the artifact the loss model exists to measure — so a long-running reader
    should checkpoint this beside its Read Position.

    Every field is plain: ``dict``, ``list``, ``str``, ``int``. Squad and lock
    records are lists rather than dictionaries keyed by ``(zone_id, squad_id)``
    because a tuple is not a JSON key; each record carries both ids instead.

    ``stale_after`` is deliberately absent. It is a reading preference rather
    than accumulated observation, so a stale file cannot reinstate a threshold
    the caller has since changed in code.

    Attributes:
        version: Schema version of this structure. ``1`` today.
        battles: Correlated Battles that reached a close, as plain dictionaries.
        squads: One record per defending squad seen; see
            :attr:`BattleLog.squads` for the keys.
        open_locks: Lock episodes observed opening and not yet observed closing,
            back to the log's retention horizon. Past it an episode is written
            into ``battles`` as :attr:`~BattleOutcome.OBSCURED` and dropped from
            here, so this list stays bounded by the squads currently under
            assault rather than by the length of the war.
        seen: Event ids already applied, which is what makes :meth:`BattleLog.add`
            idempotent across restarts as well as within a run. Pruned to the
            same retention horizon, so it is bounded by poll rate rather than by
            war length; see :meth:`BattleLog._prune`.
        latest_timestamp: The newest envelope timestamp observed, in
            milliseconds. This is the log's clock for ageing.
        opaque: Count of Opaque Payloads encountered. An undecodable payload
            carries no ``warSquad`` state to reconcile, so it can neither advance
            nor resolve a Battle — it is counted and skipped, never allowed to
            fabricate or suppress an outcome. (Its ``channelId`` still names a
            zone, but a Battle turns on squad state, not on location.) Only
            undecodable payloads are counted; see :attr:`BattleLog.opaque` for
            why an empty envelope is not one.
    """

    version: int = 1
    battles: list[dict[str, Any]] = field(default_factory=list)
    squads: list[dict[str, Any]] = field(default_factory=list)
    open_locks: list[dict[str, Any]] = field(default_factory=list)
    seen: list[str] = field(default_factory=list)
    latest_timestamp: int = 0
    opaque: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BattleLogState:
        """Rebuild a state object from a decoded JSON mapping.

        Missing keys take their defaults and unknown keys are ignored. That
        tolerance is the expansion mechanism: without it, every field a future
        release adds would be a breaking change to everyone's saved state.

        Args:
            data: A mapping produced by ``dataclasses.asdict()`` on a previous
                :attr:`BattleLog.state`, typically round-tripped through JSON.

        Returns:
            The reconstructed :class:`BattleLogState`.

        Example:
            >>> log = BattleLog(state=BattleLogState.from_dict(json.load(handle)))
        """
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})


def _battle_from_dict(data: Mapping[str, Any]) -> Battle:
    """Rebuild a :class:`Battle` from its serialised form, ignoring unknown keys."""
    known = {f.name for f in fields(Battle)}
    values = {key: value for key, value in data.items() if key in known}
    values["outcome"] = BattleOutcome(values.get("outcome", BattleOutcome.OBSCURED.value))
    return Battle(**values)


def _new_episode(key: tuple[str, str], attacker: str | None, timestamp: int) -> dict[str, Any]:
    """Return a fresh lock-episode record for ``(zone_id, squad_id)``."""
    return {
        "zone_id": key[0],
        "squad_id": key[1],
        "attacker": attacker,
        "opened_at": timestamp,
        "last_seen": timestamp,
    }


def _new_squad(zone_id: str, squad_id: str) -> dict[str, Any]:
    """Return an empty squad record for ``(zone_id, squad_id)``."""
    return {
        "zone_id": zone_id,
        "squad_id": squad_id,
        "defender": None,
        "power": None,
        "successful_defends": 0,
        "held": False,
        "status": None,
        "side": None,
        "last_seen": 0,
    }


class BattleLog:
    """Correlates Territory War Activity Events into :class:`Battle` records.

    Correlation runs on the defending squad's own ``squadStatus`` rather than on
    a localization key, because the status is what the game actually tracks and
    it needs no language bundle. In the sampled capture the ``SQUAD_DEFEATED``
    count matched the ``..._CONFLICT_SQUAD_WIN`` key count exactly — 28 of 28 —
    so the two agree, and the status additionally distinguishes an assault
    starting from a squad merely being released, which the key does not.

    Every state change is reconciled from a snapshot:

    - ``SQUAD_LOCKED`` opens a lock episode, or extends the open one. A lock
      whose ``lockName`` names a different Attacker closes the previous episode
      as :attr:`~BattleOutcome.OBSCURED` and opens a new one — its close was
      never observed.
    - ``SQUAD_DEFEATED`` closes an open episode as :attr:`~BattleOutcome.WON`,
      or records an :attr:`~BattleOutcome.ORPHANED_WIN` when the engagement was
      never seen.
    - ``SQUAD_AVAILABLE`` closes an open episode as
      :attr:`~BattleOutcome.REPULSE`. On its own it opens nothing: a squad being
      deployed or released without an observed lock is not an assault, which is
      why your own guild's defensive deployments never manufacture a Battle here
      despite carrying a ``warSquad`` exactly like an engagement does.

    Because only a lock opens an episode, and because ``successfulDefends`` is
    read as a floor and never differenced, an unreadable stream yields fewer
    observations rather than wrong ones.

    Reordering is a normal operating condition rather than an error, because the
    Read Position bound tracks the server's update batching rather than each
    event's own timestamp — so an event older than the position sent comes back
    in a later page. Within a call :meth:`add` sorts; across calls a late arrival
    **repairs** the episode it belongs to instead of starting a second one. A
    lock arriving after its own defeat turns that
    :attr:`~BattleOutcome.ORPHANED_WIN` into a :attr:`~BattleOutcome.WON`, and a
    close arriving after its lock aged out resolves that
    :attr:`~BattleOutcome.OBSCURED` episode. Either way one engagement stays one
    Battle.

    This class performs no I/O and therefore has no ``async_`` twin. The MBot
    ``API`` client, sync or async, feeds it the same raw dictionaries once they
    are normalized (see :func:`~mhanndalorian_bot.helpers.normalize_events`).

    Example:
        ```pycon
        >>> from mhanndalorian_bot import API
        >>> from mhanndalorian_bot.helpers import battle_log
        >>> api = API(api_key="...", allycode="...")
        >>> log = battle_log(api.fetch_twlogs())
        >>> [(b.attacker, b.outcome.value) for b in log.battles]
        [('Kylo', 'won'), ('Rey', 'repulse')]
        ```
    """

    def __init__(self, *, stale_after: int = 900, state: BattleLogState | None = None) -> None:
        """Create a correlator, optionally resuming from persisted state.

        Args:
            stale_after: Seconds an open lock may go without an observed close
                before it is reported as :attr:`~BattleOutcome.OBSCURED`. Age is
                measured against the newest envelope timestamp the log has seen
                rather than the wall clock, so replaying a capture gives the same
                answer today as it did during the war. Observed lock durations
                ran to a median of 76 s and a maximum of 311 s, so the default of
                900 is roughly ten times the measured tail.
            state: A previous :attr:`state` to resume from. Restoring it is what
                stops a restart from converting every in-flight Battle into an
                Orphaned Win.
        """
        self._stale_after = stale_after
        self._battles: list[Battle] = []
        self._squads: dict[tuple[str, str], dict[str, Any]] = {}
        self._open: dict[tuple[str, str], dict[str, Any]] = {}
        # Event id -> the envelope timestamp it was seen at, which is what makes
        # the set prunable. Only the ids are persisted; the timestamps exist so
        # an id can be retired once it can no longer recur.
        self._seen: dict[str, int] = {}
        self._latest: int = 0
        self._opaque: int = 0

        if state is not None:
            self._restore(state)

    def _restore(self, state: BattleLogState) -> None:
        """Repopulate the internal tables from a persisted :class:`BattleLogState`."""
        self._battles = [_battle_from_dict(entry) for entry in state.battles]
        self._squads = {
            (_as_str(entry.get("zone_id")), _as_str(entry.get("squad_id"))): {**_new_squad("", ""), **entry}
            for entry in state.squads
        }
        self._open = {
            (_as_str(entry.get("zone_id")), _as_str(entry.get("squad_id"))): dict(entry) for entry in state.open_locks
        }
        self._latest = _as_int(state.latest_timestamp)
        # Persisted ids carry no timestamp of their own, so they are dated to the
        # log's clock: a restored id survives a full retention window rather than
        # being retired on the next poll, and dedupe cannot regress across a
        # restart.
        self._seen = {event_id: self._latest for event_id in state.seen if isinstance(event_id, str)}
        self._opaque = _as_int(state.opaque)

    def add(self, events: Iterable[dict[str, Any]]) -> None:
        """Fold a page of raw Channel events into the log.

        Events are applied in timestamp order within the call, because the Read
        Position bound tracks the server's update batching rather than each
        event's own timestamp — a page can carry a defeat ahead of the lock it
        resolves. Ties keep the order the server sent them.

        Deduplication is by envelope id, so feeding the same page twice changes
        nothing. An event whose payload is opaque is counted and skipped: nothing
        inside an Opaque Payload can be attributed to a zone, so letting one
        through would fabricate or suppress an outcome.

        Args:
            events: Raw server event dictionaries, as carried by
                :attr:`~swgoh_comlink.helpers.ChannelRead.events`. Only payloads
                whose own ``type`` discriminator is
                ``TERRITORY_WAR_CONFLICT_ACTIVITY`` are correlated; a score
                update, a Territory Battle activity or anything else the feed
                carries is ignored rather than rejected, so a whole mixed page
                can be passed straight through. The filter is on the
                discriminator rather than on payload shape, so a future payload
                of a wanted type that happens to look unfamiliar still reaches
                the correlator and an unwanted one never does.

        Returns:
            None. Read the result from :attr:`battles` and :attr:`squads`.

        Example:
            >>> log.add(page.events)
            >>> log.add(page.events)  # idempotent: the second call is a no-op
        """
        # Read once, from the clock as it stood before this page: everything at or
        # below it has already been dropped from the seen-id table, so a replay of
        # it is indistinguishable from a new event. Recomputing per event would
        # move the horizon up as the sorted page advanced and never fire.
        horizon = self._retention_horizon()
        for envelope in sorted(events, key=lambda event: _as_int(event.get("timestamp"))):
            event_id = _as_str(envelope.get("id"))
            if event_id and event_id in self._seen:
                continue
            timestamp = _as_int(envelope.get("timestamp"))
            if timestamp and horizon > 0 and timestamp <= horizon:
                # Older than anything the log still remembers. It cannot be a live
                # update — the server's update batching recurs in seconds, three
                # orders of magnitude inside the horizon — so it is a replay whose
                # id was already retired, and applying it would open a second
                # episode for an engagement already recorded.
                continue
            self._latest = max(self._latest, timestamp)
            if event_id:
                # Deduplication is per envelope rather than per unpacked record:
                # one envelope can carry several payloads under a single id, and
                # marking the id seen mid-envelope would drop its remaining
                # payloads. An undated envelope is dated to the log's clock so
                # that pruning never retires it early.
                self._seen[event_id] = timestamp or self._latest
            for activity in iter_activity_events([envelope], types=_ACTIVITY_TYPE):
                self._apply(activity)
        self._prune()

    def _apply(self, activity: ActivityEvent) -> None:
        """Reconcile one unpacked Activity Event into the squad and episode tables."""
        if activity.opaque:
            # Two different things arrive opaque and only one of them is a loss.
            # ``raw`` or ``error`` set means the server had content and could not
            # hand it over — a real Opaque Payload, and the thing
            # :attr:`opaque` is offered as evidence of. Both ``None`` means the
            # server supplied nothing to decode: an empty envelope, where there
            # was nothing to lose. Counting the two together inflates the number
            # a caller reads as "the correlation is thin", so the empty envelope
            # is skipped uncounted — as unattributable as the other, but not a
            # symptom.
            if activity.raw is not None or activity.error is not None:
                self._opaque += 1
            return

        payload = activity.payload or {}
        zone_data = payload.get("zoneData") or {}
        squad = payload.get("warSquad") or {}
        if not isinstance(zone_data, dict) or not isinstance(squad, dict):
            return

        zone_id = _as_str(zone_data.get("zoneId"))
        squad_id = _as_str(squad.get("squadId"))
        if not zone_id or not squad_id:
            # A score event carries ``scoreDelta`` and no ``warSquad``; it moves
            # a zone total, not a Battle. Anything else unkeyable is skipped for
            # the same reason: a Battle is identified by zone and squad.
            return

        key = (zone_id, squad_id)
        record = self._squads.setdefault(key, _new_squad(zone_id, squad_id))
        # Through the normaliser, not against a name: a squad record restored
        # from a persisted state is merged verbatim, so its ``status`` may carry
        # any of the three renderings. Comparing it to a literal would read a
        # known-defeated squad as fresh and fabricate a duplicate Orphaned Win.
        previous = _normalize_squad_status(record["status"])
        status = _normalize_squad_status(squad.get("squadStatus"))
        self._reconcile(record, zone_data, squad, activity, status)

        if status == _LOCKED:
            self._open_lock(key, activity, squad)
        elif status == _DEFEATED:
            self._close(key, record, activity, BattleOutcome.WON, orphan=previous != _DEFEATED)
        elif status == _AVAILABLE:
            self._close(key, record, activity, BattleOutcome.REPULSE, orphan=False)

    def _reconcile(
        self,
        record: dict[str, Any],
        zone_data: Mapping[str, Any],
        squad: Mapping[str, Any],
        activity: ActivityEvent,
        status: int | None,
    ) -> None:
        """Overwrite a squad's known state from this snapshot.

        Every field is refreshed from the event rather than accumulated, except
        ``successful_defends``, which is kept as the highest reading ever seen.
        The counter is **not** monotonic — two squads in the sampled capture read
        ``0`` on their release event and ``2`` on the next lock — so it supports
        only the claim "this squad has repelled at least N" and is never
        differenced between observations.

        ``status`` is the one field an older snapshot may not overwrite. A page
        can deliver an event predating one already applied, and letting it roll
        the status back would make the next defeat read as the first one seen
        and manufacture a duplicate Orphaned Win.
        """
        stale = activity.timestamp < _as_int(record["last_seen"])

        defender = _as_str(squad.get("playerName"))
        if defender:
            record["defender"] = defender

        power = _as_int(squad.get("power"), default=0)
        if power:
            record["power"] = power

        defends = _as_int(squad.get("successfulDefends"), default=0)
        record["successful_defends"] = max(_as_int(record["successful_defends"]), defends)
        record["held"] = record["successful_defends"] > 0

        side = _side_of(zone_data)
        if side:
            record["side"] = side

        if status is not None and not stale:
            record["status"] = _SQUAD_STATUS_NAMES[status]
        record["last_seen"] = max(_as_int(record["last_seen"]), activity.timestamp)

    def _open_lock(self, key: tuple[str, str], activity: ActivityEvent, squad: Mapping[str, Any]) -> None:
        """Open a lock episode for *key*, extend the open one, or repair an Orphaned Win."""
        attacker = _attacker_of(activity, squad)
        episode = self._open.get(key)

        if episode is None:
            if self._repair_orphan(key, activity, attacker):
                return
            self._open[key] = _new_episode(key, attacker, activity.timestamp)
            return

        if attacker and episode["attacker"] and attacker != episode["attacker"]:
            # A different Attacker holds the lock, so the previous episode ended
            # without this reader seeing how. That is the "opening observed,
            # closing not observed" cell, and it is knowable now rather than at
            # the ageing horizon.
            self._battles.append(self._battle(key, episode, closed_at=None, outcome=BattleOutcome.OBSCURED))
            self._open[key] = _new_episode(key, attacker, activity.timestamp)
            return

        if attacker and not episode["attacker"]:
            episode["attacker"] = attacker
        episode["last_seen"] = max(_as_int(episode["last_seen"]), activity.timestamp)

    def _repair_orphan(self, key: tuple[str, str], activity: ActivityEvent, attacker: str | None) -> bool:
        """Fold a late-arriving lock into the Orphaned Win it turns out to have opened.

        A page boundary reorders the feed exactly the way a single page can: the
        Read Position bound tracks the server's update batching, so an event
        older than the position sent comes back in a later page. A defeat can
        therefore be applied before its own lock, leaving an Orphaned Win that a
        later page then supplies the opening for.

        That opening **repairs** the episode rather than starting a second one.
        In the loss model's quadrant the Battle moves from "opening not
        observed" to "opening observed" — an Orphaned Win becomes a
        :attr:`~BattleOutcome.WON` with an ``opened_at`` — because both ends
        turned out to be observable after all. Opening a fresh episode instead
        would count one engagement twice and leave the second half to age into
        :attr:`~BattleOutcome.OBSCURED`.

        Args:
            key: The ``(zone_id, squad_id)`` this lock belongs to.
            activity: The late-arriving ``SQUAD_LOCKED`` event.
            attacker: The Attacker named by that event, if any.

        Returns:
            Whether an Orphaned Win was repaired. ``False`` leaves the caller to
            open a new episode as usual.
        """
        chosen = -1
        for index, battle in enumerate(self._battles):
            if (battle.zone_id, battle.squad_id) != key or battle.outcome is not BattleOutcome.ORPHANED_WIN:
                continue
            if _as_int(battle.closed_at) < activity.timestamp:
                # That win closed before this lock opened, so it belongs to an
                # earlier engagement.
                continue
            if chosen < 0 or _as_int(battle.closed_at) < _as_int(self._battles[chosen].closed_at):
                # The earliest close after this opening is the one this lock
                # produced; any later close is a subsequent engagement.
                chosen = index
        if chosen < 0:
            return False

        battle = self._battles[chosen]
        record = self._squads.get(key) or {}
        self._battles[chosen] = replace(
            battle,
            defender=record.get("defender") or battle.defender,
            attacker=attacker or battle.attacker,
            opened_at=activity.timestamp,
            outcome=BattleOutcome.WON,
        )
        return True

    def _repair_obscured(self, key: tuple[str, str], activity: ActivityEvent, outcome: BattleOutcome) -> bool:
        """Fold a late close into the Obscured episode it resolves.

        An open lock past the retention horizon is written into :attr:`battles`
        as :attr:`~BattleOutcome.OBSCURED` and dropped from the open table, which
        is what keeps that table bounded. This is the other half of that bargain:
        a close arriving afterwards still resolves the episode, so eviction costs
        memory rather than accuracy and the documented promise that an aged lock
        "stays tracked" survives the pruning.

        Any lock observed in between would have opened a new episode, which the
        caller finds first — so an unresolved Obscured episode with no open
        episode behind it is the one this close belongs to.

        Args:
            key: The ``(zone_id, squad_id)`` this close belongs to.
            activity: The closing event.
            outcome: :attr:`~BattleOutcome.WON` or
                :attr:`~BattleOutcome.REPULSE`, per the observed status.

        Returns:
            Whether an Obscured Battle was resolved.
        """
        chosen = -1
        for index, battle in enumerate(self._battles):
            if (battle.zone_id, battle.squad_id) != key or battle.outcome is not BattleOutcome.OBSCURED:
                continue
            if battle.closed_at is not None or _as_int(battle.opened_at) > activity.timestamp:
                continue
            if chosen < 0 or _as_int(battle.opened_at) > _as_int(self._battles[chosen].opened_at):
                # The newest opening before this close is the episode it ends.
                chosen = index
        if chosen < 0:
            return False

        battle = self._battles[chosen]
        record = self._squads.get(key) or {}
        self._battles[chosen] = replace(
            battle,
            defender=record.get("defender") or battle.defender,
            closed_at=activity.timestamp,
            outcome=outcome,
        )
        return True

    def _close(
        self,
        key: tuple[str, str],
        record: Mapping[str, Any],
        activity: ActivityEvent,
        outcome: BattleOutcome,
        *,
        orphan: bool,
    ) -> None:
        """Close the open episode for *key*, or record an Orphaned Win when *orphan*."""
        episode = self._open.pop(key, None)
        if episode is not None:
            self._battles.append(self._battle(key, episode, closed_at=activity.timestamp, outcome=outcome))
        elif self._repair_obscured(key, activity, outcome):
            return
        elif orphan:
            # The defeat was observed and the engagement was not: it fell outside
            # this reader's earliest Read Position. A real win with no measurable
            # duration, not an error.
            self._battles.append(
                Battle(
                    zone_id=key[0],
                    squad_id=key[1],
                    defender=record.get("defender"),
                    attacker=_attacker_of(activity, {}),
                    opened_at=None,
                    closed_at=activity.timestamp,
                    outcome=BattleOutcome.ORPHANED_WIN,
                )
            )

    def _battle(
        self,
        key: tuple[str, str],
        episode: Mapping[str, Any],
        *,
        closed_at: int | None,
        outcome: BattleOutcome,
    ) -> Battle:
        """Build a :class:`Battle` from a lock episode and the squad's known state."""
        record = self._squads.get(key) or {}
        return Battle(
            zone_id=key[0],
            squad_id=key[1],
            defender=record.get("defender"),
            attacker=episode.get("attacker"),
            opened_at=_as_int(episode.get("opened_at")),
            closed_at=closed_at,
            outcome=outcome,
        )

    def _retention_horizon(self) -> int:
        """Return the timestamp below which the log no longer remembers anything.

        Everything at or before this point has been dropped from the seen-id
        table by :meth:`_prune`, so the log cannot tell a replay of it from a new
        event. Both the pruning and the staleness guard in :meth:`add` read the
        horizon from here, because the two have to agree: pruning an id and then
        accepting its replay is what would open a duplicate episode.
        """
        return self._latest - self._stale_after * _MILLISECONDS * _RETENTION_WINDOWS

    def _prune(self) -> None:
        """Retire what the log can no longer act on, so its state stays bounded.

        Retention is bounded by design, and that has to be enforced rather than
        asserted: a poll loop that never forgets makes the per-poll checkpoint
        grow with the length of the war, which is the one cost a persistable
        state must not have.

        The horizon is ``_RETENTION_WINDOWS`` (two) ageing windows behind the
        log's clock — the newest envelope timestamp seen, never the wall clock,
        so replaying a capture prunes exactly as the live run did. Two windows
        rather than one because the first is already spoken for: an open lock
        spends it becoming reportable as :attr:`~BattleOutcome.OBSCURED`, and
        only the second is slack. At the default ``stale_after`` that is thirty
        minutes, against a measured maximum lock duration of 311 s.

        Two tables are pruned, and the risk is opposite in each:

        - **Open locks.** An episode older than the horizon is written into
          :attr:`battles` as ``OBSCURED`` — it is already being reported that
          way — and dropped. Nothing is lost by it: a close arriving afterwards
          is folded back in by :meth:`_repair_obscured`.
        - **Seen event ids.** Dedupe is mandatory rather than an optimisation,
          so this is pruned only to the same horizon. Recurrence is driven by
          the server's update batching, which runs in seconds; retiring an id
          two ageing windows past its own timestamp puts the margin two orders
          of magnitude beyond the mechanism that causes a repeat.
        """
        horizon = self._retention_horizon()
        if horizon <= 0:
            return

        for key in [key for key, episode in self._open.items() if _as_int(episode.get("last_seen")) <= horizon]:
            episode = self._open.pop(key)
            self._battles.append(self._battle(key, episode, closed_at=None, outcome=BattleOutcome.OBSCURED))

        self._seen = {event_id: at for event_id, at in self._seen.items() if at > horizon}

    @property
    def opaque(self) -> int:
        """Count of Opaque Payloads seen — content unreadable, envelope only.

        Nothing inside one can be attributed to a zone, so each is counted and
        skipped. A high count against a low Battle count means the correlation is
        thin rather than the war quiet, which is a distinction no other number
        here makes.

        Only genuinely undecodable payloads are counted: a record whose ``raw``
        or ``error`` is set, meaning the server had content and could not hand it
        over. An opaque record with neither — the server supplied nothing to
        decode, an empty envelope — is skipped uncounted, because nothing was
        lost and counting it would overstate exactly the number this property
        exists to make trustworthy. See :attr:`~swgoh_comlink.helpers.ActivityEvent.raw`.
        """
        return self._opaque

    @property
    def state(self) -> BattleLogState:
        """A snapshot of the whole log as plain, JSON-serialisable data.

        Returns:
            A :class:`BattleLogState` safe to hand to ``dataclasses.asdict()``
            and ``json.dump()``. It is a copy: mutating it does not touch the
            log.

        Example:
            >>> import dataclasses, json
            >>> json.dump(dataclasses.asdict(log.state), handle)
        """
        return BattleLogState(
            version=1,
            battles=[{**asdict(battle), "outcome": battle.outcome.value} for battle in self._battles],
            squads=[dict(record) for record in self._squads.values()],
            open_locks=[dict(episode) for episode in self._open.values()],
            seen=sorted(self._seen),
            latest_timestamp=self._latest,
            opaque=self._opaque,
        )

    @property
    def battles(self) -> list[Battle]:
        """Every correlated Battle, oldest close first.

        A lock episode still within *stale_after* of the log's newest event is
        work in progress and is deliberately absent: reporting it as
        :attr:`~BattleOutcome.OBSCURED` would call a live assault lost. Past that
        horizon it appears as ``OBSCURED`` with ``closed_at`` of ``None``, and it
        stays tracked, so a close arriving late still resolves it to
        :attr:`~BattleOutcome.WON` or :attr:`~BattleOutcome.REPULSE`. That holds
        after the episode itself has been pruned out of the open table: see
        :meth:`_prune` and :meth:`_repair_obscured`.

        Returns:
            A freshly built list ordered by close time, falling back to open time
            for a Battle that never closed. Mutating it does not touch the log.
        """
        horizon = self._latest - self._stale_after * _MILLISECONDS
        aged = [
            self._battle(key, episode, closed_at=None, outcome=BattleOutcome.OBSCURED)
            for key, episode in self._open.items()
            if _as_int(episode.get("last_seen")) <= horizon
        ]
        return sorted(
            [*self._battles, *aged],
            key=lambda battle: (battle.closed_at or battle.opened_at or 0, battle.zone_id, battle.squad_id),
        )

    @property
    def squads(self) -> dict[tuple[str, str], dict[str, Any]]:
        """Every defending squad seen, keyed by ``(zone_id, squad_id)``.

        Held lives here rather than on a :class:`Battle`, because it is a
        property of the squad: the count is the squad's own and includes defends
        from before this reader subscribed, so it is not a summary of what was
        observed.

        Returns:
            A copy of the squad table. Each record carries:

            - ``zone_id`` / ``squad_id``: the key, repeated so a record survives
                serialisation on its own.
            - ``defender``: the squad's owner, or ``None`` — a ``warSquad``
                sometimes arrives with no player at all.
            - ``power``: the squad's last reported power, or ``None``.
            - ``successful_defends``: the highest reading of the squad's own
                defend counter. A floor — "this squad has repelled at least N" —
                never a delta, because the counter is not monotonic.
            - ``held``: whether that floor is above zero.
            - ``status``: the last observed ``TerritoryWarSquadStatus`` as its
                canonical name — ``SQUAD_AVAILABLE``, ``SQUAD_LOCKED``,
                ``SQUAD_DEFEATED`` — or ``None``.
            - ``side``: ``"home"``/``"away"`` from ``notificationInstanceType``,
                or ``None`` when the rendering is not recognised.
            - ``last_seen``: millisecond timestamp of the newest observation.
        """
        return {key: dict(record) for key, record in self._squads.items()}


def _attacker_of(activity: ActivityEvent, squad: Mapping[str, Any]) -> str | None:
    """Return the Attacker's name for an event, or ``None`` when neither source names one.

    The Attacker is the player who launched the Battle: the squad's ``lockName``
    while the lock holds, and otherwise the Activity Event's author. It is never
    the Defender, who owns the ``warSquad``; reading it the other way inverts
    every attribution.
    """
    return _as_str(squad.get("lockName")) or activity.author_name or None


def get_defending_squads(events: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Summarise the defending squads in a page of Channel events.

    A one-shot convenience over :class:`BattleLog` for callers who want the
    defensive picture — who is Held, at what power, in which zone — without
    keeping a correlator alive across polls. Correlating Battles needs history;
    reading squad state does not, because every ``warSquad`` event carries the
    squad's complete current state.

    Args:
        events: Raw server event dictionaries, as carried by
            :attr:`~swgoh_comlink.helpers.ChannelRead.events`. Opaque Payloads
            and non-Territory-War events are skipped.

    Returns:
        The same table as :attr:`BattleLog.squads`, keyed by
        ``(zone_id, squad_id)``.

    Example:
        >>> from swgoh_comlink.helpers import get_defending_squads
        >>> squads = get_defending_squads(page.events)
        >>> sorted(s["defender"] for s in squads.values() if s["held"])
        ['Ahsoka', 'Ezra']
    """
    log = BattleLog()
    log.add(events)
    return log.squads
