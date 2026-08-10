<!-- insertion marker -->

## [v0.11.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.11.0) - 2026-08-10

<small>[Compare with v0.10.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.10.0...v0.11.0)</small>

### ⚠ BREAKING CHANGES

- **api**: `fetch_data_async` now writes the `enums` flag to `payload.payload.enums` to match
  the synchronous `fetch_data`. Previously it was written to `payload.enums` and silently
  ignored by the server. Callers that relied on this bug (i.e. expected `enums=True` to be
  no-op in async) will see the flag take effect.
- **base**: HTTP clients, headers, and payload state are now **per-instance** instead of
  class-level. Multiple `API`/`Registry` instances in one process no longer clobber each
  other's credentials. Code referencing `MBot.client` at class level must use an instance.
- **registry**: `Registry.fetch_player_async` now raises on non-200 responses (matching the
  sync method) instead of returning an error dict (`{"msg": ..., "reason": ...}`).
- **registry**: `Registry.verify_player` / `verify_player_async` now raise `APIResponseError`
  on non-200 responses instead of logging and returning `False`. A `False` return now
  strictly means "the player is not verified".
- **errors**: non-200 responses raise typed exceptions (`BadRequestError` 400,
  `AuthenticationError` 401, `AuthorizationError` 403, `APIResponseError` otherwise). All
  subclass `MBotError(RuntimeError)`, so existing `except RuntimeError` handlers keep working.
- **errors**: input validation raises **`ValidationError`**, a sibling of `APIResponseError`
  under `MBotError`. It does **not** subclass `ValueError` or `TypeError`, so
  `except ValueError:` / `except TypeError:` around library calls silently stops catching.
  29 raise sites moved. Affects constructors, `cleanse_allycode` / `cleanse_discord_id`,
  `set_api_key` / `set_api_host`, `fetch_player` / `fetch_player_arena` / `fetch_guild` /
  `fetch_guild_leaderboard`, `human_time`, `calc_tw_score_total`, `get_tw_opponent_url`, and
  direct descriptor assignment (which moved from `AttributeError`). `except RuntimeError:` and
  `except MBotError:` keep working. A `TypeError` raised by Python itself against a method
  signature is a programming error, not bad input, and stays a plain `TypeError`.
- **api**: `fetch_player` and `fetch_guild` (+ async twins) **no longer strip the response
  envelope**. They were the only two helpers that ever did. Reach through `["events"]`, and
  `["events"]["guild"]` for guild. The envelope is not uniform across endpoints — `/conquest`
  returns three sibling keys and `/tblogs` two — so there is no single thing to unwrap to, and
  returning it whole is the only rule definable across all 18 endpoints.
- **api**: per-call allycodes are now cleansed like constructor allycodes.
  `fetch_player("123-456-789")` sends `123456789`, and one that is not 9 digits raises instead
  of reaching the server.
- **registry**: `verify_player(primary=...)` defaults to **`None`**, not `False`, and omits the
  key from the payload entirely when `None`. This lets the registry apply its documented
  behaviour — a user with no other registered accounts gets `primary: yes`. The old `False`
  default silently opted first-time users *out* of being primary. Pass `True`/`False` to state
  it explicitly.
- **api**: the five non-authenticated endpoints (`player`, `playerarena`, `guild`,
  `guildleaderboard`, `database`) raise `ValidationError` when no Discord ID is set. **Only the
  exception type changes for affected callers** — the API already rejected those requests with a
  400, verified against the live server, so no working code breaks.

### Security

- Enable TLS certificate verification on the bundled `httpx.Client` and `httpx.AsyncClient`.
  Previously both were constructed with `verify=False`, exposing API keys and signed
  requests to MITM. A new constructor kwarg `verify: bool | str = True` is available for
  callers that genuinely need a custom CA bundle (pass a path) or to opt back into the
  insecure behaviour (`verify=False`, not recommended).
- Redact API keys, allycodes, Discord IDs, and the `Authorization` / `api-key` /
  `x-discord-id` headers from DEBUG logs. The `func_debug_logger` decorator now masks
  sensitive argument names before formatting, and the post-sign header dump in
  `MBot.sign()` masks credentials.
