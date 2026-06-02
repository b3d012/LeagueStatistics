# League Statistics

This project studies competitive fairness and match balance in League of Legends using ranked match data from two regions, `ME1` and `EUW1`.

The repository is set up to support two use cases:

- a public GitHub project page with a clean summary of the current dataset
- a reusable analysis pipeline that can be pointed at newer seasons or fresh data by changing configuration instead of editing code

## Dataset Results

Current snapshot from the archived dataset:

- Regions: `ME1` and `EUW1`
- Observed sample window: `2026-01-20` through `2026-02-17` UTC
- Match count: `104,315` ME1 matches and `129,888` EUW1 matches
- Database schema: `matches(match_id, data)` and `players(puuid, crawled, tier, rank, lp)`

Headline findings from the current snapshot:

- Average match rank variance: `2.66` on ME1 vs `2.17` on EUW1
- Autofill rate: `39.58%` on ME1 vs `21.31%` on EUW1
- Rank-based win prediction accuracy: `61.05%` on ME1 vs `63.09%` on EUW1
- Rank-vs-win correlation is weak in both regions: `r = 0.0259` on ME1 and `r = -0.0205` on EUW1
- Smurf-gap estimate in unfair matches: `13.2` levels on ME1 vs `18.6` levels on EUW1

The supporting snapshot tables and figures live in `outputs_publication_analysis/`.

## Reusable Workflow

The active scripts now read their runtime settings from environment variables instead of hardcoded public tokens or fixed paths.

Required:

- `RIOT_API_KEY`

Useful overrides:

- `LEAGUE_STATS_DATA_ROOT` - where the `league_<platform>.db` files live
- `LEAGUE_STATS_OUTPUT_ROOT` - where analysis outputs are written
- `LEAGUE_STATS_SEASON_LABEL` - label printed in logs
- `LEAGUE_STATS_START_DATE` - optional UTC start date for match collection
- `LEAGUE_STATS_END_DATE` - optional UTC end date for match collection

An example template is in [`.env.example`](./.env.example).

## What The Project Measures

- Rank disparity inside matches
- Autofill and role-deviation behavior
- Win-prediction signals from rank, role, level, and time-of-day features
- Temporal patterns in match quality
- Smurf-like level gaps in unfair matches

## Outputs

Generated snapshot tables and figures live in `outputs_publication_analysis/`.

- `summary_*.csv` files capture the current analysis snapshot
- `Scripts/analysis/build_publication_tables.py` can rebuild the heavier publication tables from the configured database root
- `Scripts/analysis/export_publication_figures.py` turns the snapshot CSVs into charts in `outputs_publication_analysis/figures/`

Recommended figures:

- Rank variance by region
- Autofill rate by region
- Rank-based win prediction accuracy
- Hourly rank variance trends
- Smurf gap by region
- Rank-vs-win correlation

## Reproduce

1. Copy `.env.example` to a local `.env` file and set `RIOT_API_KEY`
2. Set `LEAGUE_STATS_DATA_ROOT` to the folder that contains the active `league_me1.db` and `league_euw1.db` files
3. Run `python Scripts/analysis/build_publication_tables.py`
4. Run `python Scripts/analysis/export_publication_figures.py`

## Repo Layout

- `Scripts/` active source code
- `outputs_publication_analysis/` generated tables and figures
- `archive/university_submission/` ignored local archive for the old submission bundle and raw databases
