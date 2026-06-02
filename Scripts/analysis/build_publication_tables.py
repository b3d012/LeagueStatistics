import sqlite3
import json
import ast
import math
import os
import sys
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
import pandas as pd

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from league_project_config import get_data_root, get_output_root, get_season_label, resolve_database_path

# Optional statistics imports
try:
    from scipy.stats import ttest_ind, mannwhitneyu
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Optional ML imports
try:
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# =========================
# CONFIG
# =========================

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = get_data_root()
SEASON_LABEL = get_season_label("current")

DATABASES = {
    "ME1": resolve_database_path("me1", DATA_DIR),
    "EUW1": resolve_database_path("euw1", DATA_DIR)
}

OUTPUT_DIR = get_output_root()
OUTPUT_DIR.mkdir(exist_ok=True)

MIN_ROLE_HISTORY = 3
MIN_RANKED_PLAYERS_PER_MATCH = 8

# Full visible rank scale
# This fixes the current limitation where MASTER+ may not be mapped fully.
RANK_MAP = {
    "IRON": 0,
    "BRONZE": 4,
    "SILVER": 8,
    "GOLD": 12,
    "PLATINUM": 16,
    "EMERALD": 20,
    "DIAMOND": 24,
    "MASTER": 28,
    "GRANDMASTER": 32,
    "CHALLENGER": 36
}

DIV_MAP = {
    "IV": 0,
    "III": 1,
    "II": 2,
    "I": 3
}


# =========================
# HELPERS
# =========================

def safe_parse_match(raw_text):
    """
    Parses match JSON safely.
    First tries json.loads().
    If the database contains Python-style strings, falls back to ast.literal_eval().
    """
    if raw_text is None:
        return None

    try:
        return json.loads(raw_text)
    except Exception:
        pass

    try:
        cleaned = (
            raw_text
            .replace("true", "True")
            .replace("false", "False")
            .replace("null", "None")
        )
        return ast.literal_eval(cleaned)
    except Exception:
        return None


def numerical_rank(tier, division):
    if tier is None:
        return None

    tier = str(tier).upper()

    if tier == "UNRANKED" or tier not in RANK_MAP:
        return None

    # MASTER, GRANDMASTER, CHALLENGER usually do not use I/II/III/IV divisions.
    if tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return RANK_MAP[tier]

    return RANK_MAP[tier] + DIV_MAP.get(str(division).upper(), 0)


def get_patch(game_version):
    """
    Converts something like 15.24.XXXXX into 15.24.
    """
    if not game_version:
        return "UNKNOWN"

    parts = str(game_version).split(".")
    if len(parts) >= 2:
        return parts[0] + "." + parts[1]

    return str(game_version)


def rank_gap_bin(gap):
    if gap < 0.5:
        return "0.00-0.49"
    elif gap < 1.0:
        return "0.50-0.99"
    elif gap < 1.5:
        return "1.00-1.49"
    elif gap < 2.0:
        return "1.50-1.99"
    elif gap < 3.0:
        return "2.00-2.99"
    elif gap < 4.0:
        return "3.00-3.99"
    else:
        return "4.00+"


def cohen_d(x, y):
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    nx = len(x)
    ny = len(y)

    if nx < 2 or ny < 2:
        return np.nan

    pooled_sd = math.sqrt(
        ((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1))
        / (nx + ny - 2)
    )

    if pooled_sd == 0:
        return np.nan

    return (np.mean(x) - np.mean(y)) / pooled_sd


