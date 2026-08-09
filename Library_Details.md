# Mhanndalorian_Bot

----

### TLS verification

The bundled `httpx.Client` and `httpx.AsyncClient` verify TLS certificates against the system trust
store by default. If you operate behind a corporate proxy that intercepts TLS with its own CA, pass
a CA bundle path to the constructor:

```python
from mhanndalorian_bot import API

api = API(api_key="...", allycode="...", verify="/etc/ssl/certs/corporate-ca.pem")
```

Verification can also be disabled (NOT recommended — exposes API keys and signed requests to MITM):

```python
api = API(api_key="...", allycode="...", verify=False)
```

You can change the setting after construction with `MBot.set_verify(verify)`.

### Client lifecycle

`API` and `Registry` hold open `httpx` client connections. For short-lived scripts the connections
are reclaimed at process exit, but long-running services (Discord bots, daemons, etc.) should close
them explicitly:

```python
from mhanndalorian_bot import API

with API(api_key="...", allycode="...") as api:
    data = api.fetch_inventory()
# sync client is closed on exit

# async equivalent
import asyncio
from mhanndalorian_bot import API

async def main():
    async with API(api_key="...", allycode="...") as api:
        data = await api.fetch_inventory_async()

asyncio.run(main())
```

`close()` / `aclose()` are also available for callers that manage lifecycle manually.

### Logging

`mhanndalorian_bot` follows Python library logging conventions: each module obtains its own logger
via `logging.getLogger(__name__)`, and the package attaches a `NullHandler` to the
`mhanndalorian_bot` root logger so importing the library is silent until you configure handlers.
The library never calls `logging.basicConfig()` or adds handlers of its own — your application
controls output.

To see DEBUG output, configure logging in your application:

```python
import logging

# Either configure the root logger (catches everything):
logging.basicConfig(level=logging.DEBUG)

# Or target only this package:
logging.getLogger('mhanndalorian_bot').setLevel(logging.DEBUG)
```

Sensitive values — API keys, allycodes, Discord IDs, and the `api-key`, `Authorization`, and
`x-discord-id` request headers — are redacted from DEBUG output. Headers are replaced with
`[REDACTED]`.

Secrets are masked to **at most a quarter of their length** (`len // 4` trailing characters), so
short values reveal nothing and long ones stay distinguishable in a log:

| Secret | Length | Logged as |
|---|---|---|
| `abc` | 3 | `***` |
| `tiny` | 4 | `***y` |
| `123456789` (allycode) | 9 | `***89` |
| `some_test_key` | 13 | `***key` |
| a 40-character API key | 40 | `***` + last 10 |

Prior to 0.11.0 the mask was a fixed last-four, which revealed 4 of a 9-digit allycode and printed
a 4-character secret in full.

For example, the following configuration:

```python
import logging
from mhanndalorian_bot import API, EndPoint

logging.basicConfig(
        format='%(levelname)s [%(asctime)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG
)

api = API(api_key="some_test_key", allycode="123456789")
api.sign(method="POST", endpoint=EndPoint.INVENTORY, payload={"payload": {"allyCode": "123456789"}})
```

Will send the `DEBUG` level output to the console or whatever `stdout` is directed to ...

```
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.utils -   [ function set_api_key() ] called with self, api_key='***key'
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.attrs - Setting '_api_key' to 'some_test_key' for object <mhanndalorian_bot.api.API object at 0x109050980>
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.utils -   [ function set_allycode() ] called with self, allycode='***89'
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.utils -   [ function cleanse_allycode() ] called with allycode='***89'
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.attrs - Setting '_allycode' to '123456789' for object <mhanndalorian_bot.api.API object at 0x109050980>
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.utils -   [ function sign() ] called with self, method='POST', endpoint=<EndPoint.INVENTORY: 'inventory'>, payload={'payload': {'allyCode': '123456789'}}, timestamp='1746876615926'
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.api - 'api-key' header removed
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.api - 'x-timestamp' header set to 1746876615926
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.api - Using API key from container class: [***key]
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.api - Payload hash digest: 4372ba9c10d1b7c387a2c490c5c510f4
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.api - HTTP client headers updated with HMAC signature: {'accept': '*/*', 'connection': 'keep-alive', 'user-agent': 'python-httpx/0.28.1', 'content-type': 'application/json', 'accept-encoding': 'br,gzip,deflate', 'x-timestamp': '1746876615926', 'authorization': '[REDACTED]'}
DEBUG [2026-08-09 18:56:53] mhanndalorian_bot.utils -   [ sign() ] took: 0.000294 seconds
```

