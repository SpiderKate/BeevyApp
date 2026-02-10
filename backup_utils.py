"""
Database backup utility module
Handles backing up the database to the Documents/BeevyApp/backup folder
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

def get_backup_dir():
    """Get the backup directory path, creating it if it doesn't exist"""
    backup_dir = Path.home() / "Documents" / "BeevyApp" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def backup_database(db_path='beevy.db', backup_name=None):
    """
    Backup the database to Documents/BeevyApp/backup/
    
    Args:
        db_path: Path to the database file (default: beevy.db)
        backup_name: Custom backup filename (default: beevy.db.bak.{timestamp})
    
    Returns:
        Tuple of (success: bool, backup_path: str, message: str)
    """
    try:
        # Check if database exists
        if not os.path.exists(db_path):
            return False, None, f"Database file not found: {db_path}"
        
        # Get backup directory
        backup_dir = get_backup_dir()
        
        # Generate backup filename if not provided
        if backup_name is None:
            ts = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_name = f'beevy.db.bak.{ts}'
        
        backup_path = backup_dir / backup_name
        
        # Create backup
        shutil.copy2(db_path, str(backup_path))
        
        message = f"Database backed up to: {backup_path}"
        return True, str(backup_path), message
    
    except Exception as e:
        return False, None, f"Backup failed: {str(e)}"

def get_backups_list():
    """Get a list of all backups in the backup directory"""
    try:
        backup_dir = get_backup_dir()
        backups = sorted(backup_dir.glob('beevy.db.bak.*'), reverse=True)
        return [{'name': b.name, 'path': str(b), 'size_mb': b.stat().st_size / (1024*1024)} 
                for b in backups]
    except Exception as e:
        return []

def cleanup_old_backups(keep_count=10):
    """
    Remove old backups, keeping only the most recent ones
    
    Args:
        keep_count: Number of backups to keep (default: 10)
    
    Returns:
        Tuple of (removed_count: int, message: str)
    """
    try:
        backup_dir = get_backup_dir()
        backups = sorted(backup_dir.glob('beevy.db.bak.*'), reverse=True)
        
        removed_count = 0
        for backup_file in backups[keep_count:]:
            backup_file.unlink()
            removed_count += 1
        
        message = f"Cleaned up {removed_count} old backups (keeping {keep_count})"
        return removed_count, message
    
    except Exception as e:
        return 0, f"Cleanup failed: {str(e)}"
