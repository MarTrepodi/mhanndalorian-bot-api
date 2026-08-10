"""Correlate a Territory War log into typed Battles and defending squads.

The parsing helpers are pure and transport-agnostic: you fetch the raw log with
the normal ``API`` client, then hand the response straight to ``battle_log`` /
``defending_squads`` — they normalize MBot's ``info``/``payload`` shape for you.

Note: `twlogs` is an *authenticated* endpoint, so this call breaks the player's
active game session. See Library_Details.md for the full list.
"""

from mhanndalorian_bot import API, APIResponseError, ValidationError
from mhanndalorian_bot.helpers import battle_log, defending_squads

try:
    with API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE") as mbot:
        twlogs = mbot.fetch_twlogs()
except ValidationError as exc:
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}") from exc

# Fold the whole log into Battles. A Battle is one attacker's assault on one
# defending squad in one zone during one lock episode; its outcome records which
# ends of the engagement were observed (won / repulse / orphaned_win / obscured).
log = battle_log(twlogs)

print(f"{len(log.battles)} battles, {log.opaque} undecodable payloads")
for battle in log.battles[:10]:
    print(
        f"  {battle.zone_id} squad={battle.squad_id[:8]} "
        f"attacker={battle.attacker!r} defender={battle.defender!r} "
        f"-> {battle.outcome.value}"
    )

# A per-squad reconciled snapshot, keyed by (zone_id, squad_id). ``held`` is the
# squad's own running defend count (it includes defends from before you started
# reading); ``successful_defends`` is what was observed in this log.
squads = defending_squads(twlogs)
print(f"\n{len(squads)} defending squads")
for (zone_id, squad_id), record in list(squads.items())[:10]:
    print(
        f"  {zone_id} squad={squad_id[:8]} defender={record['defender']!r} "
        f"held={record['held']} status={record['status']}"
    )

"""
Sample output:

460 battles, 0 undecodable payloads
  tw_jakku01_phase01_conflict01 squad=Mg_5kvMp attacker='Fraser' defender='Tich' -> orphaned_win
  tw_jakku01_phase01_conflict02 squad=CglgKEGD attacker='Kylo'   defender='Rey'  -> won
  ...

483 defending squads
  tw_jakku01_phase04_conflict01 squad=CglgKEGD defender='Rey' held=3 status=AVAILABLE
  ...
"""
