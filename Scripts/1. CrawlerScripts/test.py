import sqlite3
import os

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
    # Update these paths to match your folder structure
    check_db("ME_Crawler/league_me1.db", "MIDDLE EAST (ME1)")
    check_db("EU_Crawler/league_euw1.db", "EUROPE WEST (EUW1)")