import requests
from riotwatcher import LolWatcher, ApiError
import time

# 1. SETUP
API_KEY = "RGAPI-5d61bb4a-3913-4c74-99b8-5ab54a3879b4"  # Replace with your 24-hour key
REGION = "europe"              # Options: americas, asia, europe, sea
PLATFORM = "me1"              # Specific platform (e.g., na1, kr, euw1)
GAME_NAME = "b3do"     # Example Player Name
TAG_LINE = "1804"               # Example Tag

headers = {"X-Riot-Token": API_KEY}

def get_data():
    # STEP 1: Get PUUID from Riot ID (Account-V1)
    # Needed because the API uses an encrypted ID, not just a name
    account_url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}"
    account_data = requests.get(account_url, headers=headers).json()
    puuid = account_data['puuid']
    print(f"Found PUUID: {puuid}")

    # STEP 2: Get a list of Match IDs (Match-V5)
    # We filter for 'ranked' games as per your research methodology
    match_list_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type=ranked&start=0&count=5"
    match_ids = requests.get(match_list_url, headers=headers).json()
    print(f"Latest Match IDs: {match_ids}")

    # STEP 3: Get details for one specific match
    if match_ids:
        match_id = match_ids[0]
        details_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_details = requests.get(details_url, headers=headers).json()
        
        # Extracting relevant research data
        info = match_details['info']
        print(f"\n--- Match Analysis ({match_id}) ---")
        print(f"Game Duration: {info['gameDuration'] / 60:.2f} minutes")
        
        for p in info['participants']:
            # This captures the win/loss and position for each of the 10 players
            print(f"Player: {p['summonerName']} | Champion: {p['championName']} | "
                  f"Role: {p['teamPosition']} | Win: {p['win']}")

# Execute the script
get_data()