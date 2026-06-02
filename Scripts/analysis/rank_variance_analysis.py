import os
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

# Map Ranks to Numbers for Math [cite: 89, 109]
RANK_MAP = {
    'IRON': 0, 'BRONZE': 4, 'SILVER': 8, 'GOLD': 12, 
    'PLATINUM': 16, 'EMERALD': 20, 'DIAMOND': 24, 'MASTER': 28
}
DIV_MAP = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

def get_numerical_rank(tier, rank):
    if tier == "UNRANKED" or tier not in RANK_MAP: return None
    return RANK_MAP[tier] + DIV_MAP.get(rank, 0)

def analyze_fairness(db_path):
    # This check ensures we don't accidentally create an empty database file
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at '{db_path}'")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Reading ALL matches from {db_path}...")
    cursor.execute("SELECT match_id, data FROM matches") 
    matches = cursor.fetchall()
    
    match_variances = []

    for m_id, m_json in matches:
        try:
            # Clean boolean/null values for eval parsing
            clean_json = m_json.replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(clean_json) 
            
            participants = data['metadata']['participants']
            
            ranks = []
            for puuid in participants:
                cursor.execute("SELECT tier, rank FROM players WHERE puuid = ?", (puuid,))
                res = cursor.fetchone()
                if res and res[0] and res[0] != "UNRANKED":
                    num_rank = get_numerical_rank(res[0], res[1])
                    if num_rank is not None: 
                        ranks.append(num_rank)
            
            # Hypothesis 1: Measure Rank Disparity [cite: 93]
            if len(ranks) >= 8:
                match_variances.append(np.std(ranks))

        except Exception as e:
            continue

    if match_variances:
        print(f"\n--- 📈 {db_path.upper()} FINAL ANALYSIS ---")
        print(f"Total Matches Analyzed: {len(match_variances):,}")
        print(f"Average Match Rank Variance (Std Dev): {np.mean(match_variances):.2f}")
        print(f"Max Disparity Found: {np.max(match_variances):.2f}")
        print(f"Min Disparity Found: {np.min(match_variances):.2f}")
        print("-" * 50)
    else:
        print(f"No valid ranked matches found in {db_path}.")

    conn.close()

if __name__ == "__main__":
    data_root = get_data_root()
    analyze_fairness(str(resolve_database_path('me1', data_root)))
    analyze_fairness(str(resolve_database_path('euw1', data_root)))
