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
`x-discord-id` request headers — are redacted from DEBUG output. API keys are masked to the last
four characters (e.g. `***_key`); headers are replaced with `[REDACTED]`.

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
DEBUG [2026-05-10 11:50:15] mbot - 'api-key' header removed
DEBUG [2026-05-10 11:50:15] mbot - 'x-timestamp' header set to 1746876615926
DEBUG [2026-05-10 11:50:15] mbot - Using API key from container class: [******test_key]
DEBUG [2026-05-10 11:50:15] mbot - HMAC Hexdigest (base): 471cbc5e2edb306e5d3ea5e6c801ebb1d3019553f45156eadc0b4f84c58447a2
DEBUG [2026-05-10 11:50:15] mbot - HMAC Hexdigest (timestamp): 5429500b345af17cf253e49379287ff7e4f4de9acb073c5599565d48317920b6
DEBUG [2026-05-10 11:50:15] mbot - HMAC Hexdigest (HTTP method): efa0c3c690bdab389a791c0d79ee46e9437c594805513ccdd94ed22ab1ec85e4
DEBUG [2026-05-10 11:50:15] mbot - HMAC Hexdigest (endpoint): 3f6a25a739de719ffa224f3cb66cc8b1d8b5d2c4ca032583ceecd39b614cfd66
DEBUG [2026-05-10 11:50:15] mbot - Payload string: {"payload":{"allyCode":"123456789"}}
DEBUG [2026-05-10 11:50:15] mbot - Payload hash digest: 4372ba9c10d1b7c387a2c490c5c510f4
DEBUG [2026-05-10 11:50:15] mbot - HMAC Hexdigest (payload): 91fb5b72a92ce80c1cb410dac47896bcfb599c460afe00e86ac880252a9950d8
DEBUG [2026-05-10 11:50:15] mbot - HTTP client headers updated with HMAC signature: {'content-type': 'application/json', 'api-key': '[REDACTED]', 'x-timestamp': '1746876615926', 'Authorization': '[REDACTED]'}
```

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
- `EndPoint.GUILD` (= `'guild'`)
- `EndPoint.SQUADS` (= `'squadpresets'`)
- `EndPoint.CONQUEST` (= `'conquest'`)
- `EndPoint.FETCH` (= `'database'`) — registry lookup
- `EndPoint.REGISTER` / `EndPoint.VERIFY` (= `'comlink'`) — registry write
