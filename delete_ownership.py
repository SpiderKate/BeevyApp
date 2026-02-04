import sqlite3

conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

# Check current count
cursor.execute("SELECT COUNT(*) FROM art_ownership")
before = cursor.fetchone()[0]

# Delete all records
cursor.execute("DELETE FROM art_ownership")
conn.commit()

# Check after
cursor.execute("SELECT COUNT(*) FROM art_ownership")
after = cursor.fetchone()[0]

print(f"Deleted {before} records from art_ownership")
print(f"Records remaining: {after}")

conn.close()