- Restrict `GITHUB_TOKEN` permissions in the release workflow per CodeQL alert.
- `MBot.sign()` no longer logs intermediate or final HMAC hexdigests (the final digest *is*
  the `Authorization` header value) nor the raw payload string at DEBUG level. Only the
  non-reversible payload MD5 digest and the redacted final header set are logged.
- Secrets are masked to at most a **quarter of their length** (`len // 4` trailing characters)
  rather than a fixed last-four. The old rule revealed 4 of a 9-digit allycode and printed a
  4-character secret *in full*. Applied at both leak sites — `utils._redact_value` and
  `MBot.get_api_key()`; a previous partial fix had missed the second.
- `MBot.sign()`'s DEBUG line for a caller-supplied `api_key=` override reported the **container**
  key while labelling it the provided one, so anyone debugging a key mismatch was reading a
  wrong value.

### Bug Fixes

- **api**: `fetch_data_async` now writes the `enums` flag to the correct nested path
  (`payload.payload.enums`), matching the sync method.
- **api**: `fetch_data` and `fetch_data_async` no longer mutate caller-supplied payload
  dictionaries — the payload is deep-copied before the `enums` flag is set.
- **registry**: `Registry.__init__` now forwards `discord_id` to the parent constructor
  directly instead of passing the `None` return value of `set_discord_id()`.
- **ci**: Release workflow installs dependencies via `uv sync --frozen` (the missing
  `requirements.txt` was a leftover from the uv migration), corrects the
  `python3 install git-changelog` typo to use `uv tool run`, and uploads the built
  distributions so the `pypi-publish` job has artifacts to download.
- **api**: `fetch_tb` / `fetch_tb_async` now default `enums=False` like every other helper.
- **api**: an unsigned (`hmac=False`) request issued after a signed one restores the
  plaintext `api-key` header and drops the stale `Authorization` / `x-timestamp` headers;
  previously the credential header was permanently lost after the first signed call.
- **base**: **`x-discord-id` never reached the wire on the api-key path.** The header was
  synced to the httpx clients only as a side effect of HMAC signing, so with `hmac=False` it was
  never sent at all, from any path — constructor or setter. Every header mutator now calls
  `_sync_headers()`. Since the API returns 400 without the header on non-authenticated
  endpoints, those calls could not previously succeed under api-key auth.
- **base**: **`cleanse_discord_id` rejected every Discord account created since ~July 2022.**
  It required exactly 18 digits; snowflakes crossed to 19 on ~2022-07-23, and 17-digit accounts
  predate 2016. Since `Registry` requires a `discord_id`, the registry was unusable for those
  users. Now accepts 17–20 digits — 17 is Discord's launch floor, 20 the ceiling for an
  unsigned 64-bit value.
- **api**: `/guildleaderboard` payloads omitted the required `defId` for leaderboard types 4, 5
  and 6, producing a request the API rejects with a 400. The `oneOf` coupling is now enforced
  client-side.
- **api**: `user_discord_id`, `hmac` and `method` were **silently discarded** by
  `fetch_player` / `fetch_guild`, and not accepted at all by `fetch_player_arena` /
  `fetch_guild_leaderboard`. Four of the five non-authenticated helpers therefore sent unsigned
  requests with no `userDiscordId`. All helpers now forward `**kwargs`; an unknown keyword
  raises `TypeError` instead of vanishing.
- **utils**: `func_timer` and `func_debug_logger` were synchronous wrappers applied to coroutine
  functions, so async DEBUG timings measured coroutine *construction* — microseconds for a
  network round-trip — and `inspect.iscoroutinefunction()` reported `False` for every decorated
  async method. Both are now async-aware. `func_timer` also moved from `time.time()` to
  `time.perf_counter()`.
- **docs**: the README's recommended error handler
  (`except MBotError as exc: print(exc.status_code)`) raised `AttributeError` on any
  `ValidationError`, which carries no response attributes.

### Features

