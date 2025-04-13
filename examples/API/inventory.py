# coding=utf-8
"""
Example script for getting player inventory data
"""
from mhanndalorian_bot import API

mbot = API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE")

inventory = mbot.fetch_inventory(enums=True)

# Build a dictionary of all materials
materials = {m['id']: m['quantity'] for m in inventory['inventory']['material']}

# Build a dictionary of all currencies
currency = {c['currency']: c['quantity'] for c in inventory['inventory']['currencyItem']}

# Build a dictionary of all equipment
equipment = {e['id']: e['quantity'] for e in inventory['inventory']['equipment']}

"""
Sample output:

>>> inventory.keys()
dict_keys(['code', 'inventory'])

>>> inventory['inventory'].keys()
dict_keys(['material', 'currencyItem', 'equipment', 'unequippedMod'])

"""
