# League Statistics

This project studies competitive fairness and match balance in League of Legends using two ranked match databases: `ME1` and `EUW1`.

The repo is organized so the active analysis work is easy to find, while the older university submission material lives under `archive/` and is ignored by Git.

## What This Project Measures

- Rank disparity inside matches
- Autofill and role-deviation behavior
- Win-prediction signals from rank, role, level, and time-of-day features
- Temporal patterns in match quality
- Smurf-like level gaps in unfair matches

## Data Snapshot

- Regions: `ME1` and `EUW1`
- Match count: `104,315` ME1 matches and `129,888` EUW1 matches
- Observed sample window: `2026-01-20` through `2026-02-17` UTC
- Database schema: `matches(match_id, data)` and `players(puuid, crawled, tier, rank, lp)`

The raw `.db`, `.db-wal`, and `.db-shm` files are archived locally under `archive/university_submission/data/` and are excluded from Git history.

## Main Findings

These are the headline results from the current analysis pass:

- Average match rank variance: `2.66` on ME1 vs `2.17` on EUW1
- Autofill rate: `39.58%` on ME1 vs `21.31%` on EUW1
- Rank-based win prediction accuracy: `61.05%` on ME1 vs `63.09%` on EUW1
- Rank-vs-win correlation is weak in both regions: `r = 0.0259` on ME1 and `r = -0.0205` on EUW1
- Smurf-gap estimate in unfair matches: `13.2` levels on ME1 vs `18.6` levels on EUW1

## Outputs

Generated snapshot tables and figures live in `outputs_publication_analysis/`.

- `summary_*.csv` files capture the current analysis snapshot
- `Scripts/3. Analyzer/publication_addon_analysis.py` can rebuild the heavier publication tables from the archived databases
- `Scripts/3. Analyzer/export_publication_figures.py` turns the snapshot CSVs into charts in `outputs_publication_analysis/figures/`

Recommended figures:

- Rank variance by region
- Higher-ranked-team win rate by rank-gap bin
- GST temporal patterns
- ML accuracy and coefficient summaries

## Reproduce

1. Run `python Scripts/3. Analyzer/publication_addon_analysis.py`
2. Run `python Scripts/3. Analyzer/export_publication_figures.py`
3. Open the CSV tables and PNG charts in `outputs_publication_analysis/`

## Repo Layout

- `Scripts/` active source code
- `outputs_publication_analysis/` generated tables and figures
- `archive/university_submission/` ignored local archive for the old submission bundle and raw databases
