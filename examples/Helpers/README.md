### Territory Parsing Helper Examples

----
The scripts in this folder show how to use the `mhanndalorian_bot.helpers`
parsing layer to turn raw Territory War / Territory Battle log responses into
typed domain objects. The helpers are pure and transport-agnostic: fetch the raw
log with the normal `API` client, then pass the response straight in — the
helpers normalize MBot's `info`/`payload` wire shape for you.

- [territory_war_battles.py](territory_war_battles.py) — correlate a `twlogs`
  response into typed `Battle`s and per-squad defending snapshots.
- [territory_battle_activity.py](territory_battle_activity.py) — type a `tblogs`
  response into structured `TerritoryActivity` contributions (with recon rosters).
- [territory_war_resume.py](territory_war_resume.py) — poll a war incrementally
  (async), checkpointing correlator state so a restart doesn't misreport
  in-flight battles.

See `CONTEXT.md` for the domain vocabulary (Battle, Held, Repulse, Obscured,
Territory Activity, …) and `docs/adr/` for why the layer is shaped this way.
