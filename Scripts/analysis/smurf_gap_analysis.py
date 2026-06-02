import os
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

def analyze_smurf_impact(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"--- 👤 Smurf Impact Analysis: {db_path.upper()} ---")
    cursor.execute("SELECT data FROM matches")
    matches = cursor.fetchall()
    
    high_variance_levels = []
    low_variance_levels = []

    for row in matches:
        try:
            m_json = row[0].replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(m_json)
            
            # 1. Calculate Rank Variance for this match
            ranks = []
            levels = []
            for p in data['info']['participants']:
                levels.append(p['summonerLevel'])
                cursor.execute("SELECT tier, rank FROM players WHERE puuid = ?", (p['puuid'],))
                res = cursor.fetchone()
                if res and res[0] != "UNRANKED":
                    # Simple numerical mapping for speed
                    val = {'IRON':0,'BRONZE':4,'SILVER':8,'GOLD':12,'PLATINUM':16,'EMERALD':20,'DIAMOND':24}.get(res[0], 12)
                    ranks.append(val)
            
            if len(ranks) >= 8:
                variance = np.std(ranks)
                avg_level = np.mean(levels)
                
                # 2. Categorize by Disparity
                if variance > 3.0: # High Disparity Match
                    high_variance_levels.append(avg_level)
                elif variance < 1.0: # Highly Balanced Match
                    low_variance_levels.append(avg_level)
                    
        except: continue

    if high_variance_levels:
        print(f"Avg Level in 'Unfair' Matches: {np.mean(high_variance_levels):.1f}")
        print(f"Avg Level in 'Balanced' Matches: {np.mean(low_variance_levels):.1f}")
        print(f"The 'Smurf Gap': {np.mean(low_variance_levels) - np.mean(high_variance_levels):.1f} levels")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    data_root = get_data_root()
    analyze_smurf_impact(str(resolve_database_path('me1', data_root)))
    analyze_smurf_impact(str(resolve_database_path('euw1', data_root)))
