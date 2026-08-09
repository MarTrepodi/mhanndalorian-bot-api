"""
Class definition for SWGOH MHanndalorian Bot API module
"""

from __future__ import annotations

import copy
import logging
from enum import Enum
from typing import Any

from mhanndalorian_bot.attrs import DefId, EndPoint, LeaderboardType
from mhanndalorian_bot.base import MBot
from mhanndalorian_bot.exceptions import ValidationError, raise_for_response
from mhanndalorian_bot.utils import func_timer


def _payload_with_enums(payload: dict[str, Any], enums: bool) -> dict[str, Any]:
    """Return a deep copy of ``payload`` with the ``enums`` flag set under ``payload.payload``.

    Per spec v1.0.1 (``components.requestBodies.*.payload.properties.enums``): ``True`` asks the
    API to return enum fields as string **names**, ``False`` as integer **values** -- not the
    other way round.

    Does not mutate the caller's dictionary.
    """
    new_payload = copy.deepcopy(payload)
    new_payload.setdefault("payload", {})["enums"] = enums
    return new_payload


def _player_identity_payload(allycode: str | None, player_id: str | None, default_allycode: str) -> dict[str, Any]:
    """Build the inner payload for endpoints accepting either an allycode or a player ID.

    The two identifiers are mutually exclusive; falls back to ``default_allycode`` when
    neither is provided. A supplied allycode is cleansed exactly as a constructor allycode
    is, so ``"123-456-789"`` reaches the wire as ``"123456789"`` through either door.
    """
    if allycode and player_id:
        raise ValidationError("allycode and player_id are mutually exclusive; provide only one")
    if player_id:
        if not isinstance(player_id, str):
            raise ValidationError("player_id must be a string")
        return {"playerId": player_id}
    return {"allyCode": API._verify_allycode(allycode) if allycode else default_allycode}


