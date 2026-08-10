"""Activity Event unpacking, plus the MBot response adapter.

``ActivityEvent`` and ``iter_activity_events`` are ported verbatim from
``swgoh_comlink.helpers._chat`` (only the event-unpacking spine — the chat,
channel-discovery, rooms and read-position machinery is out of scope; see
``docs/adr/0001-port-only-the-parsing-layer.md``). ``normalize_events`` is new:
it bridges MBot's ``info``/``payload`` response shape onto the flat event
contract the ported decoders expect (see
``docs/adr/0002-normalize-event-shape-adapter.md``).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from ._utils import _as_int, _as_scalar, _as_str

__all__ = [
    "ActivityEvent",
    "iter_activity_events",
    "normalize_events",
]


@dataclass(frozen=True)
class ActivityEvent:
    """One unpacked payload from an Activity Event envelope.

    An event's ``data`` list held exactly one item in 95 of 95 sampled events,
    so flattening the envelope is safe; ``event_id`` is carried on every record
    regardless, so event counts stay recoverable from the flattened stream.

    Every field above :attr:`type` comes from the shared envelope and is carried
    down onto each flattened record; :attr:`type` and everything below it come
    from the individual ``data[]`` item.

    Attributes:
        event_id: The envelope's opaque event id. Not ordinal — there is no
            sequence signal in the feed — but stable, so it is the deduplication
            key.
        channel_id: The Channel the event arrived on, from the envelope's
            ``channelId``, or ``""`` when absent. A territory Channel maps to a
            single zone, so this attributes an event to its zone even when the
            payload — where the zone id itself lives — is an unreadable Opaque
            Payload.
        author_id: The envelope's ``authorId``, or ``""`` when absent.
        author_name: The envelope's ``authorName``, or ``""`` when absent. For a
            Territory War engagement this is the Attacker, never the Defender.
        timestamp: The envelope's ``timestamp`` in milliseconds, or ``0``.
        event_type: The envelope's ``eventType``, preserved as sent — a bare
            integer with ``enums=False`` and a string with ``enums=True`` — or
            ``None`` when absent. This is the envelope's classification and is
            distinct from :attr:`type`, the payload item's own discriminator;
            normalise it before comparing rather than matching a string literal.
        event_subtype: The envelope's ``eventSubtype``, or ``""`` when absent.
        correlation_id: The envelope's ``correlationId``, or ``""`` when absent.
        message: The envelope's ``message``. An Activity Event carries structure
            and no text, so this is ``""`` on one; a non-empty value marks a
            player-typed chat message, which is how the two are told apart.
        type: The payload item's own ``type`` discriminator, or ``""`` when
            absent.
        payload: The decoded payload, or ``None`` for an Opaque Payload.
        opaque: Whether this is an Opaque Payload — content unreadable, leaving
            only the envelope. The contribution's own detail — score, source
            zone, units — is lost, but its location is not: :attr:`channel_id`
            still attributes it to a zone.
        raw: The undecoded value when *opaque*, where the server supplied one.
            ``raw`` and ``error`` both ``None`` on an opaque record means the
            server supplied nothing to decode — an absent payload, an empty
            envelope — as against a payload that arrived undecoded, which sets
            one or both. That pair is the distinction between "the correlation
            is thin" and "there was nothing there", so a counter that cares
            should split on it rather than on ``opaque`` alone.
        error: The server's decode error, when it reported one.
    """

    event_id: str = ""
    channel_id: str = ""
    author_id: str = ""
    author_name: str = ""
    timestamp: int = 0
    event_type: int | str | None = None
    event_subtype: str = ""
    correlation_id: str = ""
    message: str = ""
    type: str = ""
    payload: dict[str, Any] | None = None
    opaque: bool = False
    raw: str | None = None
    error: str | None = None


def iter_activity_events(
    events: Iterable[dict[str, Any]],
    *,
    types: str | Iterable[str] | None = None,
) -> Iterator[ActivityEvent]:
    """Unpack raw Channel events into :class:`ActivityEvent` records.

    Yields one record per ``data[]`` item, carrying the envelope's id, author
    and timestamp down onto each. In 95 of 95 sampled events ``data`` held
    exactly one item, so in practice this is one record per event.

    An Opaque Payload — content the server returned undecoded, leaving only the
    envelope — is yielded with ``opaque=True`` and ``payload=None``, never
    skipped and never raised. Skipping it would understate what happened;
    raising would make a single unreadable payload cost the whole page. An
    Opaque Payload's own detail is unrecoverable, but its location is not: the
    envelope names the ``channel_id`` it arrived on and a territory Channel maps
    to a single zone, so a correlator can still place it on the map even though
    the zone id inside the payload is unreadable. A ``data[]`` item that is not a
    dictionary at all is unreadable in the same sense and is yielded the same
    way; because it carries no ``type``, a *types* filter excludes it, exactly as
    that filter already excludes a dictionary item whose own ``type`` is missing.

    Not every opaque record cost the same. ``raw`` or ``error`` set means the
    server had something and could not hand it over; both ``None`` means it had
    nothing to hand over. See :attr:`ActivityEvent.raw` — counting the two
    together overstates how much of the feed was lost.

    Args:
        events: Raw server event dictionaries, in the flat shape produced by
            :func:`normalize_events`.
        types: Payload ``type`` discriminator(s) to keep — a single string or
            an iterable of them, e.g. ``"TERRITORY_WAR_CONFLICT_ACTIVITY"``.
            ``None`` keeps every payload. Filtering happens on the item's own
            ``type``, which survives even when the payload does not, so opaque
            items of a wanted type are still yielded.

    Yields:
        One :class:`ActivityEvent` per surviving ``data[]`` item.

    Example:
        >>> from mhanndalorian_bot.helpers import iter_activity_events, normalize_events
        >>> events = normalize_events(api.fetch_tblogs())
        >>> opaque = sum(1 for e in iter_activity_events(events) if e.opaque)
    """
    wanted = None if types is None else frozenset([types] if isinstance(types, str) else types)

    for event in events:
        event_id = _as_str(event.get("id"))
        channel_id = _as_str(event.get("channelId"))
        author_id = _as_str(event.get("authorId"))
        author_name = _as_str(event.get("authorName"))
        timestamp = _as_int(event.get("timestamp"))
        event_type = _as_scalar(event.get("eventType"))
        event_subtype = _as_str(event.get("eventSubtype"))
        correlation_id = _as_str(event.get("correlationId"))
        message = _as_str(event.get("message"))

        for item in event.get("data") or []:
            # An item that is not a dictionary at all is unreadable in exactly
            # the sense an undecoded payload is, so it is an Opaque Payload
            # too: yielded and counted, never dropped. It carries no ``type``,
            # which is why a ``types`` filter excludes it — the same treatment
            # a dictionary item missing its ``type`` already gets.
            item_type = _as_str(item.get("type")) if isinstance(item, dict) else ""
            if wanted is not None and item_type not in wanted:
                continue

            if not isinstance(item, dict):
                yield ActivityEvent(
                    event_id=event_id,
                    channel_id=channel_id,
                    author_id=author_id,
                    author_name=author_name,
                    timestamp=timestamp,
                    event_type=event_type,
                    event_subtype=event_subtype,
                    correlation_id=correlation_id,
                    message=message,
                    payload=None,
                    opaque=True,
                    raw=item if isinstance(item, str) else None,
                )
                continue

            payload = item.get("payload")
            error = item.get("error")
            if isinstance(payload, dict):
                decoded: dict[str, Any] | None = payload
                raw: str | None = None
                opaque = False
            else:
                # Measured live: every payload arrived as a base64 protobuf
                # string. A server that tried and failed to decode reports
                # ``raw`` and ``error`` beside a null payload instead. MBot's
                # backend pre-decodes, so in practice this branch is only hit by
                # a genuinely empty or malformed item.
                decoded = None
                raw = payload if isinstance(payload, str) else item.get("raw")
                raw = raw if isinstance(raw, str) else None
                opaque = True

            yield ActivityEvent(
                event_id=event_id,
                channel_id=channel_id,
                author_id=author_id,
                author_name=author_name,
                timestamp=timestamp,
                event_type=event_type,
                event_subtype=event_subtype,
                correlation_id=correlation_id,
                message=message,
                type=item_type,
                payload=decoded,
                opaque=opaque,
                raw=raw,
                error=error if isinstance(error, str) else None,
            )


def normalize_events(response: Any) -> list[dict[str, Any]]:
    """Flatten an MBot territory-log response into the flat event contract.

    MBot's ``/twlogs`` and ``/tblogs`` return::

        {"code", "instanceId", <key>: [
            {"info": {<envelope>, "data": [{"type": ...}]},
             "payload": {<decoded body>}} ]}

    where ``<key>`` is ``"data"`` for Territory War logs and ``"event"`` for
    Territory Battle logs — an inconsistency tracked upstream as MBot backend
    issue #14. The envelope sits under ``info`` and the already-decoded payload
    is hoisted to a sibling. The ported decoders instead expect a *flat* event
    that carries the payload inside its ``data[]`` item::

        {"id", "channelId", "timestamp", ..., "data": [{"type", "payload": {...}}]}

    This lifts ``info`` to the top level and reattaches the event-level payload
    to each ``data[]`` item, so :func:`iter_activity_events` and
    :class:`~mhanndalorian_bot.helpers.BattleLog` run unchanged.

    The function is tolerant and idempotent: it accepts either a raw response
    dict or an already-unwrapped list of events, passes through events that carry
    no ``info`` wrapper (already flat), and returns ``[]`` for anything it cannot
    make sense of rather than raising.

    Args:
        response: A ``fetch_twlogs`` / ``fetch_tblogs`` response dict, or a list
            of event dicts.

    Returns:
        A list of flat event dicts ready for :func:`iter_activity_events`.
    """
    if isinstance(response, dict):
        raw = response.get("data")
        if not isinstance(raw, list):
            raw = response.get("event")
        events: list[Any] = raw if isinstance(raw, list) else []
    elif isinstance(response, list):
        events = response
    else:
        return []

    flat: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        info = event.get("info")
        if not isinstance(info, dict):
            # Already flat (or nothing to lift) — pass through unchanged, which
            # is what makes a second normalize_events call a no-op.
            flat.append(event)
            continue

        merged = {key: value for key, value in info.items() if key != "data"}
        payload = event.get("payload")
        data_items = info.get("data")
        items: list[Any] = []
        for item in data_items if isinstance(data_items, list) else []:
            # Attach the single event-level payload to the item's own ``type``.
            # Observed data lists hold exactly one item, so this reunites each
            # discriminator with its decoded body.
            items.append({**item, "payload": payload} if isinstance(item, dict) else item)
        merged["data"] = items
        flat.append(merged)

    return flat
