import sqlite3
import time
from riotwatcher import LolWatcher, ApiError

# --- CONFIGURATION ---
API_KEY = 'RGAPI-05ee1ae9-81a9-49b1-b89c-128ef1f59da2'
PLATFORM = 'euw1'  # Change to 'euw1' for your EU script
CLUSTER = 'europe' 
DB_NAME = f'league_{PLATFORM}.db'
# ---------------------

watcher = LolWatcher(API_KEY)

def setup_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Matches table: Stores raw JSON data
    cursor.execute('''CREATE TABLE IF NOT EXISTS matches 
                     (match_id TEXT PRIMARY KEY, data TEXT)''')
    # Players table: Just PUUIDs and a "crawled" flag for Phase 1
    cursor.execute('''CREATE TABLE IF NOT EXISTS players 
                     (puuid TEXT PRIMARY KEY, crawled INTEGER DEFAULT 0)''')
    conn.commit()
    return conn

def crawl():
    conn = setup_db()
    cursor = conn.cursor()

    while True:
        try:
            # Get next player who hasn't been crawled
            cursor.execute("SELECT puuid FROM players WHERE crawled = 0 LIMIT 1")
            row = cursor.fetchone()
            if not row:
                print("Queue empty. Add a seed PUUID to the players table.")
                break
            
            target_puuid = row[0]
            
            # PHASE 1: Only get Match IDs (1 Request)
            match_ids = watcher.match.matchlist_by_puuid(CLUSTER, target_puuid, queue=420, count=20)
            
            for m_id in match_ids:
                # NEW FILTER: Ensure the match actually belongs to the target platform
                if not m_id.startswith(PLATFORM.upper()):
                    continue 

                # Check if we already have this match
                cursor.execute("SELECT 1 FROM matches WHERE match_id = ?", (m_id,))
                if cursor.fetchone(): continue


                # Get Match Data (1 Request)
                m_data = watcher.match.by_id(CLUSTER, m_id)
                
                # Save Match & Extract new players to the queue
                cursor.execute("INSERT INTO matches VALUES (?, ?)", (m_id, str(m_data)))
                for p_puuid in m_data['metadata']['participants']:
                    cursor.execute("INSERT OR IGNORE INTO players (puuid) VALUES (?)", (p_puuid,))
                
                print(f"✔ Saved Match: {m_id}")
            
            # Mark player as done
            cursor.execute("UPDATE players SET crawled = 1 WHERE puuid = ?", (target_puuid,))
            conn.commit()

        except ApiError as err:
            if err.response.status_code == 429:
                wait = int(err.response.headers.get('Retry-After', 10))
                print(f"⏳ Rate limited. Sleeping {wait}s...")
                time.sleep(wait)
            elif err.response.status_code == 403:
                print("❌ API Key Expired!")
                break
            else:
                print(f"⚠ Error: {err}")
                time.sleep(5)

if __name__ == "__main__":
    crawl()