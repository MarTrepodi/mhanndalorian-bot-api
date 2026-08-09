# Mhanndalorian_Bot

Mhanndalorian_Bot is a Python library for interacting with the SWGOH Mhanndalorian Bot authenticated API and Player Registry endpoints.

See <https://mhanndalorianbot.work/apidocs.html> for the full API reference.

## Installation

Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to install Mhanndalorian_Bot.

```bash
   pip install mhanndalorian-bot
```

----

## Usage

Before accessing the Mhanndalorian Bot APIs you must first register for an `apikey`. Instructions for generating an `apikey` can be found in the [API reference](https://mhanndalorianbot.work/apidocs.html).

### Basic Usage

#### Authenticated API Endpoint Interaction
```python
from mhanndalorian_bot import API, EndPoint

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

resp = mbot.fetch_data(endpoint=EndPoint.INVENTORY)
```

#### Player Registry Interaction
```python
from mhanndalorian_bot import Registry

mbot = Registry(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>, discord_id=<YOUR DISCORD USER ID>)

resp = mbot.fetch_player(allycode=<PLAYER ALLYCODE>)
```

### Credentials from environment variables

Constructor arguments may be omitted when the `MHANN_API_KEY`, `MHANN_ALLYCODE`, and
(optionally) `MHANN_DISCORD_ID` environment variables are set:

```python
from mhanndalorian_bot import API

mbot = API()  # reads MHANN_API_KEY and MHANN_ALLYCODE
```

### Authenticated vs non-authenticated endpoints

The API distinguishes two endpoint groups. **Authenticated** endpoints log in as the registered
player and may interrupt an active in-game session: `tw`, `twlogs`, `twleaderboard`, `tb`,
`tblogs`, `tbleaderboardhistory`, `activeraid`, `gac`, `inventory`, `leaderboard`,
`squadpresets`, `conquest`, and `events`. **Non-authenticated** endpoints (`player`,
`playerarena`, `guild`, `guildleaderboard`, `database`) do not touch the game session.
Programmatically, check `EndPoint.TW.is_authenticated`.

### Error handling

Everything the library raises subclasses `MBotError`, which subclasses `RuntimeError`. Below it
the hierarchy splits in two, and the split matters when you write handlers:

```
RuntimeError
└── MBotError                    every error the library raises
    ├── ValidationError          your input was rejected locally, before any request was sent
    └── APIResponseError         non-200 response  (.status_code, .endpoint, .response_text)
        ├── BadRequestError      400
        ├── AuthenticationError  401 - bad API key or HMAC signature
        └── AuthorizationError   403 - not authorised for this account or endpoint
```

**Only `APIResponseError` and its subclasses carry `status_code` / `endpoint` /
`response_text`.** A `ValidationError` describes a request that never left the client, so it has
no response to report. Catch `APIResponseError` — not `MBotError` — when you intend to read those
attributes:

```python
from mhanndalorian_bot import API, APIResponseError, AuthenticationError, ValidationError

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

try:
    data = mbot.fetch_player(allycode=<PLAYER ALLYCODE>)
except ValidationError as exc:      # bad allycode, count out of range, defId/type mismatch...
    print(f"bad input: {exc}")
except AuthenticationError:         # HTTP 401
    ...
except APIResponseError as exc:     # any other non-200 (400, 403, 5xx, ...)
    print(exc.status_code, exc.endpoint, exc.response_text)
```

`except MBotError:` is still the right catch-all when you only need "something went wrong" and
won't touch response attributes.

#### Upgrading from 0.10.x

`ValidationError` does **not** subclass `ValueError` or `TypeError`. Handlers that previously
caught those around library calls silently stop catching:

```python
# before 0.11.0
try:
    mbot.fetch_player("123-456-789")
except ValueError:
    ...

# 0.11.0 onwards
try:
    mbot.fetch_player("123-456-789")
except ValidationError:
    ...
```

`except RuntimeError:` and `except MBotError:` keep working throughout. A `TypeError` raised by
Python itself against a method signature — an unknown keyword, a missing positional — is a
programming error rather than bad input, and is deliberately still a plain `TypeError`.

Note also that `fetch_player("123-456-789")` now sends `123456789`: per-call allycodes are
cleansed the same way constructor allycodes always were, and one that isn't 9 digits raises
instead of reaching the server.

### Guild leaderboards and player arena

Three leaderboard types require a `def_id`, and each takes it from **its own** enum — the API
constrains the *pairing*, not just the value, so `GuildRaidDefId` is only valid with
`GUILD_RAID_HIGH_WATERMARK`:

| `LeaderboardType` | `def_id` |
|---|---|
| `UNSPECIFIED`, `GUILD_RAID_ALL_COMP_PTS`, `GUILD_GALACTIC_POWER` | none — passing one is rejected |
| `GUILD_TERRITORY_BATTLE_STARS` | `TerritoryBattleDefId` |
| `GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER` | `TerritoryWarDefId` |
| `GUILD_RAID_HIGH_WATERMARK` | `GuildRaidDefId` |

```python
from mhanndalorian_bot import API, GuildRaidDefId, LeaderboardType

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

top_gp = mbot.fetch_guild_leaderboard(LeaderboardType.GUILD_GALACTIC_POWER, count=100)
raid = mbot.fetch_guild_leaderboard(LeaderboardType.GUILD_RAID_HIGH_WATERMARK,
                                    def_id=GuildRaidDefId.RANCOR_DIFF01)

# raw strings work too, exactly like EndPoint
raid = mbot.fetch_guild_leaderboard(LeaderboardType.GUILD_RAID_HIGH_WATERMARK,
                                    def_id="GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01")

# playerarena is also a lightweight allycode <-> playerId translation
profile = mbot.fetch_player_arena(player_id=<PLAYER ID>)
```

`count` must be 1–200. A missing, mismatched, or unexpected `def_id` raises `ValidationError`
locally rather than sending a request the API would reject with a 400.

`fetch_player` and `fetch_player_arena` accept either `allycode` or `player_id` (mutually
exclusive).

Applications approved to act on behalf of other users can pass `user_discord_id=<DISCORD ID>` to
any fetch helper; this forces HMAC signing as the API requires. One caveat worth knowing: the API
spec declares `userDiscordId` for the authenticated endpoints and for `player` / `playerarena`,
but **not** for `guild` / `guildleaderboard`. The library sends it wherever you pass it; whether
the server honours it on those two endpoints is unverified.

### The `enums` flag

Every fetch helper accepts `enums` (default `False`), which selects how the API renders enum
fields in the response:

- `enums=False` → integer values
- `enums=True` → string names

```python
mbot.fetch_inventory()              # enum fields come back as integers
mbot.fetch_inventory(enums=True)    # ...as string names
```

### Timeouts and retries

```python
mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>, timeout=30.0, retries=2)
```

`timeout` (seconds, default 75) applies to every request; `retries` (default 0) retries failed
*connection attempts* only — failed responses are never retried.

### Resource cleanup

`API` and `Registry` hold open HTTP connections. For long-running services use the (async-)context
manager so the underlying client is closed on exit:

```python
from mhanndalorian_bot import API

with API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>) as mbot:
    data = mbot.fetch_inventory()

# async
import asyncio
from mhanndalorian_bot import API

async def main():
    async with API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>) as mbot:
        data = await mbot.fetch_inventory_async()

asyncio.run(main())
```

`close()` / `aclose()` are also available for explicit cleanup outside a `with` block.

### TLS verification

TLS certificate verification uses the system trust store by default. Pass a CA bundle path via
`verify="/path/to/ca.pem"` for custom roots, or `verify=False` to disable verification (NOT
recommended — exposes API keys and signed requests to MITM).

### Advanced Usage

`mhanndalorian_bot` includes `async` methods in both the `API` and `Registry` modules. These are provided to facilitate
usage within
Python scripts that may primarily make use of the `asyncio` (or equivalent) module, such as Discord bots. Since the
Mhanndalorian
web services/APIs deal with SWGOH player registration and data access, it is likely that the primary consumers of those
services
will be bots.

#### Authenticated API Endpoint Interaction

```python
import asyncio
from mhanndalorian_bot import API, EndPoint, MBotError

async def main():
    mbot = API(api_key="super_secret_test_key", allycode="123456789")

    try:
        fetch_data_resp = await mbot.fetch_data_async(EndPoint.INVENTORY)
    except MBotError as exc:
        print(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}")
        return

    if 'inventory' in fetch_data_resp:
        material: list = fetch_data_resp['inventory']['material']
        currency: list = fetch_data_resp['inventory']['currencyItem']
        equipment: list = fetch_data_resp['inventory']['equipment']
        unequipped_mods: list = fetch_data_resp['inventory']['unequippedMod']

if __name__ == '__main__':
    asyncio.run(main())
```

#### Player Registry Interaction

```python
import asyncio
from mhanndalorian_bot import MBotError, Registry

async def main():
    reg = Registry(api_key=<YOUR API KEY>, allycode=<YOUR ALLYCODE>, discord_id=<YOUR DISCORD USER ID>)

    try:
        fetch_resp = await reg.fetch_player_async(allycode=<PLAYER ALLYCODE>)
    except MBotError as exc:
        print(f"Registry error {exc.status_code}: {exc.response_text}")
        return

    player_allycode = fetch_resp['allyCode']
    player_discord_id = fetch_resp['discordId']

if __name__ == '__main__':
    asyncio.run(main())
```

More information can be found
on [GitHub](https://github.com/MarTrepodi/mhanndalorian-bot-api/blob/main/Library_Details.md)