"""
Backup Script
Archives the current Jarvis Assistant project to a zip file with timestamp
"""
import shutil
import datetime
import os

def backup_project():
    # Source: Current directory
    source_dir = os.getcwd()
    
    # Destination: Desktop/jarvis_backups
    backup_root = os.path.expanduser("~/Desktop/jarvis_backups")
    os.makedirs(backup_root, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"jarvis_assistant_backup_{timestamp}"
    archive_path = os.path.join(backup_root, archive_name)
    
    print(f"📦 Backing up {source_dir}...")
    
    try:
        shutil.make_archive(archive_path, 'zip', source_dir)
        print(f"✅ Success! Backup created at: {archive_path}.zip")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

if __name__ == "__main__":
    backup_project()
