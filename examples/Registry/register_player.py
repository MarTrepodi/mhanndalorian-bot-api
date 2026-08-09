"""
Example script to register a player in the player registry

This register_player() method is used to add a new player to the registry.
It is expected that the fetch_player() method has been called previously and the player
did not exist in the registry.

The register_player() method returns a dictionary indicating the unlocked portrait
and title that the player must apply in SWGOH before verify_player() will succeed.
"""

from mhanndalorian_bot import APIResponseError, Registry, ValidationError

# The context manager closes the underlying httpx clients on exit.
try:
    with Registry(
        api_key="YOUR_API_KEY",
        allycode="YOUR_ALLYCODE",
        discord_id="YOUR_DISCORD_ID",
    ) as mbot:
        player_reg_result = mbot.register_player(
            discord_id="PLAYER_DISCORD_ID",
            allycode="PLAYER_ALLYCODE",
        )
except ValidationError as exc:
    # Raised before any request is sent -- e.g. a malformed allycode or Discord ID.
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"Registry error {exc.status_code}: {exc.response_text}") from exc

print(player_reg_result)
