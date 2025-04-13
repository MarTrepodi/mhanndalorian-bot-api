"""
Example script to register a player in the player registry

This register_player() method is used to add a new player to the registry.
It is expected that the fetch_player() method has been called previously and the player
did not exist in the registry.

The register_player() method returns a dictionary indicating.
"""
from mhanndalorian_bot import Registry

mbot = Registry(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE")

player_reg_result = mbot.register_player(discord_id="PLAYER_DISCORD_ID", allycode="PLAYER_ALLYCODE")
