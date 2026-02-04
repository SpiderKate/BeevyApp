import sqlite3

conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

# Check how many files reference originals folder
cursor.execute("SELECT COUNT(*) FROM art WHERE thumbnail_path LIKE '%originals%' OR preview_path LIKE '%originals%' OR original_path LIKE '%originals%'")
count = cursor.fetchone()[0]

print(f"Files referencing originals folder: {count}")

# Show what files exist in original/ folder but not in database
cursor.execute("SELECT thumbnail_path, preview_path, original_path FROM art")
all_files = cursor.fetchall()

all_paths = set()
for row in all_files:
    for path in row:
        if path:
            all_paths.add(path)

print(f"\nTotal unique file paths in database: {len(all_paths)}")

conn.close()
