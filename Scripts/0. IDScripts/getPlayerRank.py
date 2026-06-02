from riotwatcher import LolWatcher, RiotWatcher, ApiError

# Use your REFRESHED 24-hour key
API_KEY = 'RGAPI-5d61bb4a-3913-4c74-99b8-5ab54a3879b4' 

lol_watcher = LolWatcher(API_KEY)
riot_watcher = RiotWatcher(API_KEY)

# Region settings for Middle East
my_platform = 'me1'
my_cluster = 'europe'

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