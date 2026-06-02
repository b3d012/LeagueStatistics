import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from riotwatcher import ApiError, LolWatcher

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
watcher = LolWatcher(API_KEY)

DATA_ROOT = get_data_root()
SEASON_LABEL = get_season_label('current')
START_DATE, END_DATE = get_date_window()
START_TIME = parse_date_to_unix_ms(START_DATE) if START_DATE else None
END_TIME = parse_date_to_unix_ms(END_DATE, end_of_day=True) if END_DATE else None

# Define the two regions you are analyzing
REGIONS = [
    {'platform': 'me1', 'db': str(resolve_database_path('me1', DATA_ROOT)), 'name': 'MIDDLE EAST'},
    {'platform': 'euw1', 'db': str(resolve_database_path('euw1', DATA_ROOT)), 'name': 'EUROPE WEST'}
]

# Shared Global Trackers
start_time = datetime.now()
stats = {reg['platform']: {'done_this_session': 0, 'last_rank': 'N/A', 'total_in_db': 0, 'remaining': 0} for reg in REGIONS}

def setup_columns(db_path):
    """Ensures the database has the rank columns for H1/H2 analysis."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(players)")
    columns = [column[1] for column in cursor.fetchall()]
    
    for col, col_type in [('tier', 'TEXT'), ('rank', 'TEXT'), ('lp', 'INTEGER')]:
        if col not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()

def display_dashboard():
    """Prints a clean metrics dashboard with ETAs every 5 minutes."""
    while True:
        time.sleep(300) # Wait 5 minutes
        uptime = datetime.now() - start_time
        uptime_seconds = uptime.total_seconds()
        
        print(f"\n" + "="*60)
        print(f"📊 MASTER DASHBOARD | Uptime: {str(uptime).split('.')[0]}")
        print("="*60)
        
        for reg in REGIONS:
            p = reg['platform']
            # Live DB check for totals
            conn = sqlite3.connect(reg['db'])
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM players")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM players WHERE tier IS NOT NULL")
            done = cursor.fetchone()[0]
            conn.close()
            
            remaining = total - done
            progress = (done/total)*100 if total > 0 else 0
            
            # Calculate ETA based on current session speed
            speed_per_sec = stats[p]['done_this_session'] / uptime_seconds if uptime_seconds > 0 else 0
            if speed_per_sec > 0 and remaining > 0:
                eta_seconds = remaining / speed_per_sec
                eta_str = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta_str = "Calculating..."

            print(f"📍 {reg['name']} ({p.upper()})")
            print(f"   Progress: {done:,} / {total:,} ({progress:.2f}%)")
            print(f"   Last Rank: {stats[p]['last_rank']}")
            print(f"   Est. Time Remaining: {eta_str}")
            print("-" * 30)
        print("="*60 + "\n")

def enrich_region(platform, db_path):
    """The main enrichment loop for a specific region."""
    setup_columns(db_path)
    # Use check_same_thread=False for multi-threaded SQLite access
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL") # This is the magic fix for "locked" errors
    cursor = conn.cursor()
    
    while True:
        try:
            # Batch process 10 players to optimize disk I/O
            cursor.execute("SELECT puuid FROM players WHERE tier IS NULL LIMIT 10")
            players = cursor.fetchall()
            
            if not players:
                print(f"✅ {platform.upper()} fully enriched!")
                break

            for (puuid,) in players:
                try:
                    # Fetch rank data (1 API Request)
                    league_data = watcher.league.by_puuid(platform, puuid)
                    
                    tier, rank, lp = "UNRANKED", "N/A", 0
                    if league_data:
                        for entry in league_data:
                            if entry['queueType'] == 'RANKED_SOLO_5x5':
                                tier, rank, lp = entry['tier'], entry['rank'], entry['leaguePoints']
                    
                    cursor.execute("UPDATE players SET tier=?, rank=?, lp=? WHERE puuid=?", 
                                   (tier, rank, lp, puuid))
                    
                    # Update global stats for dashboard
                    stats[platform]['last_rank'] = f"{tier} {rank}"
                    stats[platform]['done_this_session'] += 1
                    
                except ApiError as err:
                    if err.response.status_code == 429:
                        wait = int(err.response.headers.get('Retry-After', 10))
                        print(f"⏳ {platform.upper()} Rate Limit: Sleeping {wait}s...")
                        time.sleep(wait)
                    elif err.response.status_code == 403:
                        print(f"❌ {platform.upper()} Key Expired! Update RGAPI key.")
                        return
                    else:
                        time.sleep(2)
            
            conn.commit()

        except Exception as e:
            print(f"⚠ Thread Error ({platform}): {e}")
            time.sleep(5)

if __name__ == "__main__":
    print(f"🚀 Master Enrichment Pipeline Started at {start_time.strftime('%H:%M:%S')}")
    print(f"Season label: {SEASON_LABEL}")
    if START_DATE or END_DATE:
        print(f"Match window: {START_DATE or 'open'} -> {END_DATE or 'open'}")
    
    # Start the Dashboard on a background thread
    threading.Thread(target=display_dashboard, daemon=True).start()

    # Start the ME1 and EUW Enrichment threads
    threads = []
    for reg in REGIONS:
        t = threading.Thread(target=enrich_region, args=(reg['platform'], reg['db']))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
