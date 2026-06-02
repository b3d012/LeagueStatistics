import collections
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

# Numerical mapping logic
RANK_MAP = {'IRON': 0, 'BRONZE': 4, 'SILVER': 8, 'GOLD': 12, 'PLATINUM': 16, 'EMERALD': 20, 'DIAMOND': 24, 'MASTER': 28}
DIV_MAP = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

def get_rank_val(tier, rank):
    if tier == "UNRANKED" or tier not in RANK_MAP: return None
    return RANK_MAP[tier] + DIV_MAP.get(rank, 0)

def analyze_correlation(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"\n--- 📊 Correlation Analysis: {db_path.upper()} ---")
    
    cursor.execute("SELECT data FROM matches")
    matches = cursor.fetchall()
    
    # Pass 1: Build Role Map to identify 'Main' roles
    print("Building Role Map...")
    player_roles = collections.defaultdict(list)
    for row in matches:
        try:
            data = eval(row[0].replace("true", "True").replace("false", "False").replace("null", "None"))
            for p in data['info']['participants']:
                if p.get('teamPosition'):
                    player_roles[p['puuid']].append(p['teamPosition'])
        except: continue

    main_roles = {k: collections.Counter(v).most_common(1)[0][0] for k, v in player_roles.items() if len(v) >= 3}

    # Pass 2: Calculate Rank Variance vs Autofill count per match
    print("Calculating Match Statistics...")
    match_stats = []
    for row in matches:
        try:
            data = eval(row[0].replace("true", "True").replace("false", "False").replace("null", "None"))
            ranks = []
            autofills = 0
            
            for p in data['info']['participants']:
                # Rank logic
                cursor.execute("SELECT tier, rank FROM players WHERE puuid = ?", (p['puuid'],))
                res = cursor.fetchone()
                if res and res[0]:
                    val = get_rank_val(res[0], res[1])
                    if val is not None: ranks.append(val)
                
                # Autofill logic
                if p['puuid'] in main_roles and p.get('teamPosition') != main_roles[p['puuid']]:
                    autofills += 1
            
            if len(ranks) >= 8:
                match_stats.append((np.std(ranks), autofills))
        except: continue

    if match_stats:
        variances, autofill_counts = zip(*match_stats)
        correlation = np.corrcoef(variances, autofill_counts)[0, 1]
        print(f"Total Matches Sampled: {len(match_stats):,}")
        print(f"Correlation Coefficient (r): {correlation:.4f}")
        
        if correlation > 0.3:
            print("Verdict: MODERATE correlation. The system sacrifices both quality and role simultaneously.")
        elif correlation > 0.5:
            print("Verdict: STRONG correlation. High 'System Stress' detected.")
    
    conn.close()

# CRITICAL: This is the trigger that actually runs the code
if __name__ == "__main__":
    data_root = get_data_root()
    analyze_correlation(str(resolve_database_path('me1', data_root)))
    analyze_correlation(str(resolve_database_path('euw1', data_root)))
