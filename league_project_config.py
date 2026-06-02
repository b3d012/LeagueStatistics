from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARCHIVE_DATA_ROOT = ROOT / "archive" / "university_submission" / "data"
DEFAULT_DATA_ROOT = ARCHIVE_DATA_ROOT if ARCHIVE_DATA_ROOT.exists() else ROOT


def require_riot_api_key(env_var: str = "RIOT_API_KEY") -> str:
    key = os.getenv(env_var)
    if not key:
        raise RuntimeError(
            f"{env_var} is not set. Create a local environment variable or .env file "
            "with your Riot API key before running the crawler or enrichment scripts."
        )
    return key


def get_data_root() -> Path:
    value = os.getenv("LEAGUE_STATS_DATA_ROOT")
    if value:
        return Path(value).expanduser().resolve()
    return DEFAULT_DATA_ROOT


def get_output_root() -> Path:
    value = os.getenv("LEAGUE_STATS_OUTPUT_ROOT")
    if value:
        return Path(value).expanduser().resolve()
    return ROOT / "outputs_publication_analysis"


def get_season_label(default: str = "current") -> str:
    return os.getenv("LEAGUE_STATS_SEASON_LABEL", default)


def get_date_window() -> tuple[str | None, str | None]:
    return os.getenv("LEAGUE_STATS_START_DATE"), os.getenv("LEAGUE_STATS_END_DATE")


def resolve_database_path(platform: str, data_root: Path | None = None) -> Path:
    root = data_root if data_root is not None else get_data_root()
    return Path(root) / f"league_{platform}.db"


def parse_date_to_unix_ms(date_text: str, *, end_of_day: bool = False) -> int:
    if not date_text:
        raise ValueError("date_text is required")

    parsed = datetime.fromisoformat(date_text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end_of_day and parsed.time() == datetime.min.time():
        parsed = parsed + timedelta(days=1) - timedelta(milliseconds=1)
    return int(parsed.timestamp() * 1000)

