import sqlite3
conn = sqlite3.connect('rooms.db')
cursor = conn.cursor()
cursor.execute("ALTER TABLE rooms ADD COLUMN is_public BOOLEAN DEFAULT FALSE")
conn.commit()
conn.close()