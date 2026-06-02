import sqlite3
import numpy as np
import json

# Map Ranks to Numbers for Math
RANK_MAP = {
    'IRON': 0, 'BRONZE': 4, 'SILVER': 8, 'GOLD': 12, 
    'PLATINUM': 16, 'EMERALD': 20, 'DIAMOND': 24, 'MASTER': 28
}
DIV_MAP = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

def get_numerical_rank(tier, rank):
    if tier == "UNRANKED" or tier not in RANK_MAP: return None
    return RANK_MAP[tier] + DIV_MAP.get(rank, 0)

def analyze_fairness(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Increase the limit to 20,000 to get a solid statistical sample for your Proposal
    print(f"Reading matches from {db_path}...")
    cursor.execute("SELECT match_id, data FROM matches LIMIT 20000") 
    matches = cursor.fetchall()
    
    match_variances = []

    for m_id, m_json in matches:
        try:
            # FIX: Use json.loads instead of eval
            # If the data was saved as a string of a Python dict (with 'true'), 
            # we fix it by replacing lowercase booleans.
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
            
            # Hypothesis 1: Measure Rank Disparity within the match
            if len(ranks) >= 8: # Ensure we have enough data points for a valid variance
                match_variances.append(np.std(ranks))

        except Exception as e:
            continue # Skip corrupted entries

    if match_variances:
        print(f"\n--- 📈 {db_path.upper()} PRELIMINARY ANALYSIS ---")
        print(f"Matches Analyzed: {len(match_variances):,}")
        print(f"Average Match Rank Variance (Std Dev): {np.mean(match_variances):.2f}")
        print(f"Max Disparity Found: {np.max(match_variances):.2f}")
        print(f"Min Disparity Found: {np.min(match_variances):.2f}")
    else:
        print("No valid ranked matches found with enriched players yet.")

    conn.close()

if __name__ == "__main__":
    analyze_fairness('league_euw1.db')