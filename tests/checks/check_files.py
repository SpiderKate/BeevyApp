import sqlite3
import os
from pathlib import Path

conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

# Get all file paths referenced in the database
cursor.execute("""
    SELECT DISTINCT thumbnail_path, preview_path, original_path, examples_path
    FROM art
""")

all_db_files = set()
for row in cursor.fetchall():
    for path in row:
        if path:
            all_db_files.add(path)

print(f"Total unique files in database: {len(all_db_files)}\n")

# Check each upload folder
folders = ['thumbs', 'examples', 'owned', 'original']
upload_root = Path('static/uploads/shop')

for folder in folders:
    folder_path = upload_root / folder
    if not folder_path.exists():
        print(f"❌ {folder}/ does NOT exist")
        continue
    
    # Get all actual files in this folder
    files = list(folder_path.glob('*'))
    file_count = len(files)
    
    # Check how many are referenced in database
    referenced = 0
    orphaned = []
    
    for file_path in files:
        rel_path = str(file_path).replace('\\', '/').replace('static/', '')
        if rel_path in all_db_files:
            referenced += 1
        else:
            orphaned.append(file_path.name)
    
    print(f"📁 {folder}/")
    print(f"   Total files: {file_count}")
    print(f"   Referenced in DB: {referenced}")
    print(f"   Orphaned (not in DB): {len(orphaned)}")
    if orphaned and len(orphaned) <= 5:
        for o in orphaned:
            print(f"      - {o}")
    elif orphaned:
        for o in orphaned[:3]:
            print(f"      - {o}")
        print(f"      ... and {len(orphaned)-3} more")
    print()

# Check art_ownership.source for owned copies
cursor.execute("""
    SELECT DISTINCT source FROM art_ownership WHERE source IS NOT NULL AND source != ''
""")
owned_sources = set()
for row in cursor.fetchall():
    if row[0]:
        owned_sources.add(row[0])

print(f"Files in art_ownership.source (owner copies): {len(owned_sources)}")

conn.close()
