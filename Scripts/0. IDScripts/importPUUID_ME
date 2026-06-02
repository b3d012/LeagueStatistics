import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

conn = sqlite3.connect(str(resolve_database_path('me1', get_data_root())))
conn.execute("INSERT OR IGNORE INTO players (puuid, crawled) VALUES ('zvzfPccpt0aeqXSJnRgerDSs1_g1ojBkpeIKfY5BrbUYYPm_F4HMsvKiPPAA96Wo7fN87w0s2LNuWg', 0)")
conn.commit()
