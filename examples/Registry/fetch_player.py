"""
Example script to fetch a player from the player registry

`database` is a non-authenticated endpoint, so this does not touch the player's game session.
"""

from mhanndalorian_bot import APIResponseError, Registry, ValidationError

# The context manager closes the underlying httpx clients on exit.
try:
    with Registry(
        api_key="YOUR_API_KEY",
        allycode="YOUR_ALLYCODE",
        discord_id="PLAYER_DISCORD_ID",
    ) as mbot:
        player_result = mbot.fetch_player(allycode="PLAYER_ALLYCODE")
except ValidationError as exc:
    # Raised before any request is sent -- e.g. a malformed allycode or Discord ID.
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"Registry error {exc.status_code}: {exc.response_text}") from exc

if player_result:
    print(player_result)
else:
    print("Player not found")
