import sqlite3
conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")
cursor.execute("PRAGMA foreign_keys;")
print(cursor.fetchone())

cursor.execute("CREATE table users (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(50), surname VARCHAR(50), username VARCHAR(50), email VARCHAR(50), password VARCHAR(100), dob VARCHAR(14));")
cursor.execute("CREATE table art (id INTEGER PRIMARY KEY AUTOINCREMENT, info VARCHAR(300),tat INT, price INT, type VARCHAR(10), user_ID INT, FOREIGN KEY(user_ID) REFERENCES users(id));")
cursor.execute("CREATE table rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, room_ID INT, name VARCHAR(100), password VARCHAR(100), is_public BOOLEAN, user_ID INT, FOREIGN KEY(user_ID) REFERENCES users(id));")

conn.commit()
conn.close()