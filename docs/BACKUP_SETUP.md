# Database Backup Configuration

## Setup Complete ✓

Your database backup system is now configured. Here's what was changed:

## Backup Location

**New location**: `C:\Users\{YourUsername}\Documents\BeevyApp\backup\`

All future backups will automatically go to this folder instead of the project root.

## How It Works

### 1. **Automatic Weekly Backups**
   - **Runs**: Every Sunday at 2:00 AM
   - **Automatically**: Keeps the last 10 backups
   - **Older backups**: Automatically deleted to save space

### 2. **Manual Backups** (For developers)
   ```python
   from backup_utils import backup_database
   
   success, path, message = backup_database()
   if success:
       print(f"Backup created at: {path}")
   ```

### 3. **Backup Files**
   Files are named: `beevy.db.bak.20260207140230` (timestamp format)
   
   Example:
   ```
   C:\Users\{Your User}\Documents\BeevyApp\backup\
   ├── beevy.db.bak.20260207140230
   ├── beevy.db.bak.20260131161431
   └── beevy.db.bak.20260131155320
   ```

## Files Changed

### New Files
- **`backup_utils.py`** - Backup utility module with functions:
  - `backup_database()` - Creates a backup
  - `get_backups_list()` - Lists all backups
  - `cleanup_old_backups()` - Removes old backups

### Modified Files

1. **`app.py`**
   - Added APScheduler import
   - Added weekly backup job configuration
   - Scheduler initializes on first app request
   - Runs every Sunday at 2 AM

2. **`scripts/migrate_db.py`**
   - Updated to save backups to `Documents/BeevyApp/backup/`
   - Migration log now shows full backup path

3. **`requirements.txt`**
   - Added `Flask-APScheduler==1.13.1`

## Old Backups

The existing backup files in your project root (`beevy.db.bak.20260131*`) are still there. They're protected from accidental deletion. You can manually move or delete them if you want to clean up the project folder:

```powershell
# View them
Get-ChildItem -Path "c:\path\to\BeevyApp" -Filter "beevy.db.bak.*"

# Delete them (optional)
Remove-Item -Path "c:\path\to\BeevyApp\beevy.db.bak.*"
```

## Backup Utilities

The `backup_utils.py` module provides these functions:

### `backup_database(db_path='beevy.db', backup_name=None)`
Creates a backup of your database.
```python
success, path, message = backup_database()
```

### `get_backups_list()`
Returns list of all backups with their sizes.
```python
backups = get_backups_list()
for backup in backups:
    print(f"{backup['name']} - {backup['size_mb']:.2f} MB")
```

### `cleanup_old_backups(keep_count=10)`
Removes old backups, keeping only the N most recent.
```python
removed, message = cleanup_old_backups(keep_count=5)
```

## Testing the Backup System

To test if everything works:

```python
# In Python shell or script:
from backup_utils import backup_database, get_backups_list

# Create a backup
success, path, msg = backup_database()
print(f"Success: {success}")
print(f"Path: {path}")

# List all backups
backups = get_backups_list()
for b in backups:
    print(f"- {b['name']} ({b['size_mb']:.2f} MB)")
```

## Scheduler Details

The APScheduler is configured with:
- **Trigger**: Cron expression (every Sunday at 2 AM)
- **Job ID**: `weekly_backup`
- **Timezone**: Uses system timezone
- **Persistence**: Runs automatically when app starts

### When Scheduler Activates
The scheduler starts on the first HTTP request after the app launches. You'll see this in the console:

```
 * Running on http://127.0.0.1:5000
 * APScheduler started
```

## Logs

Backup logs are printed to stderr and include:
```
✓ Weekly backup completed: Database backed up to: C:\Users\...\Documents\BeevyApp\backup\beevy.db.bak.20260207140230
✓ Cleaned up 0 old backups (keeping 10)
```

## Storage Savings

- **Database size**: ~1-2 MB (typical SQLite)
- **Backup folder with 10 backups**: ~10-20 MB 
- **Retention**: 10 latest backups automatically kept
- **Auto cleanup**: Prevents unlimited disk use

## Modifying Backup Schedule

To change when backups run, edit `app.py` and modify the `@scheduler.scheduled_job` parameters:

```python
scheduler.add_job(
    func=weekly_backup_job,
    trigger='cron',
    day_of_week='sun',    # 0=Monday, 6=Sunday
    hour=2,               # Hour (0-23)
    minute=0,             # Minute (0-59)
    id='weekly_backup',
    name='Weekly Database Backup'
)
```

Examples:
```python
# Daily at 3 AM
day_of_week='*', hour=3, minute=0

# Every Monday at 6 PM  
day_of_week='mon', hour=18, minute=0

# Every 6 hours
trigger='interval', hours=6

# Every weekday at 9 AM
day_of_week='mon-fri', hour=9, minute=0
```

## Troubleshooting

### Scheduler not running?
Check that:
1. Flask app has received at least one HTTP request
2. Port 5000 is not blocked
3. APScheduler is installed: `pip list | findstr apscheduler`

### Backup not creating?
Check:
1. Database file `beevy.db` exists in project root
2. Documents\BeevyApp\backup\ folder is writable
3. Check stderr output for error messages

### "Database is locked" error?
Your app is running and database is in use. The backup will retry next week or you can:
```python
# Manually backup after ensuring app isn't using DB
from backup_utils import backup_database
backup_database()
```

## Summary

✓ Backups go to: `Documents\BeevyApp\backup\`
✓ Weekly automatic backups: Every Sunday at 2 AM
✓ Auto-cleanup: Keeps last 10 backups
✓ Manual backup: Available via Python API
✓ Dependency: Flask-APScheduler installed
