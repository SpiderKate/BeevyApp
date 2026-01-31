Migration folder

This folder contains records of database migrations performed on this repository.

- `migration_log.txt` contains appended lines for each migration run by `scripts/migrate_db.py`.

How to run the migration script:

1. Activate your virtualenv: `.venv\Scripts\Activate.ps1` (Windows PowerShell)
2. Run the migration: `.venv\Scripts\python.exe scripts\migrate_db.py`

The script will back up the existing `beevy.db` to `beevy.db.bak.<timestamp>` and replace it with the migrated DB. A log entry will be appended to `migrations/migration_log.txt` with details.
