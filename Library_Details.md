# Mhanndalorian_Bot

----

### Logging

`mhanndalorina_bot` leverages the Python standard `logging` library to output `DEBUG` level messages at various places.

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
DEBUG [2025-02-08 11:50:15] mbot - 'api-key' header removed
DEBUG [2025-02-08 11:50:15] mbot - 'x-timestamp' header set to 1739033415926
DEBUG [2025-02-08 11:50:15] mbot - Using API key from container class: [******test_key]
DEBUG [2025-02-08 11:50:15] mbot - HMAC Hexdigest (base): 471cbc5e2edb306e5d3ea5e6c801ebb1d3019553f45156eadc0b4f84c58447a2
DEBUG [2025-02-08 11:50:15] mbot - HMAC Hexdigest (timestamp): 5429500b345af17cf253e49379287ff7e4f4de9acb073c5599565d48317920b6
DEBUG [2025-02-08 11:50:15] mbot - HMAC Hexdigest (HTTP method): efa0c3c690bdab389a791c0d79ee46e9437c594805513ccdd94ed22ab1ec85e4
DEBUG [2025-02-08 11:50:15] mbot - HMAC Hexdigest (endpoint): 3f6a25a739de719ffa224f3cb66cc8b1d8b5d2c4ca032583ceecd39b614cfd66
DEBUG [2025-02-08 11:50:15] mbot - Payload string: {"payload":{"allyCode":"123456789"}}
DEBUG [2025-02-08 11:50:15] mbot - Payload hash digest: 4372ba9c10d1b7c387a2c490c5c510f4
DEBUG [2025-02-08 11:50:15] mbot - HMAC Hexdigest (payload): 91fb5b72a92ce80c1cb410dac47896bcfb599c460afe00e86ac880252a9950d8
DEBUG [2025-02-08 11:50:15] mbot - HTTP client headers updated with HMAC signature: Headers({'accept': '*/*', 'accept-encoding': 'gzip, deflate, br, zstd', 'connection': 'keep-alive', 'user-agent': 'python-httpx/0.28.1', 'content-type': 'application/json', 'x-timestamp': '1739033415926', 'authorization': '[secure]'})
```

### Library Details

There are extensive descriptions of each of the methods and public facing functions within the `mhanndalorian_bot`
library.

From the Python interactive console, the builtin `help()` function can be used to access the details of the library,
modules, and methods.

#### API Module

```python
>>> help(API)

Help on class API in module mhanndalorian_bot.api:

