import os
import sys
from pathlib import Path

from riotwatcher import ApiError, LolWatcher, RiotWatcher

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import require_riot_api_key

API_KEY = require_riot_api_key()

lol_watcher = LolWatcher(API_KEY)
riot_watcher = RiotWatcher(API_KEY)

# Region settings for Middle East
my_platform = os.getenv("RIOT_PLATFORM", 'me1')
my_cluster = os.getenv("RIOT_REGION", 'europe')

def get_me_rank_fixed(game_name, tag_line):
    try:
        # 1. Get PUUID (Always available)
        account = riot_watcher.account.by_riot_id(my_cluster, game_name, tag_line)
        puuid = account['puuid']
        
        # 2. Skip the Summoner-V4 step entirely! 
        # Newer versions of RiotWatcher support getting league entries by PUUID.
        # This avoids the 'id' KeyError.
        league_data = lol_watcher.league.by_puuid(my_platform, puuid)
        
        print(f"--- Data for {game_name}#{tag_line} ---")
        if not league_data:
            print("Player is unranked in all queues.")
        else:
            for entry in league_data:
                if entry['queueType'] == 'RANKED_SOLO_5x5':
                    print(f"Queue: Solo/Duo | Rank: {entry['tier']} {entry['rank']} | LP: {entry['leaguePoints']}")

    except ApiError as err:
        print(f"Error: {err}")
    except KeyError as e:
        print(f"Still missing a field: {e}")

get_me_rank_fixed("b3do", "1804")
