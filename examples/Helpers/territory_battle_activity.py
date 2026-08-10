"""Type a Territory Battle log into structured contribution activities.

``territory_activities`` turns a ``tblogs`` response into ``TerritoryActivity``
records — one per scored contribution (deploy / recon / covert / strike),
carrying zone lineage, coerced scores, and any recon roster.

Note: `tblogs` is an *authenticated* endpoint, so this call breaks the player's
active game session. See Library_Details.md for the full list.
"""

from mhanndalorian_bot import API, APIResponseError, ValidationError
from mhanndalorian_bot.helpers import territory_activities

try:
    with API(api_key="YOUR_API_KEY", allycode="YOUR_ALLYCODE") as mbot:
        tblogs = mbot.fetch_tblogs()
except ValidationError as exc:
    raise SystemExit(f"Bad input: {exc}") from exc
except APIResponseError as exc:
    raise SystemExit(f"API error {exc.status_code} from {exc.endpoint}: {exc.response_text}") from exc

# By default only the four Territory Battle activity families are typed; pass
# ``types=None`` to type every zone body, or a subset to narrow it.
activities = list(territory_activities(tblogs))
print(f"{len(activities)} territory activities")

for activity in activities[:10]:
    origin = "direct deploy" if activity.is_direct_deploy else f"from {activity.source_zone_id}"
    kind = "structural" if activity.is_structural else activity.message_key
    print(
        f"  {activity.activity_type} zone={activity.zone_id} "
        f"score +{activity.score_delta} (total {activity.score_total}) "
        f"[{origin}] {kind}"
    )
    for unit in activity.units:  # populated only for recon activities
        print(f"      recon unit {unit.unit_id} L{unit.level} T{unit.tier}")

"""
Sample output:

312 territory activities
  TERRITORY_CONFLICT_ACTIVITY zone=..._conflict02 score +1500 (total 42000)
      [from ..._strike04] TERRITORY_CHANNEL_ACTIVITY_STRIKE_LINKED_CONFLICT_CONTRIBUTION
  TERRITORY_RECON_ACTIVITY zone=..._recon01 score +0 (total 0) [direct deploy] structural
      recon unit HERMITYODA L85 T13
  ...
"""
