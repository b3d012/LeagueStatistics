import os
import sys
from pathlib import Path

from riotwatcher import RiotWatcher

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import require_riot_api_key

# Use RiotWatcher (not LolWatcher) for account IDs
rw = RiotWatcher(require_riot_api_key())

region = os.getenv("RIOT_REGION", "europe")
me_game_name = os.getenv("RIOT_ME_GAME_NAME", "b3do")
me_tag_line = os.getenv("RIOT_ME_TAG_LINE", "1804")
eu_game_name = os.getenv("RIOT_EU_GAME_NAME", "manga")
eu_tag_line = os.getenv("RIOT_EU_TAG_LINE", "420")

# For ME1 (Seed with your ME account)
me_acc = rw.account.by_riot_id(region, me_game_name, me_tag_line)
print(f"ME PUUID: {me_acc['puuid']}")

# For EUW (Seed with your EU account)
eu_acc = rw.account.by_riot_id(region, eu_game_name, eu_tag_line)
print(f"EU PUUID: {eu_acc['puuid']}")