Two things to note in that output. The `api-key` header is **absent** from the final header dump:
HMAC signing removes it, because the key itself is never transmitted under that scheme — only the
signature in `Authorization`. And `accept-encoding` carries `br,gzip,deflate` as the API asks;
the `brotli` decoder ships as a required dependency so the `br` offer can actually be honoured.

### API reference

The full method-by-method reference is available from a Python REPL via the `help()` builtin:

```python
>>> from mhanndalorian_bot import API, Registry, EndPoint
>>> help(API)
>>> help(Registry)
>>> help(EndPoint)
```

### EndPoint enum

`EndPoint` is a helper for selecting a target endpoint. Every method that accepts an `endpoint`
parameter takes either an `EndPoint` member or its underlying string value:

```python
>>> api.fetch_data(EndPoint.INVENTORY)
>>> api.fetch_data("inventory")          # equivalent
```

Current members:

- `EndPoint.TW` (= `'tw'`)
- `EndPoint.RAID` (= `'activeraid'`)
- `EndPoint.TWLOGS` (= `'twlogs'`)
- `EndPoint.TWLEADERBOARD` (= `'twleaderboard'`)
- `EndPoint.GAC` (= `'gac'`)
- `EndPoint.INVENTORY` (= `'inventory'`)
- `EndPoint.TB` (= `'tb'`)
- `EndPoint.TBLOGS` (= `'tblogs'`)
- `EndPoint.TBHISTORY` (= `'tbleaderboardhistory'`)
- `EndPoint.EVENTS` (= `'events'`)
- `EndPoint.LEADERBOARD` / `EndPoint.ARENA` (= `'leaderboard'`)
- `EndPoint.PLAYER` (= `'player'`)
- `EndPoint.PLAYERARENA` (= `'playerarena'`)
- `EndPoint.GUILD` (= `'guild'`)
- `EndPoint.GUILDLEADERBOARD` (= `'guildleaderboard'`)
- `EndPoint.SQUADS` (= `'squadpresets'`)
- `EndPoint.CONQUEST` (= `'conquest'`)
- `EndPoint.FETCH` (= `'database'`) — registry lookup
- `EndPoint.REGISTER` / `EndPoint.VERIFY` (= `'comlink'`) — registry write

`ARENA`/`LEADERBOARD` and `REGISTER`/`VERIFY` are intentional aliases, so the enum has 21 members
over 19 distinct slugs. `EndPoint.get_endpoints()` returns member *names* and therefore includes
both spellings; for distinct slugs use `[member.value for member in EndPoint]`.

### Session-breaking endpoints

The API splits its endpoints in two, and the distinction has a user-visible consequence:

- **Authenticated** — logs in as the registered player and **will break that player's active game
  session**: `tw`, `twlogs`, `twleaderboard`, `tb`, `tblogs`, `tbleaderboardhistory`, `activeraid`,
  `gac`, `inventory`, `leaderboard`, `squadpresets`, `conquest`, `events`.
- **Non-authenticated** — leaves the session alone: `player`, `playerarena`, `guild`,
  `guildleaderboard`, `database`.

This matters most for bots polling on a timer: each poll of an authenticated endpoint ejects the
player from the game. Since 0.11.0 the library says so at runtime as well as in the docstrings,
emitting a `SessionBreakWarning` once per endpoint per process. Check before calling:

```python
>>> EndPoint.TW.is_authenticated
True
>>> EndPoint.PLAYER.is_authenticated
False
```

### Exceptions

See the hierarchy and upgrade notes in [README.md](README.md#error-handling). In brief: everything
raised subclasses `MBotError(RuntimeError)`; `ValidationError` covers input rejected locally and
carries no response attributes, while `APIResponseError` and its 400/401/403 subclasses carry
`status_code`, `endpoint`, and `response_text`.
