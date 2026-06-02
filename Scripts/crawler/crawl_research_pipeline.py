import json
import sqlite3
import sys
import threading
import time
from pathlib import Path

from riotwatcher import LolWatcher, RiotWatcher, ApiError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import (
    get_data_root,
    get_date_window,
    get_season_label,
    parse_date_to_unix_ms,
    require_riot_api_key,
    resolve_database_path,
)

# --- CONFIGURATION ---
API_KEY = require_riot_api_key()
PLATFORM = 'me1'
CLUSTER = 'europe'
SEASON_LABEL = get_season_label('current')
DATA_ROOT = get_data_root()
DB_NAME = str(resolve_database_path(PLATFORM, DATA_ROOT))
START_DATE, END_DATE = get_date_window()
START_TIME = parse_date_to_unix_ms(START_DATE) if START_DATE else None
END_TIME = parse_date_to_unix_ms(END_DATE, end_of_day=True) if END_DATE else None
SEED_GAME_NAME = 'b3do'
SEED_TAG_LINE = '1804'

lol_watcher = LolWatcher(API_KEY)
riot_watcher = RiotWatcher(API_KEY)

def setup_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    curr = conn.cursor()
    
    # 1. Matches Table
    curr.execute('''CREATE TABLE IF NOT EXISTS matches 
                    (match_id TEXT PRIMARY KEY, data TEXT)''')
    
    # 2. Players/Queue Table (Stores Ranks too!)
    curr.execute('''CREATE TABLE IF NOT EXISTS players 
                    (puuid TEXT PRIMARY KEY, 
                     tier TEXT, rank TEXT, lp INTEGER,
                     crawled INTEGER DEFAULT 0)''')
    
    conn.commit()
    return conn

def print_metrics(db_path):
    """Independent metrics reporter - opens its own connection"""
    while True:
        try:
            # Metrics need their own connection in a thread
            m_conn = sqlite3.connect(db_path)
            cursor = m_conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM matches")
            match_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM players WHERE crawled = 1")
            processed_players = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM players WHERE crawled = 0")
            queue_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM players WHERE tier IS NOT NULL")
            players_with_ranks = cursor.fetchone()[0]
            
            print(f"\n--- 📊 {time.strftime('%H:%M:%S')} METRICS UPDATE ---")
            print(f"✅ Total Matches Saved: {match_count}")
            print(f"👤 Players with Rank Data: {players_with_ranks}")
            print(f"📋 Queue List (Remaining): {queue_count}")
            print(f"📈 Total Network Size: {processed_players + queue_count}")
            print(f"----------------------------------\n")
            m_conn.close()
        except Exception as e:
            print(f"Metric error: {e}")
        time.sleep(300)

def crawl():
    conn = setup_db()
    cursor = conn.cursor()

    # Seed check
    cursor.execute("SELECT COUNT(*) FROM players")
    if cursor.fetchone()[0] == 0:
        print("🌱 Seeding database with your account...")
        try:
            me = riot_watcher.account.by_riot_id(CLUSTER, SEED_GAME_NAME, SEED_TAG_LINE)
            cursor.execute("INSERT OR IGNORE INTO players (puuid) VALUES (?)", (me['puuid'],))
            conn.commit()
        except ApiError as e:
            print(f"Seeding failed! Check API Key/Name. Error: {e}")
            return

    # Start Metrics Thread
    metrics_thread = threading.Thread(target=print_metrics, args=(DB_NAME,), daemon=True)
    metrics_thread.start()

    print("🚀 Crawler Active. Press CTRL+C to stop.")

    try:
        while True:
            cursor.execute("SELECT puuid FROM players WHERE crawled = 0 LIMIT 1")
            row = cursor.fetchone()
            if not row:
                print("🏁 Queue empty!")
                break
            
            target_puuid = row[0]
            
            try:
                # 1. GET RANK DATA (Crucial for your 'Fairness' study)
                # We do this first so we have the rank for the player database
                league_entries = lol_watcher.league.by_puuid(PLATFORM, target_puuid)
                tier, rank, lp = "UNRANKED", "N/A", 0
                for entry in league_entries:
                    if entry['queueType'] == 'RANKED_SOLO_5x5':
                        tier, rank, lp = entry['tier'], entry['rank'], entry['leaguePoints']
                
                # Update player record with their rank
                cursor.execute("UPDATE players SET tier=?, rank=?, lp=?, crawled=1 WHERE puuid=?", 
                             (tier, rank, lp, target_puuid))

                # 2. GET MATCHES
                match_ids = lol_watcher.match.matchlist_by_puuid(
                    CLUSTER,
                    target_puuid,
                    queue=420,
                    count=20,
                    start_time=START_TIME,
                    end_time=END_TIME,
                )
                
                for m_id in match_ids:
                    cursor.execute("SELECT 1 FROM matches WHERE match_id = ?", (m_id,))
                    if cursor.fetchone(): continue
                    
                    match_data = lol_watcher.match.by_id(CLUSTER, m_id)
                    
                    # Store Match
                    cursor.execute("INSERT OR IGNORE INTO matches (match_id, data) VALUES (?, ?)", 
                                 (m_id, json.dumps(match_data)))
                    
                    # Add new players to queue
                    for p in match_data['info']['participants']:
                        cursor.execute("INSERT OR IGNORE INTO players (puuid) VALUES (?)", (p['puuid'],))

                conn.commit()
                print(f"✔ Processed: {target_puuid[:8]}... | Rank: {tier} {rank}")
                
            except ApiError as err:
                if err.response.status_code == 429:
                    wait = int(err.response.headers.get('Retry-After', 20))
                    print(f"⏳ Rate Limit. Sleeping {wait}s...")
                    time.sleep(wait)
                elif err.response.status_code == 403:
                    print("❌ API Key Expired.")
                    return
                else:
                    print(f"⚠️ API Error: {err.response.status_code}")
                    # Mark as crawled anyway to skip problematic players
                    cursor.execute("UPDATE players SET crawled=1 WHERE puuid=?", (target_puuid,))

    except KeyboardInterrupt:
        print("\n💾 Progress saved. Shutting down safely.")
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"Running season label: {SEASON_LABEL}")
    print(f"Using database: {DB_NAME}")
    crawl()
