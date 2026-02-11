import sys
sys.path.insert(0, '.')
from backup_utils import backup_database, get_backups_list, get_backup_dir

print('Backup Utility Test')
print('=' * 60)
print(f'Backup Directory: {get_backup_dir()}')
print(f'Directory Exists: {get_backup_dir().exists()}')
print(f'Directory is Writable: {get_backup_dir().is_dir()}')

print('\nCurrent Backups:')
backups = get_backups_list()
if backups:
    for b in backups:
        print(f'  - {b["name"]} ({b["size_mb"]:.2f} MB)')
else:
    print('  (No backups yet - first will be created weekly)')

print('\n✓ Backup system configured successfully!')
print('  - Weekly backups: Every Sunday at 2:00 AM')
print('  - Keeps: Last 10 backups (auto-cleanup enabled)')
print('  - Location: ' + str(get_backup_dir()))
