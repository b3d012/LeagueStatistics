import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

conn = sqlite3.connect(str(resolve_database_path('euw1', get_data_root())))
conn.execute("INSERT OR IGNORE INTO players (puuid, crawled) VALUES ('K3m8Y1g0x0CE1bBNDhhIehTZazmgVNUNl0jTU6tYwn7lg4yMc2rgitvHRcyAqUhLLfhF-EArGWRQMw', 0)")
conn.commit()
