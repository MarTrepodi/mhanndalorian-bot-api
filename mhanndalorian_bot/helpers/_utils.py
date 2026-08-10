"""Shared scalar coercers for the territory parsing layer.

Territory payloads arrive with numbers rendered as strings and enum fields
rendered as either a bare integer (``enums=False``) or a string (``enums=True``).
These three coercers normalize that at the edge so the decoders can treat every
field uniformly. Ported verbatim from ``swgoh_comlink.helpers._utils``.
"""

from __future__ import annotations

from typing import Any


def _as_int(value: Any) -> int:
    """Return *value* as an int, or ``0`` when it is not one. Numbers arrive as strings."""
    if isinstance(value, bool):
        # ``bool`` is an ``int`` subclass, so ``int(True)`` is ``1`` — which
        # reads as real data (a timestamp, a score). ``0`` is the "no value"
        # sentinel and stays that.
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_str(value: Any) -> str:
    """Return *value* when it is a string, else ``""``."""
    return value if isinstance(value, str) else ""


def _as_scalar(value: Any) -> int | str | None:
    """Return *value* when it is an int or a string, else ``None``.

    An enum-rendered field (``ChannelEventType``, ``TerritoryZoneState`` and the
    like) is a bare integer with ``enums=False`` and a string with
    ``enums=True``, so both are preserved exactly as sent. ``bool`` is excluded
    despite subclassing ``int`` — it is never a real enum value, and letting
    ``True`` through would read as the value ``1``.
    """
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, str)) else None
