import shutil
import os
from datetime import datetime

def backup_databases():
    # Define source and destination
    source_files = ['league_me1.db', 'league_euw1.db']
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