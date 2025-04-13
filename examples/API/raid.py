# coding=utf-8
"""
Example script for getting data for the currently active raid
"""
from mhanndalorian_bot import API

mbot = API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE")

raid = mbot.fetch_raid()

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
