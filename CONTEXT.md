# Mhanndalorian Bot — Domain Context

The ubiquitous language for `mhanndalorian_bot`. This glossary is a shared
dictionary, not a spec: it defines what terms *mean*, not how the code works.

It was seeded by the Territory Battle / Territory War parsing layer ported from
`swgoh_comlink` (see [ADR 0001](docs/adr/0001-port-only-the-parsing-layer.md))
and will grow as other areas of the library are modelled.

## Language

### Activity Events

**Activity Event**:
A game-generated event on a territory channel describing a structural change — a
deploy, a defend, a score change — carrying a localization key and structured
data rather than free text. Distinct from a player chat message, which has a
`message` body.
_Avoid_: log entry, chat message, log event.

**Envelope**:
The outer, always-readable part of an Activity Event — its id, channel, author,
timestamp, and event type — as opposed to the decoded payload it carries. The
envelope survives even when the payload does not. (For how MBot's backend
delivers it on the wire, see [ADR 0002](docs/adr/0002-normalize-event-shape-adapter.md).)
_Avoid_: header, metadata, info block.

**Opaque Payload**:
An Activity Event whose decoded body is unavailable, leaving only the Envelope.
Still attributable to its zone through the channel id, so a correlator can place
it on the map even though its inner detail is lost.
_Avoid_: corrupt event, invalid event, bad payload.

### Territory Battle

**Territory Activity**:
One player's scored contribution to a Territory Battle zone — a deploy, recon,
covert, or strike — carrying contribution and lineage but no attacker, defender,
or win/loss. The TB counterpart to a Battle, but looser.
_Avoid_: TB battle, TB event, contribution event.

**Parent Zone**:
The conflict zone where a Territory Activity's points land (`zoneId`).
_Avoid_: target zone.

**Source Zone**:
The child zone a Territory Activity originated from (`sourceZoneId`). An empty
source zone means a Direct Deploy.
_Avoid_: origin zone, from zone.

**Direct Deploy**:
A Territory Activity with no Source Zone — deployed straight to the Parent Zone.

**Structural Activity**:
A Territory Activity whose localization key is `EMPTY` — a pure score or
structure change with no player-facing message.

### Territory War

**Battle**:
One Attacker's assault on one defending squad in one zone during one lock
episode. Keyed by zone + squad + episode — never by attacker or player.
_Avoid_: attack, fight, engagement.

**Attacker**:
The player who assaulted a defending squad (the lock's author). Never the
squad's owner.
_Avoid_: aggressor, opponent.

**Defender**:
The owner of the defending squad (`warSquad`).
_Avoid_: owner, holder.

**Held**:
A squad's own running count of successful defends, including defends that
happened before observation began. A property of the squad, not of any one
Battle.
_Avoid_: defend count, defends, kills.

**Repulse**:
The attributable form of a successful defend — a lock that ended with the squad
still standing (lock → available).
_Avoid_: successful defense, hold, win.

**Orphaned Win**:
A Battle whose win was observed but whose opening was not. Provisional and
repairable when the opening arrives later.

**Obscured**:
A Battle whose opening was observed but whose close was not. Provisional and
repairable when the close arrives later.

**Battle Outcome**:
Which ends of a Battle were observed — Won, Repulse, Orphaned Win, or Obscured.
A record of *observation*, not of what "really" happened (see
[ADR 0003](docs/adr/0003-tw-loss-model.md)).
_Avoid_: result, status, verdict.

### Pre-existing territory terms (leaderboard domain)

These predate the parsing layer and belong to the leaderboard/definition domain,
which is separate from the Activity Event domain above.

**Territory War Score**:
A guild's cumulative TW banner total, summed across zones (`calc_tw_score_total`).
Not the same as a Battle's score, which is a single zone's running tally.

**Definition Id**:
The stable identifier for a leaderboard or event definition (`TerritoryWarDefId`,
`TerritoryBattleDefId`, `GuildRaidDefId`).
_Avoid_: def id string, leaderboard key.
