<!-- insertion marker -->

## [v0.11.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/releases/tag/v0.11.0) - 2026-05-10

<small>[Compare with v0.10.0](https://github.com/MarTrepodi/mhanndalorian-bot-api/compare/v0.10.0...v0.11.0)</small>

### ⚠ BREAKING CHANGES

- **api**: `fetch_data_async` now writes the `enums` flag to `payload.payload.enums` to match
  the synchronous `fetch_data`. Previously it was written to `payload.enums` and silently
  ignored by the server. Callers that relied on this bug (i.e. expected `enums=True` to be
  no-op in async) will see the flag take effect.

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

### Features

- Add `MBot.close()` / `MBot.aclose()` and (async-)context-manager support
  (`with API(...) as api:` / `async with API(...) as api:`) for explicit HTTP-client
  lifecycle management.
- Add `verify` constructor kwarg and `MBot.set_verify()` method for TLS configuration.

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
