import sqlite3
conn = sqlite3.connect('rooms.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM rooms;")
print(cursor.fetchall())
conn.close()