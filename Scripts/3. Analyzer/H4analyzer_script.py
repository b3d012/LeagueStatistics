import sqlite3
import numpy as np
from datetime import datetime
import os

# Numerical mapping logic included directly [cite: 191]
RANK_MAP = {
    'IRON': 0, 'BRONZE': 4, 'SILVER': 8, 'GOLD': 12, 
    'PLATINUM': 16, 'EMERALD': 20, 'DIAMOND': 24, 'MASTER': 28
}
DIV_MAP = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

def get_numerical_rank(tier, rank):
    if tier == "UNRANKED" or tier not in RANK_MAP: return None
    return RANK_MAP[tier] + DIV_MAP.get(rank, 0)

def analyze_temporal_fairness(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n--- 🕒 Temporal Analysis: {db_path.upper()} ---")
    cursor.execute("SELECT data FROM matches")
    matches = cursor.fetchall()
    
    hourly_data = {i: [] for i in range(24)}

    for row in matches:
        try:
            # Clean JSON for parsing [cite: 158, 159]
            m_json = row[0].replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(m_json)
            
            # Extract hour from timestamp
            timestamp = data['info']['gameStartTimestamp'] / 1000
            match_hour = datetime.fromtimestamp(timestamp).hour
            
            ranks = []
            for p in data['info']['participants']:
                cursor.execute("SELECT tier, rank FROM players WHERE puuid = ?", (p['puuid'],))
                res = cursor.fetchone()
                if res and res[0] and res[0] != "UNRANKED":
                    val = get_numerical_rank(res[0], res[1])
                    if val: ranks.append(val)
            
            if len(ranks) >= 8:
                hourly_data[match_hour].append(np.std(ranks))
        except:
            continue

    print(f"{'Hour':<6} | {'Avg Variance':<12} | {'Match Count':<12}")
    print("-" * 38)
    for hour in sorted(hourly_data.keys()):
        variances = hourly_data[hour]
        if variances:
            avg_v = np.mean(variances)
            print(f"{hour:02d}:00  | {avg_v:<12.2f} | {len(variances):<12,}")
    
    conn.close()

# THIS IS THE PART THAT WAS MISSING: CALLING THE FUNCTION
if __name__ == "__main__":
    analyze_temporal_fairness('league_me1.db')
    analyze_temporal_fairness('league_euw1.db')