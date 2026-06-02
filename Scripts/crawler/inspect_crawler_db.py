import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

def check_db(db_path, region_name):
    if not os.path.exists(db_path):
        print(f"--- ❌ {region_name} database not found at {db_path} ---")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count Matches
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        # Count Players (Total and Crawled)
        cursor.execute("SELECT COUNT(*) FROM players")
        total_players = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM players WHERE crawled = 1")
        crawled_players = cursor.fetchone()[0]
        
        print(f"--- 📊 {region_name} STATUS ---")
        print(f"✅ Total Matches Saved: {match_count:,}")
        print(f"👥 Unique Players Found: {total_players:,}")
        print(f"🕵️  Players Crawled: {crawled_players:,}")
        print(f"📈 Completion: {(match_count/100000)*100:.2f}% of 100k goal")
        print("-" * 25)
        
        conn.close()
    except Exception as e:
        print(f"Error checking {region_name}: {e}")

if __name__ == "__main__":
    data_root = get_data_root()
    check_db(str(resolve_database_path('me1', data_root)), "MIDDLE EAST (ME1)")
    check_db(str(resolve_database_path('euw1', data_root)), "EUROPE WEST (EUW1)")