def mean_diff_ci(x, y):
    """
    95% confidence interval for difference in means.
    Uses normal approximation, acceptable here because sample size is huge.
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    mean_diff = np.mean(x) - np.mean(y)

    se = math.sqrt((np.var(x, ddof=1) / len(x)) + (np.var(y, ddof=1) / len(y)))
    lower = mean_diff - 1.96 * se
    upper = mean_diff + 1.96 * se

    return mean_diff, lower, upper


# =========================
# LOAD DATABASE
# =========================

def load_players(cursor):
    """
    Loads player ranks once to avoid millions of repeated SQL queries.
    """
    player_rank = {}

    cursor.execute("SELECT puuid, tier, rank, lp FROM players")
    rows = cursor.fetchall()

    for puuid, tier, division, lp in rows:
        player_rank[puuid] = {
            "tier": tier,
            "rank": division,
            "lp": lp,
            "rank_value": numerical_rank(tier, division)
        }

    return player_rank


def build_role_map(matches):
    """
    Builds observed main role map.
    This is a proxy for role preference, not confirmed Riot autofill.
    """
    role_history = defaultdict(list)

    for match in matches:
        info = match.get("info", {})
        for p in info.get("participants", []):
            puuid = p.get("puuid")
            role = p.get("teamPosition")

            if puuid and role:
                role_history[puuid].append(role)

    main_role_map = {}

    for puuid, roles in role_history.items():
        if len(roles) >= MIN_ROLE_HISTORY:
            main_role_map[puuid] = Counter(roles).most_common(1)[0][0]

    return main_role_map


def extract_match_features(region, db_path):
    print(f"\n=== Loading {region}: {db_path} ===")

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return [], {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    player_rank = load_players(cursor)

    cursor.execute("SELECT match_id, data FROM matches")
    raw_matches = cursor.fetchall()

    matches = []
    for match_id, raw_text in raw_matches:
        parsed = safe_parse_match(raw_text)
        if parsed is not None:
            parsed["_match_id"] = match_id
            matches.append(parsed)

    print(f"{region}: Parsed {len(matches):,} matches")

    main_role_map = build_role_map(matches)
    print(f"{region}: Built role map for {len(main_role_map):,} players")

    feature_rows = []

    for match in matches:
        info = match.get("info", {})
        participants = info.get("participants", [])

        if len(participants) < 10:
            continue

        match_id = match.get("_match_id")
        game_version = info.get("gameVersion", "UNKNOWN")
        patch = get_patch(game_version)

        timestamp_ms = info.get("gameStartTimestamp")
        if timestamp_ms:
            # UTC hour
            utc_hour = pd.to_datetime(timestamp_ms, unit="ms", utc=True).hour

            # Gulf Standard Time, UTC+4
            gst_hour = (utc_hour + 4) % 24
        else:
            utc_hour = np.nan
            gst_hour = np.nan

        team_ranks = {100: [], 200: []}
        team_levels = {100: [], 200: []}
        team_role_deviation = {100: 0, 200: 0}
        all_ranks = []

        winning_team = None

        for p in participants:
            team_id = p.get("teamId")
            puuid = p.get("puuid")

            if p.get("win") is True:
                winning_team = team_id

            level = p.get("summonerLevel")
            if level is not None and team_id in team_levels:
                team_levels[team_id].append(level)

            if puuid in player_rank:
                rank_value = player_rank[puuid]["rank_value"]
                if rank_value is not None and team_id in team_ranks:
                    team_ranks[team_id].append(rank_value)
                    all_ranks.append(rank_value)

            actual_role = p.get("teamPosition")
            if puuid in main_role_map and actual_role:
                if actual_role != main_role_map[puuid] and team_id in team_role_deviation:
                    team_role_deviation[team_id] += 1

        if winning_team not in [100, 200]:
            continue

        if len(team_ranks[100]) < 4 or len(team_ranks[200]) < 4:
            continue

        if len(all_ranks) < MIN_RANKED_PLAYERS_PER_MATCH:
            continue

        blue_avg_rank = np.mean(team_ranks[100])
        red_avg_rank = np.mean(team_ranks[200])

        blue_rank_std = np.std(team_ranks[100])
        red_rank_std = np.std(team_ranks[200])

        blue_avg_level = np.mean(team_levels[100]) if team_levels[100] else np.nan
        red_avg_level = np.mean(team_levels[200]) if team_levels[200] else np.nan

        rank_diff_blue_minus_red = blue_avg_rank - red_avg_rank
        abs_team_rank_gap = abs(rank_diff_blue_minus_red)

        if rank_diff_blue_minus_red > 0:
            higher_ranked_team = 100
        elif rank_diff_blue_minus_red < 0:
            higher_ranked_team = 200
        else:
            higher_ranked_team = None

        if higher_ranked_team is None:
            higher_ranked_team_win = np.nan
        else:
            higher_ranked_team_win = 1 if winning_team == higher_ranked_team else 0

        blue_win = 1 if winning_team == 100 else 0

        row = {
            "region": region,
            "match_id": match_id,
            "patch": patch,
            "utc_hour": utc_hour,
            "gst_hour": gst_hour,

            "rank_variance": np.std(all_ranks),
            "ranked_players_count": len(all_ranks),

            "blue_avg_rank": blue_avg_rank,
            "red_avg_rank": red_avg_rank,
            "rank_diff_blue_minus_red": rank_diff_blue_minus_red,
            "abs_team_rank_gap": abs_team_rank_gap,
            "rank_gap_bin": rank_gap_bin(abs_team_rank_gap),

            "blue_rank_std": blue_rank_std,
            "red_rank_std": red_rank_std,
            "rank_std_diff_blue_minus_red": blue_rank_std - red_rank_std,

            "blue_role_deviation_count": team_role_deviation[100],
            "red_role_deviation_count": team_role_deviation[200],
            "role_deviation_diff_blue_minus_red": team_role_deviation[100] - team_role_deviation[200],
            "total_role_deviation_count": team_role_deviation[100] + team_role_deviation[200],

            "blue_avg_level": blue_avg_level,
            "red_avg_level": red_avg_level,
            "level_diff_blue_minus_red": blue_avg_level - red_avg_level,

            "winning_team": winning_team,
            "blue_win": blue_win,
            "higher_ranked_team": higher_ranked_team,
            "higher_ranked_team_win": higher_ranked_team_win
        }

        feature_rows.append(row)

    conn.close()

    summary = {
        "region": region,
        "database": db_path,
        "raw_matches_in_db": len(raw_matches),
        "parsed_matches": len(matches),
        "valid_feature_matches": len(feature_rows),
        "players_in_rank_table": len(player_rank),
        "players_with_observed_main_role": len(main_role_map)
    }

    print(f"{region}: Extracted {len(feature_rows):,} valid feature rows")

    return feature_rows, summary


# =========================
# ANALYSIS TABLES
# =========================

def make_dataset_summary(summaries):
    df = pd.DataFrame(summaries)
    out = OUTPUT_DIR / "table_1_dataset_summary.csv"
    df.to_csv(out, index=False)
    print(f"Saved: {out}")
    return df


def make_h1_effect_size_table(features_df):
    me = features_df.loc[features_df["region"] == "ME1", "rank_variance"].dropna().values
    euw = features_df.loc[features_df["region"] == "EUW1", "rank_variance"].dropna().values

    mean_diff, ci_low, ci_high = mean_diff_ci(me, euw)

    row = {
        "metric": "Rank variance",
        "ME1_n": len(me),
        "EUW1_n": len(euw),
        "ME1_mean": np.mean(me),
        "EUW1_mean": np.mean(euw),
        "mean_difference_ME1_minus_EUW1": mean_diff,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "cohen_d": cohen_d(me, euw),
        "ME1_median": np.median(me),
        "EUW1_median": np.median(euw),
        "ME1_std": np.std(me, ddof=1),
        "EUW1_std": np.std(euw, ddof=1)
    }

    if SCIPY_AVAILABLE:
        t_stat, t_p = ttest_ind(me, euw, equal_var=False)
        u_stat, u_p = mannwhitneyu(me, euw, alternative="two-sided")

        row["welch_t_statistic"] = t_stat
        row["welch_t_p_value"] = t_p
        row["mannwhitney_u_statistic"] = u_stat
        row["mannwhitney_u_p_value"] = u_p
    else:
        row["welch_t_statistic"] = "scipy_not_installed"
        row["welch_t_p_value"] = "scipy_not_installed"
        row["mannwhitney_u_statistic"] = "scipy_not_installed"
        row["mannwhitney_u_p_value"] = "scipy_not_installed"

    df = pd.DataFrame([row])
    out = OUTPUT_DIR / "table_2_h1_effect_size_rank_variance.csv"
    df.to_csv(out, index=False)
    print(f"Saved: {out}")
    return df


def make_outcome_fairness_bins(features_df):
    valid = features_df.dropna(subset=["higher_ranked_team_win"]).copy()

    grouped = (
        valid
        .groupby(["region", "rank_gap_bin"])
        .agg(
            matches=("match_id", "count"),
            avg_abs_team_rank_gap=("abs_team_rank_gap", "mean"),
            higher_ranked_team_win_rate=("higher_ranked_team_win", "mean"),
            avg_rank_variance=("rank_variance", "mean"),
            avg_role_deviation_count=("total_role_deviation_count", "mean")
        )
        .reset_index()
    )

    grouped["higher_ranked_team_win_rate_percent"] = grouped["higher_ranked_team_win_rate"] * 100
    grouped["deviation_from_50_percent"] = grouped["higher_ranked_team_win_rate_percent"] - 50

    order = ["0.00-0.49", "0.50-0.99", "1.00-1.49", "1.50-1.99", "2.00-2.99", "3.00-3.99", "4.00+"]
    grouped["rank_gap_bin"] = pd.Categorical(grouped["rank_gap_bin"], categories=order, ordered=True)
    grouped = grouped.sort_values(["region", "rank_gap_bin"])

    out = OUTPUT_DIR / "table_3_outcome_fairness_by_team_rank_gap.csv"
    grouped.to_csv(out, index=False)
    print(f"Saved: {out}")
    return grouped


def make_patch_control_table(features_df):
    grouped = (
        features_df
        .groupby(["region", "patch"])
        .agg(
            matches=("match_id", "count"),
            avg_rank_variance=("rank_variance", "mean"),
            median_rank_variance=("rank_variance", "median"),
            higher_ranked_team_win_rate=("higher_ranked_team_win", "mean"),
            avg_abs_team_rank_gap=("abs_team_rank_gap", "mean"),
            avg_role_deviation_count=("total_role_deviation_count", "mean")
        )
        .reset_index()
    )

    grouped["higher_ranked_team_win_rate_percent"] = grouped["higher_ranked_team_win_rate"] * 100
    grouped = grouped.sort_values(["region", "patch"])

    out = OUTPUT_DIR / "table_4_patch_control_summary.csv"
    grouped.to_csv(out, index=False)
    print(f"Saved: {out}")
    return grouped


def make_temporal_peak_offpeak_table(features_df):
    df = features_df.copy()

    # Using GST because ME server audience is Gulf-based.
    # Adjust this in the paper if you decide to report UTC instead.
    def bucket_hour(hour):
        if pd.isna(hour):
            return "UNKNOWN"
        hour = int(hour)
        if 20 <= hour <= 23:
            return "Peak evening, 20:00-23:00 GST"
        if 6 <= hour <= 9:
            return "Off-peak morning, 06:00-09:00 GST"
        return "Other"

    df["time_bucket_gst"] = df["gst_hour"].apply(bucket_hour)

    grouped = (
        df
        .groupby(["region", "time_bucket_gst"])
        .agg(
            matches=("match_id", "count"),
            avg_rank_variance=("rank_variance", "mean"),
            median_rank_variance=("rank_variance", "median"),
            avg_abs_team_rank_gap=("abs_team_rank_gap", "mean"),
            avg_role_deviation_count=("total_role_deviation_count", "mean")
        )
        .reset_index()
        .sort_values(["region", "time_bucket_gst"])
    )

    out = OUTPUT_DIR / "table_5_temporal_peak_offpeak_gst.csv"
    grouped.to_csv(out, index=False)
    print(f"Saved: {out}")
    return grouped


def make_ml_prediction_tables(features_df):
    if not SKLEARN_AVAILABLE:
        print("Skipping ML prediction tables because scikit-learn is not installed.")
        return None, None

    df = features_df.dropna(subset=[
        "rank_diff_blue_minus_red",
        "rank_std_diff_blue_minus_red",
        "role_deviation_diff_blue_minus_red",
        "level_diff_blue_minus_red",
        "gst_hour",
        "blue_win"
    ]).copy()

    # Cyclical encoding for hour
    df["hour_sin"] = np.sin(2 * np.pi * df["gst_hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["gst_hour"] / 24)

    feature_cols = [
        "rank_diff_blue_minus_red",
        "rank_std_diff_blue_minus_red",
        "role_deviation_diff_blue_minus_red",
        "level_diff_blue_minus_red",
        "hour_sin",
        "hour_cos"
    ]

    results = []
    coefficient_rows = []

    for region_label in ["ME1", "EUW1", "COMBINED"]:
        if region_label == "COMBINED":
            model_df = df.copy()
            model_df["region_me1"] = (model_df["region"] == "ME1").astype(int)
            cols = feature_cols + ["region_me1"]
        else:
            model_df = df[df["region"] == region_label].copy()
            cols = feature_cols

        if len(model_df) < 1000:
            continue

        X = model_df[cols]
        y = model_df["blue_win"].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y
        )

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("logreg", LogisticRegression(max_iter=1000))
        ])

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)

        try:
            auc = roc_auc_score(y_test, y_prob)
        except Exception:
            auc = np.nan

        results.append({
            "model_scope": region_label,
            "n_matches_used": len(model_df),
            "test_size": len(y_test),
            "accuracy": accuracy,
            "roc_auc": auc,
            "features": ", ".join(cols)
        })

        coefs = model.named_steps["logreg"].coef_[0]

        for feature_name, coef_value in zip(cols, coefs):
            coefficient_rows.append({
                "model_scope": region_label,
                "feature": feature_name,
                "coefficient": coef_value
            })

    results_df = pd.DataFrame(results)
    coefs_df = pd.DataFrame(coefficient_rows)

    out1 = OUTPUT_DIR / "table_6_ml_winner_prediction_results.csv"
    out2 = OUTPUT_DIR / "table_7_ml_winner_prediction_coefficients.csv"

    results_df.to_csv(out1, index=False)
    coefs_df.to_csv(out2, index=False)

    print(f"Saved: {out1}")
    print(f"Saved: {out2}")

    return results_df, coefs_df


# =========================
# MAIN
# =========================

def main():
    all_rows = []
    summaries = []

    print("\nStarting publication add-on analysis...")
    print(f"Season label: {SEASON_LABEL}")
    print(f"Using data root: {DATA_DIR}\n")

    for region, db_path in DATABASES.items():
        rows, summary = extract_match_features(region, str(db_path))
        all_rows.extend(rows)
        summaries.append(summary)

    if not all_rows:
        print("No feature rows extracted. Check database paths.")
        return

    features_df = pd.DataFrame(all_rows)

    full_out = OUTPUT_DIR / "all_match_features_publication.csv"
    features_df.to_csv(full_out, index=False)
    print(f"\nSaved full match feature table: {full_out}")

    print("\nGenerating publication tables...")

    make_dataset_summary(summaries)
    make_h1_effect_size_table(features_df)
    make_outcome_fairness_bins(features_df)
    make_patch_control_table(features_df)
    make_temporal_peak_offpeak_table(features_df)
    make_ml_prediction_tables(features_df)

    print("\nDONE.")
    print(f"All outputs saved in: {OUTPUT_DIR.resolve()}")
    print("\nMost important files for the paper:")
    print("1. table_2_h1_effect_size_rank_variance.csv")
    print("2. table_3_outcome_fairness_by_team_rank_gap.csv")
    print("3. table_6_ml_winner_prediction_results.csv")
    print("4. table_7_ml_winner_prediction_coefficients.csv")
    print("5. table_4_patch_control_summary.csv")


if __name__ == "__main__":
    main()
