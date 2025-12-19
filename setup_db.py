import sqlite3
conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")
cursor.execute("PRAGMA foreign_keys;")
print(cursor.fetchone())

cursor.execute("DELETE FROM art;")
#cursor.execute("CREATE table users (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(50), surname VARCHAR(50), username VARCHAR(50), email VARCHAR(50), password VARCHAR(100), dob VARCHAR(14));")
#cursor.execute("DROP table art;")
#cursor.execute("CREATE table art (id INTEGER PRIMARY KEY AUTOINCREMENT, title VARCHAR(50) NOT NULL, description VARCHAR(300),tat INT NOT NULL, price INT NOT NULL, type VARCHAR(10) NOT NULL, thumbnail_path VARCHAR, examples_path VARCHAR, slots INT, user_ID INT, FOREIGN KEY(user_ID) REFERENCES users(id));")
#cursor.execute("CREATE table rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, room_ID INT, name VARCHAR(100), password VARCHAR(100), is_public BOOLEAN, user_ID INT, FOREIGN KEY(user_ID) REFERENCES users(id));")
#cursor.execute("""
#    ALTER TABLE users ADD COLUMN social_links TEXT;
#""")


conn.commit()
conn.close()