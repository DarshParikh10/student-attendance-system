import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES students (id)
)
''')

cur.executemany('INSERT INTO students (name) VALUES (?)', [
    ("Darsh",),
    ("Dvij",),
    ("Rishabh",),
    ("Saloni",),
    ("Janu",),
    ("Virali",),
    ("Tithi",),
    ("Shivam",),
    ("Arya",)
])

conn.commit()
conn.close()
print("Database initialized.")
