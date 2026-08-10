"""Poll a Territory War incrementally, checkpointing correlator state.

The event feed is a bounded, shared queue: fall behind and events are evicted,
so a long war is read by polling and folding each page into a running
``BattleLog``. Persisting the log's state between polls (and across restarts) is
what stops a restart from reporting every in-flight Battle as an Orphaned Win.

``battle_log(response, state=...)`` seeds a fresh correlator from prior state and
adds the new page; folding overlapping pages is safe because events dedupe by
their envelope id. This example runs one poll — wrap the marked section in your
own scheduler to keep it running.

Note: `twlogs` is an *authenticated* endpoint, so each call breaks the player's
active game session. See Library_Details.md for the full list.
"""

import asyncio
import dataclasses
import json
from pathlib import Path

from mhanndalorian_bot import API, APIResponseError, ValidationError
from mhanndalorian_bot.helpers import BattleLogState, battle_log

CHECKPOINT = Path("tw_battlelog_state.json")


def load_state() -> BattleLogState | None:
    """Resume from a previous run, if one was checkpointed."""
    if CHECKPOINT.exists():
        return BattleLogState.from_dict(json.loads(CHECKPOINT.read_text()))
    return None


def save_state(state: BattleLogState) -> None:
    """Persist correlator state as plain JSON for the next poll/run."""
    CHECKPOINT.write_text(json.dumps(dataclasses.asdict(state)))


async def poll_once() -> None:
    state = load_state()

    # ── one poll ────────────────────────────────────────────────────────
    try:
        async with API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE") as mbot:
            twlogs = await mbot.fetch_twlogs_async()
    except ValidationError as exc:
        raise SystemExit(f"Bad input: {exc}") from exc
    except APIResponseError as exc:
        raise SystemExit(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}") from exc

    log = battle_log(twlogs, state=state)
    save_state(log.state)
    # ────────────────────────────────────────────────────────────────────

    live = sum(1 for b in log.battles if b.outcome.value == "obscured")
    print(f"{len(log.battles)} battles so far ({live} still open); state checkpointed to {CHECKPOINT}")


if __name__ == "__main__":
    asyncio.run(poll_once())

"""
Run it repeatedly (e.g. every minute) and the Battle list grows monotonically;
late-arriving events repair provisional outcomes in place rather than
duplicating engagements:

$ python territory_war_resume.py
128 battles so far (3 still open); state checkpointed to tw_battlelog_state.json
$ python territory_war_resume.py
141 battles so far (2 still open); state checkpointed to tw_battlelog_state.json
"""