class API(MBot):
    """
    Container class for MBot module to facilitate interacting with Mhanndalorian Bot authenticated
    endpoints for SWGOH. See https://mhanndalorianbot.work/api.html for more information.
    """

    logger = logging.getLogger(__name__)

    @staticmethod
    def _resolve_endpoint(ep: EndPoint | str) -> str:
        """Convert the given endpoint to its string representation."""
        return f"/api/{ep.value}" if isinstance(ep, EndPoint) else f"/api/{ep}"

    @staticmethod
    def _verify_allycode(allycode: str) -> str:
        """Normalise and validate a per-call allycode.

        Delegates to :meth:`MBot.cleanse_allycode` so a per-call allycode is subject to
        exactly the rules a constructor allycode is: dashes stripped, then 9 digits
        required. Previously this checked only "is a non-empty string", so
        ``fetch_player("123-456-789")`` put the dashes on the wire while
        ``API(allycode="123-456-789")`` normalised them away.

        Raises:
            ValidationError: if the value is not a string of 9 digits once dashes are stripped.
        """
        return MBot.cleanse_allycode(allycode)

    @staticmethod
    def _verify_guild_id(guild_id: str) -> str:
        """Verify that the provided guild_id is a string and is not empty.

        Guild IDs are opaque server-issued tokens (spec example: ``B2-VYdu3SEevuO3NTCW52Q``)
        declared only as ``{"type": "string"}`` -- no pattern, length or format. Dashes are
        legitimate content, so there is no cleansing step to mirror here and no format rule
        the spec would support inventing. Non-empty string is the whole contract.

        Raises:
            ValidationError: if the value is not a string, or is empty.
        """
        if not isinstance(guild_id, str):
            raise ValidationError("guild_id must be a string")
        if not guild_id:
            raise ValidationError("guild_id cannot be empty")
        return guild_id

    @func_timer
    def fetch_data(
        self,
        endpoint: EndPoint | str,
        *,
        method: str | None = None,
        hmac: bool | None = None,
        payload: dict[str, Any] | None = None,
        enums: bool = False,
        user_discord_id: str | None = None,
    ) -> dict[Any, Any]:
        """Return data from the provided API endpoint using standard synchronous HTTP requests

        Args
            endpoint: API endpoint as a string or EndPoint enum

        Keyword Args
            method: HTTP method as a string, defaults to POST
            hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
            payload: Dictionary of payload data to be sent with the request, defaults to empty dict.
            enums: How enum fields come back in the response. ``True`` returns them as string
                   **names** (e.g. ``"UNITSTATTYPE_HEALTH"``); ``False`` (the default) returns
                   them as integer **values** (e.g. ``1``).
            user_discord_id: Discord ID of the user the request is made on behalf of. Requires an
                             application approved to act as other users; forces HMAC signing.

        Returns
            Dictionary from JSON response, if found.
        """

        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = _payload_with_enums(payload or self.payload, enums)

        if user_discord_id:
            payload["payload"]["userDiscordId"] = self.cleanse_discord_id(user_discord_id)
            if not is_hmac_signed:
                self.logger.warning("userDiscordId requires HMAC signing; enabling HMAC for this request.")
                is_hmac_signed = True

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                + f"Payload: {payload}"
            )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        result = self.client.post(endpoint, json=payload)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"HTTP request completed - Status: {result.status_code}")

        if result.status_code == 200:
            return result.json()
        raise_for_response(result, endpoint)

    def fetch_tw_leaderboard(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TWLEADERBOARD, **kwargs)

    def fetch_twlogs(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TWLOGS, **kwargs)

    def fetch_tblogs(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TBLOGS, **kwargs)

    def fetch_inventory(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player INVENTORY endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.INVENTORY, **kwargs)

    def fetch_arena(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player squad and fleet arena endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.ARENA, **kwargs)

    def fetch_tb(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TB endpoint for the currently active Territory Battle guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TB, **kwargs)

    def fetch_tb_history(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLEADERBOARDHISTORY endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TBHISTORY, **kwargs)

    def fetch_tw(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TW endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.TW, **kwargs)

    def fetch_raid(self, **kwargs) -> dict[Any, Any]:
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.RAID, **kwargs)

    def fetch_player(self, allycode: str | None = None, *, player_id: str | None = None, **kwargs) -> dict[Any, Any]:
        """Return data from the PLAYER endpoint for the provided allycode or player ID

        Non-authenticated endpoint: does not use the player's EA game session.

        Args
            allycode: Player allycode as a string. Defaults to the instance allycode.

        Keyword Args
            player_id: Player ID as a string, mutually exclusive with allycode.
            **kwargs: Forwarded verbatim to :meth:`fetch_data`, which defines the accepted set
                      (``method``, ``hmac``, ``enums``, ``user_discord_id``). Unknown keywords
                      raise ``TypeError`` there.
        """
        identity = _player_identity_payload(allycode, player_id, self.allycode)
        kwargs.setdefault("enums", False)
        player = self.fetch_data(endpoint=EndPoint.PLAYER, payload={"payload": identity}, **kwargs)

        if isinstance(player, dict) and "events" in player:
            return player["events"]
        return player

    def fetch_guild(self, guild_id: str, **kwargs) -> dict[Any, Any]:
        """Return data from the GUILD endpoint for the provided guild

        Non-authenticated endpoint: does not use the player's EA game session.

        Keyword Args
            **kwargs: Forwarded verbatim to :meth:`fetch_data`, which defines the accepted set
                      (``method``, ``hmac``, ``enums``, ``user_discord_id``). Unknown keywords
                      raise ``TypeError`` there.
        """
        validated_guild_id = self._verify_guild_id(guild_id)
        kwargs.setdefault("enums", False)
        guild = self.fetch_data(endpoint=EndPoint.GUILD, payload={"payload": {"guildId": validated_guild_id}}, **kwargs)

        if isinstance(guild, dict) and "events" in guild and "guild" in guild["events"]:
            return guild["events"]["guild"]
        return guild

    def fetch_squad_presets(self, **kwargs) -> dict[Any, Any]:
        """Return data from the SQUADPRESETS endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.SQUADS, **kwargs)

    def fetch_gac(self, **kwargs) -> dict[Any, Any]:
        """Return data from the GAC endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.GAC, **kwargs)

    def fetch_conquest(self, **kwargs) -> dict[Any, Any]:
        """Return data from the CONQUEST endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.CONQUEST, **kwargs)

    def fetch_events(self, **kwargs) -> dict[Any, Any]:
        """Return data from the EVENTS endpoint listing current and upcoming game events

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.EVENTS, **kwargs)

    def fetch_guild_leaderboard(
        self,
        leaderboard_type: LeaderboardType | int,
        *,
        count: int = 50,
        def_id: DefId | str | None = None,
        **kwargs,
    ) -> dict[Any, Any]:
        """Return data from the GUILDLEADERBOARD endpoint

        Non-authenticated endpoint: does not use the player's EA game session.

        Args
            leaderboard_type: LeaderboardType enum member or its integer value.

        Keyword Args
            count: Number of leaderboard entries to return, between 1 and 200. Default: 50
            def_id: Leaderboard definition ID, as an enum member or its raw string value. Each
                    leaderboard type is coupled to its own enum of legal values:
                    type 4 (GUILD_TERRITORY_BATTLE_STARS) requires a ``TerritoryBattleDefId``,
                    type 5 (GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER) a ``TerritoryWarDefId``,
                    type 6 (GUILD_RAID_HIGH_WATERMARK) a ``GuildRaidDefId``
                    (e.g. ``GuildRaidDefId.RANCOR_DIFF01``). Types 0, 1 and 3 accept no def_id.
            **kwargs: Forwarded verbatim to :meth:`fetch_data`, which defines the accepted set
                      (``method``, ``hmac``, ``enums``, ``user_discord_id``). ``enums`` defaults
                      to False; unknown keywords raise ``TypeError`` there.

        Raises
            ValidationError: if leaderboard_type is not a legal type, count is out of bounds,
                        or def_id is missing, unexpected, or not a legal value for the given
                        leaderboard type.
        """
        payload = self._build_guild_leaderboard_payload(leaderboard_type, count, def_id)
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.GUILDLEADERBOARD, payload=payload, **kwargs)

    def fetch_player_arena(
        self, allycode: str | None = None, *, player_id: str | None = None, **kwargs
    ) -> dict[Any, Any]:
        """Return data from the PLAYERARENA endpoint for the provided allycode or player ID

        Non-authenticated endpoint: does not use the player's EA game session. Also a lightweight
        way to translate between allycode and player ID.

        Args
            allycode: Player allycode as a string. Defaults to the instance allycode.

        Keyword Args
            player_id: Player ID as a string, mutually exclusive with allycode.
            **kwargs: Forwarded verbatim to :meth:`fetch_data`, which defines the accepted set
                      (``method``, ``hmac``, ``enums``, ``user_discord_id``). ``enums`` defaults
                      to False; unknown keywords raise ``TypeError`` there.
        """
        identity = _player_identity_payload(allycode, player_id, self.allycode)
        kwargs.setdefault("enums", False)
        return self.fetch_data(EndPoint.PLAYERARENA, payload={"payload": identity}, **kwargs)

    @staticmethod
    def _resolve_def_id(leaderboard_type: LeaderboardType, def_id: DefId | str | None) -> str | None:
        """Validate ``def_id`` against ``leaderboard_type`` and return its raw string value.

        Enforces the spec's ``oneOf`` coupling: leaderboard types 4, 5 and 6 each require a
        ``defId`` drawn from their own distinct enum, while types 0, 1 and 3 accept none.
        Accepts either an enum member or its raw string value.
        """
        def_id_enum = leaderboard_type.def_id_enum

        if def_id_enum is None:
            if def_id is not None:
                raise ValidationError(
                    f"leaderboard_type {leaderboard_type.name} ({int(leaderboard_type)}) does not "
                    f"accept a def_id, got {def_id!r}"
                )
            return None

        legal = ", ".join(repr(member.value) for member in def_id_enum)

        if def_id is None:
            raise ValidationError(
                f"leaderboard_type {leaderboard_type.name} ({int(leaderboard_type)}) requires a "
                f"def_id from {def_id_enum.__name__}; expected one of: {legal}"
            )

        raw = def_id.value if isinstance(def_id, Enum) else def_id
        if not isinstance(raw, str):
            raise ValidationError(f"def_id must be a {def_id_enum.__name__} member or its string value, got {def_id!r}")

        try:
            return str(def_id_enum(raw).value)
        except ValueError:
            raise ValidationError(
                f"invalid def_id {def_id!r} for leaderboard_type {leaderboard_type.name} "
                f"({int(leaderboard_type)}); expected one of: {legal}"
            ) from None

    @staticmethod
    def _build_guild_leaderboard_payload(
        leaderboard_type: LeaderboardType | int, count: int, def_id: DefId | str | None
    ) -> dict[str, Any]:
        """Validate arguments and build the payload for the GUILDLEADERBOARD endpoint."""
        try:
            leaderboard_type = LeaderboardType(leaderboard_type)
        except ValueError:
            legal_types = ", ".join(f"{member.name} ({int(member)})" for member in LeaderboardType)
            raise ValidationError(
                f"invalid leaderboard_type {leaderboard_type!r}; expected one of: {legal_types}"
            ) from None
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 200:
            raise ValidationError(f"count must be an integer between 1 and 200, got {count!r}")
        inner: dict[str, Any] = {"leaderboardType": int(leaderboard_type), "count": count}
        resolved_def_id = API._resolve_def_id(leaderboard_type, def_id)
        if resolved_def_id is not None:
            inner["defId"] = resolved_def_id
        return {"payload": inner}

    # Async methods
    @func_timer
    async def fetch_data_async(
        self,
        endpoint: str | EndPoint,
        *,
        method: str | None = None,
        hmac: bool | None = None,
        payload: dict[str, Any] | None = None,
        enums: bool = False,
        user_discord_id: str | None = None,
    ) -> dict[Any, Any]:
        """Return data from the provided API endpoint using asynchronous HTTP requests

        Args
            endpoint: API endpoint as a string or EndPoint enum

        Keyword Args
            method: HTTP method as a string, defaults to POST
            hmac: Boolean flag indicating whether the endpoints requires HMAC signature authentication
            payload: Dictionary of payload data to be sent with the request, defaults to empty dict.
            enums: How enum fields come back in the response. ``True`` returns them as string
                   **names** (e.g. ``"UNITSTATTYPE_HEALTH"``); ``False`` (the default) returns
                   them as integer **values** (e.g. ``1``).
            user_discord_id: Discord ID of the user the request is made on behalf of. Requires an
                             application approved to act as other users; forces HMAC signing.

        Returns
            Dictionary from JSON response.
        """
        endpoint = self._resolve_endpoint(endpoint)
        method = (method or "POST").upper()
        is_hmac_signed = hmac if hmac is not None else self.hmac
        payload = _payload_with_enums(payload or self.payload, enums)

        if user_discord_id:
            payload["payload"]["userDiscordId"] = self.cleanse_discord_id(user_discord_id)
            if not is_hmac_signed:
                self.logger.warning("userDiscordId requires HMAC signing; enabling HMAC for this request.")
                is_hmac_signed = True

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"Preparing API call - Endpoint: {endpoint}, Method: {method}, HMAC: {is_hmac_signed}, "
                + f"Payload: {payload}"
            )

        if is_hmac_signed:
            self.logger.debug("HMAC signing is required. Calling 'sign' method.")
            self.sign(method=method, endpoint=endpoint, payload=payload)
        else:
            self._ensure_api_key_header()

        result = await self.aclient.post(endpoint, json=payload)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"HTTP request completed - Status: {result.status_code}")

        if result.status_code == 200:
            return result.json()
        raise_for_response(result, endpoint)

    async def fetch_tw_leaderboard_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLEADERBOARD endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TWLEADERBOARD, **kwargs)

    async def fetch_twlogs_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TWLOGS endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TWLOGS, **kwargs)

    async def fetch_tblogs_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLOGS endpoint for the currently active Territory Battle guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TBLOGS, **kwargs)

    async def fetch_inventory_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player INVENTORY endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.INVENTORY, **kwargs)

    async def fetch_arena_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the player squad and fleet arena endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.ARENA, **kwargs)

    async def fetch_tb_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TB endpoint for the currently active Territory Battle guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TB, **kwargs)

    async def fetch_tb_history_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TBLEADERBOARDHISTORY endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TBHISTORY, **kwargs)

    async def fetch_tw_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the TW endpoint for the currently active Territory War guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.TW, **kwargs)

    async def fetch_raid_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the ACTIVERAID endpoint for the currently active raid guild event

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.RAID, **kwargs)

    async def fetch_player_async(
        self, allycode: str | None = None, *, player_id: str | None = None, **kwargs
    ) -> dict[Any, Any]:
        """Return data from the PLAYER endpoint for the provided allycode or player ID

        Non-authenticated endpoint: does not use the player's EA game session.

        Args
            allycode: Player allycode as a string. Defaults to the instance allycode.

        Keyword Args
            player_id: Player ID as a string, mutually exclusive with allycode.
            **kwargs: Forwarded verbatim to :meth:`fetch_data_async`, which defines the accepted
                      set (``method``, ``hmac``, ``enums``, ``user_discord_id``). Unknown keywords
                      raise ``TypeError`` there.
        """
        identity = _player_identity_payload(allycode, player_id, self.allycode)
        kwargs.setdefault("enums", False)
        player = await self.fetch_data_async(endpoint=EndPoint.PLAYER, payload={"payload": identity}, **kwargs)

        if isinstance(player, dict) and "events" in player:
            return player["events"]
        return player

    async def fetch_guild_async(self, guild_id: str, **kwargs) -> dict[Any, Any]:
        """Return data from the GUILD endpoint for the provided guild

        Non-authenticated endpoint: does not use the player's EA game session.

        Keyword Args
            **kwargs: Forwarded verbatim to :meth:`fetch_data_async`, which defines the accepted
                      set (``method``, ``hmac``, ``enums``, ``user_discord_id``). Unknown keywords
                      raise ``TypeError`` there.
        """
        validated_guild_id = self._verify_guild_id(guild_id)
        kwargs.setdefault("enums", False)
        guild = await self.fetch_data_async(
            endpoint=EndPoint.GUILD, payload={"payload": {"guildId": validated_guild_id}}, **kwargs
        )

        if isinstance(guild, dict) and "events" in guild and "guild" in guild["events"]:
            return guild["events"]["guild"]
        return guild

    async def fetch_squad_presets_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the SQUADPRESETS endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.SQUADS, **kwargs)

    async def fetch_gac_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the GAC endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.GAC, **kwargs)

    async def fetch_conquest_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the CONQUEST endpoint

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.CONQUEST, **kwargs)

    async def fetch_events_async(self, **kwargs) -> dict[Any, Any]:
        """Return data from the EVENTS endpoint listing current and upcoming game events

        Authenticated endpoint: uses the registered player's EA session and may interrupt an
        active game session.
        """
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.EVENTS, **kwargs)

    async def fetch_guild_leaderboard_async(
        self,
        leaderboard_type: LeaderboardType | int,
        *,
        count: int = 50,
        def_id: DefId | str | None = None,
        **kwargs,
    ) -> dict[Any, Any]:
        """Return data from the GUILDLEADERBOARD endpoint

        Non-authenticated endpoint: does not use the player's EA game session.

        Args
            leaderboard_type: LeaderboardType enum member or its integer value.

        Keyword Args
            count: Number of leaderboard entries to return, between 1 and 200. Default: 50
            def_id: Leaderboard definition ID, as an enum member or its raw string value. Each
                    leaderboard type is coupled to its own enum of legal values:
                    type 4 (GUILD_TERRITORY_BATTLE_STARS) requires a ``TerritoryBattleDefId``,
                    type 5 (GUILD_TERRITORY_WAR_OPPONENT_GALACTIC_POWER) a ``TerritoryWarDefId``,
                    type 6 (GUILD_RAID_HIGH_WATERMARK) a ``GuildRaidDefId``
                    (e.g. ``GuildRaidDefId.RANCOR_DIFF01``). Types 0, 1 and 3 accept no def_id.
            **kwargs: Forwarded verbatim to :meth:`fetch_data_async`, which defines the accepted
                      set (``method``, ``hmac``, ``enums``, ``user_discord_id``). ``enums``
                      defaults to False; unknown keywords raise ``TypeError`` there.

        Raises
            ValidationError: if leaderboard_type is not a legal type, count is out of bounds,
                        or def_id is missing, unexpected, or not a legal value for the given
                        leaderboard type.
        """
        payload = self._build_guild_leaderboard_payload(leaderboard_type, count, def_id)
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.GUILDLEADERBOARD, payload=payload, **kwargs)

    async def fetch_player_arena_async(
        self, allycode: str | None = None, *, player_id: str | None = None, **kwargs
    ) -> dict[Any, Any]:
        """Return data from the PLAYERARENA endpoint for the provided allycode or player ID

        Non-authenticated endpoint: does not use the player's EA game session. Also a lightweight
        way to translate between allycode and player ID.

        Args
            allycode: Player allycode as a string. Defaults to the instance allycode.

        Keyword Args
            player_id: Player ID as a string, mutually exclusive with allycode.
            **kwargs: Forwarded verbatim to :meth:`fetch_data_async`, which defines the accepted
                      set (``method``, ``hmac``, ``enums``, ``user_discord_id``). ``enums``
                      defaults to False; unknown keywords raise ``TypeError`` there.
        """
        identity = _player_identity_payload(allycode, player_id, self.allycode)
        kwargs.setdefault("enums", False)
        return await self.fetch_data_async(EndPoint.PLAYERARENA, payload={"payload": identity}, **kwargs)
