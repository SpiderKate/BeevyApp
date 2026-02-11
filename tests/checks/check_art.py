import sqlite3

conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

# Count art records
cursor.execute("SELECT COUNT(*) FROM art")
art_count = cursor.fetchone()[0]
print(f"Total art records in database: {art_count}\n")

# Show all art with their file paths
cursor.execute("""
    SELECT id, title, thumbnail_path, preview_path, original_path, is_active
    FROM art
    LIMIT 20
""")

print("Sample art records:")
for row in cursor.fetchall():
    art_id, title, thumb, preview, original, is_active = row
    active_str = "✓ ACTIVE" if is_active else "✗ INACTIVE"
    print(f"ID {art_id}: {title} [{active_str}]")
    print(f"  thumb: {thumb}")
    print(f"  preview: {preview}")
    print(f"  original: {original}")
    print()

conn.close()