- **api**: `/guildleaderboard` `defId` values are exposed as three enums coupled to their
  leaderboard type — `TerritoryBattleDefId` (type 4), `TerritoryWarDefId` (type 5),
  `GuildRaidDefId` (type 6) — plus `LeaderboardType.def_id_enum` / `.requires_def_id`. One enum
  per type rather than one flat set, so autocomplete only ever offers values legal for the type
  already chosen.
- **api**: calling one of the 13 authenticated endpoints emits **`SessionBreakWarning`**, once
  per endpoint per process. Those endpoints break the player's active Star Wars: Galaxy of
  Heroes session, which matters most for bots polling on a timer. Silence with
  `warnings.filterwarnings("ignore", category=SessionBreakWarning)`.
- **attrs**: `EndPoint.requires_discord_id` and `NON_AUTHENTICATED_ENDPOINTS`, alongside the
  existing `is_authenticated` / `AUTHENTICATED_ENDPOINTS`.
- **base**: the documented `Accept-Encoding: br,gzip,deflate` header is now sent. `httpx[brotli]`
  is a hard dependency so the `br` offer can actually be honoured — verified decoding a real
  brotli response on Python 3.10 through 3.14.
- Add `MBot.close()` / `MBot.aclose()` and (async-)context-manager support
  (`with API(...) as api:` / `async with API(...) as api:`) for explicit HTTP-client
  lifecycle management.
- Add `verify` constructor kwarg and `MBot.set_verify()` method for TLS configuration.
- **api**: new endpoint helpers for full parity with API spec v1.0.1 (all with async twins):
  `fetch_guild_leaderboard` (`/api/guildleaderboard`, with `LeaderboardType` enum, `count`
  1-200 validation, and optional `def_id`), `fetch_player_arena` (`/api/playerarena`), and
  `fetch_events` (`/api/events`).
- **api**: `fetch_player` / `fetch_player_arena` accept `player_id` as a mutually-exclusive
  alternative to `allycode`, matching the live API contract.
- **api**: `fetch_data` / `fetch_data_async` accept `user_discord_id` for applications
  approved to act on behalf of other users; sets `payload.userDiscordId` and forces HMAC
  signing as the API requires. Available from every named helper via `**kwargs`.
- **base**: credentials fall back to the `MHANN_API_KEY`, `MHANN_ALLYCODE`, and
  `MHANN_DISCORD_ID` environment variables when constructor arguments are omitted.
- **base**: new constructor kwargs `timeout` (default 75.0 seconds) and `retries`
  (connection-level retries via httpx transports, default 0).
- **attrs**: new `LeaderboardType` IntEnum, `EndPoint.GUILDLEADERBOARD` / `EndPoint.PLAYERARENA`
  members, `AUTHENTICATED_ENDPOINTS` frozenset, and `EndPoint.is_authenticated` property.
  Docstrings on all session-breaking helpers now carry an explicit warning.
- **errors**: new public exception hierarchy exported from the package root: `MBotError`,
  `APIResponseError` (with `status_code`, `endpoint`, `response_text` attributes),
  `BadRequestError`, `AuthenticationError`, `AuthorizationError`.
- **packaging**: ship a `py.typed` marker (PEP 561) and the `Typing :: Typed` classifier so
  type checkers consume the library's inline annotations.

### Changed

- HMAC signature tracing now short-circuits when DEBUG logging is disabled, avoiding
  repeated `hmac_obj.hexdigest()` state copies in hot paths.
- Type hints modernized to PEP 604 syntax (`str | None` instead of `Optional[str]`,
  `dict[str, Any]` instead of `Dict[str, Any]`); requires Python ≥ 3.10 which the
  package already declared.
- `calc_tw_score_total` accepts any iterable of zone-status dicts and uses a generator
  expression instead of a temporary list inside `sum()`.
- Logging follows Python library best practices: a `NullHandler` is attached to the
  `mhanndalorian_bot` root logger in `__init__.py` so importing the package never
  emits "no handler" warnings; consumers configure handlers / levels on their own
  application loggers. Each module obtains its logger via `logging.getLogger(__name__)`.
