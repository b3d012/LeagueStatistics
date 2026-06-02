import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from league_project_config import get_data_root, resolve_database_path

def backup_databases():
    # Define source and destination
    data_root = get_data_root()
    source_files = [
        str(resolve_database_path('me1', data_root)),
        str(resolve_database_path('euw1', data_root)),
    ]
    backup_root = 'Backups'
    
    # Create timestamped folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    target_dir = os.path.join(backup_root, f"Backup_{timestamp}")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    print(f"🛡️ Starting daily backup for {timestamp}...")
    
    for db in source_files:
        if os.path.exists(db):
            file_name = os.path.basename(db)
            shutil.copy2(db, os.path.join(target_dir, file_name))
            print(f"✅ Successfully backed up: {file_name}")
        else:
            print(f"⚠ Warning: {db} not found. Skipping.")

    print(f"✨ Backup complete. You can now refresh your RGAPI key safely.")

if __name__ == "__main__":
    backup_databases()
