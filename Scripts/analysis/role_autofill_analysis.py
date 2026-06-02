import collections
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

def analyze_full_h2(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. PRE-CALCULATE MAIN ROLES
    # We create a map: {puuid: 'MOST_PLAYED_ROLE'}
    print(f"--- 🛠 Processing {db_path}: Building Role Map ---")
    player_role_history = collections.defaultdict(list)
    
    cursor.execute("SELECT data FROM matches")
    all_matches = cursor.fetchall()
    
    for row in all_matches:
        try:
            m_json = row[0].replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(m_json)
            for p in data['info']['participants']:
                if p.get('teamPosition'):
                    player_role_history[p['puuid']].append(p['teamPosition'])
        except:
            continue

    # Identify the 'Main' for every player discovered [cite: 108]
    main_role_map = {}
    for puuid, roles in player_role_history.items():
        if len(roles) >= 3: # Only include players with a history
            main_role_map[puuid] = collections.Counter(roles).most_common(1)[0][0]

    # 2. AUDIT MATCHES FOR AUTOFILL [cite: 90, 94]
    print(f"--- 🔍 Auditing {len(all_matches):,} matches for Autofill events ---")
    total_audited_players = 0
    autofill_events = 0

    for row in all_matches:
        try:
            m_json = row[0].replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(m_json)
            for p in data['info']['participants']:
                puuid = p['puuid']
                actual_role = p.get('teamPosition')
                
                # If we know their 'Main', check if they were autofilled [cite: 108]
                if puuid in main_role_map and actual_role:
                    total_audited_players += 1
                    if actual_role != main_role_map[puuid]:
                        autofill_events += 1
        except:
            continue

    # 3. REPORT FINAL NUMBERS [cite: 86]
    if total_audited_players > 0:
        rate = (autofill_events / total_audited_players) * 100
        print(f"\n--- 📊 {db_path.upper()} FINAL ROLE RESULTS ---")
        print(f"Total Matches Processed: {len(all_matches):,}")
        print(f"Unique Players with History: {len(main_role_map):,}")
        print(f"Total Role Assignments Audited: {total_audited_players:,}")
        print(f"Confirmed Autofill Events: {autofill_events:,}")
        print(f"GLOBAL AUTOFILL RATE: {rate:.2f}%")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    data_root = get_data_root()
    analyze_full_h2(str(resolve_database_path('me1', data_root)))
    analyze_full_h2(str(resolve_database_path('euw1', data_root)))
