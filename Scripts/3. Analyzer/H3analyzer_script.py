import sqlite3
import numpy as np
import os

# Map Ranks to Numbers
RANK_MAP = {
    'IRON': 0, 'BRONZE': 4, 'SILVER': 8, 'GOLD': 12, 
    'PLATINUM': 16, 'EMERALD': 20, 'DIAMOND': 24, 'MASTER': 28
}
DIV_MAP = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

def get_numerical_rank(tier, rank):
    if tier == "UNRANKED" or tier not in RANK_MAP: return None
    return RANK_MAP[tier] + DIV_MAP.get(rank, 0)

def analyze_h3_predictability(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"--- 📈 Analyzing H3 Predictability: {db_path.upper()} ---")
    cursor.execute("SELECT data FROM matches")
    matches = cursor.fetchall()
    
    correct_predictions = 0
    total_valid_matches = 0

    for row in matches:
        try:
            m_json = row[0].replace("true", "True").replace("false", "False").replace("null", "None")
            data = eval(m_json)
            
            # Team 100 = Blue, Team 200 = Red
            team_ranks = {100: [], 200: []}
            winning_team = None
            
            for p in data['info']['participants']:
                # Get the winner
                if p['win']:
                    winning_team = p['teamId']
                
                # Get their rank from our enriched database
                cursor.execute("SELECT tier, rank FROM players WHERE puuid = ?", (p['puuid'],))
                res = cursor.fetchone()
                if res and res[0] and res[0] != "UNRANKED":
                    num_rank = get_numerical_rank(res[0], res[1])
                    if num_rank is not None:
                        team_ranks[p['teamId']].append(num_rank)

            # Only analyze if we have rank data for most players to ensure accuracy
            if len(team_ranks[100]) >= 4 and len(team_ranks[200]) >= 4:
                blue_avg = sum(team_ranks[100]) / len(team_ranks[100])
                red_avg = sum(team_ranks[200]) / len(team_ranks[200])
                
                if blue_avg == red_avg: continue # Skip perfectly equal matches
                
                predicted_winner = 100 if blue_avg > red_avg else 200
                
                total_valid_matches += 1
                if predicted_winner == winning_team:
                    correct_predictions += 1
                    
        except:
            continue

    if total_valid_matches > 0:
        accuracy = (correct_predictions / total_valid_matches) * 100
        print(f"Total Valid Matches Analyzed: {total_valid_matches:,}")
        print(f"Rank-Based Win Prediction Accuracy: {accuracy:.2f}%")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    analyze_h3_predictability('league_me1.db')
    analyze_h3_predictability('league_euw1.db')