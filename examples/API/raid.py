"""
Example script for getting data for the currently active raid

Note: `activeraid` is an *authenticated* endpoint, so this call will break the player's
active game session. See Library_Details.md for the full list.
"""

from mhanndalorian_bot import API, APIResponseError, ValidationError

# The context manager closes the underlying httpx clients on exit.
try:
    with API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE") as mbot:
        raid = mbot.fetch_raid()
except ValidationError as exc:
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}") from exc

"""
Sample output:

>>> raid.keys()
dict_keys(['code', 'data'])

>>> pp(raid['data'], depth=1)
{'expireTime': '1744641010000',
 'guildRewardScore': 420580000,
 'raidId': 'naboo',
 'raidMember': [...]}

The 'raidMember' key contains a list of players in the guild. Each player is represented by a dictionary.

>>> pp(raid['data']['raidMember'][0], depth=1)
{'memberProgress': 5400000,
 'memberRank': 38,
 'playerId': 'XXX'}
>>>
"""