class API(mhanndalorian_bot.base.MBot)
 |  API(
 |      api_key: 'str',
 |      allycode: 'str',
 |      *,
 |      api_host: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = True
 |  )
 |
 |  Container class for MBot module to facilitate interacting with Mhanndalorian Bot authenticated
 |  endpoints for SWGOH. See https://mhanndalorianbot.work/api.html for more information.
 |
 |  Method resolution order:
 |      API
 |      mhanndalorian_bot.base.MBot
 |      builtins.object
 |
 |  Methods defined here:
 |
 |  fetch_data(
 |      self,
 |      endpoint: 'str | EndPoint',
 |      *,
 |      method: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = None
 |  ) -> 'Dict[Any, Any]'
 |      Return data from the provided API endpoint using standard synchronous HTTP requests
 |
 |      Args
 |          endpoint: API endpoint as a string or EndPoint enum
 |
 |      Keyword Args
 |          method: HTTP method as a string, defaults to POST
 |          hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
 |
 |      Returns
 |          Dictionary from JSON response, if found.
 |
 |  async fetch_data_async(
 |      self,
 |      endpoint: 'str | EndPoint',
 |      *,
 |      method: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = None
 |  ) -> 'Dict[Any, Any]'
 |      Return data from the provided API endpoint using asynchronous HTTP requests
 |
 |      Args
 |          endpoint: API endpoint as a string or EndPoint enum
 |
 |      Keyword Args
 |          method: HTTP method as a string, defaults to POST
 |          hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
 |
 |      Returns
 |          httpx.Response object
 |
 |  ----------------------------------------------------------------------
 |  Methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  __init__(
 |      self,
 |      api_key: 'str',
 |      allycode: 'str',
 |      *,
 |      api_host: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = True
 |  )
 |      Initialize self.  See help(type(self)) for accurate signature.
 |
 |  get_api_key(self)
 |      Return masked API key for logging purposes.
 |
 |  set_allycode(self, allycode: 'str')
 |      Set the allycode value for the container class and update relevant attributes
 |
 |  set_api_key(self, api_key: 'str')
 |      Set the api_key value for the container class and update relevant attributes (including headers)
 |
 |  sign(
 |      self,
 |      method: 'str',
 |      endpoint: 'str | EndPoint',
 |      payload: 'dict[str, Any] | Sentinel' = <NotSet>,
 |      *,
 |      timestamp: 'str' = None,
 |      api_key: 'str' = None
 |  ) -> 'None'
 |      Create HMAC signature for request
 |
 |      Args
 |          method: HTTP method as a string
 |          endpoint: API endpoint path as a string or EndPoint enum instance
 |          payload: Dictionary containing API endpoint payload data.
 |                   This will be converted to a JSON string and hashed.
 |                   If no payload is provided, a default containing the currently set allyCode will be used.
 |
 |      Keyword Args
 |          timestamp: Optional timestamp string to use instead of generating a new one. (primarily for testing)
 |          api_key: Optional API key to use instead of the one set in the container class. (primarily for testing)
 |
 |  ----------------------------------------------------------------------
 |  Class methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  set_api_host(api_host: 'str')
 |      Set the api_host value for the container class and update relevant attributes
 |
 |  set_client(**kwargs: 'Any')
 |      Set the client values for the container class and update relevant attributes
 |
 |  ----------------------------------------------------------------------
 |  Static methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  cleanse_allycode(allycode: 'str') -> 'str'
 |      Remove any dashes from provided string and verify the result contains exactly 9 digits
 |
 |  cleanse_discord_id(discord_id: 'str') -> 'str'
 |      Validate that discord ID is an 18 character string of only numerical digits
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors inherited from mhanndalorian_bot.base.MBot:
 |
 |  allycode
 |
 |  api_key
 |
 |  debug
 |
 |  hmac
 |
 |  ----------------------------------------------------------------------
 |  Data and other attributes inherited from mhanndalorian_bot.base.MBot:
 |
 |  aclient = <httpx.AsyncClient object>
 |
 |  api_host = 'https://mhanndalorianbot.work'
 |
 |  client = <httpx.Client object>
```

#### Registry Module

```python
 >>> help(Registry)
 Help on class Registry in module mhanndalorian_bot.registry:

