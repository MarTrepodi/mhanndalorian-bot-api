"""
Example script for getting player inventory data

Note: `inventory` is an *authenticated* endpoint, so this call will break the player's
active game session. See Library_Details.md for the full list.
"""

from mhanndalorian_bot import API, APIResponseError, ValidationError

# The context manager closes the underlying httpx clients on exit. For a short script the
# connections would be reclaimed at process exit anyway, but long-running services
# (Discord bots, daemons) should always use it.
try:
    with API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE") as mbot:
        # enums=True returns enum fields as string names; the default (False) returns integers.
        inventory = mbot.fetch_inventory(enums=True)
except ValidationError as exc:
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}") from exc

# Build a dictionary of all materials
materials = {m["id"]: m["quantity"] for m in inventory["inventory"]["material"]}

# Build a dictionary of all currencies
currency = {c["currency"]: c["quantity"] for c in inventory["inventory"]["currencyItem"]}

# Build a dictionary of all equipment
equipment = {e["id"]: e["quantity"] for e in inventory["inventory"]["equipment"]}

"""
Sample output:

>>> inventory.keys()
dict_keys(['code', 'inventory'])

>>> inventory['inventory'].keys()
dict_keys(['material', 'currencyItem', 'equipment', 'unequippedMod'])

"""
