"""Territory Battle / Territory War parsing helpers.

A transport-agnostic layer that turns the raw dictionaries returned by MBot's
``fetch_twlogs`` / ``fetch_tblogs`` / ``fetch_tw`` / ``fetch_tb`` into typed
domain objects. Ported from ``swgoh_comlink`` (see ``docs/adr/``).

The three convenience entrypoints accept a raw ``fetch_*`` response and
normalize it internally, so the common case is a one-liner::

    from mhanndalorian_bot import API
    from mhanndalorian_bot.helpers import battle_log, territory_activities

    api = API(api_key="...", allycode="...")
    log = battle_log(api.fetch_twlogs())          # -> BattleLog, already populated
    acts = list(territory_activities(api.fetch_tblogs()))

The lower-level functions (``normalize_events``, ``iter_activity_events``,
``parse_territory_activity``, ``BattleLog``, ...) are exported for callers that
want to drive the pipeline themselves.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ._events import ActivityEvent, iter_activity_events, normalize_events
from ._tb import (
    TERRITORY_ACTIVITY_TYPES,
    TerritoryActivity,
    TerritoryReconUnit,
    iter_territory_activities,
    parse_territory_activity,
)
from ._war import (
    Battle,
    BattleLog,
    BattleLogState,
    BattleOutcome,
    get_defending_squads,
)

__all__ = [
    # Event spine + adapter
    "ActivityEvent",
    "iter_activity_events",
    "normalize_events",
    # Territory Battle activity
    "TERRITORY_ACTIVITY_TYPES",
    "TerritoryActivity",
    "TerritoryReconUnit",
    "iter_territory_activities",
    "parse_territory_activity",
    # Territory War correlation
    "Battle",
    "BattleLog",
    "BattleLogState",
    "BattleOutcome",
    "get_defending_squads",
    # MBot convenience entrypoints
    "territory_activities",
    "battle_log",
    "defending_squads",
]


def territory_activities(
    response: Any,
    *,
    types: str | list[str] | tuple[str, ...] | None = TERRITORY_ACTIVITY_TYPES,
) -> Iterator[TerritoryActivity]:
    """Type a ``fetch_tblogs`` / ``fetch_twlogs`` response into Territory Activities.

    Normalizes *response* and runs it through :func:`iter_territory_activities`.
    See that function for the *types* filter semantics.
    """
    return iter_territory_activities(normalize_events(response), types=types)


def battle_log(
    response: Any,
    *,
    stale_after: int = 900,
    state: BattleLogState | None = None,
) -> BattleLog:
    """Build a :class:`BattleLog` from a ``fetch_twlogs`` response.

    Normalizes *response*, feeds it to a fresh (or resumed) correlator, and
    returns the populated log. Call again with the same ``state`` to fold in
    later pages incrementally.
    """
    log = BattleLog(stale_after=stale_after, state=state)
    log.add(normalize_events(response))
    return log


def defending_squads(response: Any) -> dict[tuple[str, str], dict[str, Any]]:
    """Reconcile the defending squads in a ``fetch_twlogs`` response.

    A one-shot convenience over :func:`get_defending_squads`; normalizes
    *response* first. Keyed by ``(zone_id, squad_id)``.
    """
    return get_defending_squads(normalize_events(response))