- Removed the unused `mhanndalorian_bot.config.Config` class and its sole reference
  from `mhanndalorian_bot.attrs`.
- Removed the dead `mhanndalorian_bot.attrs.DiscordId` descriptor (never used or exported).
- Ruff lint rules broadened to `E, F, I, UP, B` and the whole codebase formatted with
  `ruff format`; both are now enforced in CI (no `continue-on-error`).
- CI test job no longer tolerates failures (`|| true` removed) — the registry tests that
  previously hit the live API are now mocked with `pytest-httpx` — and enforces a
  coverage floor of 80% (currently ~87%).

### Documentation

- `README.md` and `Library_Details.md` document the new `verify` kwarg, the
  context-manager / `close()` / `aclose()` lifecycle helpers, and the redaction
  applied to DEBUG output.
- `examples/Registry/register_player.py` now passes the required `discord_id` to
  `Registry(...)`; previously the example would `TypeError` if run as-is.

## [v0.10.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.10.0) - 2026-01-30

<small>[Compare with v0.9.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.9.0...v0.10.0)</small>

### Features

- add conquest support to API
  methods ([ccd0979](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/ccd097944bec8d4c6234b9926b2ad05dbaed6137)
  by MarTrepodi).

## [v0.9.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.9.0) - 2025-11-15

<small>[Compare with v0.8.1](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.8.1...v0.9.0)</small>

### Bug Fixes

- add discord_id support in bot initialization (
  #2) ([11fa544](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/11fa544b30991aa8767e9c725c30c2cb0bd6d7dc) by
  MarTrepodi).

### Features

- allow flexible kwargs in API
  methods ([1d81014](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/1d810147034afc9f241ec93a8de4eee4a0a4938f)
  by MarTrepodi).
- automate changelog updates in release
  workflow ([5ac0dc9](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/5ac0dc9bb707264b8cf219bd450087b51a22eeb3)
  by MarTrepodi).

## [v0.8.1](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.8.1) - 2025-09-22

<small>[Compare with v0.8.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.8.0...v0.8.1)</small>

### Bug Fixes

- add GITHUB_TOKEN to release
  workflow ([21226d7](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/21226d7511905b17d4431f111df759d9a3ba3be7)
  by MarTrepodi).
- remove global flag from Git user config in
  workflow ([c73cfea](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/c73cfea095910ba42ac58cb2a9b1ce02e03c8053)
  by MarTrepodi).
- set user config in release workflow for
  tagging ([656f1a4](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/656f1a4ca20816d07ca2ae9ec8201f3148287bbb)
  by MarTrepodi).
- add missing 'build' dependency to release
  workflow ([c40d124](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/c40d124965597f8c6679425cd5dd64e815f49631)
  by MarTrepodi).
- correct enums payload nesting in API
  methods ([4bec81e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/4bec81e6673a84022aafc1ab80a1500678ee4c52)
  by MarTrepodi).
- correct nested payload structure in fetch_guild
  methods ([11bcb77](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/11bcb77687d5a95e5b4b2f4052b2c4a3803fc296)
  by MarTrepodi).

### Features

- add TB history
  support ([d019676](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/d019676d55411257d147f049f3f7bf2e6bbe2e5b)
  by MarTrepodi).
- add utility to generate TW opponent
  URL ([f91f01e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/f91f01e410ab9ecdf8258dc263e15cfbe3d2caf6) by
  MarTrepodi).
- add GITHUB_TOKEN to release workflow ([21226d7](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/21226d7511905b17d4431f111df759d9a3ba3be7) by MarTrepodi).
- remove global flag from Git user config in workflow ([c73cfea](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/c73cfea095910ba42ac58cb2a9b1ce02e03c8053) by MarTrepodi).
- set user config in release workflow for tagging ([656f1a4](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/656f1a4ca20816d07ca2ae9ec8201f3148287bbb) by MarTrepodi).
- add missing 'build' dependency to release workflow ([c40d124](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/c40d124965597f8c6679425cd5dd64e815f49631) by MarTrepodi).
- correct enums payload nesting in API methods ([4bec81e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/4bec81e6673a84022aafc1ab80a1500678ee4c52) by MarTrepodi).
- correct nested payload structure in fetch_guild methods ([11bcb77](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/11bcb77687d5a95e5b4b2f4052b2c4a3803fc296) by MarTrepodi).

