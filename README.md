# Mhanndalorian_Bot

Mhanndalorian_Bot is a Python library for interacting with the SWGOH Mhanndalorian Bot authenticated API and Player Registry endpoints.

See https://mhanndalorianbot.work/api.html for more details

## Installation

Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to install Mhanndalorian_Bot.

```bash
   pip install mhanndalorian-bot
```

----

## Usage

Before accessing the Mhanndalorian Bot APIs you must first register for an `apikey`. Instructions for generating an `apikey` can be found [here](https://mhanndalorianbot.work/api.html#api-setup).

### Basic Usage

#### Authenticated API Endpoint Interaction
```python
from mhanndalorian_bot import API, EndPoint

mbot = API(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>)

resp = mbot.fetch_data(endpoint=EndPoint.INVENTORY)
```

#### Player Registry Interaction
```python
from mhanndalorian_bot import Registry

mbot = Registry(api_key=<YOUR APIKEY>, allycode=<YOUR ALLYCODE>, discord_id=<YOUR DISCORD USER ID>)

resp = mbot.fetch_player(allycode=<PLAYER ALLYCODE>)
```

### Advanced Usage

`mhanndalorian_bot` includes `async` methods in both the `API` and `Registry` modules. These are provided to facilitate
usage within
Python scripts that may primarily make use of the `asyncio` (or equivalent) module, such as Discord bots. Since the
Mhanndalorian
web services/APIs deal with SWGOH player registration and data access, it is likely that the primary consumers of those
services
will be bots.

#### Authenticated API Endpoint Interaction

```python
import asyncio
from mhanndalorian_bot import API, EndPoint

async def main():
    mbot = API(api_key="super_secret_test_key", allycode="123456789")
    
    fetch_data_resp = await mbot.fetch_data_async(EndPoint.INVENTORY)

    if isinstance(fetch_data_resp, dict):
        if 'msg' in fetch_data_resp:
            # An unexpected error occurred
            print(f"An unexpected error occurred: {fetch_data_resp}")
        elif 'inventory' in fetch_data_resp:
            material: list = fetch_data_resp['inventory']['material']
            currency: list = fetch_data_resp['inventory']['currencyItem']
            equipment: list = fetch_data_resp['inventory']['equipment']
            unequipped_mods: list = fetch_data_resp['inventory']['unequippedMod']
        else:
            raise RuntimeError("Not sure what happened.")

if __name__ == '__main__':
    asyncio.run(main())
```

#### Player Registry Interaction

```python
import asyncio
from mhanndalorian_bot import Registry

async def main():
    reg = Registry(api_key=<YOUR API KEY>, allycode=<YOUR ALLYCODE>, discord_id=<YOUR DISCORD USER ID>)

    # Returns 'None' if player does not exist in the registry
    fetch_resp = await reg.fetch_player_async(allycode)

    if isinstance(fetch_resp, dict):
        if 'msg' in fetch_resp:
            # An unexpected error occurred
            print(f"An unexpected error occurred: {fetch_resp}")
        else:
            player_allycode = fetch_resp['allyCode']
            player_discord_id = fetch_resp['discordId']

if __name__ == '__main__':
    asyncio.run(main())
```

More information can be found
on [GitHub](https://github.com/MarTrepodi/mhanndalorian-bot-api/tree/main/Library_Details.md)