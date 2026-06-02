import os
import time
import sys
from pathlib import Path

import requests
from riotwatcher import ApiError, LolWatcher

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import require_riot_api_key

# 1. SETUP
API_KEY = require_riot_api_key()
REGION = os.getenv("RIOT_REGION", "europe")  # Options: americas, asia, europe, sea
PLATFORM = os.getenv("RIOT_PLATFORM", "me1")
GAME_NAME = os.getenv("RIOT_GAME_NAME", "b3do")
TAG_LINE = os.getenv("RIOT_TAG_LINE", "1804")

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