class Registry(mhanndalorian_bot.base.MBot)
 |  Registry(
 |      api_key: 'str',
 |      allycode: 'str',
 |      *,
 |      api_host: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = True
 |  )
 |
 |  Container class for MBot module to facilitate interacting with Mhanndalorian Bot SWGOH player registry
 |
 |  Method resolution order:
 |      Registry
 |      mhanndalorian_bot.base.MBot
 |      builtins.object
 |
 |  Methods defined here:
 |
 |  fetch_player(self, allycode: 'str', *, hmac: 'bool') -> 'Dict[Any, Any] | None'
 |      Return player data from the provided allycode
 |
 |      Args
 |          allycode: Player allycode as a string.
 |
 |      Keyword Args
 |          hmac: Boolean flag to indicate use of HMAC request signing.
 |
 |      Returns
 |          Dictionary from JSON response, if found. Else None.
 |
 |  async fetch_player_async(self, allycode: 'str', *, hmac: 'bool') -> 'Dict[Any, Any] | None'
 |      Return player data from the provided allycode
 |
 |      Args
 |          allycode: Player allycode as a string.
 |
 |      Keyword Args
 |          hmac: Boolean flag to indicate use of HMAC request signing.
 |
 |      Returns
 |          Dictionary from JSON response, if found. Else None.
 |
 |  register_player(self, discord_id: 'str', allycode: 'str', *, hmac: 'bool') -> 'Dict[str, Any]'
 |      Register a player in the registry
 |
 |      Args
 |          discord_id: Discord user ID as a string
 |          allycode: Player allycode as a string
 |
 |      Keyword Args
 |          hmac: Boolean flag to indicate use of HMAC request signing.
 |
 |      Returns
 |          Dict containing `unlockedPlayerPortrait` and `unlockedPlayerTitle` keys, if successful
 |
 |  async register_player_async(self, discord_id: 'str', allycode: 'str', *, hmac: 'bool') -> 'Dict[Any, Any]'
 |      Register a player in the registry
 |
 |      Args
 |          discord_id: Discord user ID as a string.
 |          allycode: Player allycode as a string.
 |
 |      Keyword Args
 |          hmac: Boolean flag to indicate use of HMAC request signing.
 |
 |      Returns
 |          Dict containing `unlockedPlayerPortrait` and `unlockedPlayerTitle` keys, if successful.
 |
 |  verify_player(
 |      self,
 |      discord_id: 'str',
 |      allycode: 'str',
 |      *,
 |      primary: 'bool' = False,
 |      hmac: 'bool'
 |  ) -> 'bool'
 |      Perform player portrait and title verification after register_player() has been called.
 |
 |      Args
 |          discord_id: Discord user ID as a string.
 |          allycode: Player allycode as a string.
 |
 |      Keyword Args
 |          primary: Boolean indicating whether this allycode should be used as the primary for the discord ID
 |                      in cases where multiple allycodes are registered to the same discord ID.
 |          hmac: Boolean flag to indicate use of HMAC request signing.
 |
 |      Returns
 |          True if successful, False otherwise
 |
 |  async verify_player_async(
 |      self,
 |      discord_id: 'str',
 |      allycode: 'str',
 |      *,
 |      primary: 'bool' = False,
 |      hmac: 'bool' = False
 |  ) -> 'bool'
 |      Perform player portrait and title verification
 |
 |      Args
 |          discord_id: Discord user ID as a string
 |          allycode: Player allycode as a string
 |
 |      Keyword Args
 |          primary: Boolean indicating whether this allycode should be used as the primary for the discord ID
 |                      in cases where multiple allycodes are registered to the same discord ID
 |          hmac: Boolean flag to indicate use of HMAC request signing. Default: False.
 |
 |      Returns
 |          True if successful, False otherwise
 |
 |  ----------------------------------------------------------------------
 |  Methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  __init__(
 |      self,
 |      api_key: 'str',
 |      allycode: 'str',
 |      *,
 |      api_host: 'Optional[str]' = None,
 |      hmac: 'Optional[bool]' = True
 |  )
 |      Initialize self.  See help(type(self)) for accurate signature.
 |
 |  get_api_key(self)
 |      Return masked API key for logging purposes.
 |
 |  set_allycode(self, allycode: 'str')
 |      Set the allycode value for the container class and update relevant attributes
 |
 |  set_api_key(self, api_key: 'str')
 |      Set the api_key value for the container class and update relevant attributes (including headers)
 |
 |  sign(
 |      self,
 |      method: 'str',
 |      endpoint: 'str | EndPoint',
 |      payload: 'dict[str, Any] | Sentinel' = <NotSet>,
 |      *,
 |      timestamp: 'str' = None,
 |      api_key: 'str' = None
 |  ) -> 'None'
 |      Create HMAC signature for request
 |
 |      Args
 |          method: HTTP method as a string
 |          endpoint: API endpoint path as a string or EndPoint enum instance
 |          payload: Dictionary containing API endpoint payload data.
 |                   This will be converted to a JSON string and hashed.
 |                   If no payload is provided, a default containing the currently set allyCode will be used.
 |
 |      Keyword Args
 |          timestamp: Optional timestamp string to use instead of generating a new one. (primarily for testing)
 |          api_key: Optional API key to use instead of the one set in the container class. (primarily for testing)
 |
 |  ----------------------------------------------------------------------
 |  Class methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  set_api_host(api_host: 'str')
 |      Set the api_host value for the container class and update relevant attributes
 |
 |  set_client(**kwargs: 'Any')
 |      Set the client values for the container class and update relevant attributes
 |
 |  ----------------------------------------------------------------------
 |  Static methods inherited from mhanndalorian_bot.base.MBot:
 |
 |  cleanse_allycode(allycode: 'str') -> 'str'
 |      Remove any dashes from provided string and verify the result contains exactly 9 digits
 |
 |  cleanse_discord_id(discord_id: 'str') -> 'str'
 |      Validate that discord ID is an 18 character string of only numerical digits
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors inherited from mhanndalorian_bot.base.MBot:
 |
 |  allycode
 |
 |  api_key
 |
 |  debug
 |
 |  hmac
 |
 |  ----------------------------------------------------------------------
 |  Data and other attributes inherited from mhanndalorian_bot.base.MBot:
 |
 |  aclient = <httpx.AsyncClient object>
 |
 |  api_host = 'https://mhanndalorianbot.work'
 |
 |  client = <httpx.Client object>
