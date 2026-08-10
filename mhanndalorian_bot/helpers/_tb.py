"""Typed Territory Battle zone activity.

:func:`~swgoh_comlink.helpers.iter_activity_events` (see ``helpers/_chat.py``)
unpacks a Channel event envelope and hands the payload back as an untyped
``dict``. This module types the *body* of that payload for the four Territory
Battle zone activities — conflict, strike, recon and covert — turning
``payload["zoneData"]["sourceZoneId"]`` reach-throughs into a flat, frozen
:class:`TerritoryActivity`.

It is a decoder, not a correlator. Each record is one activity standing on its
own; nothing here folds a stream into per-zone running totals or rebuilds the
strike/recon/covert → conflict lineage as a graph. A Territory Battle has no
Attacker, Defender or Battle the way a Territory War does — the glossary gives
it none — so there is deliberately no
:class:`~swgoh_comlink.helpers.BattleLog` analogue. What it has instead is
lineage, and this record surfaces it as two fields
(:attr:`TerritoryActivity.zone_id` and :attr:`TerritoryActivity.source_zone_id`)
rather than inferring a relationship the game does not document.

The shape follows the comlink-rust ``TerritoryZoneData`` schema. comlink decodes
these payloads server-side, so a well-formed activity is already a plain dict
here rather than a base64 protobuf; an Opaque Payload — one comlink could not
decode — cannot be typed and is reported as ``None`` by
:func:`parse_territory_activity`. Count those through
:func:`~swgoh_comlink.helpers.iter_activity_events`, which yields them, if you
need the tally.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from ._events import ActivityEvent, iter_activity_events
from ._utils import _as_int, _as_scalar, _as_str

__all__ = [
    "TERRITORY_ACTIVITY_TYPES",
    "TerritoryActivity",
    "TerritoryReconUnit",
    "iter_territory_activities",
    "parse_territory_activity",
]

# The ``data[]`` ``type`` discriminators for the four Territory Battle zone
# activities, confirmed against the comlink-rust ``ChannelEventData`` variants.
# Territory War's own ``TERRITORY_WAR_CONFLICT_ACTIVITY`` is absent on purpose —
# it carries a ``warSquad`` and belongs to :class:`~swgoh_comlink.helpers.BattleLog` —
# and ``TERRITORY_MAP_ACTIVITY`` is absent because it carries ``mapData`` rather
# than the ``zoneData`` this record is built from.
TERRITORY_ACTIVITY_TYPES: tuple[str, ...] = (
    "TERRITORY_CONFLICT_ACTIVITY",
    "TERRITORY_STRIKE_ACTIVITY",
    "TERRITORY_RECON_ACTIVITY",
    "TERRITORY_COVERT_ACTIVITY",
)


@dataclass(frozen=True)
class TerritoryReconUnit:
    """One unit named in a recon contribution.

    Recon activities are the only family that names units; every other family
    leaves :attr:`TerritoryActivity.units` empty.

    Attributes:
        unit_id: The unit definition id, from ``unitIdentifier``. Unsuffixed, not
            a roster instance id.
        level: The unit's level, or ``0`` when absent.
        tier: The unit's gear tier, preserved as sent — a bare integer with
            ``enums=False`` and a string with ``enums=True`` — or ``None``.
        relic_tier: The unit's **encoded** relic tier (the player-facing relic
            number is this minus two), preserved as sent, or ``None``.
        squad_id: The recon squad the unit was placed in, or ``""``.
    """

    unit_id: str = ""
    level: int = 0
    tier: int | str | None = None
    relic_tier: int | str | None = None
    squad_id: str = ""


@dataclass(frozen=True)
class TerritoryActivity:
    """One decoded Territory Battle zone activity.

    A flat view over a single ``TerritoryZoneData`` payload plus the envelope it
    arrived in. Every field down to :attr:`activity_type` is envelope provenance
    carried from the :class:`~swgoh_comlink.helpers.ActivityEvent`; the rest is
    the decoded zone body.

    The two lineage fields are the point of the record. A contribution scores a
    conflict zone — :attr:`zone_id` — but may originate in a child strike, recon
    or covert zone, named by :attr:`source_zone_id`. A contribution deployed
    straight to the conflict zone carries an empty :attr:`source_zone_id` (see
    :attr:`is_direct_deploy`); a recon event read on its own zone's Channel
    self-pairs, with :attr:`source_zone_id` equal to :attr:`zone_id`. The
    relationship was read off packet captures, not documented, so treat it as
    observed rather than guaranteed.

    Attributes:
        event_id: The envelope's event id — the deduplication key.
        channel_id: The Channel the activity arrived on. A territory Channel maps
            to a single zone, so this locates even an event whose finer detail is
            missing.
        author_id: The contributing player's id, or ``""``.
        author_name: The contributing player's name, or ``""``.
        timestamp: The envelope timestamp in milliseconds, or ``0``.
        activity_type: The ``data[]`` discriminator — one of
            :data:`TERRITORY_ACTIVITY_TYPES` under the default filter.
        zone_id: The conflict zone this contribution scores (the parent).
        source_zone_id: The child zone the contribution came from, or ``""`` for
            a direct deploy.
        score_delta: Points this contribution added, coerced to int.
        score_total: The zone's running score after it, coerced to int.
        participation_delta: Participation this contribution added, coerced to
            int.
        participation_total: The zone's running participation after it.
        state: The zone's ``TerritoryZoneState``, preserved as sent (int or
            string), or ``None``.
        instance_type: The zone's ``instanceType``. Score activity is filed under
            ``HOME`` while describing away-map activity, so filter on
            :attr:`notification_instance_type`, never this.
        notification_instance_type: The zone's ``notificationInstanceType`` — the
            field to filter map side on.
        message_key: The activity-log localization key. ``"EMPTY"`` (or ``""``)
            means the game renders the line from structure alone; see
            :attr:`is_structural`.
        message_params: The localization parameters, as raw dicts, in order.
        platoon_id: The recon platoon id, or ``""`` for a non-recon activity.
        units: The units named in a recon contribution; empty for every other
            family.
        guild_id: The contributing guild's id, or ``""``.
        map_id: The territory map definition id, or ``""``.
        map_instance_id: The specific map instance id, or ``""``.
    """

    event_id: str = ""
    channel_id: str = ""
    author_id: str = ""
    author_name: str = ""
    timestamp: int = 0
    activity_type: str = ""
    zone_id: str = ""
    source_zone_id: str = ""
    score_delta: int = 0
    score_total: int = 0
    participation_delta: int = 0
    participation_total: int = 0
    state: int | str | None = None
    instance_type: int | str | None = None
    notification_instance_type: int | str | None = None
    message_key: str = ""
    message_params: tuple[dict[str, Any], ...] = ()
    platoon_id: str = ""
    units: tuple[TerritoryReconUnit, ...] = ()
    guild_id: str = ""
    map_id: str = ""
    map_instance_id: str = ""

    @property
    def is_direct_deploy(self) -> bool:
        """Whether the contribution went straight to its conflict zone.

        ``True`` when there is no source zone — the contribution was deployed to
        the conflict zone itself rather than fed up from a child zone.
        """
        return not self.source_zone_id

    @property
    def is_structural(self) -> bool:
        """Whether the game renders this activity's line from structure alone.

        ``True`` when the activity carries no localization text of its own — the
        ``EMPTY`` key — so a reader should present the record's fields rather
        than a message.
        """
        return self.message_key in ("", "EMPTY")


def _recon_units(payload: dict[str, Any]) -> tuple[TerritoryReconUnit, ...]:
    """Type the ``units`` list of a recon payload; empty for every other family."""
    return tuple(
        TerritoryReconUnit(
            unit_id=_as_str(unit.get("unitIdentifier")),
            level=_as_int(unit.get("level")),
            tier=_as_scalar(unit.get("tier")),
            relic_tier=_as_scalar(unit.get("unitRelicTier")),
            squad_id=_as_str(unit.get("squadId")),
        )
        for unit in payload.get("units") or []
        if isinstance(unit, dict)
    )


def parse_territory_activity(event: ActivityEvent) -> TerritoryActivity | None:
    """Type one Territory Battle zone activity, or ``None`` when it cannot be.

    Returns ``None`` for anything without a readable ``zoneData`` body: an Opaque
    Payload (nothing decoded), or an activity of a kind this record does not
    model — a ``TERRITORY_MAP_ACTIVITY`` carries ``mapData``, a chat message
    carries neither. It does **not** gate on :attr:`~ActivityEvent.type`, so a
    Territory War conflict activity — which also carries ``zoneData`` — types
    successfully here; its ``warSquad`` is simply not represented, because squad
    state is :class:`~swgoh_comlink.helpers.BattleLog`'s concern.
    :func:`iter_territory_activities` is the type-gated entry point.

    Args:
        event: One :class:`~swgoh_comlink.helpers.ActivityEvent`, as produced by
            :func:`~swgoh_comlink.helpers.iter_activity_events`.

    Returns:
        A :class:`TerritoryActivity`, or ``None`` when the event has no readable
        zone body.

    Example:
        >>> from swgoh_comlink.helpers import iter_activity_events, parse_territory_activity
        >>> activities = [
        ...     a for e in iter_activity_events(page.events) if (a := parse_territory_activity(e))
        ... ]
    """
    payload = event.payload
    if event.opaque or not isinstance(payload, dict):
        return None
    zone = payload.get("zoneData")
    if not isinstance(zone, dict):
        return None

    message = zone.get("activityLogMessage")
    message = message if isinstance(message, dict) else {}
    params = tuple(param for param in message.get("param") or [] if isinstance(param, dict))

    return TerritoryActivity(
        event_id=event.event_id,
        channel_id=event.channel_id,
        author_id=event.author_id,
        author_name=event.author_name,
        timestamp=event.timestamp,
        activity_type=event.type,
        zone_id=_as_str(zone.get("zoneId")),
        source_zone_id=_as_str(zone.get("sourceZoneId")),
        score_delta=_as_int(zone.get("scoreDelta")),
        score_total=_as_int(zone.get("scoreTotal")),
        participation_delta=_as_int(zone.get("participationDelta")),
        participation_total=_as_int(zone.get("participationTotal")),
        state=_as_scalar(zone.get("state")),
        instance_type=_as_scalar(zone.get("instanceType")),
        notification_instance_type=_as_scalar(zone.get("notificationInstanceType")),
        message_key=_as_str(message.get("key")),
        message_params=params,
        platoon_id=_as_str(payload.get("platoonId")),
        units=_recon_units(payload),
        guild_id=_as_str(zone.get("guildId")),
        map_id=_as_str(zone.get("mapId")),
        map_instance_id=_as_str(zone.get("mapInstanceId")),
    )


def iter_territory_activities(
    events: Iterable[dict[str, Any]],
    *,
    types: str | Iterable[str] | None = TERRITORY_ACTIVITY_TYPES,
) -> Iterator[TerritoryActivity]:
    """Type the Territory Battle zone activities in a stream of raw Channel events.

    The convenience path over :func:`~swgoh_comlink.helpers.iter_activity_events`
    and :func:`parse_territory_activity`: it unpacks each envelope, keeps the
    activity types in *types*, and yields only those that carry a readable zone
    body. Opaque Payloads and non-zone activities are dropped silently — read the
    events with :func:`~swgoh_comlink.helpers.iter_activity_events` directly if
    you need to count what was lost.

    Args:
        events: Raw server event dictionaries, as carried by
            :attr:`~swgoh_comlink.helpers.ChannelRead.events`.
        types: Activity ``type`` discriminator(s) to keep. Defaults to the four
            Territory Battle families in :data:`TERRITORY_ACTIVITY_TYPES`; pass
            ``None`` to attempt every type, which still yields only those with a
            zone body.

    Yields:
        One :class:`TerritoryActivity` per typed activity.

    Example:
        >>> from swgoh_comlink.helpers import iter_territory_activities
        >>> page = read_channel_events(auth, channels)
        >>> for activity in iter_territory_activities(page.events):
        ...     if not activity.is_direct_deploy:
        ...         print(activity.source_zone_id, "->", activity.zone_id, activity.score_delta)
    """
    for event in iter_activity_events(events, types=types):
        activity = parse_territory_activity(event)
        if activity is not None:
            yield activity
