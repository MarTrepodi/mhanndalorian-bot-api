# Mhanndalorian_Bot

Mhanndalorian_Bot is a Python library for interacting with the SWGOH Mhanndalorian Bot authenticated API and Player Registry endpoints.

See https://mhanndalorianbot.work/api.html for more details

## Installation

Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to install Mhanndalorian_Bot.

```bash
   pip install mhanndalorian-bot
```

----

## Usage

Before accessing the Mhanndalorian Bot APIs you must first register for an `apikey`. Instructions for generating an `apikey` can be found [here](https://mhanndalorianbot.work/api.html#api-setup).

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

Non-200 responses raise typed exceptions carrying `status_code`, `endpoint`, and
`response_text` attributes. All subclass `MBotError`, which subclasses `RuntimeError`:

```python
from mhanndalorian_bot import API, AuthenticationError, MBotError

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

try:
    data = mbot.fetch_inventory()
except AuthenticationError:      # HTTP 401 - bad API key or HMAC signature
    ...
except MBotError as exc:         # any other API error (400, 403, 5xx, ...)
    print(exc.status_code, exc.endpoint)
```

### Guild leaderboards and player arena

```python
from mhanndalorian_bot import API, LeaderboardType

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

top_gp = mbot.fetch_guild_leaderboard(LeaderboardType.GUILD_GALACTIC_POWER, count=100)
raid = mbot.fetch_guild_leaderboard(LeaderboardType.GUILD_RAID_HIGH_WATERMARK,
                                    def_id="GUILD:RAIDS:NORMAL_DIFF:RANCOR:DIFF01")

# playerarena is also a lightweight allycode <-> playerId translation
profile = mbot.fetch_player_arena(player_id=<PLAYER ID>)
```

`fetch_player` and `fetch_player_arena` accept either `allycode` or `player_id` (mutually
exclusive). Applications approved to act on behalf of other users can pass
`user_discord_id=<DISCORD ID>` to any fetch helper; this forces HMAC signing as the API requires.

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