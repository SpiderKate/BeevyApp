import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        surname TEXT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        dob TEXT NOT NULL
)
''') 
conn.commit()
conn.close()