### Features

- add TB history support ([d019676](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/d019676d55411257d147f049f3f7bf2e6bbe2e5b) by MarTrepodi).
- add utility to generate TW opponent URL ([f91f01e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/f91f01e410ab9ecdf8258dc263e15cfbe3d2caf6) by MarTrepodi).

## [v0.8.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.8.0) - 2025-07-01

<small>[Compare with v0.7.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.7.0...v0.8.0)</small>

### Features

- add support for discord_id in
  fetch_player ([02f16d3](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/02f16d3883a7c6634be3c51536502d959422a5c5)
  by MarTrepodi).
- add support for discord_id in fetch_player ([02f16d3](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/02f16d3883a7c6634be3c51536502d959422a5c5) by MarTrepodi).

## [v0.7.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.7.0) - 2025-06-19

<small>[Compare with v0.6.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.6.0...v0.7.0)</small>

### Features

- add support for GAC
  endpoint ([5cde44e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/5cde44ebc7008c80d605a479d3811157be2d97be)
  by MarTrepodi).
- add support for squad presets
  endpoint ([b31630a](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/b31630aa93fecb3182c9ff0c8ca2f55825d4b6d5)
  by MarTrepodi).
- add support for GAC endpoint ([5cde44e](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/5cde44ebc7008c80d605a479d3811157be2d97be) by MarTrepodi).
- add support for squad presets endpoint ([b31630a](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/b31630aa93fecb3182c9ff0c8ca2f55825d4b6d5) by MarTrepodi).

## [v0.6.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.6.0) - 2025-05-01

<small>[Compare with v0.5.2](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.5.2...v0.6.0)</small>

### Features

- add example scripts and README files for
  usage ([9421572](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/942157202fa58f632b2b3f9aa62aa24f5b6b092d)
  by MarTrepodi).

## [v0.5.2](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.5.2) - 2025-04-13

<small>[Compare with v0.5.1](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.5.1...v0.5.2)</small>

### Features

- add example scripts and README files for
  usage ([63350b7](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/63350b75bf409206bd84a7096dbf9c73aacbf790)
  by MarTrepodi).
- add optional 'enums' parameter to API
  methods ([6c78a07](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/6c78a072bdb1c76e8d37ade5bec88b588f772b62)
  by MarTrepodi).
- add human-readable unix time conversion
  utility ([afb2001](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/afb2001f5ce8672cc3fc3d5c7b0812f50201a859)
  by MarTrepodi).

## [v0.5.1](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.5.1) - 2025-04-13

<small>[Compare with first commit](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/d8ca0c85027fde044efebcfd42923012183ec2d1...v0.5.1)</small>

### Features

- add support for fetching Territory War (TW)
  data ([d829bab](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/d829bab68808069dcc02e430531ea9bd4b0fa792)
  by MarTrepodi).
- enhance player and guild data
  handling ([9f99a24](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/9f99a24470748f54d96e9b6ae64c37446a3ed0bf)
  by MarTrepodi).
- add support for player and guild data
  fetching ([86968ea](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/86968ea93716da5be848042e3af4d5adc336aca8)
  by MarTrepodi).
- configure semantic-release for automated
  versioning ([16ee448](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/16ee448dfbf0380e400b2b0c88e2271ffef13f87)
  by MarTrepodi).
- add new endpoints for TB and raid data
  fetching ([caf9485](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/caf94852f32b1a918e43d66c6ad9180cff2da32b)
  by MarTrepodi).
- add x-discord-id header for Registry
  endpoints ([febde24](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/febde24cc746e5ba8373610182aa54aa0d8aa175)
  by MarTrepodi).

### Code Refactoring

- add input validation and simplify
  logic ([80bef6a](https://github.com/MarTrepodi/mhanndalorian-bot-api/commit/80bef6ab2bdf87ab2351891550bc748f136666c8)
  by MarTrepodi).