```

#### EndPoint Enum Class

The `EndPoint` Enumn class is provided as a helper to indicate which endpoint requests should be executed against.
Any method that has a `endpoint` parameter, either a `str` or `EndPoint` Enum member can be used.

For example, the `fetch_data()` method in the `API` module takes a required positional `endpoint` argument. The
following two variations are functionally equivalent:

```python
>>> api.fetch_data(EndPoint.INVENTORY)
>>>
>>> api.fetch_data("inventory")
```

```python
>>> help(EndPoint)
 
Help on class EndPoint in module mhanndalorian_bot.attrs:

class EndPoint(enum.Enum)
 |  EndPoint(*values)
 |
 |  Enum class for MBot API endpoints
 |
 |  Method resolution order:
 |      EndPoint
 |      enum.Enum
 |      builtins.object
 |
 |  Data and other attributes defined here:
 |
 |  EVENTS = <EndPoint.EVENTS: 'events'>
 |
 |  FETCH = <EndPoint.FETCH: 'database'>
 |
 |  GAC = <EndPoint.GAC: 'gac'>
 |
 |  INVENTORY = <EndPoint.INVENTORY: 'inventory'>
 |
 |  RAID = <EndPoint.RAID: 'activeraid'>
 |
 |  REGISTER = <EndPoint.REGISTER: 'comlink'>
 |
 |  TB = <EndPoint.TB: 'tb'>
 |
 |  TBLOGS = <EndPoint.TBLOGS: 'tblogs'>
 |
 |  TW = <EndPoint.TW: 'tw'>
 |
 |  TWLEADERBOARD = <EndPoint.TWLEADERBOARD: 'twleaderboard'>
 |
 |  TWLOGS = <EndPoint.TWLOGS: 'twlogs'>
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors inherited from enum.Enum:
 |
 |  name
 |      The name of the Enum member.
 |
 |  value
 |      The value of the Enum member.
 |
 |  ----------------------------------------------------------------------
 |  Static methods inherited from enum.EnumType:
 |
 |  __contains__(value)
 |      Return True if `value` is in `cls`.
 |
 |      `value` is in `cls` if:
 |      1) `value` is a member of `cls`, or
 |      2) `value` is the value of one of the `cls`'s members.
 |
 |  __getitem__(name)
 |      Return the member matching `name`.
 |
 |  __iter__()
 |      Return members in definition order.
 |
 |  __len__()
 |      Return the number of members (no aliases)
 |
 |  ----------------------------------------------------------------------
 |  Readonly properties inherited from enum.EnumType:
 |
 |  __members__
 |      Returns a mapping of member name->value.
 |
 |      This mapping lists all enum members, including aliases. Note that this
 |      is a read-only view of the internal mapping.
```